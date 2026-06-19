"""
ShotTaker — shared frame capture & analysis.

Tries to use the rust_capture native extension first (DXGI on Windows,
platform stubs on Linux/Mac). Falls back to mss + numpy if not available.

Either way the public API is identical:
  grab(sct_or_none, monitor_setting, settings) -> PIL Image
  small_array(img) -> numpy array (320x180)
  score_diff(a, b) -> float
  quality_reject(small, settings, reference) -> str | None
  list_monitors() -> list[dict]
"""

import ctypes

# =============================================================================
# BACKEND SELECTION
# =============================================================================

# Allow settings.json to force mss even if rust_capture is installed.
# Useful for A/B comparison testing between builds.
def _force_mss():
    try:
        import json, os
        # Walk up from this file looking for user_data/data/settings.json
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "user_data", "data", "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("force_mss", False)
    except Exception:
        pass
    return False

_FORCE_MSS = _force_mss()

try:
    if _FORCE_MSS:
        raise ImportError("force_mss is enabled in settings")
    import rust_capture as _rc
    RUST_AVAILABLE = True
    print(f"[FRAMES] rust_capture loaded — backend: {_rc.__backend__}")
except ImportError as _e:
    _rc = None
    RUST_AVAILABLE = False
    if _FORCE_MSS:
        print("[FRAMES] rust_capture disabled by force_mss setting — using mss")
    else:
        print("[FRAMES] rust_capture not found — using mss fallback")

try:
    import mss as _mss
    import numpy as np
    from PIL import Image
    MSS_AVAILABLE = True
except Exception:
    MSS_AVAILABLE = False

AVAILABLE = RUST_AVAILABLE or MSS_AVAILABLE
COMPARE_SIZE = (320, 180)


# =============================================================================
# PERFORMANCE TRACKER
# Logs grab time, diff time, and process CPU % every N captures.
# Works on both Rust and mss builds — just shows different backend names.
# =============================================================================
import time as _time
import threading as _threading

class _PerfTracker:
    def __init__(self):
        self._lock = _threading.Lock()
        self._grab_times = []
        self._diff_times = []
        self._capture_count = 0
        self._log_every = 50        # print a summary every N grabs
        self._backend = "dxgi" if RUST_AVAILABLE else "mss"
        self._start = _time.monotonic()

    def record_grab(self, elapsed):
        with self._lock:
            self._grab_times.append(elapsed)
            self._capture_count += 1
            if self._capture_count % self._log_every == 0:
                self._report()

    def record_diff(self, elapsed):
        with self._lock:
            self._diff_times.append(elapsed)

    def _report(self):
        if not self._grab_times:
            return
        try:
            import psutil, os
            cpu = psutil.Process(os.getpid()).cpu_percent(interval=None)
            cpu_str = f"  cpu={cpu:.1f}%"
        except Exception:
            cpu_str = ""

        g = self._grab_times
        d = self._diff_times
        uptime = _time.monotonic() - self._start

        grab_avg = sum(g) / len(g) * 1000
        grab_max = max(g) * 1000
        diff_avg = (sum(d) / len(d) * 1000) if d else 0.0
        diff_max = (max(d) * 1000) if d else 0.0

        print(
            f"[PERF] backend={self._backend}"
            f"  grabs={self._capture_count}"
            f"  grab_avg={grab_avg:.1f}ms  grab_max={grab_max:.1f}ms"
            f"  diff_avg={diff_avg:.1f}ms  diff_max={diff_max:.1f}ms"
            f"{cpu_str}"
            f"  uptime={uptime/60:.1f}min"
        )
        # Keep only last 200 samples to avoid unbounded growth
        self._grab_times = g[-200:]
        self._diff_times = d[-200:]

    def reset(self):
        with self._lock:
            self._grab_times.clear()
            self._diff_times.clear()
            self._capture_count = 0
            self._start = _time.monotonic()


PERF = _PerfTracker()


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


# =============================================================================
# MONITOR LISTING
# =============================================================================
def list_monitors():
    """Returns list of {index, x, y, width, height, primary} dicts."""
    if RUST_AVAILABLE:
        return _rc.list_monitors()
    # mss fallback
    if MSS_AVAILABLE:
        with _mss.mss() as sct:
            out = []
            for i, m in enumerate(sct.monitors[1:], start=0):
                out.append({
                    "index": i,
                    "x": m["left"],
                    "y": m["top"],
                    "width": m["width"],
                    "height": m["height"],
                    "primary": i == 0,
                })
            return out
    return []


# =============================================================================
# MONITOR SELECTION  (used by mss fallback path only)
# =============================================================================
def _pick_monitor_mss(sct, setting):
    monitors = sct.monitors
    if setting == "all":
        return monitors[0]
    if setting and setting != "auto":
        try:
            idx = int(setting)
            if 1 <= idx < len(monitors):
                return monitors[idx]
        except (ValueError, TypeError):
            pass
    rect = foreground_rect()
    if rect:
        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2
        for m in monitors[1:]:
            if m["left"] <= cx < m["left"] + m["width"] \
                    and m["top"] <= cy < m["top"] + m["height"]:
                return m
    return monitors[1] if len(monitors) > 1 else monitors[0]


def _monitor_index_from_setting(setting):
    """Resolve monitor setting string to a 0-based index for rust_capture."""
    if setting and setting not in ("auto", "all"):
        try:
            return max(0, int(setting) - 1)
        except (ValueError, TypeError):
            pass
    if setting == "auto":
        rect = foreground_rect()
        if rect:
            cx = (rect[0] + rect[2]) // 2
            cy = (rect[1] + rect[3]) // 2
            for m in list_monitors():
                if m["x"] <= cx < m["x"] + m["width"] \
                        and m["y"] <= cy < m["y"] + m["height"]:
                    return m["index"]
    return 0  # primary


# =============================================================================
# FRAME GRAB
# Returns a PIL RGB Image.
# sct argument is accepted for API compatibility but ignored when Rust is used.
# =============================================================================
def grab(sct, monitor_setting="auto"):
    _t0 = _time.monotonic()
    if RUST_AVAILABLE:
        try:
            idx = _monitor_index_from_setting(monitor_setting)
            buf, w, h = _rc.grab_frame(idx)
            img = Image.frombytes("RGB", (w, h), bytes(buf))
            PERF.record_grab(_time.monotonic() - _t0)
            return img
        except Exception as e:
            print(f"[FRAMES] Rust grab failed ({e}), falling back to mss")

    # mss fallback
    if MSS_AVAILABLE:
        if sct is None:
            raise RuntimeError("mss fallback requires an active mss context")
        monitor = _pick_monitor_mss(sct, monitor_setting)
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        PERF.record_grab(_time.monotonic() - _t0)
        return img

    raise RuntimeError("No capture backend available — install mss or build rust_capture")


# =============================================================================
# DOWNSCALE
# =============================================================================
def small_array(img, size=COMPARE_SIZE):
    """Downscaled numpy array for fast comparison."""
    return np.array(img.resize(size, Image.BILINEAR))


# =============================================================================
# SCORING  — uses Rust if available, otherwise numpy
# =============================================================================
def score_diff(a, b):
    """Weighted MAD: 60% luminance, 40% colour. Higher = more change."""
    _t0 = _time.monotonic()
    if RUST_AVAILABLE:
        result = float(_rc.score_diff(a.tobytes(), b.tobytes()))
    else:
        diff = np.abs(a.astype(np.float32) - b.astype(np.float32))
        lum = (diff * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
        result = float(0.6 * lum.mean() + 0.4 * diff.mean())
    PERF.record_diff(_time.monotonic() - _t0)
    return result


def mean_luminance(small):
    if RUST_AVAILABLE:
        return float(_rc.mean_luminance(small.tobytes()))
    return float(
        (small.astype(np.float32) * np.array([0.299, 0.587, 0.114], dtype=np.float32))
        .sum(axis=2).mean()
    )


def detail_score(small):
    """Std-dev of luminance — low = flat/uniform (menus, loading screens)."""
    if RUST_AVAILABLE:
        h, w = small.shape[:2]
        return float(_rc.detail_score(small.tobytes(), w, h))
    lum = (small.astype(np.float32) * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
    return float(lum.std())


def is_letterboxed(small, bar_lum=16.0, min_bars=0.10):
    if RUST_AVAILABLE:
        h, w = small.shape[:2]
        return bool(_rc.is_letterboxed(small.tobytes(), w, h))
    # numpy fallback
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


# =============================================================================
# QUALITY GATE
# Returns rejection reason string, or None if frame is worth keeping.
# =============================================================================
def quality_reject(small, settings, reference=None):
    if RUST_AVAILABLE:
        h, w = small.shape[:2]
        ref_bytes = reference.tobytes() if reference is not None else None
        result = _rc.quality_reject(
            small.tobytes(), w, h,
            ref_bytes,
            float(settings.get("dark_threshold", 12.0)),
            float(settings.get("dedupe_threshold", 6.0)),
            bool(settings.get("suppress_dark_frames", True)),
            bool(settings.get("suppress_loading_screens", True)),
            bool(settings.get("letterbox_suppression", True)),
            bool(settings.get("dedupe_enabled", True)),
        )
        return result

    # numpy fallback
    if settings.get("suppress_dark_frames", True):
        if mean_luminance(small) < float(settings.get("dark_threshold", 12.0)):
            return "dark"
    if settings.get("suppress_loading_screens", True):
        if detail_score(small) < 6.0:
            return "low-detail"
    if settings.get("letterbox_suppression", True):
        if is_letterboxed(small):
            return "letterbox"
    if reference is not None and settings.get("dedupe_enabled", True):
        if score_diff(reference, small) < float(settings.get("dedupe_threshold", 6.0)):
            return "duplicate"
    return None


# =============================================================================
# LEGACY COMPATIBILITY  (pick_monitor used by capture_manager mss path)
# =============================================================================
def pick_monitor(sct, setting):
    """Legacy API — used when mss context is passed directly."""
    return _pick_monitor_mss(sct, setting)
