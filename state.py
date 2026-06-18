"""
ShotTaker — active-game state, session history, and event log.

Writes status/state.json on every tick, appends finished sessions to
status/sessions.json, logs achievement/capture events to status/events.json,
and records the most recent capture (status/last_capture.json) for UI toasts.
"""

import os
import time
import uuid

import config

ACTIVE_GAME = ""
ACTIVE_PLATFORM = ""
SESSION_START = 0.0
SESSION_SHOTS = 0
SESSION_ID = ""


def session_id():
    return SESSION_ID


def set_active(exe, platform=""):
    global ACTIVE_GAME, ACTIVE_PLATFORM, SESSION_START, SESSION_SHOTS, SESSION_ID
    ACTIVE_GAME = exe
    ACTIVE_PLATFORM = platform
    SESSION_START = time.time()
    SESSION_SHOTS = 0
    SESSION_ID = uuid.uuid4().hex[:12]
    os.makedirs(config.STATUS_DIR, exist_ok=True)
    try:
        with open(config.ACTIVE_FILE, "w", encoding="utf-8") as f:
            f.write(exe)
    except OSError:
        pass


def clear_active():
    global ACTIVE_GAME, ACTIVE_PLATFORM
    if ACTIVE_GAME and SESSION_START:
        _save_last_session()
        _append_session()
    ACTIVE_GAME = ""
    ACTIVE_PLATFORM = ""
    try:
        open(config.ACTIVE_FILE, "w").close()
    except OSError:
        pass


def add_session_shot():
    global SESSION_SHOTS
    SESSION_SHOTS += 1


def _session_record():
    return {
        "id": SESSION_ID,
        "game": ACTIVE_GAME,
        "platform": ACTIVE_PLATFORM,
        "start": SESSION_START,
        "end": time.time(),
        "duration": round(time.time() - SESSION_START),
        "shots": SESSION_SHOTS,
        "timestamp": time.strftime("%Y-%m-%d %H:%M", time.localtime(SESSION_START)),
    }


def _save_last_session():
    config.write_json(config.LASTSESSION_FILE, _session_record())


def _append_session():
    sessions = config.read_json(config.SESSIONS_FILE, []) or []
    sessions.append(_session_record())
    # keep most recent 1000
    sessions = sessions[-1000:]
    config.write_json(config.SESSIONS_FILE, sessions)


def note_capture(path, shot_type):
    """Record the latest capture so the UI can show a toast."""
    config.write_json(config.STATUS_FILE.replace("state.json", "last_capture.json"), {
        "path": path,
        "type": shot_type,
        "ts": time.time(),
    })


def log_event(kind, data=None):
    """Append an event (e.g. achievement) to the event log."""
    events = config.read_json(config.EVENTS_FILE, []) or []
    events.append({
        "kind": kind,
        "game": ACTIVE_GAME,
        "platform": ACTIVE_PLATFORM,
        "session": SESSION_ID,
        "ts": time.time(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data or {},
    })
    config.write_json(config.EVENTS_FILE, events[-2000:])


def write(game_list, game_active):
    config.write_json(config.STATE_FILE, {
        "games": len(game_list),
        "activeGame": ACTIVE_GAME,
        "activePlatform": ACTIVE_PLATFORM,
        "gameActive": game_active,
        "sessionShots": SESSION_SHOTS,
    })
