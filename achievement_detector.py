"""
ShotTaker — Steam achievement detector.

Watches Steam's appcache/stats/*.bin files; a newer mtime implies an achievement
unlock, which fires a capture burst and logs an event.
"""

import os
import time
import threading
import glob

import config

DEFAULT_STATS_PATHS = [
    os.path.expandvars(r"%PROGRAMFILES(X86)%\Steam\appcache\stats"),
    os.path.expandvars(r"%PROGRAMFILES%\Steam\appcache\stats"),
    r"C:\Program Files (x86)\Steam\appcache\stats",
    r"C:\Program Files\Steam\appcache\stats",
]


def find_steam_stats_folder():
    s = config.load_settings()
    configured = s.get("steam_stats_folder", "")
    if configured and os.path.exists(configured):
        print(f"[ACH] Using configured stats folder: {configured}")
        return configured
    for path in DEFAULT_STATS_PATHS:
        if os.path.exists(path):
            print(f"[ACH] Found Steam stats folder: {path}")
            return path
    print("[ACH] Steam stats folder not found. Set it in Settings.")
    return None


def snapshot_stats(folder):
    result = {}
    if not folder or not os.path.exists(folder):
        return result
    for f in glob.glob(os.path.join(folder, "*.bin")):
        try:
            result[f] = os.path.getmtime(f)
        except OSError:
            pass
    return result


class AchievementDetector:

    def __init__(self):
        self._thread = None
        self._running = False
        self._is_active = None
        self._get_platform = None
        self._get_game = None
        self._get_settings = None
        self._stats_folder = None
        self._last_snapshot = {}

    def start(self, is_game_active, get_platform, get_game, get_settings):
        self._is_active = is_game_active
        self._get_platform = get_platform
        self._get_game = get_game
        self._get_settings = get_settings
        self._running = True
        self._stats_folder = find_steam_stats_folder()
        self._last_snapshot = snapshot_stats(self._stats_folder)
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("[ACH] Trophy watch online — ready for the next unlock.")

    def stop(self):
        self._running = False

    def _watch_loop(self):
        while self._running:
            try:
                self._check()
            except Exception as e:
                print(f"[ACH] Watch error: {e}")
            time.sleep(1)

    def _check(self):
        if not self._stats_folder or not self._is_active():
            return
        settings = self._get_settings()
        if not settings.get("achievement_screenshots_enabled", False):
            return

        current = snapshot_stats(self._stats_folder)
        triggered = any(
            self._last_snapshot.get(p) is not None and m > self._last_snapshot[p]
            for p, m in current.items()
        )
        self._last_snapshot = current

        if triggered:
            print("[ACH] Achievement unlocked — capturing the glory.")
            self._fire(settings)

    def _fire(self, settings):
        from screenshots import fire_achievement_burst
        game = self._get_game() if self._get_game else ""
        platform = self._get_platform() if self._get_platform else "steam"
        try:
            import state
            state.log_event("achievement", {"game": game})
        except Exception:
            pass
        threading.Thread(
            target=fire_achievement_burst,
            args=(game, platform, settings),
            daemon=True,
        ).start()

    def rescan_folder(self):
        self._stats_folder = find_steam_stats_folder()
        self._last_snapshot = snapshot_stats(self._stats_folder)
        print(f"[ACH] Stats folder: {self._stats_folder or 'not found'}")


achievement_detector = AchievementDetector()
