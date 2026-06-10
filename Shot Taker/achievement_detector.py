import os
import time
import threading
import glob
import json


# =========================
# LOAD STEAM STATS PATH FROM SETTINGS
# =========================
def get_stats_folder_from_settings():
    try:
        with open("data/settings.json", "r") as f:
            s = json.load(f)
        path = s.get("steam_stats_folder", "")
        if path and os.path.exists(path):
            return path
    except:
        pass
    return None


# =========================
# DEFAULT STEAM STATS PATHS
# Fallback if not configured
# =========================
DEFAULT_STATS_PATHS = [
    os.path.expandvars(r"%APPDATA%\Roaming\Steam\appcache\stats"),
    os.path.expandvars(r"%APPDATA%\Steam\appcache\stats"),
    r"C:\Program Files (x86)\Steam\appcache\stats",
    r"C:\Program Files\Steam\appcache\stats",
]


def find_steam_stats_folder():
    # Check settings first
    from_settings = get_stats_folder_from_settings()
    if from_settings:
        print(f"[ACH] Using configured Steam stats folder: {from_settings}")
        return from_settings

    # Fall back to defaults
    for path in DEFAULT_STATS_PATHS:
        if os.path.exists(path):
            print(f"[ACH] Found Steam stats folder: {path}")
            return path

    print("[ACH] Steam stats folder not found. Configure it in Settings > Platforms.")
    return None


# =========================
# SNAPSHOT STATS FILES
# =========================
def snapshot_stats(folder):
    result = {}
    if not folder or not os.path.exists(folder):
        return result
    for f in glob.glob(os.path.join(folder, "*.bin")):
        try:
            result[f] = os.path.getmtime(f)
        except:
            pass
    return result


# =========================
# ACHIEVEMENT DETECTOR
# =========================
class AchievementDetector:

    def __init__(self):
        self._thread       = None
        self._running      = False
        self._is_active    = None
        self._get_platform = None
        self._get_settings = None
        self._stats_folder = None
        self._last_snapshot = {}

    def start(self, is_game_active, get_platform, get_settings):
        self._is_active    = is_game_active
        self._get_platform = get_platform
        self._get_settings = get_settings
        self._running      = True

        self._stats_folder  = find_steam_stats_folder()
        self._last_snapshot = snapshot_stats(self._stats_folder)

        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("[ACH] Achievement detector started.")

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
        if not self._stats_folder:
            return

        if not self._is_active():
            return

        settings = self._get_settings()

        if not settings.get("achievement_screenshots_enabled", False):
            return

        current = snapshot_stats(self._stats_folder)
        triggered = False

        for path, mtime in current.items():
            old_mtime = self._last_snapshot.get(path)
            if old_mtime is not None and mtime > old_mtime:
                print(f"[ACH] Achievement detected! Stats file changed: {os.path.basename(path)}")
                triggered = True
                break

        self._last_snapshot = current

        if triggered:
            platform = self._get_platform()
            self._fire(platform, settings)

    def _fire(self, platform, settings):
        from screenshots import fire_achievement_burst
        threading.Thread(
            target=fire_achievement_burst,
            args=(platform, settings),
            daemon=True
        ).start()

    def rescan_folder(self):
        self._stats_folder  = find_steam_stats_folder()
        self._last_snapshot = snapshot_stats(self._stats_folder)
        print(f"[ACH] Stats folder: {self._stats_folder or 'not found'}")


achievement_detector = AchievementDetector()
