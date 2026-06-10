import json
import os
import time

ACTIVE_GAME = ""
ACTIVE_PLATFORM = ""
SESSION_START = 0
SESSION_SHOTS = 0


def set_active(exe, platform=""):
    global ACTIVE_GAME, ACTIVE_PLATFORM, SESSION_START, SESSION_SHOTS
    ACTIVE_GAME = exe
    ACTIVE_PLATFORM = platform
    SESSION_START = time.time()
    SESSION_SHOTS = 0

    os.makedirs("status", exist_ok=True)

    with open("status/active_game.txt", "w") as f:
        f.write(exe)


def clear_active():
    global ACTIVE_GAME, ACTIVE_PLATFORM
    # Save last session before clearing
    if ACTIVE_GAME and SESSION_START:
        _save_last_session()
    ACTIVE_GAME = ""
    ACTIVE_PLATFORM = ""

    try:
        open("status/active_game.txt", "w").close()
    except:
        pass


def _save_last_session():
    import time as t
    session = {
        "game":      ACTIVE_GAME,
        "platform":  ACTIVE_PLATFORM,
        "start":     SESSION_START,
        "end":       t.time(),
        "shots":     SESSION_SHOTS,
        "timestamp": t.strftime("%Y-%m-%d %H:%M", t.localtime(SESSION_START))
    }
    os.makedirs("status", exist_ok=True)
    with open("status/last_session.json", "w") as f:
        json.dump(session, f, indent=2)


def add_session_shot():
    global SESSION_SHOTS
    SESSION_SHOTS += 1


def write(game_list, game_active):
    data = {
        "games": len(game_list),
        "activeGame": ACTIVE_GAME,
        "activePlatform": ACTIVE_PLATFORM,
        "gameActive": game_active
    }

    os.makedirs("status", exist_ok=True)

    with open("status/state.json", "w") as f:
        json.dump(data, f, indent=4)
