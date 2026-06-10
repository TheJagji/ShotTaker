"""
ShotTaker — Flask web server and REST API.
Serves the UI and exposes all backend functionality to the front-end.
"""

import os
import io
import sys
import json
import hashlib
import subprocess
import threading

from flask import Flask, render_template, jsonify, request, send_from_directory

import config
import scanner
import gamenames
from branding import BRAND, generate_icon
from blacklist import load_blacklist, add_to_blacklist, remove_from_blacklist
from platform_detect import run_detection
from steam_detect import detect_steam_libraries

app = Flask(__name__, template_folder=config.TEMPLATES_DIR, static_folder=config.STATIC_DIR)

_path_cache = {}


def _cache(path):
    h = hashlib.md5(os.path.abspath(path).encode()).hexdigest()
    _path_cache[h] = path
    return h


def _attach_urls(items):
    for item in items:
        h = _cache(item["path"])
        item["url"] = f"/api/gallery/file/{h}"
        item["thumb"] = f"/api/gallery/thumb/{h}"
        item["name"] = gamenames.friendly(item["game"]) if item["game"].endswith(".exe") else item["game"]
    return items


# =========================
# BRAND + UI
# =========================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/brand")
def brand():
    return jsonify(BRAND)


@app.route("/favicon.ico")
def favicon():
    for fn in ("icon.ico", "icon.png"):
        if os.path.exists(os.path.join(config.STATIC_DIR, fn)):
            return send_from_directory(config.STATIC_DIR, fn)
    return "", 204


# =========================
# SETUP
# =========================
@app.route("/api/setup/status")
def setup_status():
    return jsonify({"setup_complete": config.settings_exists()})


@app.route("/api/setup/complete", methods=["POST"])
def setup_complete():
    data = request.json or {}
    config.save_settings(data)
    scanner.scan_games()
    return jsonify({"success": True})


# =========================
# STATUS / STATS
# =========================
@app.route("/api/status")
def status():
    return jsonify(config.read_json(config.STATE_FILE, {
        "games": 0, "activeGame": "", "activePlatform": "", "gameActive": False}))


@app.route("/api/stats")
def stats_basic():
    return jsonify(config.read_json(config.STATS_FILE, {"scan_count": 0, "screenshots_taken": 0}))


@app.route("/api/stats/summary")
def stats_summary():
    import stats as stats_mod
    return jsonify(stats_mod.summary())


@app.route("/api/sessions")
def sessions():
    data = config.read_json(config.SESSIONS_FILE, []) or []
    for s in data:
        s["name"] = gamenames.friendly(s.get("game", ""))
    return jsonify(list(reversed(data)))


@app.route("/api/events")
def events():
    data = config.read_json(config.EVENTS_FILE, []) or []
    return jsonify(list(reversed(data[-200:])))


@app.route("/api/capture/last")
def last_capture():
    return jsonify(config.read_json(config.data_path("status", "last_capture.json"), None))


# =========================
# GAMES / NAMES
# =========================
@app.route("/api/games")
def games():
    g = config.read_json(config.GAMES_FILE, {}) or {}
    return jsonify({"games": g, "names": gamenames.resolve_all(list(g.keys()))})


@app.route("/api/games/disable", methods=["POST"])
def disable_game():
    exe = (request.json or {}).get("exe", "").lower().strip()
    if exe:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(config.DISABLED_FILE, "a", encoding="utf-8") as f:
            f.write(exe + "\n")
        scanner.scan_games()
    return jsonify({"success": True})


@app.route("/api/names/set", methods=["POST"])
def set_name():
    data = request.json or {}
    gamenames.set_override(data.get("exe", ""), data.get("name", ""))
    return jsonify({"success": True})


# =========================
# BLACKLIST
# =========================
@app.route("/api/blacklist")
def blacklist():
    return jsonify(load_blacklist())


@app.route("/api/blacklist/add", methods=["POST"])
def blacklist_add():
    exe = (request.json or {}).get("exe", "").lower().strip()
    if exe:
        add_to_blacklist(exe)
        scanner.scan_games()
    return jsonify({"success": True})


@app.route("/api/blacklist/remove", methods=["POST"])
def blacklist_remove():
    exe = (request.json or {}).get("exe", "").lower().strip()
    if exe:
        remove_from_blacklist(exe)
    return jsonify({"success": True})


@app.route("/api/blacklist/move_to_games", methods=["POST"])
def move_to_games():
    exe = (request.json or {}).get("exe", "").lower().strip()
    if exe:
        remove_from_blacklist(exe)
        scanner.scan_games()
    return jsonify({"success": True})


@app.route("/api/scan/games")
def scan_games_route():
    scanner.scan_games()
    return jsonify({"success": True})


# =========================
# FOLDERS
# =========================
@app.route("/api/folders")
def folders():
    return jsonify(config.read_json(config.FOLDERS_FILE, {}) or {})


@app.route("/api/folders/save", methods=["POST"])
def save_folders_api():
    config.write_json(config.FOLDERS_FILE, request.json)
    return jsonify({"success": True})


@app.route("/api/folders/autodetect", methods=["POST"])
def autodetect():
    selected = request.json or {}
    results = run_detection(selected)
    if selected.get("steam"):
        vdf = detect_steam_libraries()
        results["steam"] = list(set(results.get("steam", []) + vdf))
    folders = config.read_json(config.FOLDERS_FILE, {}) or {}
    for key, new_paths in results.items():
        folders[key] = list(set(folders.get(key, []) + new_paths))
    config.write_json(config.FOLDERS_FILE, folders)
    return jsonify({"success": True, "results": results, "folders": folders})


@app.route("/api/folders/add", methods=["POST"])
def add_folder():
    data = request.json or {}
    platform, path = data.get("platform", "").strip(), data.get("path", "").strip()
    if not platform or not path:
        return jsonify({"success": False, "error": "Missing platform or path"})
    folders = config.read_json(config.FOLDERS_FILE, {}) or {}
    folders.setdefault(platform, [])
    if path not in folders[platform]:
        folders[platform].append(path)
        config.write_json(config.FOLDERS_FILE, folders)
    return jsonify({"success": True, "folders": folders})


@app.route("/api/folders/remove", methods=["POST"])
def remove_folder():
    data = request.json or {}
    platform, path = data.get("platform", "").strip(), data.get("path", "").strip()
    folders = config.read_json(config.FOLDERS_FILE, {}) or {}
    if platform in folders and path in folders[platform]:
        folders[platform].remove(path)
        config.write_json(config.FOLDERS_FILE, folders)
    return jsonify({"success": True, "folders": folders})


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
            result["path"] = path or None
            result["cancelled"] = not path
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=pick)
    t.start()
    t.join(timeout=120)
    if result.get("path"):
        return jsonify({"success": True, "path": result["path"]})
    if result.get("cancelled"):
        return jsonify({"success": False, "cancelled": True})
    return jsonify({"success": False, "error": result.get("error", "Unknown error")})


@app.route("/api/folders/open", methods=["POST"])
def open_folder():
    path = (request.json or {}).get("path", "").strip()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "Folder not found"})
    try:
        os.startfile(path)  # noqa: explorer
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# SETTINGS / PROFILES
# =========================
@app.route("/api/settings")
def get_settings():
    return jsonify(config.load_settings())


@app.route("/api/settings", methods=["POST"])
def save_settings():
    config.save_settings(request.json or {})
    return jsonify({"success": True})


@app.route("/api/profiles")
def get_profiles():
    return jsonify(config.load_profiles())


@app.route("/api/profiles/save", methods=["POST"])
def save_profiles():
    data = request.json or {}
    exe = (data.get("exe") or "").lower().strip()
    profile = data.get("profile") or {}
    profiles = config.load_profiles()
    if profile:
        profiles[exe] = profile
    else:
        profiles.pop(exe, None)
    config.save_profiles(profiles)
    return jsonify({"success": True, "profiles": profiles})


# =========================
# CAPTURE CONTROL
# =========================
@app.route("/api/capture/pause", methods=["POST"])
def toggle_pause():
    paused = bool((request.json or {}).get("paused", False))
    config.update_settings(capture_paused=paused)
    return jsonify({"success": True, "paused": paused})


@app.route("/api/monitors")
def monitors():
    out = []
    try:
        import mss
        with mss.mss() as sct:
            for i, m in enumerate(sct.monitors):
                out.append({"index": i, "label": ("All displays" if i == 0 else f"Display {i}"),
                            "width": m["width"], "height": m["height"]})
    except Exception as e:
        print(f"[WEB] Monitor enum error: {e}")
    return jsonify(out)


# =========================
# SOUND
# =========================
@app.route("/api/sound/upload", methods=["POST"])
def upload_sound():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"})
    f = request.files["file"]
    ext = os.path.splitext((f.filename or "").lower())[1]
    if ext not in {".mp3", ".wav", ".ogg", ".m4a"}:
        return jsonify({"success": False, "error": "Use mp3, wav, ogg or m4a."})
    os.makedirs(config.SOUNDS_DIR, exist_ok=True)
    f.save(os.path.join(config.SOUNDS_DIR, f"notification{ext}"))
    config.update_settings(notification_sound=f"/static/sounds/notification{ext}")
    return jsonify({"success": True, "path": f"/static/sounds/notification{ext}"})


@app.route("/api/sound/delete", methods=["POST"])
def delete_sound():
    s = config.load_settings()
    old = s.get("notification_sound", "")
    if old.startswith("/static/sounds/"):
        full = os.path.join(config.app_dir(), old.lstrip("/").replace("/", os.sep))
        if os.path.exists(full):
            os.remove(full)
    config.update_settings(notification_sound="")
    return jsonify({"success": True})


# =========================
# GALLERY
# =========================
@app.route("/api/gallery/screenshots")
def gallery_screenshots():
    from gallery_manager import list_screenshots, paginate
    items = list_screenshots(
        game_filter=request.args.get("game") or None,
        type_filter=request.args.get("type") or None,
        favorites_only=request.args.get("favorites") == "1",
        tag=request.args.get("tag") or None,
        search=request.args.get("search") or None,
        sort=request.args.get("sort", "newest"),
    )
    result = paginate(items, int(request.args.get("page", 1)), int(request.args.get("per_page", 24)))
    _attach_urls(result["items"])
    return jsonify(result)


@app.route("/api/gallery/games")
def gallery_games():
    from gallery_manager import list_games
    g = list_games()
    return jsonify([{"folder": x, "name": gamenames.friendly(x) if x.endswith(".exe") else x} for x in g])


@app.route("/api/gallery/tags")
def gallery_tags():
    return jsonify(library_all_tags())


def library_all_tags():
    import library
    return library.all_tags()


@app.route("/api/gallery/file/<h>")
def gallery_file(h):
    path = _path_cache.get(h, "")
    if not path or not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(os.path.dirname(path), os.path.basename(path))


@app.route("/api/gallery/thumb/<h>")
def gallery_thumb(h):
    from gallery_manager import ensure_thumbnail
    path = _path_cache.get(h, "")
    if not path or not os.path.exists(path):
        return send_from_directory(config.STATIC_DIR, "icon.png")
    try:
        thumb = ensure_thumbnail(path)
        if thumb and os.path.exists(thumb):
            return send_from_directory(os.path.dirname(thumb), os.path.basename(thumb))
    except Exception as e:
        print(f"[GAL] thumb error: {e}")
    return send_from_directory(os.path.dirname(path), os.path.basename(path))


@app.route("/api/gallery/open", methods=["POST"])
def gallery_open():
    path = os.path.normpath((request.json or {}).get("path", ""))
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "File not found"})
    open_with = config.load_settings().get("open_with", "")
    try:
        if open_with:
            subprocess.Popen([open_with, path])
        else:
            os.startfile(path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/gallery/delete", methods=["POST"])
def gallery_delete():
    import library
    from gallery_manager import thumb_path_for
    paths = (request.json or {}).get("paths")
    if not paths:
        single = (request.json or {}).get("path")
        paths = [single] if single else []
    deleted = 0
    for p in paths:
        p = os.path.normpath(p)
        if not os.path.exists(p):
            continue
        try:
            os.remove(p)
            library.on_delete(p)
            thumb = thumb_path_for(p)
            if os.path.exists(thumb):
                os.remove(thumb)
            deleted += 1
        except OSError:
            pass
    return jsonify({"success": True, "deleted": deleted})


@app.route("/api/gallery/favorite", methods=["POST"])
def gallery_favorite():
    import library
    path = os.path.normpath((request.json or {}).get("path", ""))
    return jsonify({"success": True, "favorite": library.toggle_favorite(path)})


@app.route("/api/gallery/tag", methods=["POST"])
def gallery_tag():
    import library
    data = request.json or {}
    meta = library.set_tags(os.path.normpath(data.get("path", "")), data.get("tags", []))
    return jsonify({"success": True, "tags": meta.get("tags", [])})


@app.route("/api/gallery/rate", methods=["POST"])
def gallery_rate():
    import library
    data = request.json or {}
    meta = library.set_rating(os.path.normpath(data.get("path", "")), data.get("rating", 0))
    return jsonify({"success": True, "rating": meta.get("rating", 0)})


@app.route("/api/gallery/rename", methods=["POST"])
def gallery_rename():
    from gallery_manager import bulk_rename
    data = request.json or {}
    paths, game = data.get("paths", []), data.get("game_name", "").strip()
    if not paths or not game:
        return jsonify({"success": False, "error": "Missing paths or game name"})
    results = bulk_rename(paths, game, data.get("shot_type", "Imported"), config.load_settings())
    return jsonify({"success": True, "results": results,
                    "renamed": sum(1 for r in results if r["success"])})


@app.route("/api/session/last")
def session_last():
    return jsonify(config.read_json(config.LASTSESSION_FILE, None))


@app.route("/api/gallery/session")
def gallery_session():
    from gallery_manager import list_screenshots, paginate
    session = config.read_json(config.LASTSESSION_FILE, None)
    if not session:
        return jsonify({"items": [], "total": 0, "page": 1, "pages": 0})
    game = session.get("game", "")
    start, end = session.get("start", 0), session.get("end", 0)
    shots = [s for s in list_screenshots() if start <= s["mtime"] <= end + 60]
    result = paginate(shots, int(request.args.get("page", 1)), int(request.args.get("per_page", 24)))
    _attach_urls(result["items"])
    result["session"] = session
    return jsonify(result)


# =========================
# EXPORT
# =========================
@app.route("/api/export/<kind>", methods=["POST"])
def export_route(kind):
    import export as ex
    paths = (request.json or {}).get("paths", [])
    if not paths:
        return jsonify({"success": False, "error": "No screenshots selected"})
    try:
        if kind == "zip":
            out = ex.export_zip(paths)
        elif kind == "contactsheet":
            out = ex.contact_sheet(paths)
        elif kind == "gif":
            out = ex.make_gif(paths, fps=int((request.json or {}).get("fps", 2)))
        else:
            return jsonify({"success": False, "error": "Unknown export type"})
        if not out:
            return jsonify({"success": False, "error": "Export failed"})
        try:
            os.startfile(os.path.dirname(out))
        except Exception:
            pass
        return jsonify({"success": True, "path": out})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# MANUAL BURST
# =========================
@app.route("/api/burst/fire", methods=["POST"])
def fire_burst():
    from screenshots import fire_achievement_burst
    st = config.read_json(config.STATE_FILE, {}) or {}
    game = st.get("activeGame", "") or "Manual"
    platform = st.get("activePlatform", "steam")
    settings = config.load_settings()
    settings["achievement_screenshots_enabled"] = True  # explicit user action
    threading.Thread(target=fire_achievement_burst, args=(game, platform, settings), daemon=True).start()
    return jsonify({"success": True})


@app.route("/api/capture/now", methods=["POST"])
def capture_now():
    from capture_manager import capture_screenshot
    st = config.read_json(config.STATE_FILE, {}) or {}
    game = st.get("activeGame", "") or "Manual"
    threading.Thread(target=capture_screenshot,
                     args=(game, "Manual", config.load_settings(), "manual", False), daemon=True).start()
    return jsonify({"success": True})


# =========================
# CONFIG IMPORT / EXPORT
# =========================
@app.route("/api/config/export")
def config_export():
    return jsonify({
        "settings": config.load_settings(),
        "folders": config.read_json(config.FOLDERS_FILE, {}),
        "profiles": config.load_profiles(),
        "blacklist": load_blacklist(),
        "names": config.read_json(config.NAMEMAP_FILE, {}),
    })


@app.route("/api/config/import", methods=["POST"])
def config_import():
    data = request.json or {}
    if "settings" in data:
        config.save_settings(data["settings"])
    if "folders" in data:
        config.write_json(config.FOLDERS_FILE, data["folders"])
    if "profiles" in data:
        config.save_profiles(data["profiles"])
    if "names" in data:
        config.write_json(config.NAMEMAP_FILE, data["names"])
    scanner.scan_games()
    return jsonify({"success": True})


# =========================
# DEBUG / SYSINFO / STARTUP / STEAM
# =========================
@app.route("/api/debug/status")
def debug_status():
    return jsonify({"debug_mode": config.load_settings().get("debug_mode", False)})


@app.route("/api/debug/set", methods=["POST"])
def debug_set():
    enabled = bool((request.json or {}).get("enabled", False))
    config.update_settings(debug_mode=enabled)
    return jsonify({"success": True, "debug_mode": enabled})


@app.route("/api/sysinfo")
def sysinfo():
    import platform
    return jsonify({
        "ShotTaker Version": BRAND["version"],
        "OS": f"{platform.system()} {platform.release()}",
        "Python": sys.version.split()[0],
        "Architecture": platform.machine(),
        "Frozen": config.is_frozen(),
    })


@app.route("/api/startup/status")
def startup_status():
    try:
        from app_window import is_in_startup
        return jsonify({"in_startup": is_in_startup()})
    except Exception as e:
        return jsonify({"in_startup": False, "error": str(e)})


@app.route("/api/startup/enable", methods=["POST"])
def startup_enable():
    from app_window import add_to_startup
    return jsonify({"success": add_to_startup()})


@app.route("/api/startup/disable", methods=["POST"])
def startup_disable():
    from app_window import remove_from_startup
    return jsonify({"success": remove_from_startup()})


@app.route("/api/steam/lookup")
def steam_lookup():
    appid = request.args.get("appid", "").strip()
    if not appid.isdigit():
        return jsonify({"success": False, "error": "Invalid AppID"})
    try:
        import urllib.request
        url = f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic"
        req = urllib.request.Request(url, headers={"User-Agent": "ShotTaker/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        app_data = data.get(str(appid), {})
        if app_data.get("success") and app_data.get("data"):
            return jsonify({"success": True, "name": app_data["data"].get("name", ""), "appid": appid})
        return jsonify({"success": False, "error": "AppID not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =========================
# LOG CAPTURE
# =========================
_log_buffer = []
_orig_stdout = sys.stdout


class LogCapture:
    def write(self, msg):
        try:
            _orig_stdout.write(msg)
        except Exception:
            pass
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8", "replace")
        if msg and msg.strip():
            _log_buffer.append(str(msg).strip())
            if len(_log_buffer) > 300:
                _log_buffer.pop(0)

    def flush(self):
        try:
            _orig_stdout.flush()
        except Exception:
            pass


sys.stdout = LogCapture()


@app.route("/api/log")
def get_log():
    return jsonify(list(reversed(_log_buffer)))


def run():
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False, threaded=True)
