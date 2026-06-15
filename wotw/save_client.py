# ===========================================================================
# save_client.py  —  saving and loading the player's progress.
# ---------------------------------------------------------------------------
# The game can save through a small web API (api.py) if that server happens to
# be running, but normally it just reads/writes a local `saves.json` file.
# Either way the game code only calls load_progress() / save_progress(); this
# module hides the "API first, fall back to file" detail.
#
# A "save record" is a plain dict: which level, where the player is, the timer,
# and which enemies have been defeated.
# ===========================================================================
"""Client the game uses to persist progress through the save API.

Primary path is the FastAPI server (api.py). If the server is not running,
it falls back to reading/writing the same saves.json file the API uses, so
progress is preserved either way.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"   # where the optional API server lives
PLAYER_ID = 1                        # single-player, so always slot 1
_TIMEOUT = 1.0                       # give the API 1s to answer, else give up

# Save next to the source in dev, but to a writable user folder when packaged
# (the PyInstaller bundle itself is read-only).
if getattr(sys, "frozen", False):
    _SAVE_DIR = Path.home() / ".wok_of_the_warrior"
    _SAVE_DIR.mkdir(parents=True, exist_ok=True)
    SAVES_FILE = _SAVE_DIR / "saves.json"
else:
    SAVES_FILE = Path(__file__).parent / "saves.json"


# ----------------------------------------------------------------- HTTP path
# These talk to the api.py server over HTTP. They throw if the server is down,
# and the public functions below catch that and fall back to the file.

def _request(method, path, body=None):
    """Send one HTTP request to the API and return the parsed JSON reply."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _api_find():
    """Ask the API for this player's existing save (or None)."""
    saves = _request("GET", "/saves")
    for s in (saves or []):
        if s.get("player_id") == PLAYER_ID:
            return s
    return None


def _api_save(body):
    """Create or update this player's save through the API."""
    target = _api_find()
    if target:                       # already exists -> update it
        _request("PUT", f"/saves/{target['id']}", {
            "current_level": body["current_level"],
            "score": body["score"],
            "position_x": body["position_x"],
            "position_y": body["position_y"],
            "defeated_enemies": body["defeated_enemies"],
            "time_remaining": body["time_remaining"],
        })
    else:                            # no save yet -> create one
        _request("POST", "/saves", body)


# ----------------------------------------------------------------- file path
# These read/write saves.json directly — used when the API server isn't running.

def _file_find():
    """Read this player's save out of saves.json (or None)."""
    if not SAVES_FILE.exists():
        return None
    try:
        data = json.loads(SAVES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None                  # corrupt/unreadable file -> treat as no save
    for s in data.get("saves", {}).values():
        if s.get("player_id") == PLAYER_ID:
            return s
    return None


def _file_save(body):
    """Write this player's save into saves.json (creating the file if needed)."""
    data = {"id_counter": 1, "saves": {}}
    if SAVES_FILE.exists():           # start from existing contents if any
        try:
            data = json.loads(SAVES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Find this player's existing slot, or make a new one.
    saves = data.setdefault("saves", {})
    slot = next((sid for sid, s in saves.items()
                 if s.get("player_id") == PLAYER_ID), None)
    if slot is None:
        slot = str(data.get("id_counter", 1))
        data["id_counter"] = int(slot) + 1

    saves[slot] = {"id": int(slot), **body}
    SAVES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ----------------------------------------------------------------- public API
# These three are the only functions game.py calls.

def load_progress():
    """Return the player's saved record, or None if there is none.

    Tries the API first; if the server is down it reads the local file instead.
    """
    try:
        record = _api_find()
        if record:
            return record
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass  # server down — try the file
    return _file_find()


def save_progress(current_level, position_x, position_y, score=0,
                  defeated_enemies=None, time_remaining=60.0):
    """Persist progress via the API, falling back to the file if it's down."""
    # Bundle everything the game wants to remember into one record.
    body = {
        "player_id": PLAYER_ID,
        "current_level": int(current_level),
        "score": int(score),
        "position_x": float(position_x),
        "position_y": float(position_y),
        "defeated_enemies": list(defeated_enemies or []),
        "time_remaining": float(time_remaining),
    }
    try:
        _api_save(body)
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        _file_save(body)


def save_progress_async(current_level, position_x, position_y, score=0,
                        defeated_enemies=None, time_remaining=60.0):
    """Same as save_progress, but on a background thread.

    Saving touches the network/disk, which can briefly stall; doing it on a
    separate thread keeps the game from stuttering. Used for autosaves.
    """
    threading.Thread(
        target=save_progress,
        args=(current_level, position_x, position_y, score,
              defeated_enemies, time_remaining),
        daemon=True,                 # don't keep the program alive for this
    ).start()
