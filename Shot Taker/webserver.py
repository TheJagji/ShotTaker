from flask import Flask, render_template, jsonify, request
import json
import os
import subprocess
import threading

import scanner
from blacklist import (
    load_blacklist,
    load_full_blacklist,
    add_to_blacklist,
    remove_from_blacklist
)
from platform_detect import run_detection
from steam_detect import detect_steam_libraries

app = Flask(__name__)

# Cache mapping hash -> full path for gallery serving
_path_cache = {}

FOLDER_FILE = "data/folders.json"
SETTINGS_FILE = "data/settings.json"


# =========================
# DEFAULT SETTINGS
# =========================
DEFAULT_SETTINGS = {
    "interval": 420000,
    "first_delay": 10,
    "hotkeys": {
        "steam":       "f12",
        "gog":         "f12",
        "epic":        "f13",
        "ubisoft":     "f13",
        "ea":          "f13",
        "extra_games": "f10"
    },
    "screenshot_folders": {
        "steam":   "",
        "gog":     "",
        "epic":    "",
        "ubisoft": "",
        "ea":      "",
        "custom":  []
    }
}


# =========================
# HELPERS
# =========================
def load_folders():
    try:
        with open(FOLDER_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "steam": [], "gog": [], "epic": [],
            "ubisoft": [], "ea": [], "extra_games": []
        }


def save_folders(data):
    os.makedirs("data", exist_ok=True)
    with open(FOLDER_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT_SETTINGS.copy()


def save_settings_data(data):
    os.makedirs("data", exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# FAVICON
# =========================
@app.route("/favicon.ico")
def favicon():
    ico = os.path.join("static", "icon.ico")
    png = os.path.join("static", "icon.png")
    if os.path.exists(ico):
        return app.send_static_file("icon.ico")
    elif os.path.exists(png):
        return app.send_static_file("icon.png")
    return "", 204


# =========================
# HOME
# =========================
@app.route("/")
def home():
    return render_template("index.html")


# =========================
# SETUP STATUS
# Returns whether first-run setup has been completed
# =========================
@app.route("/api/setup/status")
def setup_status():
    completed = os.path.exists(SETTINGS_FILE)
    return jsonify({"setup_complete": completed})


# =========================
# SETUP COMPLETE
# Called when wizard finishes — saves all setup data at once
# =========================
@app.route("/api/setup/complete", methods=["POST"])
def setup_complete():
    data = request.json or {}

    settings = DEFAULT_SETTINGS.copy()
    settings["interval"] = data.get("interval", 420000)
    settings["first_delay"] = data.get("first_delay", 10)

    # Hotkeys per platform
    if "hotkeys" in data:
        settings["hotkeys"].update(data["hotkeys"])

    # Screenshot folder paths per platform
    if "screenshot_folders" in data:
        settings["screenshot_folders"].update(data["screenshot_folders"])

    # Notification preference
    settings["notifications_enabled"] = data.get("notifications_enabled", True)

    # Burst settings
    settings["burst_enabled"] = data.get("burst_enabled", False)
    settings["burst_shots"]   = min(10, max(1, int(data.get("burst_shots", 3))))
    settings["burst_delay"]   = max(0.5, float(data.get("burst_delay", 0.5)))

    # Achievement settings
    settings["achievement_screenshots_enabled"] = data.get("achievement_screenshots_enabled", False)
    ach = data.get("achievement_burst", {})
    settings["achievement_burst"] = {
        "shots": min(10, max(1, int(ach.get("shots", 7)))),
        "delay": max(0.5, float(ach.get("delay", 0.5)))
    }

    save_settings_data(settings)

    # Trigger a game scan now that folders may be configured
    scanner.scan_games()

    return jsonify({"success": True})


# =========================
# STATUS
# =========================
@app.route("/api/status")
def status():
    try:
        with open("status/state.json", "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({
            "games": 0,
            "activeGame": "",
            "activePlatform": "",
            "gameActive": False
        })


# =========================
# STATS
# =========================
@app.route("/api/stats")
def stats():
    try:
        with open("status/stats.json", "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"scan_count": 0, "screenshots_taken": 0})


# =========================
# GAMES
# Returns dict: { "exe.exe": "platform" }
# =========================
@app.route("/api/games")
def games():
    try:
        with open("status/games.json", "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({})


# =========================
# DISABLE GAME
# =========================
@app.route("/api/games/disable", methods=["POST"])
def disable_game():
    exe = request.json.get("exe", "").lower().strip()
    if exe:
        os.makedirs("data", exist_ok=True)
        with open("data/disabled_games.txt", "a") as f:
            f.write(exe + "\n")
        scanner.scan_games()
    return jsonify({"success": True})


# =========================
# BLACKLIST
# =========================
@app.route("/api/blacklist")
def blacklist():
    return jsonify(load_blacklist())


@app.route("/api/blacklist/add", methods=["POST"])
def blacklist_add():
    exe = request.json.get("exe", "").lower().strip()
    if exe:
        add_to_blacklist(exe)
        scanner.scan_games()
    return jsonify({"success": True})


@app.route("/api/blacklist/remove", methods=["POST"])
def blacklist_remove():
    exe = request.json.get("exe", "").lower().strip()
    if exe:
        remove_from_blacklist(exe)
    return jsonify({"success": True})


@app.route("/api/blacklist/move_to_games", methods=["POST"])
def move_to_games():
    exe = request.json.get("exe", "").lower().strip()
    if exe:
        remove_from_blacklist(exe)
        scanner.scan_games()
    return jsonify({"success": True})


# =========================
# MANUAL GAME SCAN
# =========================
@app.route("/api/scan/games")
def scan_games():
    scanner.scan_games()
    return jsonify({"success": True})


# =========================
# FOLDERS
# =========================
@app.route("/api/folders")
def folders():
    return jsonify(load_folders())


@app.route("/api/folders/save", methods=["POST"])
def save_folders_api():
    save_folders(request.json)
    return jsonify({"success": True})


@app.route("/api/folders/autodetect", methods=["POST"])
def autodetect():
    selected = request.json or {}

    # Path-based detection
    results = run_detection(selected)

    # Steam: also use VDF library detection and merge
    if selected.get("steam"):
        vdf_paths = detect_steam_libraries()
        existing = results.get("steam", [])
        merged = list(set(existing + vdf_paths))
        results["steam"] = merged

    folders = load_folders()

    # Merge — add new paths, keep existing manual ones
    for key, new_paths in results.items():
        if key in folders:
            merged = list(set(folders[key] + new_paths))
            folders[key] = merged

    save_folders(folders)
    return jsonify({"success": True, "results": results, "folders": folders})


# =========================
# ADD FOLDER FOR PLATFORM
# =========================
@app.route("/api/folders/add", methods=["POST"])
def add_folder():
    data = request.json or {}
    platform = data.get("platform", "").strip()
    path = data.get("path", "").strip()

    if not platform or not path:
        return jsonify({"success": False, "error": "Missing platform or path"})

    folders = load_folders()
    if platform not in folders:
        folders[platform] = []

    if path not in folders[platform]:
        folders[platform].append(path)
        save_folders(folders)

    return jsonify({"success": True, "folders": folders})


# =========================
# REMOVE FOLDER FOR PLATFORM
# =========================
@app.route("/api/folders/remove", methods=["POST"])
def remove_folder():
    data = request.json or {}
    platform = data.get("platform", "").strip()
    path = data.get("path", "").strip()

    if not platform or not path:
        return jsonify({"success": False, "error": "Missing platform or path"})

    folders = load_folders()
    if platform in folders and path in folders[platform]:
        folders[platform].remove(path)
        save_folders(folders)

    return jsonify({"success": True, "folders": folders})


# =========================
# BROWSE FOR FOLDER (tkinter folder picker)
# Opens a Windows folder picker dialog.
# Note: dialog may appear behind other windows — check your taskbar.
# =========================
@app.route("/api/browse/folder", methods=["POST"])
def browse_folder():
    result = {"path": None, "cancelled": False}

    def pick():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            path = filedialog.askdirectory(title="Select Folder")
            root.destroy()
            result["path"] = path if path else None
            if not path:
                result["cancelled"] = True
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=pick)
    t.start()
    t.join(timeout=60)

    if result.get("path"):
        return jsonify({"success": True, "path": result["path"]})
    elif result.get("cancelled"):
        return jsonify({"success": False, "cancelled": True})
    else:
        return jsonify({"success": False, "error": result.get("error", "Unknown error")})


# =========================
# OPEN SCREENSHOT FOLDER IN EXPLORER
# =========================
@app.route("/api/folders/open", methods=["POST"])
def open_folder():
    data = request.json or {}
    path = data.get("path", "").strip()

    if not path:
        return jsonify({"success": False, "error": "No path provided"})

    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Folder not found"})

    try:
        subprocess.Popen(f'explorer "{path}"')
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# SETTINGS
# =========================
@app.route("/api/settings")
def get_settings():
    return jsonify(load_settings())


@app.route("/api/settings", methods=["POST"])
def save_settings():
    save_settings_data(request.json)
    return jsonify({"success": True})


# =========================
# SOUND UPLOAD
# Stores custom notification sound in data/sounds/
# =========================
@app.route("/api/sound/upload", methods=["POST"])
def upload_sound():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"})

    f = request.files["file"]
    if not f.filename:
        return jsonify({"success": False, "error": "No filename"})

    # Only allow audio files
    allowed = {".mp3", ".wav", ".ogg", ".m4a"}
    ext = os.path.splitext(f.filename.lower())[1]
    if ext not in allowed:
        return jsonify({"success": False, "error": f"File type {ext} not allowed. Use mp3, wav, ogg or m4a."})

    os.makedirs("static/sounds", exist_ok=True)
    save_path = f"static/sounds/notification{ext}"
    f.save(save_path)

    # Save the path in settings
    settings = load_settings()
    settings["notification_sound"] = f"/static/sounds/notification{ext}"
    save_settings_data(settings)

    return jsonify({"success": True, "path": f"/static/sounds/notification{ext}"})


# =========================
# SOUND DELETE (revert to default)
# =========================
@app.route("/api/sound/delete", methods=["POST"])
def delete_sound():
    settings = load_settings()
    old_path = settings.get("notification_sound", "")

    # Remove file if it exists
    if old_path and old_path.startswith("/static/sounds/"):
        full = old_path.lstrip("/")
        if os.path.exists(full):
            os.remove(full)

    settings["notification_sound"] = ""
    save_settings_data(settings)
    return jsonify({"success": True})


# =========================
# DETECTION LOG
# Returns recent console output for debugging
# =========================
import io, sys

_log_buffer = []
_orig_stdout = sys.stdout

class LogCapture:
    def write(self, msg):
        _orig_stdout.write(msg)
        if msg.strip():
            _log_buffer.append(msg.strip())
            if len(_log_buffer) > 200:
                _log_buffer.pop(0)
    def flush(self):
        _orig_stdout.flush()

sys.stdout = LogCapture()


@app.route("/api/log")
def get_log():
    lines = list(_log_buffer)
    lines.reverse()
    return jsonify(lines)


# =========================
# GALLERY API
# =========================
@app.route("/api/gallery/screenshots")
def gallery_screenshots():
    from gallery_manager import list_screenshots, paginate
    game   = request.args.get("game", "")
    type_  = request.args.get("type", "")
    page   = int(request.args.get("page", 1))
    per    = int(request.args.get("per_page", 24))

    items = list_screenshots(
        game_filter = game or None,
        type_filter = type_ or None
    )
    result = paginate(items, page, per)

    settings = load_settings()
    base = settings.get("screenshot_folder", "screenshots")

    # Store paths in a session cache, serve by index
    import hashlib
    for item in result["items"]:
        h = hashlib.md5(item["path"].encode()).hexdigest()
        _path_cache[h] = item["path"]
        item["url"]   = f"/api/gallery/file/{h}"
        item["thumb"] = f"/api/gallery/thumb/{h}"

    return jsonify(result)


@app.route("/api/gallery/games")
def gallery_games():
    from gallery_manager import list_games
    return jsonify(list_games())


@app.route("/api/gallery/file/<h>")
def gallery_file(h):
    from flask import send_from_directory as sfd
    try:
        path = _path_cache.get(h, "")
        if not path or not os.path.exists(path):
            return jsonify({"error": "Not found"}), 404
        return sfd(
            os.path.abspath(os.path.dirname(path)),
            os.path.basename(path)
        )
    except Exception as e:
        print(f"[GAL] File route error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/gallery/thumb/<h>")
def gallery_thumb(h):
    from flask import send_from_directory as sfd
    from gallery_manager import ensure_thumbnail
    try:
        path = _path_cache.get(h, "")
        if not path or not os.path.exists(path):
            return sfd(os.path.abspath("static"), "icon.png")

        try:
            thumb = ensure_thumbnail(path)
            if thumb and os.path.exists(thumb):
                return sfd(
                    os.path.abspath(os.path.dirname(thumb)),
                    os.path.basename(thumb)
                )
        except Exception as te:
            print(f"[GAL] Thumbnail generation failed: {te}")

        # Fall back to full image
        return sfd(
            os.path.abspath(os.path.dirname(path)),
            os.path.basename(path)
        )
    except Exception as e:
        print(f"[GAL] Thumb route error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/gallery/open", methods=["POST"])
def gallery_open():
    """Open a screenshot in the configured app (default: mspaint)."""
    path = os.path.normpath((request.json or {}).get("path", ""))
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "File not found"})

    settings = load_settings()
    open_with = settings.get("open_with", "mspaint")

    try:
        subprocess.Popen([open_with, path])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/gallery/delete", methods=["POST"])
def gallery_delete():
    path = os.path.normpath((request.json or {}).get("path", ""))
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "File not found"})
    try:
        os.remove(path)
        # Also remove thumbnail if it exists
        from gallery_manager import thumb_path_for
        thumb = thumb_path_for(path)
        if os.path.exists(thumb):
            os.remove(thumb)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# MANUAL BURST
# =========================
@app.route("/api/burst/fire", methods=["POST"])
def fire_burst():
    try:
        from screenshots import fire_achievement_burst
        import threading

        settings = load_settings()

        # Get active platform from state
        try:
            with open("status/state.json", "r") as f:
                st = json.load(f)
            platform = st.get("activePlatform", "steam")
        except:
            platform = "steam"

        threading.Thread(
            target=fire_achievement_burst,
            args=(platform, settings),
            daemon=True
        ).start()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# DEBUG MODE TOGGLE
# =========================
@app.route("/api/debug/status")
def debug_status():
    settings = load_settings()
    return jsonify({"debug_mode": settings.get("debug_mode", False)})


@app.route("/api/debug/set", methods=["POST"])
def debug_set():
    enabled = request.json.get("enabled", False)
    settings = load_settings()
    settings["debug_mode"] = enabled
    save_settings_data(settings)
    return jsonify({"success": True, "debug_mode": enabled})


# =========================
# STEAM APPID LOOKUP
# Uses Steam's public API - no key required
# =========================
@app.route("/api/steam/lookup")
def steam_appid_lookup():
    appid = request.args.get("appid", "").strip()
    if not appid or not appid.isdigit():
        return jsonify({"success": False, "error": "Invalid AppID"})

    try:
        import urllib.request
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic"
        req = urllib.request.Request(url, headers={"User-Agent": "ShotTaker/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        app_data = data.get(str(appid), {})
        if app_data.get("success") and app_data.get("data"):
            name = app_data["data"].get("name", "")
            return jsonify({"success": True, "name": name, "appid": appid})
        else:
            return jsonify({"success": False, "error": "AppID not found"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# STEAM BATCH LOOKUP
# Look up multiple AppIDs at once
# =========================
@app.route("/api/steam/lookup/batch", methods=["POST"])
def steam_appid_batch():
    appids = (request.json or {}).get("appids", [])
    results = {}

    for appid in appids[:20]:  # Cap at 20 to avoid hammering Steam API
        appid = str(appid).strip()
        if not appid.isdigit():
            continue
        try:
            import urllib.request, time
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic"
            req = urllib.request.Request(url, headers={"User-Agent": "ShotTaker/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            app_data = data.get(str(appid), {})
            if app_data.get("success") and app_data.get("data"):
                results[appid] = app_data["data"].get("name", "")
            time.sleep(0.5)  # Be polite to Steam API
        except Exception as e:
            results[appid] = None

    return jsonify(results)


# =========================
# BULK RENAME
# =========================
@app.route("/api/gallery/rename", methods=["POST"])
def gallery_rename():
    from gallery_manager import bulk_rename
    data     = request.json or {}
    paths    = data.get("paths", [])
    game     = data.get("game_name", "").strip()
    shot_type = data.get("shot_type", "Imported")

    if not paths or not game:
        return jsonify({"success": False, "error": "Missing paths or game name"})

    settings = load_settings()
    results  = bulk_rename(paths, game, shot_type, settings)
    ok       = sum(1 for r in results if r["success"])

    return jsonify({"success": True, "results": results, "renamed": ok})


# =========================
# LAST SESSION
# =========================
@app.route("/api/session/last")
def last_session():
    try:
        with open("status/last_session.json", "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify(None)


@app.route("/api/gallery/session")
def gallery_session():
    """Return screenshots from the last game session."""
    from gallery_manager import list_screenshots, paginate, load_settings
    import hashlib

    try:
        with open("status/last_session.json", "r") as f:
            session = json.load(f)
    except:
        return jsonify({"items": [], "total": 0, "page": 1, "pages": 0})

    game    = session.get("game", "")
    start   = session.get("start", 0)
    end     = session.get("end", 0)

    # Get all screenshots and filter by game and time window
    all_shots = list_screenshots(game_filter=game or None)
    session_shots = [s for s in all_shots if start <= s["mtime"] <= end + 60]

    page   = int(request.args.get("page", 1))
    per    = int(request.args.get("per_page", 24))
    result = paginate(session_shots, page, per)

    for item in result["items"]:
        import hashlib
        h = hashlib.md5(item["path"].encode()).hexdigest()
        _path_cache[h] = item["path"]
        item["url"]   = f"/api/gallery/file/{h}"
        item["thumb"] = f"/api/gallery/thumb/{h}"

    result["session"] = session
    return jsonify(result)


# =========================
# SYSTEM INFO
# =========================
@app.route("/api/sysinfo")
def sysinfo():
    import platform
    import sys

    try:
        with open("data/settings.json") as f:
            s = json.load(f)
        version = s.get("version", "1.2")
    except:
        version = "1.2"

    return jsonify({
        "ShotTaker Version": version,
        "OS": platform.system() + " " + platform.release(),
        "OS Version": platform.version(),
        "Python": sys.version.split()[0],
        "Architecture": platform.machine(),
    })


# =========================
# STARTUP / WINDOW SETTINGS
# =========================
@app.route("/api/startup/status")
def startup_status():
    try:
        from app_window import is_in_startup
        return jsonify({"in_startup": is_in_startup()})
    except Exception as e:
        return jsonify({"in_startup": False, "error": str(e)})


@app.route("/api/startup/enable", methods=["POST"])
def startup_enable():
    try:
        from app_window import add_to_startup
        ok = add_to_startup()
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/startup/disable", methods=["POST"])
def startup_disable():
    try:
        from app_window import remove_from_startup
        ok = remove_from_startup()
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# START
# =========================
def run():
    app.run(host="127.0.0.1", port=5050, debug=False)
