"""
ShotTaker — central configuration, settings, and path resolution.

Single source of truth for:
  - file-system paths (frozen/PyInstaller-aware)
  - settings load/save with a defaults merge + validation
  - app directory bootstrap + seeding of bundled default files

Every module should import from here instead of hard-coding "data/..." paths
or re-implementing load_settings().
"""

import os
import sys
import json
import shutil
import threading

from branding import BRAND


# =========================
# PATHS  (frozen-aware)
# =========================
def is_frozen():
    return getattr(sys, "frozen", False)


def bundle_dir():
    """Read-only resources (templates, static, seed data). PyInstaller _MEIPASS when frozen."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def app_dir():
    """Writable base dir for user data. Next to the exe when frozen, else the source dir."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def res_path(*parts):
    """Path to a bundled read-only resource."""
    return os.path.join(bundle_dir(), *parts)


def data_path(*parts):
    """Path to a writable user-data file/dir."""
    return os.path.join(app_dir(), *parts)


# Common locations
USER_DATA_DIR = data_path("user_data")
DATA_DIR     = data_path("user_data", "data")
STATUS_DIR   = data_path("user_data", "status")
COMMANDS_DIR = data_path("user_data", "commands")
STATIC_DIR   = data_path("static")          # read-only source assets — served by Flask
SOUNDS_DIR   = data_path("user_data", "sounds")  # user-uploaded sounds
TEMPLATES_DIR = res_path("templates")        # read-only (bundled)

SETTINGS_FILE  = os.path.join(DATA_DIR, "settings.json")
FOLDERS_FILE   = os.path.join(DATA_DIR, "folders.json")
PROFILES_FILE  = os.path.join(DATA_DIR, "profiles.json")
COUNTER_FILE   = os.path.join(DATA_DIR, "shot_counters.json")
LIBRARY_FILE   = os.path.join(DATA_DIR, "library.json")        # favorites/tags index
NAMEMAP_FILE   = os.path.join(DATA_DIR, "game_names.json")     # exe -> friendly name
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.txt")
BLACKLIST_DEFAULT_FILE = os.path.join(DATA_DIR, "blacklist_default.txt")
DISABLED_FILE  = os.path.join(DATA_DIR, "disabled_games.txt")

STATE_FILE     = os.path.join(STATUS_DIR, "state.json")
STATS_FILE     = os.path.join(STATUS_DIR, "stats.json")
GAMES_FILE     = os.path.join(STATUS_DIR, "games.json")
ACTIVE_FILE    = os.path.join(STATUS_DIR, "active_game.txt")
LASTSESSION_FILE = os.path.join(STATUS_DIR, "last_session.json")
SESSIONS_FILE  = os.path.join(STATUS_DIR, "sessions.json")
EVENTS_FILE    = os.path.join(STATUS_DIR, "events.json")

ABOUT_FILE     = os.path.join(data_path("data"), "about.txt")


def default_screenshot_folder():
    return data_path("user_data", "Screenshots")


# =========================
# DEFAULT SETTINGS
# =========================
DEFAULTS = {
    "version": BRAND["version"],

    # --- capture ---
    "capture_mode": "timelapse",        # timelapse | action | hybrid
    "interval": 420000,                  # ms between time-lapse shots
    "first_delay": 10,                   # seconds before first shot
    "screenshot_folder": "",            # "" -> default_screenshot_folder()
    "per_game_folders": True,
    "screenshot_format": "png",          # png | jpeg | webp
    "jpeg_quality": 90,
    "webp_quality": 90,
    "capture_scale": 100,                # percent of native resolution
    "monitor": "auto",                   # auto | all | "1" | "2" ...

    # --- action shots ---
    "sensitivity": 30.0,                 # diff threshold to fire
    "action_cooldown": 5.0,              # seconds between action shots

    # --- quality filters (Milestone 2) ---
    "suppress_loading_screens": True,
    "suppress_dark_frames": True,
    "dark_threshold": 12.0,              # mean luminance below this = skip
    "letterbox_suppression": True,
    "dedupe_enabled": True,
    "dedupe_threshold": 6.0,             # diff below this vs last keeper = duplicate
    "precapture_buffer": False,          # save frame just before the change

    # --- time-lapse burst ---
    "burst_enabled": False,
    "burst_shots": 3,
    "burst_delay": 0.5,

    # --- achievements ---
    "achievement_screenshots_enabled": False,
    "achievement_burst": {"shots": 7, "delay": 0.5},
    "steam_stats_folder": "",
    "steam_hotkey_backup": False,
    "hotkeys": {
        "steam": "f12", "gog": "f12", "epic": "f13",
        "ubisoft": "f13", "ea": "f13", "extra": "f10",
    },

    # --- manual capture hotkey ---
    "manual_hotkey_enabled": True,
    "manual_hotkey": "f9",

    # --- watermark (Milestone 3) ---
    "watermark_enabled": False,
    "watermark_text": "{game} - {date}",

    # --- storage guardrails (Milestone 3) ---
    "max_shots_per_game": 0,             # 0 = unlimited
    "max_disk_mb": 0,                    # 0 = unlimited
    "storage_policy": "rotate",          # rotate (delete oldest) | stop

    # --- notifications ---
    "notifications_enabled": True,
    "notification_sound": "",
    "capture_toast": True,               # small toast when a shot is taken

    # --- window / theme ---
    "popup_on_game": True,
    "minimise_to_tray": True,
    "popup_duration": 5,
    "theme": "dark",                     # dark | light

    # --- privacy guard (Milestone 5) ---
    "privacy_guard_enabled": False,
    "privacy_apps": ["1password", "keepass", "bitwarden", "lastpass", "banking"],
    "capture_paused": False,

    # --- gallery / misc ---
    "open_with": "",                     # "" -> OS default
    "resolve_game_names": True,
    "debug_mode": False,
}

_lock = threading.Lock()


def _deep_merge(base, override):
    """Recursively merge override into a copy of base."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings():
    """Load settings.json merged over DEFAULTS so missing keys always resolve."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            user = json.load(f)
    except Exception:
        user = {}
    return _deep_merge(DEFAULTS, user)


def save_settings(settings):
    """Persist settings (only what's given, but we store the merged result)."""
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        merged = _deep_merge(DEFAULTS, settings)
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)
        os.replace(tmp, SETTINGS_FILE)
    return merged


def update_settings(**kwargs):
    """Patch specific keys and save."""
    s = load_settings()
    s.update(kwargs)
    return save_settings(s)


def settings_exists():
    return os.path.exists(SETTINGS_FILE)


# =========================
# PER-GAME PROFILES
# =========================
def load_profiles():
    return read_json(PROFILES_FILE, {}) or {}


def save_profiles(profiles):
    write_json(PROFILES_FILE, profiles)


def profile_for(exe):
    return load_profiles().get((exe or "").lower(), {})


def settings_for_game(exe):
    """Settings with any per-game profile overrides merged on top."""
    s = load_settings()
    prof = profile_for(exe)
    return _deep_merge(s, prof) if prof else s


def get_screenshot_folder(settings=None):
    s = settings or load_settings()
    folder = s.get("screenshot_folder", "")
    return folder if folder else default_screenshot_folder()


# =========================
# JSON HELPERS
# =========================
def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# =========================
# APP BOOTSTRAP
# =========================
def ensure_dirs():
    for d in [USER_DATA_DIR, DATA_DIR, STATUS_DIR, COMMANDS_DIR, STATIC_DIR, SOUNDS_DIR]:
        os.makedirs(d, exist_ok=True)
    for flag in ("scan.flag", "reload.flag"):
        p = os.path.join(COMMANDS_DIR, flag)
        if not os.path.exists(p):
            open(p, "w").close()
    _seed_defaults()
    seed_static()


def seed_static():
    """When frozen, copy bundled static assets (js/css) into the writable static dir."""
    if not is_frozen():
        return
    src = res_path("static")
    if not os.path.isdir(src):
        return
    for root, _, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        for fn in files:
            sp = os.path.join(root, fn)
            dp = os.path.join(STATIC_DIR, os.path.relpath(sp, src))
            try:
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                shutil.copyfile(sp, dp)
            except OSError:
                pass


def _seed_defaults():
    """Copy bundled read-only seed files into the writable data dir on first run."""
    seeds = [
        ("data/blacklist_default.txt", BLACKLIST_DEFAULT_FILE),
    ]
    for rel, dest in seeds:
        if os.path.exists(dest):
            continue
        src = res_path(*rel.split("/"))
        try:
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(src, dest)
        except Exception as e:
            print(f"[CFG] Seed failed for {rel}: {e}")
