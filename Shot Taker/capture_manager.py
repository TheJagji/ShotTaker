"""
ShotTaker — core capture engine.

Grabs frames (mss), applies the quality gate (dark / loading / letterbox / dedupe),
saves PNG/JPEG/WebP with optional scaling + watermark, records library metadata,
generates thumbnails, updates stats, and enforces storage guardrails.
"""

import os
import time
import threading
from datetime import datetime
from pathlib import Path

import config
import library

try:
    import frames
    import mss
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    AVAILABLE = frames.AVAILABLE
except Exception as e:  # pragma: no cover
    AVAILABLE = False
    print(f"[CAP] capture deps unavailable: {e}")


# =========================
# COUNTERS  (case-normalised key — fixes duplicate-counter bug)
# =========================
_counter_lock = threading.Lock()
# in-memory reference frame per game for dedupe
_last_keeper = {}


def load_counters():
    return config.read_json(config.COUNTER_FILE, {}) or {}


def save_counters(counters):
    config.write_json(config.COUNTER_FILE, counters)


def next_counter(game_name, shot_type):
    with _counter_lock:
        counters = load_counters()
        key = f"{game_name.lower()}_{shot_type}"
        n = counters.get(key, 0) + 1
        counters[key] = n
        save_counters(counters)
        return n


def reset_counters(game_name=None):
    with _counter_lock:
        if game_name is None:
            save_counters({})
        else:
            counters = load_counters()
            pref = game_name.lower() + "_"
            for k in [k for k in counters if k.lower().startswith(pref)]:
                del counters[k]
            save_counters(counters)


# =========================
# NAMING / PATHS
# =========================
def sanitise_name(name):
    clean = name
    if clean.lower().endswith(".exe"):
        clean = clean[:-4]
    for ch in '<>:"/\\|?*':
        clean = clean.replace(ch, "_")
    return clean.strip() or "Unknown"


def _ext_for(settings):
    fmt = settings.get("screenshot_format", "png").lower()
    return {"jpeg": ".jpg", "jpg": ".jpg", "webp": ".webp"}.get(fmt, ".png")


def build_save_path(game_name, shot_type, settings):
    base = config.get_screenshot_folder(settings)
    per_game = settings.get("per_game_folders", True)
    ext = _ext_for(settings)
    n = next_counter(game_name, shot_type)
    filename = f"{game_name}_{shot_type}_{n:03d}{ext}"
    folder = Path(base) / game_name if per_game else Path(base)
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / filename)


# =========================
# IMAGE PROCESSING
# =========================
def _apply_scale(img, settings):
    scale = int(settings.get("capture_scale", 100) or 100)
    if scale >= 100 or scale <= 0:
        return img
    w, h = img.size
    return img.resize((max(1, w * scale // 100), max(1, h * scale // 100)), Image.LANCZOS)


def _apply_watermark(img, game_name, settings):
    if not settings.get("watermark_enabled", False):
        return img
    try:
        text = settings.get("watermark_text", "{game} - {date}")
        text = text.replace("{game}", game_name).replace(
            "{date}", datetime.now().strftime("%Y-%m-%d %H:%M"))
        draw = ImageDraw.Draw(img)
        w, h = img.size
        size = max(14, h // 45)
        try:
            font = ImageFont.truetype("arialbd.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = w - tw - size, h - th - size
        # shadow + text
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0), font=font)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
    except Exception as e:
        print(f"[CAP] Watermark error: {e}")
    return img


def _save_image(img, path, settings):
    fmt = settings.get("screenshot_format", "png").lower()
    if img.mode in ("RGBA", "P", "LA") and fmt in ("jpeg", "jpg"):
        img = img.convert("RGB")
    if fmt in ("jpeg", "jpg"):
        img.save(path, "JPEG", quality=int(settings.get("jpeg_quality", 90)), optimize=True)
    elif fmt == "webp":
        img.save(path, "WEBP", quality=int(settings.get("webp_quality", 90)), method=4)
    else:
        img.save(path, "PNG", optimize=True)


# =========================
# THUMBNAILS
# =========================
def generate_thumbnail(screenshot_path, settings):
    try:
        base = config.get_screenshot_folder(settings)
        thumb_dir = Path(base) / ".thumbs"
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
# STATS
# =========================
def increment_screenshot_count():
    try:
        stats = config.read_json(config.STATS_FILE, {}) or {}
        stats["screenshots_taken"] = stats.get("screenshots_taken", 0) + 1
        config.write_json(config.STATS_FILE, stats)
        try:
            import state
            state.add_session_shot()
        except Exception:
            pass
    except Exception as e:
        print(f"[CAP] Stats update error: {e}")


# =========================
# CORE CAPTURE
# =========================
def _finalize(img, small, game_name, shot_type, settings, reason):
    """Process + save an already-grabbed frame. Returns the saved path."""
    clean = sanitise_name(game_name)
    img = _apply_scale(img, settings)
    img = _apply_watermark(img, clean, settings)
    path = build_save_path(clean, shot_type, settings)
    _save_image(img, path, settings)

    _last_keeper[game_name.lower()] = small

    w, h = img.size
    library.record(path, game=clean, type=shot_type, reason=reason,
                   ts=time.time(), w=w, h=h, session=_current_session_id())
    increment_screenshot_count()
    try:
        import state
        state.note_capture(path, shot_type)
    except Exception:
        pass

    threading.Thread(target=generate_thumbnail, args=(path, settings), daemon=True).start()
    threading.Thread(target=_enforce, args=(settings, clean), daemon=True).start()
    print(f"[CAP] In the bag: {os.path.basename(path)} ({reason})")
    return path


def _enforce(settings, game_name):
    try:
        base = config.get_screenshot_folder(settings)
        gf = os.path.join(base, game_name) if settings.get("per_game_folders", True) else base
        library.enforce_storage(settings, gf)
    except Exception as e:
        print(f"[CAP] Storage enforce error: {e}")


def _current_session_id():
    try:
        import state
        return state.session_id()
    except Exception:
        return ""


def _blocked_by_privacy(settings):
    if settings.get("capture_paused", False):
        return "paused"
    if settings.get("privacy_guard_enabled", False):
        title = frames.foreground_title().lower()
        for term in settings.get("privacy_apps", []):
            if term and term.lower() in title:
                return "privacy"
    return None


def save_frame(img, small, game_name, shot_type, settings, reason="", gate=True):
    """Save an already-grabbed frame, subject to privacy guard + quality gate. Returns path or None."""
    blocked = _blocked_by_privacy(settings)
    if blocked:
        print(f"[CAP] Blocked ({blocked}) for {game_name}")
        return None
    if gate:
        ref = _last_keeper.get(game_name.lower())
        reject = frames.quality_reject(small, settings, reference=ref)
        if reject:
            print(f"[CAP] Skipped ({reject}) for {game_name}")
            return None
    return _finalize(img, small, game_name, shot_type, settings, reason)


def capture_screenshot(game_name, shot_type, settings, reason="", gate=True):
    """
    Grab a fresh frame and save it, subject to the quality gate.
    Returns the saved path, or None if rejected/failed.
    """
    if not AVAILABLE:
        print("[CAP] capture unavailable (mss/PIL/numpy missing)")
        return None
    try:
        with mss.mss() as sct:
            monitor = frames.pick_monitor(sct, settings.get("monitor", "auto"))
            img = frames.grab(sct, monitor)
        small = frames.small_array(img)
        return save_frame(img, small, game_name, shot_type, settings, reason, gate=gate)
    except Exception as e:
        print(f"[CAP] Capture error: {e}")
        return None


# =========================
# TIMELAPSE SESSION
# =========================
def run_timelapse_session(is_active, game_name, settings):
    interval_sec = settings.get("interval", 420000) / 1000.0
    first_delay = settings.get("first_delay", 10)
    burst_enabled = settings.get("burst_enabled", False)
    burst_shots = min(10, max(1, int(settings.get("burst_shots", 3))))
    burst_delay = max(0.3, float(settings.get("burst_delay", 0.5)))

    print(f"[CAP] TimeLapse session started for {game_name}")
    _last_keeper.pop(game_name.lower(), None)
    time.sleep(first_delay)
    if not is_active():
        return

    def shot():
        capture_screenshot(game_name, "TimeLapse", settings, reason="timelapse")

    def burst():
        if burst_enabled:
            for _ in range(burst_shots - 1):
                time.sleep(burst_delay)
                if is_active():
                    shot()

    shot()
    burst()
    while is_active():
        time.sleep(interval_sec)
        if not is_active():
            break
        shot()
        burst()
    print(f"[CAP] TimeLapse session ended for {game_name}")


# =========================
# ACHIEVEMENT BURST
# =========================
def capture_achievement_burst(game_name, settings):
    ach = settings.get("achievement_burst", {})
    shots = min(15, max(1, int(ach.get("shots", 7))))
    delay = max(0.3, float(ach.get("delay", 0.5)))
    print(f"[CAP] Achievement burst: {shots} shots for {game_name}")
    for i in range(shots):
        # Bursts bypass dedupe so all frames are kept
        capture_screenshot(game_name, "Achievement", settings, reason="achievement", gate=False)
        if i < shots - 1:
            time.sleep(delay)
