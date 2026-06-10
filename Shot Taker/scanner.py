"""
ShotTaker — game folder scanner.

Walks configured folders for .exe files and builds a platform-tagged dict
{ "exe.exe": "platform" } stored in GAME_LIST and status/games.json.
"""

import os

import config

GAME_LIST = {}

# Scan order — first platform to claim an exe wins.
PLATFORM_KEYS = [
    "steam", "gog", "epic", "ubisoft", "ea",
    "xbox", "battlenet", "riot", "rockstar", "itch", "extra",
]

JUNK_DIRS = {
    "__pycache__", "node_modules", ".git", "logs", "cache",
    "shadercache", "htmlcache", "webcache", "_commonredist", "directx",
}

SKIP_PATTERNS = [
    "install", "setup", "unins", "update", "updater",
    "crashpad", "crashreport", "crash_handler", "crashhandler",
    "redist", "vcredist", "directx", "dotnet", "prereq", "prerequisite",
    "launcher", "helper", "service", "uninstall", "touchup", "cleanup",
]


def load_folders():
    return config.read_json(config.FOLDERS_FILE, None) or {k: [] for k in PLATFORM_KEYS}


def load_disabled():
    try:
        with open(config.DISABLED_FILE, "r", encoding="utf-8") as f:
            return {x.strip().lower() for x in f if x.strip()}
    except OSError:
        return set()


def scan_folder(path, platform, blacklist, disabled, hints):
    games = {}
    if not os.path.exists(path):
        print(f"  [SCAN] Folder not found, skipping: {path}")
        return games
    print(f"  [SCAN] Scanning: {path}")
    count = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d.lower() not in JUNK_DIRS]
        for f in files:
            if not f.lower().endswith(".exe"):
                continue
            exe = f.lower().strip()
            if exe in blacklist or exe in disabled:
                continue
            if any(x in exe for x in SKIP_PATTERNS):
                continue
            if exe not in games:
                games[exe] = platform
                count += 1
                # Title hint: top-level folder under the scanned root (usually the game name)
                try:
                    rel = os.path.relpath(root, path)
                    top = rel.split(os.sep)[0]
                    if top and top != "." and exe not in hints:
                        hints[exe] = top
                except ValueError:
                    pass
    print(f"  [SCAN] Found {count} executables in {path}")
    return games


def scan_games(blacklist=None):
    global GAME_LIST
    from blacklist import load_full_blacklist

    if blacklist is None:
        blacklist = load_full_blacklist()
    blacklist = set(blacklist)
    folders = load_folders()
    disabled = load_disabled()

    found = {}
    hints = {}
    print("[SCAN] Sweeping the drives for games...")
    for platform in PLATFORM_KEYS:
        paths = folders.get(platform, [])
        if not paths:
            continue
        print(f"[SCAN] Platform: {platform} ({len(paths)} folder(s))")
        for path in paths:
            for exe, plat in scan_folder(path, platform, blacklist, disabled, hints).items():
                found.setdefault(exe, plat)

    GAME_LIST = found
    print(f"[SCAN] Roster locked — {len(GAME_LIST)} games found.")
    config.write_json(config.GAMES_FILE, GAME_LIST)

    try:
        import gamenames
        gamenames.update_hints(hints)
    except Exception as e:
        print(f"[SCAN] Name-hint update failed: {e}")

    stats = config.read_json(config.STATS_FILE, {}) or {}
    stats["scan_count"] = stats.get("scan_count", 0) + 1
    stats["games_found"] = len(GAME_LIST)
    stats.setdefault("screenshots_taken", 0)
    config.write_json(config.STATS_FILE, stats)
    return GAME_LIST
