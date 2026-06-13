"""
ShotTaker — entry point. Starts detection, capture, web server, and the window.
"""

import time
import threading
import os

import config
import scanner
import state
import gamenames
import webserver

from blacklist import load_full_blacklist
from detector import find_game
from app_window import window_manager, start_window

try:
    from screenshots import run_capture_session, manual_hotkey
    print("[INIT] screenshots: OK")
except Exception as e:
    print(f"[INIT] screenshots import failed: {e}")
    def run_capture_session(*a, **k): pass
    manual_hotkey = None

try:
    from achievement_detector import achievement_detector
except Exception as e:
    print(f"[INIT] achievement_detector failed: {e}")
    achievement_detector = None

try:
    from change_detector import change_detector
except Exception as e:
    print(f"[INIT] change_detector failed: {e}")
    change_detector = None


# Shared active-game state for callbacks
_ctx = {"game": None, "platform": None, "name": None}


def game_loop():
    current_game = None
    session_active = threading.Event()

    if achievement_detector:
        try:
            achievement_detector.start(
                is_game_active=lambda: _ctx["game"] is not None,
                get_platform=lambda: _ctx["platform"] or "steam",
                get_game=lambda: _ctx["name"],
                get_settings=lambda: config.settings_for_game(_ctx["game"] or ""),
            )
        except Exception as e:
            print(f"[GAME] Achievement detector start failed: {e}")

    if change_detector:
        try:
            change_detector.start(
                is_game_active=lambda: _ctx["game"] is not None,
                get_game_name=lambda: _ctx["name"],
                get_settings=lambda: config.settings_for_game(_ctx["game"] or ""),
            )
        except Exception as e:
            print(f"[GAME] Change detector start failed: {e}")

    if manual_hotkey:
        try:
            manual_hotkey.start(get_active_game=lambda: _ctx["name"])
        except Exception as e:
            print(f"[GAME] Manual hotkey start failed: {e}")

    print("[GAME] Standing by for a game to launch. GL HF.")

    while True:
        try:
            exe, platform = find_game(scanner.GAME_LIST, load_full_blacklist())

            if exe and exe != current_game:
                if current_game:
                    print(f"[GAME] Swapped lobbies: {current_game} -> {exe}")
                    session_active.clear()
                    time.sleep(0.5)
                else:
                    print(f"[GAME] Game on: {exe} ({platform}) — rolling tape.")

                current_game = exe
                settings = config.settings_for_game(exe)
                name = gamenames.friendly(exe) if settings.get("resolve_game_names", True) else exe

                _ctx.update(game=exe, platform=platform, name=name)
                state.set_active(exe, platform)
                state.write(scanner.GAME_LIST, True)
                window_manager.on_game_detected(exe, platform)

                if achievement_detector:
                    achievement_detector.rescan_folder()

                session_active.set()

                def make_session(cap_exe, cap_name, cap_platform, cap_settings, event):
                    def session():
                        run_capture_session(
                            lambda: current_game == cap_exe and event.is_set(),
                            cap_name, cap_platform, cap_settings,
                        )
                    return session

                threading.Thread(
                    target=make_session(exe, name, platform, settings, session_active),
                    daemon=True,
                ).start()

            elif not exe and current_game:
                print(f"[GAME] GG — {current_game} closed. Session saved.")
                session_active.clear()
                current_game = None
                _ctx.update(game=None, platform=None, name=None)
                state.clear_active()
                state.write(scanner.GAME_LIST, False)
            else:
                state.write(scanner.GAME_LIST, exe is not None)

        except Exception as e:
            print(f"[GAME] Loop error: {e}")

        time.sleep(5)


def command_loop():
    scan_flag = os.path.join(config.COMMANDS_DIR, "scan.flag")
    reload_flag = os.path.join(config.COMMANDS_DIR, "reload.flag")
    while True:
        try:
            if os.path.exists(scan_flag) and os.path.getsize(scan_flag) > 0:
                open(scan_flag, "w").close()
                print("[CMD] Scan triggered.")
                scanner.scan_games()
            if os.path.exists(reload_flag) and os.path.getsize(reload_flag) > 0:
                open(reload_flag, "w").close()
                print("[CMD] Reload triggered.")
        except Exception as e:
            print(f"[CMD] Loop error: {e}")
        time.sleep(2)


def watchdog(threads):
    """Restart any core background thread that dies."""
    while True:
        time.sleep(10)
        for name, spec in threads.items():
            t = spec["thread"]
            if not t.is_alive():
                print(f"[WATCHDOG] Restarting dead thread: {name}")
                nt = threading.Thread(target=spec["target"], daemon=True)
                nt.start()
                spec["thread"] = nt


def _boot_banner():
    v = config.BRAND["version"]
    print("=" * 56)
    print("   S H O T T A K E R   v" + v)
    print("   auto-capture for PC gaming   ::   press start")
    print("=" * 56)


if __name__ == "__main__":
    _boot_banner()
    config.ensure_dirs()

    print("[INIT] Booting up — sweeping your drives for games...")
    scanner.scan_games()
    print(f"[INIT] {len(scanner.GAME_LIST)} games on the roster.")

    core = {
        "game_loop": {"target": game_loop, "thread": threading.Thread(target=game_loop, daemon=True)},
        "command_loop": {"target": command_loop, "thread": threading.Thread(target=command_loop, daemon=True)},
        "web_server": {"target": webserver.run, "thread": threading.Thread(target=webserver.run, daemon=True)},
    }
    for spec in core.values():
        spec["thread"].start()

    threading.Thread(target=watchdog, args=(core,), daemon=True).start()

    time.sleep(1)
    print("[INIT] Loading HUD...")
    start_window()
