"""
ShotTaker — gallery indexing, search, thumbnails, and bulk rename.

Lists screenshots from the configured folder, merges in library metadata
(favorite / tags / rating), supports filter+search+sort, and renames imported
files into the ShotTaker convention.
"""

import os
import shutil
from pathlib import Path

import config
import library

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SHOT_TYPES = ["TimeLapse", "DynamicShot", "Achievement", "Manual", "Imported"]


def get_screenshot_folder():
    return config.get_screenshot_folder()


def sanitise_game_name(name):
    clean = name
    for ch in '<>:"/\\|?*':
        clean = clean.replace(ch, "_")
    return clean.strip() or "Unknown"


# =========================
# THUMBNAILS
# =========================
def thumb_path_for(screenshot_path):
    base = Path(get_screenshot_folder())
    thumb_dir = base / ".thumbs"
    try:
        rel = Path(screenshot_path).relative_to(base)
        return str(thumb_dir / rel.with_suffix(".jpg"))
    except ValueError:
        return str(thumb_dir / (Path(screenshot_path).stem + ".jpg"))


def ensure_thumbnail(screenshot_path):
    if not PIL_AVAILABLE:
        return None
    thumb = thumb_path_for(screenshot_path)
    if os.path.exists(thumb):
        return thumb
    try:
        Path(thumb).parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(screenshot_path)
        img.thumbnail((400, 225), Image.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(thumb, "JPEG", quality=82, optimize=True)
        return thumb
    except Exception as e:
        print(f"[GAL] Thumbnail error: {e}")
        return None


# =========================
# PARSE
# =========================
def parse_screenshot(f, base):
    name = f.stem
    try:
        rel_parts = f.relative_to(base).parts
        folder_game = rel_parts[0] if len(rel_parts) > 1 else None
    except ValueError:
        folder_game = None

    shot_type, game_name, shot_num = None, None, 0
    for st in SHOT_TYPES:
        if f"_{st}_" in name:
            idx = name.rfind(f"_{st}_")
            game_name = name[:idx]
            rest = name[idx + 1:].split("_", 1)
            shot_type = rest[0]
            try:
                shot_num = int(rest[1]) if len(rest) > 1 else 0
            except ValueError:
                shot_num = 0
            break
    if not game_name:
        game_name = folder_game or "Unknown"
        shot_type = "Imported"

    try:
        mtime = f.stat().st_mtime
        size = f.stat().st_size
    except OSError:
        mtime = size = 0

    meta = library.get(str(f))
    return {
        "path": str(f),
        "game": game_name,
        "type": shot_type,
        "num": shot_num,
        "filename": f.name,
        "mtime": mtime,
        "size": size,
        "ext": f.suffix.lower(),
        "favorite": meta.get("favorite", False),
        "tags": meta.get("tags", []),
        "rating": meta.get("rating", 0),
        "reason": meta.get("reason", ""),
    }


# =========================
# LIST + SEARCH + SORT
# =========================
def list_screenshots(game_filter=None, type_filter=None, favorites_only=False,
                     tag=None, search=None, sort="newest"):
    base = Path(get_screenshot_folder())
    if not base.exists():
        return []

    results = []
    search_l = (search or "").lower().strip()
    for f in base.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in EXTS or ".thumbs" in f.parts:
            continue
        item = parse_screenshot(f, base)
        if game_filter and game_filter != item["game"]:
            continue
        if type_filter and type_filter != item["type"]:
            continue
        if favorites_only and not item["favorite"]:
            continue
        if tag and tag not in item["tags"]:
            continue
        if search_l and search_l not in item["filename"].lower() and search_l not in item["game"].lower() \
                and not any(search_l in t.lower() for t in item["tags"]):
            continue
        results.append(item)

    reverse = sort != "oldest"
    if sort in ("largest", "smallest"):
        results.sort(key=lambda x: x["size"], reverse=(sort == "largest"))
    elif sort == "rating":
        results.sort(key=lambda x: (x["rating"], x["mtime"]), reverse=True)
    else:
        results.sort(key=lambda x: x["mtime"], reverse=reverse)
    return results


def list_games():
    base = Path(get_screenshot_folder())
    games = set()
    if base.exists():
        for item in base.iterdir():
            if item.is_dir() and item.name != ".thumbs":
                games.add(item.name)
        for item in list_screenshots():
            if item["game"] and item["game"] != "Unknown":
                games.add(item["game"])
    return sorted(games)


def list_types():
    return SHOT_TYPES


# =========================
# BULK RENAME
# =========================
def bulk_rename(file_paths, game_name, shot_type, settings):
    from capture_manager import next_counter

    game_name = sanitise_game_name(game_name)
    base = Path(config.get_screenshot_folder(settings))
    per_game = settings.get("per_game_folders", True)
    results = []

    for old_str in file_paths:
        old = Path(os.path.normpath(old_str))
        if not old.exists():
            results.append({"old_path": old_str, "success": False, "error": "File not found"})
            continue
        try:
            ext = old.suffix.lower() if old.suffix.lower() in EXTS else ".png"
            n = next_counter(game_name, shot_type)
            new_dir = base / game_name if per_game else base
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / f"{game_name}_{shot_type}_{n:03d}{ext}"

            shutil.move(str(old), str(new_path))
            library.on_rename(str(old), str(new_path))

            old_thumb = Path(thumb_path_for(str(old)))
            if old_thumb.exists():
                new_thumb = Path(thumb_path_for(str(new_path)))
                new_thumb.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_thumb), str(new_thumb))

            if per_game and old.parent != new_dir and old.parent != base:
                try:
                    if not any(old.parent.iterdir()):
                        old.parent.rmdir()
                except OSError:
                    pass

            results.append({"old_path": old_str, "new_path": str(new_path), "success": True})
        except Exception as e:
            results.append({"old_path": old_str, "success": False, "error": str(e)})
    return results


def paginate(items, page, per_page=24):
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    return {
        "items": items[start:start + per_page],
        "total": total, "page": page, "pages": pages, "per_page": per_page,
    }
