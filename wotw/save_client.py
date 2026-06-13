"""Client the game uses to persist progress through the save API.

Primary path is the FastAPI server (api.py). If the server is not running,
it falls back to reading/writing the same saves.json file the API uses, so
progress is preserved either way.
"""
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
PLAYER_ID = 1
_TIMEOUT = 1.0

# Same file api.py persists to, so HTTP and file fallback stay in sync.
SAVES_FILE = Path(__file__).parent / "saves.json"


# ----------------------------------------------------------------- HTTP path

def _request(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def _api_find():
    saves = _request("GET", "/saves")
    for s in (saves or []):
        if s.get("player_id") == PLAYER_ID:
            return s
    return None


def _api_save(body):
    target = _api_find()
    if target:
        _request("PUT", f"/saves/{target['id']}", {
            "current_level": body["current_level"],
            "score": body["score"],
            "position_x": body["position_x"],
            "position_y": body["position_y"],
            "defeated_enemies": body["defeated_enemies"],
            "time_remaining": body["time_remaining"],
        })
    else:
        _request("POST", "/saves", body)


# ----------------------------------------------------------------- file path

def _file_find():
    if not SAVES_FILE.exists():
        return None
    try:
        data = json.loads(SAVES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for s in data.get("saves", {}).values():
        if s.get("player_id") == PLAYER_ID:
            return s
    return None


def _file_save(body):
    data = {"id_counter": 1, "saves": {}}
    if SAVES_FILE.exists():
        try:
            data = json.loads(SAVES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    saves = data.setdefault("saves", {})
    slot = next((sid for sid, s in saves.items()
                 if s.get("player_id") == PLAYER_ID), None)
    if slot is None:
        slot = str(data.get("id_counter", 1))
        data["id_counter"] = int(slot) + 1

    saves[slot] = {"id": int(slot), **body}
    SAVES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ----------------------------------------------------------------- public API

def load_progress():
    """Return the player's saved record, or None if there is none."""
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
    """Fire-and-forget save so the game loop never blocks on I/O."""
    threading.Thread(
        target=save_progress,
        args=(current_level, position_x, position_y, score,
              defeated_enemies, time_remaining),
        daemon=True,
    ).start()
