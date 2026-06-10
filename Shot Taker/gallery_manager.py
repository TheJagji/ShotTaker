import os
import json
import shutil
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# =========================
# LOAD SETTINGS
# =========================
def load_settings():
    try:
        with open("data/settings.json", "r") as f:
            return json.load(f)
    except:
        return {}


# =========================
# GET SCREENSHOT FOLDER
# =========================
def get_screenshot_folder():
    return load_settings().get("screenshot_folder", "screenshots")


# =========================
# SANITISE GAME NAME
# Only strips Windows-illegal filename chars, keeps spaces (Steam convention)
# =========================
def sanitise_game_name(name):
    clean = name
    for ch in '<>:"/\\|?*':
        clean = clean.replace(ch, '_')
    return clean.strip() or "Unknown"


# =========================
# THUMB PATH FOR SCREENSHOT
# =========================
def thumb_path_for(screenshot_path):
    base = Path(get_screenshot_folder())
    thumb_dir = base / ".thumbs"
    try:
        rel = Path(screenshot_path).relative_to(base)
        return str(thumb_dir / rel.with_suffix(".jpg"))
    except:
        name = Path(screenshot_path).stem
        return str(thumb_dir / (name + ".jpg"))


# =========================
# ENSURE THUMBNAIL EXISTS
# =========================
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
# PARSE SCREENSHOT FILE
# Handles both our naming convention and imported files
# =========================
def parse_screenshot(f, base):
    """
    Returns a dict describing a screenshot file.
    Handles:
    - Our convention: GameName_TimeLapse_001.png
    - Files in subfolders: folder name = game name
    - Files in root: game = "Unknown"
    - Any .png/.jpg/.jpeg file
    """
    name = f.stem
    parts = f.parts

    # Determine game name from folder structure first
    try:
        rel = f.relative_to(base)
        rel_parts = rel.parts
        # File is in a subfolder — folder name is the game
        if len(rel_parts) > 1:
            folder_game = rel_parts[0]
        else:
            folder_game = None
    except:
        folder_game = None

    shot_type = None
    game_name = None
    shot_num  = 0

    # Try to parse our naming convention
    for shot_t in ["DynamicShot", "TimeLapse", "Achievement", "Imported"]:
        if f"_{shot_t}_" in name:
            idx = name.rfind(f"_{shot_t}_")
            parsed_game = name[:idx]
            rest = name[idx + 1:]
            type_and_num = rest.split("_", 1)
            shot_type = type_and_num[0]
            try:
                shot_num = int(type_and_num[1]) if len(type_and_num) > 1 else 0
            except:
                shot_num = 0
            game_name = parsed_game
            break

    # If not our convention
    if not game_name:
        # Use folder name as game if available, otherwise Unknown
        game_name = folder_game if folder_game else "Unknown"
        shot_type = "Imported"
        shot_num  = 0

    try:
        mtime = f.stat().st_mtime
    except:
        mtime = 0

    return {
        "path":     str(f),
        "game":     game_name,
        "type":     shot_type,
        "num":      shot_num,
        "filename": f.name,
        "mtime":    mtime,
        "ext":      f.suffix.lower(),
    }


# =========================
# LIST ALL SCREENSHOTS
# Picks up PNG, JPG, JPEG — both our convention and imported files
# =========================
def list_screenshots(game_filter=None, type_filter=None):
    base = Path(get_screenshot_folder())
    if not base.exists():
        return []

    results = []
    extensions = {".png", ".jpg", ".jpeg"}

    for f in base.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in extensions:
            continue
        # Skip thumbnails folder
        if ".thumbs" in f.parts:
            continue

        item = parse_screenshot(f, base)

        if game_filter and game_filter != item["game"]:
            continue
        if type_filter and type_filter != item["type"]:
            continue

        results.append(item)

    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


# =========================
# LIST GAME NAMES
# Includes both parsed names and folder names
# =========================
def list_games():
    base = Path(get_screenshot_folder())
    games = set()

    if base.exists():
        # Add folder names as game names
        for item in base.iterdir():
            if item.is_dir() and item.name != ".thumbs":
                games.add(item.name)

        # Also add parsed game names from files
        for item in list_screenshots():
            if item["game"] and item["game"] != "Unknown":
                games.add(item["game"])

    return sorted(games)


# =========================
# LIST SHOT TYPES
# =========================
def list_types():
    return ["TimeLapse", "DynamicShot", "Achievement", "Imported"]


# =========================
# BULK RENAME
# Renames a list of files to our convention with a new game name and type.
# Moves files to correct subfolder if per_game_folders is enabled.
# Returns list of {old_path, new_path, success, error}
# =========================
def bulk_rename(file_paths, game_name, shot_type, settings):
    from capture_manager import next_counter

    game_name = sanitise_game_name(game_name)
    base      = Path(settings.get("screenshot_folder", "screenshots"))
    per_game  = settings.get("per_game_folders", True)

    results = []

    for old_path_str in file_paths:
        old_path = Path(os.path.normpath(old_path_str))

        if not old_path.exists():
            results.append({"old_path": old_path_str, "success": False, "error": f"File not found: {old_path}"})
            continue

        try:
            # Keep original extension
            orig_ext = old_path.suffix.lower()
            ext = orig_ext if orig_ext in (".png", ".jpg", ".jpeg") else ".png"

            n        = next_counter(game_name, shot_type)
            new_name = f"{game_name}_{shot_type}_{n:03d}{ext}"

            if per_game:
                new_dir = base / game_name
            else:
                new_dir = base

            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / new_name

            # Move the file
            shutil.move(str(old_path), str(new_path))

            # Move thumbnail if it exists
            try:
                old_thumb = Path(thumb_path_for(str(old_path)))
                if old_thumb.exists():
                    new_thumb = Path(thumb_path_for(str(new_path)))
                    new_thumb.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_thumb), str(new_thumb))
            except:
                pass

            # Remove old empty folder
            try:
                if per_game and old_path.parent != new_dir and old_path.parent != base:
                    if not any(old_path.parent.iterdir()):
                        old_path.parent.rmdir()
            except:
                pass

            results.append({
                "old_path": old_path_str,
                "new_path": str(new_path),
                "success": True
            })

        except Exception as e:
            results.append({"old_path": old_path_str, "success": False, "error": str(e)})

    return results


# =========================
# PAGINATE
# =========================
def paginate(items, page, per_page=24):
    total  = len(items)
    pages  = max(1, (total + per_page - 1) // per_page)
    page   = max(1, min(page, pages))
    start  = (page - 1) * per_page
    end    = start + per_page
    return {
        "items":    items[start:end],
        "total":    total,
        "page":     page,
        "pages":    pages,
        "per_page": per_page,
    }
