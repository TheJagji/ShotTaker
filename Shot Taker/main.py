import time
import threading
import os
import json

import scanner
import webserver
import state

from blacklist import load_full_blacklist
from detector import find_game
from app_window import window_manager, start_window

try:
    from screenshots import run_capture_session, fire_achievement_burst
    print("[INIT] screenshots: OK")
except Exception as e:
    print(f"[INIT] screenshots import failed: {e}")
    def run_capture_session(*a, **k): pass
    def fire_achievement_burst(*a, **k): pass

try:
    from achievement_detector import achievement_detector
    print("[INIT] achievement_detector: OK")
except Exception as e:
    print(f"[INIT] achievement_detector import failed: {e}")
    achievement_detector = None

try:
    from change_detector import change_detector
    print("[INIT] change_detector: OK")
except Exception as e:
    print(f"[INIT] change_detector import failed: {e}")
    change_detector = None


# =========================
# LOAD SETTINGS
# =========================
def load_settings():
    try:
        with open("data/settings.json", "r") as f:
            return json.load(f)
    except:
        return {"interval": 420000, "first_delay": 10}


# =========================
# GAME LOOP
# =========================
def game_loop():

    current_game     = None
    current_platform = None
    session_active   = threading.Event()

    # Start achievement detector
    try:
        if achievement_detector:
            achievement_detector.start(
                is_game_active = lambda: current_game is not None,
                get_platform   = lambda: current_platform or "steam",
                get_settings   = load_settings
            )
            print("[GAME] Achievement detector started OK.")
    except Exception as e:
        print(f"[GAME] Achievement detector start failed: {e}")

    # Start change detector
    try:
        if change_detector:
            change_detector.start(
                is_game_active = lambda: current_game is not None,
                get_game_name  = lambda: current_game,
                get_settings   = load_settings
            )
            print("[GAME] Change detector started OK.")
    except Exception as e:
        print(f"[GAME] Change detector start failed: {e}")

    print("[GAME] Detection loop started.")

    while True:

        try:
            blacklist = load_full_blacklist()
            exe, platform = find_game(scanner.GAME_LIST, blacklist)

            # Game started or switched
            if exe and exe != current_game:

                if current_game:
                    print(f"[GAME] Switched: {current_game} -> {exe}")
                    session_active.clear()
                    time.sleep(0.5)
                else:
                    print(f"[GAME] Started: {exe} ({platform})")

                current_game     = exe
                current_platform = platform

                state.set_active(exe, platform)
                state.write(scanner.GAME_LIST, True)

                # Notify tray + window
                window_manager.on_game_detected(exe, platform)

                # Rescan achievement stats baseline
                if achievement_detector:
                    achievement_detector.rescan_folder()

                # Start capture session
                settings = load_settings()
                session_active.set()

                def make_session(cap_exe, cap_platform, cap_settings, event):
                    def session():
                        run_capture_session(
                            lambda: current_game == cap_exe and event.is_set(),
                            cap_exe,
                            cap_platform,
                            cap_settings
                        )
                    return session

                threading.Thread(
                    target=make_session(exe, platform, settings, session_active),
                    daemon=True
                ).start()

            # Game stopped
            elif not exe and current_game:
                print(f"[GAME] Stopped: {current_game}")
                session_active.clear()
                current_game     = None
                current_platform = None
                state.clear_active()
                state.write(scanner.GAME_LIST, False)

            # No change
            else:
                state.write(scanner.GAME_LIST, exe is not None)

        except Exception as e:
            print(f"[GAME] Loop error: {e}")

        time.sleep(5)


# =========================
# COMMAND LOOP
# =========================
def command_loop():

    while True:

        try:
            scan_flag = "commands/scan.flag"
            if os.path.exists(scan_flag) and os.path.getsize(scan_flag) > 0:
                open(scan_flag, "w").close()
                print("[CMD] Scan triggered.")
                scanner.scan_games()

            reload_flag = "commands/reload.flag"
            if os.path.exists(reload_flag) and os.path.getsize(reload_flag) > 0:
                open(reload_flag, "w").close()
                print("[CMD] Reload triggered.")

        except Exception as e:
            print(f"[CMD] Loop error: {e}")

        time.sleep(2)


# =========================
# ENSURE DIRS
# =========================
def ensure_dirs():
    for d in ["data", "status", "commands", "static"]:
        os.makedirs(d, exist_ok=True)
    for flag in ["commands/scan.flag", "commands/reload.flag"]:
        if not os.path.exists(flag):
            open(flag, "w").close()


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    print("Starting ShotTaker...")

    ensure_dirs()

    print("[INIT] Running initial game scan...")
    scanner.scan_games()
    print(f"[INIT] {len(scanner.GAME_LIST)} games loaded")

    threading.Thread(target=game_loop,    daemon=True).start()
    threading.Thread(target=command_loop, daemon=True).start()

    threading.Thread(
        target=lambda: webserver.run(),
        daemon=True
    ).start()

    time.sleep(1)

    print("[INIT] Opening ShotTaker window...")
    start_window()
