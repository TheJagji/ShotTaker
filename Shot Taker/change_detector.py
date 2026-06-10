import threading
import time
import json

try:
    import mss
    import numpy as np
    from PIL import Image
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

from capture_manager import (
    capture_screenshot,
    generate_thumbnail,
    increment_screenshot_count
)

# Disable pyautogui failsafe to prevent accidental crashes
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except:
    pass

# =========================
# THUMBNAIL SIZE FOR COMPARISON
# =========================
_COMPARE_SIZE = (320, 180)


# =========================
# FRAME DIFFERENCE SCORE
# Weighted MAD: 60% luminance, 40% colour
# Adapted from DScreenshot by permission
# =========================
def score_diff(a, b):
    diff = np.abs(a.astype(np.float32) - b.astype(np.float32))
    lum = (diff * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=2)
    return float(0.6 * lum.mean() + 0.4 * diff.mean())


# =========================
# CHANGE DETECTOR
# Monitors the screen and fires Action Shots when
# significant scene changes are detected
# =========================
class ChangeDetector:

    def __init__(self):
        self._thread    = None
        self._running   = False
        self._is_active = None
        self._get_game  = None
        self._get_settings = None

    def start(self, is_game_active, get_game_name, get_settings):
        if not MSS_AVAILABLE:
            print("[ACT] mss not available — Action Shots unavailable")
            return

        self._is_active    = is_game_active
        self._get_game     = get_game_name
        self._get_settings = get_settings
        self._running      = True

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[ACT] Action Shots detector started")

    def stop(self):
        self._running = False
        print("[ACT] Action Shots detector stopped")

    def _loop(self):
        prev_small = None
        last_capture = 0.0

        with mss.mss() as sct:
            while self._running:
                try:
                    settings = self._get_settings()
                    capture_mode = settings.get("capture_mode", "timelapse")

                    # Only run if mode includes action shots
                    if capture_mode not in ("action", "hybrid"):
                        time.sleep(2)
                        continue

                    # Only capture when game is active
                    if not self._is_active():
                        prev_small = None
                        time.sleep(1)
                        continue

                    # Check the foreground window is not the desktop or a system window
                    try:
                        import ctypes
                        hwnd = ctypes.windll.user32.GetForegroundWindow()
                        if hwnd:
                            buf = ctypes.create_unicode_buffer(256)
                            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                            title = buf.value.lower()
                            # Skip if foreground is desktop, taskbar, or ShotTaker itself
                            skip_titles = ['', 'program manager', 'shottaker',
                                         'task manager', 'task switching']
                            if any(s in title for s in skip_titles):
                                prev_small = None
                                time.sleep(1)
                                continue
                    except:
                        pass

                    sensitivity = float(settings.get("sensitivity", 30.0))
                    cooldown    = float(settings.get("action_cooldown", 5.0))

                    # Grab primary monitor
                    monitor = sct.monitors[1]
                    raw     = sct.grab(monitor)
                    frame   = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                    small   = np.array(frame.resize(_COMPARE_SIZE, Image.BILINEAR))

                    now = time.time()

                    if prev_small is not None:
                        diff = score_diff(prev_small, small)

                        if diff >= sensitivity and (now - last_capture) >= cooldown:
                            game = self._get_game()
                            if game:
                                print(f"[ACT] Scene change (score={diff:.1f}, threshold={sensitivity}) — capturing for {game}")
                                path = capture_screenshot(game, "DynamicShot", settings)
                                if path:
                                    increment_screenshot_count()
                                    threading.Thread(
                                        target=generate_thumbnail,
                                        args=(path, settings),
                                        daemon=True
                                    ).start()
                                last_capture = now

                    prev_small = small

                except Exception as e:
                    print(f"[ACT] Detection error: {e}")

                time.sleep(0.5)


# Shared instance
change_detector = ChangeDetector()
