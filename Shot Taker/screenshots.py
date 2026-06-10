import time
import threading
import json

try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Prevent corner-triggered crashes
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


# =========================
# LOAD SETTINGS
# =========================
def load_settings():
    try:
        with open("data/settings.json", "r") as f:
            return json.load(f)
    except:
        return {}


# =========================
# STEAM HOTKEY (BACKUP MODE)
# Only Steam — Epic/GOG removed from hotkey system
# =========================
DEFAULT_STEAM_HOTKEY = "f12"


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
# ACHIEVEMENT BURST
# Handles both direct capture and hotkey modes
# =========================
def fire_achievement_burst(game_name, platform, settings):
    from capture_manager import capture_achievement_burst

    capture_mode = settings.get("capture_mode", "timelapse")
    ach_enabled = settings.get("achievement_screenshots_enabled", False)

    if not ach_enabled:
        return

    print(f"[SHOT] Achievement burst for {game_name}")

    # Direct capture
    capture_achievement_burst(game_name, settings)

    # Also press Steam hotkey if backup mode is on and platform is steam
    if platform == "steam" and settings.get("steam_hotkey_backup", False):
        ach_cfg = settings.get("achievement_burst", {})
        shots = min(10, max(1, int(ach_cfg.get("shots", 7))))
        delay = max(0.5, float(ach_cfg.get("delay", 0.5)))
        for _ in range(shots):
            press_steam_hotkey(settings)
            time.sleep(delay)


# =========================
# MAIN CAPTURE SESSION
# Starts the appropriate capture mode(s) for the active game.
# Called from main.py when a game is detected.
# =========================
def run_capture_session(is_active, game_name, platform, settings):
    capture_mode = settings.get("capture_mode", "timelapse")

    print(f"[SHOT] Starting capture session: mode={capture_mode}, game={game_name}")

    threads = []

    # TimeLapse mode
    if capture_mode in ("timelapse", "hybrid"):
        from capture_manager import run_timelapse_session
        t = threading.Thread(
            target=run_timelapse_session,
            args=(is_active, game_name, settings),
            daemon=True
        )
        threads.append(t)

    # Steam hotkey backup (optional, Steam only)
    if platform == "steam" and settings.get("steam_hotkey_backup", False):
        t = threading.Thread(
            target=_run_steam_hotkey_session,
            args=(is_active, settings),
            daemon=True
        )
        threads.append(t)

    for t in threads:
        t.start()

    # Action Shots runs via change_detector (already started in main.py)
    # No thread needed here — it monitors continuously


def _run_steam_hotkey_session(is_active, settings):
    """Backup Steam hotkey session — runs alongside direct capture."""
    interval_ms = settings.get("interval", 420000)
    first_delay = settings.get("first_delay", 10)
    interval_sec = interval_ms / 1000

    time.sleep(first_delay)
    if not is_active():
        return

    press_steam_hotkey(settings)

    while is_active():
        time.sleep(interval_sec)
        if not is_active():
            break
        press_steam_hotkey(settings)
