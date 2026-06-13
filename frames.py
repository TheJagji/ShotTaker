"""
ShotTaker — shared frame capture & analysis.

Pure-ish helpers used by both the time-lapse and action-shot capture paths:
  - monitor selection (auto / all / specific index)
  - frame grabbing -> PIL Image
  - downscaled comparison arrays
  - scene-difference scoring (weighted MAD)
  - quality gates: dark frame, low-detail/loading screen, letterbox
  - near-duplicate detection vs a reference frame
"""

import ctypes

try:
    import mss
    import numpy as np
    from PIL import Image
    AVAILABLE = True
except Exception:
    AVAILABLE = False


COMPARE_SIZE = (320, 180)


# =========================
# FOREGROUND WINDOW
# =========================
def foreground_title():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def foreground_rect():
    """(left, top, right, bottom) of the focused window, or None."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = ctypes.wintypes.RECT() if hasattr(ctypes, "wintypes") else None
        if rect is None:
            import ctypes.wintypes as wt
            rect = wt.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return None


# =========================
# MONITOR SELECTION
# =========================
def pick_monitor(sct, setting):
    """
    setting: 'auto' | 'all' | '1' | '2' ...
    Returns an mss monitor dict.
    """
    monitors = sct.monitors  # [0]=virtual union, [1..]=individual
    if setting == "all":
        return monitors[0]

    if setting and setting != "auto":
        try:
            idx = int(setting)
            if 1 <= idx < len(monitors):
                return monitors[idx]
        except (ValueError, TypeError):
            pass

    # auto: monitor containing the focused window's centre, else primary
    rect = foreground_rect()
    if rect:
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        for m in monitors[1:]:
            if m["left"] <= cx < m["left"] + m["width"] and m["top"] <= cy < m["top"] + m["height"]:
                return m

    return monitors[1] if len(monitors) > 1 else monitors[0]


def grab(sct, monitor):
    """Grab a monitor as a PIL RGB Image."""
    raw = sct.grab(monitor)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def small_array(img, size=COMPARE_SIZE):
    """Downscaled numpy array for fast comparison."""
    return np.array(img.resize(size, Image.BILINEAR))


# =========================
# SCORING
# =========================
def score_diff(a, b):
    """Weighted Mean Absolute Difference: 60% luminance, 40% colour. Higher = more change."""
    diff = np.abs(a.astype(np.float32) - b.astype(np.float32))
    lum = (diff * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
    return float(0.6 * lum.mean() + 0.4 * diff.mean())


def mean_luminance(small):
    return float((small.astype(np.float32) * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2).mean())


def detail_score(small):
    """Std-dev of luminance — low values mean flat/uniform frames (menus, loading)."""
    lum = (small.astype(np.float32) * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
    return float(lum.std())


def is_letterboxed(small, bar_lum=16.0, min_bars=0.10):
    """
    Detects large black bars top+bottom (cinematic/cutscene/loading).
    Returns True if both top and bottom >=min_bars fraction of rows are near-black.
    """
    lum = (small.astype(np.float32) * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
    rows = lum.mean(axis=1)
    h = len(rows)
    dark = rows < bar_lum
    top = 0
    while top < h and dark[top]:
        top += 1
    bot = 0
    while bot < h and dark[h - 1 - bot]:
        bot += 1
    return (top / h) >= min_bars and (bot / h) >= min_bars


# =========================
# QUALITY GATE
# Returns a rejection reason string, or None if the frame is worth keeping.
# =========================
def quality_reject(small, settings, reference=None):
    if settings.get("suppress_dark_frames", True):
        if mean_luminance(small) < float(settings.get("dark_threshold", 12.0)):
            return "dark"

    if settings.get("suppress_loading_screens", True):
        # Very low detail = flat colour / simple loading screen
        if detail_score(small) < 6.0:
            return "low-detail"

    if settings.get("letterbox_suppression", True):
        if is_letterboxed(small):
            return "letterbox"

    if reference is not None and settings.get("dedupe_enabled", True):
        if score_diff(reference, small) < float(settings.get("dedupe_threshold", 6.0)):
            return "duplicate"

    return None
