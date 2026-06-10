import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import mss
    import numpy as np
    from PIL import Image
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("[CAP] mss/PIL not installed. Direct capture unavailable.")


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
# COUNTER MANAGEMENT
# Per-game, per-type shot counters that persist across sessions
# =========================
COUNTER_FILE = "data/shot_counters.json"
_counter_lock = threading.Lock()


def load_counters():
    try:
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_counters(counters):
    os.makedirs("data", exist_ok=True)
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters, f, indent=2)


def next_counter(game_name, shot_type):
    """Returns the next shot number for this game+type, increments and saves."""
    with _counter_lock:
        counters = load_counters()
        key = f"{game_name}_{shot_type}"
        n = counters.get(key, 0) + 1
        counters[key] = n
        save_counters(counters)
        return n


def reset_counters(game_name=None):
    """Reset counters for a specific game or all games."""
    with _counter_lock:
        if game_name is None:
            save_counters({})
        else:
            counters = load_counters()
            keys_to_remove = [k for k in counters if k.startswith(game_name + "_")]
            for k in keys_to_remove:
                del counters[k]
            save_counters(counters)


# =========================
# SANITISE GAME NAME
# Makes it safe for filenames
# =========================
def sanitise_name(name):
    """
    Sanitises a game name for use in filenames.
    Keeps spaces (Steam convention) — only strips Windows-illegal chars.
    """
    clean = name
    # Remove .exe suffix first
    if clean.lower().endswith('.exe'):
        clean = clean[:-4]
    # Strip only Windows-illegal filename characters
    for ch in '<>:"/\\|?*':
        clean = clean.replace(ch, '_')
    return clean.strip() or "Unknown"


# =========================
# BUILD SAVE PATH
# =========================
def build_save_path(game_name, shot_type, settings):
    """
    shot_type: 'TimeLapse' or 'DynamicShot' or 'Achievement'
    Returns full path to save the screenshot.
    Format: PNG or JPEG based on settings.
    """
    base     = settings.get("screenshot_folder", "screenshots")
    per_game = settings.get("per_game_folders", True)
    fmt      = settings.get("screenshot_format", "png").lower()
    ext      = ".jpg" if fmt == "jpeg" else ".png"

    n = next_counter(game_name, shot_type)
    filename = f"{game_name}_{shot_type}_{n:03d}{ext}"

    if per_game:
        folder = Path(base) / game_name
    else:
        folder = Path(base)

    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


# =========================
# CAPTURE SCREENSHOT
# Captures the primary monitor (or game monitor if detectable)
# =========================
def capture_screenshot(game_name, shot_type, settings):
    if not MSS_AVAILABLE:
        print("[CAP] mss not available — cannot capture directly")
        return None

    try:
        clean_name = sanitise_name(game_name)
        save_path = build_save_path(clean_name, shot_type, settings)

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            fmt = settings.get("screenshot_format", "png").lower()
            if fmt == "jpeg":
                quality = settings.get("jpeg_quality", 90)
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                img.save(save_path, "JPEG", quality=quality, optimize=True)
            else:
                img.save(save_path, "PNG", optimize=True)

        print(f"[CAP] Saved: {os.path.basename(save_path)}")
        return save_path

    except Exception as e:
        print(f"[CAP] Capture error: {e}")
        return None


# =========================
# GENERATE THUMBNAIL
# =========================
def generate_thumbnail(screenshot_path, settings):
    try:
        base = settings.get("screenshot_folder", "screenshots")
        thumb_dir = Path(base) / ".thumbs"
        thumb_dir.mkdir(parents=True, exist_ok=True)

        rel = Path(screenshot_path).relative_to(Path(base))
        thumb_path = thumb_dir / rel.with_suffix(".jpg")
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        img = Image.open(screenshot_path)
        img.thumbnail((400, 225), Image.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(str(thumb_path), "JPEG", quality=82, optimize=True)

        return str(thumb_path)

    except Exception as e:
        print(f"[CAP] Thumbnail error: {e}")
        return None


# =========================
# UPDATE SCREENSHOT STATS
# =========================
def increment_screenshot_count():
    try:
        stats_path = "status/stats.json"
        stats = {}
        try:
            with open(stats_path, "r") as f:
                stats = json.load(f)
        except:
            pass
        stats["screenshots_taken"] = stats.get("screenshots_taken", 0) + 1
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=4)
        # Also increment session counter
        try:
            import state
            state.add_session_shot()
        except:
            pass
    except Exception as e:
        print(f"[CAP] Stats update error: {e}")


# =========================
# TIMELAPSE SESSION
# Captures on a timer interval while game is active
# =========================
def run_timelapse_session(is_active, game_name, settings):
    interval_ms = settings.get("interval", 420000)
    first_delay = settings.get("first_delay", 10)
    interval_sec = interval_ms / 1000

    burst_enabled = settings.get("burst_enabled", False)
    burst_shots = min(10, max(1, int(settings.get("burst_shots", 3))))
    burst_delay = max(0.5, float(settings.get("burst_delay", 0.5)))

    print(f"[CAP] TimeLapse session started for {game_name}")
    time.sleep(first_delay)

    if not is_active():
        return

    def do_capture():
        path = capture_screenshot(game_name, "TimeLapse", settings)
        if path:
            increment_screenshot_count()
            threading.Thread(
                target=generate_thumbnail,
                args=(path, settings),
                daemon=True
            ).start()

    do_capture()

    if burst_enabled:
        for _ in range(burst_shots - 1):
            time.sleep(burst_delay)
            if is_active():
                do_capture()

    while is_active():
        time.sleep(interval_sec)
        if not is_active():
            break
        do_capture()
        if burst_enabled:
            for _ in range(burst_shots - 1):
                time.sleep(burst_delay)
                if is_active():
                    do_capture()

    print(f"[CAP] TimeLapse session ended for {game_name}")


# =========================
# ACHIEVEMENT CAPTURE BURST
# Direct capture version of achievement burst
# =========================
def capture_achievement_burst(game_name, settings):
    ach_cfg = settings.get("achievement_burst", {})
    shots = min(10, max(1, int(ach_cfg.get("shots", 7))))
    delay = max(0.5, float(ach_cfg.get("delay", 0.5)))

    print(f"[CAP] Achievement burst: {shots} shots for {game_name}")

    for i in range(shots):
        path = capture_screenshot(game_name, "Achievement", settings)
        if path:
            increment_screenshot_count()
            threading.Thread(
                target=generate_thumbnail,
                args=(path, settings),
                daemon=True
            ).start()
        if i < shots - 1:
            time.sleep(delay)
