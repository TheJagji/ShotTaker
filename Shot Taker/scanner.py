import os
import json

# Module-level game dict: { "exe.exe": "platform" }
GAME_LIST = {}


# =========================
# LOAD FOLDERS
# =========================
def load_folders():
    try:
        with open("data/folders.json", "r") as f:
            return json.load(f)
    except:
        return {
            "steam": [], "gog": [], "epic": [],
            "ubisoft": [], "ea": [], "extra_games": []
        }


# =========================
# LOAD DISABLED GAMES
# =========================
def load_disabled():
    try:
        with open("data/disabled_games.txt", "r") as f:
            return {x.strip().lower() for x in f if x.strip()}
    except:
        return set()


# =========================
# SCAN SINGLE FOLDER
# =========================
def scan_folder(path, platform, blacklist, disabled):
    games = {}

    if not os.path.exists(path):
        print(f"  [SCAN] Folder not found, skipping: {path}")
        return games

    print(f"  [SCAN] Scanning: {path}")
    count = 0

    for root, dirs, files in os.walk(path):
        # Skip common junk subdirectories to speed up scan
        dirs[:] = [d for d in dirs if d.lower() not in (
            "__pycache__", "node_modules", ".git", "logs", "cache",
            "shadercache", "htmlcache", "webcache"
        )]

        for f in files:
            if not f.endswith(".exe"):
                continue

            exe = f.lower().strip()

            if exe in blacklist:
                continue

            if exe in disabled:
                continue

            # Skip installers, updaters, launchers, crash handlers
            skip_patterns = [
                "install", "setup", "unins", "update", "updater",
                "crashpad", "crashreport", "crash_handler",
                "redist", "vcredist", "directx",
                "dotnet", "prereq", "prerequisite",
                "launcher" # most game launchers aren't the game itself
            ]
            if any(x in exe for x in skip_patterns):
                continue

            if exe not in games:
                games[exe] = platform
                count += 1

    print(f"  [SCAN] Found {count} executables in {path}")
    return games


# =========================
# MAIN SCAN
# =========================
def scan_games(blacklist=None):
    global GAME_LIST

    from blacklist import load_full_blacklist

    if blacklist is None:
        blacklist = load_full_blacklist()

    blacklist = set(blacklist)
    folders = load_folders()
    disabled = load_disabled()

    found = {}
    platform_keys = ["steam", "gog", "epic", "ubisoft", "ea", "extra_games"]

    print("[SCAN] Starting game scan...")

    for platform in platform_keys:
        paths = folders.get(platform, [])
        if not paths:
            continue
        print(f"[SCAN] Platform: {platform} ({len(paths)} folder(s))")
        for path in paths:
            result = scan_folder(path, platform, blacklist, disabled)
            for exe, plat in result.items():
                if exe not in found:
                    found[exe] = plat

    GAME_LIST = found
    print(f"[SCAN] Complete — {len(GAME_LIST)} games found")

    # Save game list
    os.makedirs("status", exist_ok=True)
    with open("status/games.json", "w") as f:
        json.dump(GAME_LIST, f, indent=4)

    # Update stats
    stats = {
        "screenshots_taken": 0,
        "scan_count": 1,
        "active_game": "",
        "uptime": 0
    }
    try:
        with open("status/stats.json", "r") as f:
            old = json.load(f)
            stats["scan_count"] = old.get("scan_count", 0) + 1
            stats["screenshots_taken"] = old.get("screenshots_taken", 0)
            stats["active_game"] = old.get("active_game", "")
    except:
        pass

    with open("status/stats.json", "w") as f:
        json.dump(stats, f, indent=4)

    return GAME_LIST
