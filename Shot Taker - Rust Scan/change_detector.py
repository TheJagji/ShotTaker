"""
ShotTaker — Action Shots detector.

Continuously samples the screen and fires a capture when a significant scene
change is detected. Saves the in-hand frame (or the pre-change frame when the
pre-capture buffer is enabled) and defers quality filtering to the capture gate.
"""

import threading
import time

import config

try:
    import frames
    import mss
    AVAILABLE = frames.AVAILABLE
except Exception:
    AVAILABLE = False

from capture_manager import save_frame


class ChangeDetector:

    def __init__(self):
        self._thread = None
        self._running = False
        self._is_active = None
        self._get_game = None
        self._get_settings = None

    def start(self, is_game_active, get_game_name, get_settings):
        if not AVAILABLE:
            print("[ACT] frame deps unavailable — Action Shots disabled")
            return
        self._is_active = is_game_active
        self._get_game = get_game_name
        self._get_settings = get_settings
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[ACT] Action cam armed — watching for the big plays.")

    def stop(self):
        self._running = False

    def _loop(self):
        prev_small = None
        prev_img = None
        last_capture = 0.0
        skip_titles = ["", "program manager", "shottaker", "task manager", "task switching"]

        # Only open an mss context if Rust backend is not available
        def run(sct):
            nonlocal prev_small, prev_img, last_capture
            while self._running:
                try:
                    settings = self._get_settings()
                    mode = settings.get("capture_mode", "timelapse")
                    if mode not in ("action", "hybrid") or settings.get("capture_paused", False):
                        prev_small = prev_img = None
                        time.sleep(1.5)
                        continue
                    if not self._is_active():
                        prev_small = prev_img = None
                        time.sleep(1)
                        continue

                    title = frames.foreground_title().lower()
                    if any(s and s in title for s in skip_titles) or title == "":
                        prev_small = prev_img = None
                        time.sleep(1)
                        continue

                    sensitivity = float(settings.get("sensitivity", 30.0))
                    cooldown = float(settings.get("action_cooldown", 5.0))
                    precapture = settings.get("precapture_buffer", False)
                    monitor_setting = settings.get("monitor", "auto")

                    img = frames.grab(sct, monitor_setting)
                    small = frames.small_array(img)
                    now = time.time()

                    if prev_small is not None:
                        diff = frames.score_diff(prev_small, small)
                        if diff >= sensitivity and (now - last_capture) >= cooldown:
                            game = self._get_game()
                            if game:
                                print(f"[ACT] Something popped off (score={diff:.1f} / {sensitivity}) — grabbing it.")
                                if precapture and prev_img is not None:
                                    save_frame(prev_img, prev_small, game, "DynamicShot", settings, "action")
                                save_frame(img, small, game, "DynamicShot", settings, "action")
                                last_capture = now

                    prev_small = small
                    prev_img = img if precapture else None

                except Exception as e:
                    print(f"[ACT] Detection error: {e}")

                time.sleep(0.5)

        if frames.RUST_AVAILABLE:
            run(None)
        elif AVAILABLE:
            with mss.mss() as sct:
                run(sct)
        else:
            print("[ACT] No capture backend available")


change_detector = ChangeDetector()
