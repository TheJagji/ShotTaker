"""
ShotTaker — capture session router, achievement burst, manual hotkey.

run_capture_session() starts the appropriate capture worker(s) for the active
game. Action Shots run via the always-on change_detector (started in main.py).
A global manual hotkey lets the user grab a shot on demand.
"""

import time
import threading
import ctypes

import config

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


DEFAULT_STEAM_HOTKEY = "f12"


# =========================
# STEAM HOTKEY (optional backup)
# =========================
def press_steam_hotkey(settings):
    if not PYAUTOGUI_AVAILABLE:
        return
    key = settings.get("hotkeys", {}).get("steam", DEFAULT_STEAM_HOTKEY)
    if not key or key.lower() in ("none", "disabled", ""):
        return
    parts = [k.strip() for k in key.lower().split("+")]
    try:
        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)
    except Exception as e:
        print(f"[SHOT] Hotkey error: {e}")


# =========================
# ACHIEVEMENT BURST  (game_name now correctly threaded through)
# =========================
def fire_achievement_burst(game_name, platform, settings):
    from capture_manager import capture_achievement_burst

    if not settings.get("achievement_screenshots_enabled", False):
        return
    game_name = game_name or "Achievement"
    print(f"[SHOT] Achievement burst for {game_name} ({platform})")

    capture_achievement_burst(game_name, settings)

    if platform == "steam" and settings.get("steam_hotkey_backup", False):
        ach = settings.get("achievement_burst", {})
        shots = min(15, max(1, int(ach.get("shots", 7))))
        delay = max(0.3, float(ach.get("delay", 0.5)))
        for _ in range(shots):
            press_steam_hotkey(settings)
            time.sleep(delay)


# =========================
# CAPTURE SESSION
# =========================
def run_capture_session(is_active, game_name, platform, settings):
    mode = settings.get("capture_mode", "timelapse")
    print(f"[SHOT] Starting capture session: mode={mode}, game={game_name}")

    threads = []
    if mode in ("timelapse", "hybrid"):
        from capture_manager import run_timelapse_session
        threads.append(threading.Thread(
            target=run_timelapse_session, args=(is_active, game_name, settings), daemon=True))

    if platform == "steam" and settings.get("steam_hotkey_backup", False):
        threads.append(threading.Thread(
            target=_run_steam_hotkey_session, args=(is_active, settings), daemon=True))

    for t in threads:
        t.start()
    # Action Shots run via the always-on change_detector.


def _run_steam_hotkey_session(is_active, settings):
    interval_sec = settings.get("interval", 420000) / 1000.0
    time.sleep(settings.get("first_delay", 10))
    if not is_active():
        return
    press_steam_hotkey(settings)
    while is_active():
        time.sleep(interval_sec)
        if not is_active():
            break
        press_steam_hotkey(settings)


# =========================
# MANUAL CAPTURE HOTKEY  (global, via GetAsyncKeyState)
# =========================
_VK = {f"f{i}": 0x70 + (i - 1) for i in range(1, 25)}  # F1..F24
_VK.update({c: ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz0123456789"})
_MODS = {"ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12}


def _parse_hotkey(spec):
    mods, main = [], None
    for part in (spec or "").lower().split("+"):
        part = part.strip()
        if part in _MODS:
            mods.append(_MODS[part])
        elif part in _VK:
            main = _VK[part]
    return mods, main


def _down(vk):
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


class ManualHotkey:
    def __init__(self):
        self._running = False
        self._get_game = None

    def start(self, get_active_game):
        self._get_game = get_active_game
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("[SHOT] Manual trigger armed — hit your hotkey to snap.")

    def _loop(self):
        from capture_manager import capture_screenshot
        prev = False
        while self._running:
            try:
                settings = config.load_settings()
                if not settings.get("manual_hotkey_enabled", True):
                    prev = False
                    time.sleep(0.4)
                    continue
                mods, main = _parse_hotkey(settings.get("manual_hotkey", "f9"))
                if main is None:
                    time.sleep(0.4)
                    continue
                pressed = _down(main) and all(_down(m) for m in mods)
                if pressed and not prev:
                    game = (self._get_game() if self._get_game else None) or "Manual"
                    print(f"[SHOT] Manual snap — {game}.")
                    capture_screenshot(game, "Manual", settings, reason="manual", gate=False)
                prev = pressed
            except Exception as e:
                print(f"[SHOT] Manual hotkey error: {e}")
            time.sleep(0.05)


manual_hotkey = ManualHotkey()
