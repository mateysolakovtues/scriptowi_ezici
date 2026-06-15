# ===========================================================================
# api.py  —  an OPTIONAL little web server for saving games.
# ---------------------------------------------------------------------------
# This is a learning/demo REST API built with FastAPI. The game does NOT need
# it to run (save_client.py falls back to writing saves.json directly), but if
# you start it with:   uvicorn api:app --reload
# then the game will save/load through these HTTP endpoints instead.
#
# It keeps saves in a dict in memory (`fake_db`) and mirrors them to disk so
# they survive a restart. Not a real database — just enough to learn REST.
# ===========================================================================
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Wok of the Warrior - API")

# Saves are persisted here so progress survives a server restart.
SAVES_FILE = Path(__file__).parent / "saves.json"


# --- Request body shapes ----------------------------------------------------
# Pydantic models validate the JSON sent to each endpoint and give nice errors.

class SaveGameCreate(BaseModel):     # body for POST /saves (a brand new save)
    player_id: int
    current_level: int
    score: int
    position_x: float
    position_y: float
    defeated_enemies: list[str] = []
    time_remaining: float = 60.0

class SaveGameUpdate(BaseModel):     # body for PUT /saves/{id} (replace it all)
    current_level: int
    score: int
    position_x: float
    position_y: float
    defeated_enemies: list[str] = []
    time_remaining: float = 60.0

class SaveGamePatch(BaseModel):      # body for PATCH /saves/{id} (tweak a field)
    score: Optional[int] = None
    current_level: Optional[int] = None

# In-memory "database": save_id -> save record. id_counter hands out new ids.
fake_db = {}
id_counter = 1


def _load_db():
    """Populate fake_db / id_counter from disk on startup."""
    global fake_db, id_counter
    if not SAVES_FILE.exists():
        return
    try:
        data = json.loads(SAVES_FILE.read_text(encoding="utf-8"))
        fake_db = {int(k): v for k, v in data.get("saves", {}).items()}
        id_counter = data.get("id_counter", max(fake_db, default=0) + 1)
    except (json.JSONDecodeError, ValueError, OSError):
        fake_db = {}
        id_counter = 1


def _persist_db():
    """Write the whole save store back to disk."""
    payload = {
        "id_counter": id_counter,
        "saves": {str(k): v for k, v in fake_db.items()},
    }
    SAVES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_load_db()   # load any existing saves the moment the server starts


# --- Endpoints (each @app.xxx decorator wires a URL to a function) ----------

@app.post("/sign-in", status_code=200)
def sign_in(credentials: dict):
    """Toy "login": accept the password "123" and hand back a fake token."""
    if credentials.get("password") == "123":
        return {"token": "fake-jwt-token-for-game"}
    raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/saves", status_code=status.HTTP_201_CREATED)
def create_save(save_data: SaveGameCreate):
    """Create a new save and return it (with its new id)."""
    global id_counter
    save_id = id_counter
    fake_db[save_id] = {"id": save_id, **save_data.model_dump()}
    id_counter += 1
    _persist_db()
    return fake_db[save_id]

@app.get("/saves", status_code=200)
def get_all_saves():
    """List every save."""
    return list(fake_db.values())

@app.get("/saves/{save_id}", status_code=200)
def get_save(save_id: int):
    """Fetch one save by id (404 if it doesn't exist)."""
    if save_id not in fake_db:
        raise HTTPException(status_code=404, detail="Save not found")
    return fake_db[save_id]

@app.put("/saves/{save_id}", status_code=200)
def update_entire_save(save_id: int, updated_data: SaveGameUpdate):
    """Replace all the fields of an existing save."""
    if save_id not in fake_db:
        raise HTTPException(status_code=404, detail="Save not found")
    fake_db[save_id].update(updated_data.model_dump())
    _persist_db()
    return fake_db[save_id]

@app.patch("/saves/{save_id}", status_code=200)
def patch_save_attribute(save_id: int, patch_data: SaveGamePatch):
    """Update just one or two fields of a save (e.g. only the score)."""
    if save_id not in fake_db:
        raise HTTPException(status_code=404, detail="Save not found")

    stored_data = fake_db[save_id]
    # exclude_unset=True -> only overwrite fields actually sent in the request.
    update_dict = patch_data.model_dump(exclude_unset=True)
    stored_data.update(update_dict)
    _persist_db()
    return stored_data

@app.delete("/saves/{save_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_save(save_id: int):
    """Delete a save. 204 = success with no body."""
    if save_id not in fake_db:
        raise HTTPException(status_code=404, detail="Save not found")
    del fake_db[save_id]
    _persist_db()
    # 204 responses must carry no body — return a bare Response, not None.
    return Response(status_code=status.HTTP_204_NO_CONTENT)