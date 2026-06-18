"""
ShotTaker — screenshot library metadata + storage management.

Maintains data/library.json: a map of {normalized_path: metadata} carrying
favorite / tags / rating / capture-reason / session / resolution. Also enforces
storage guardrails (max shots per game, max disk usage) with favorite protection.
"""

import os
import threading

import config

_lock = threading.Lock()


def _key(path):
    return os.path.normcase(os.path.abspath(path))


def _load():
    return config.read_json(config.LIBRARY_FILE, {}) or {}


def _save(idx):
    config.write_json(config.LIBRARY_FILE, idx)


DEFAULT_META = {
    "favorite": False,
    "tags": [],
    "rating": 0,
    "game": "",
    "type": "",
    "reason": "",
    "session": "",
    "ts": 0,
    "w": 0,
    "h": 0,
}


# =========================
# METADATA
# =========================
def record(path, **fields):
    """Create/update the metadata entry for a screenshot."""
    with _lock:
        idx = _load()
        k = _key(path)
        meta = idx.get(k, dict(DEFAULT_META))
        meta.update(fields)
        idx[k] = meta
        _save(idx)
    return meta


def get(path):
    idx = _load()
    return idx.get(_key(path), dict(DEFAULT_META))


def get_many(paths):
    idx = _load()
    out = {}
    for p in paths:
        out[p] = idx.get(_key(p), dict(DEFAULT_META))
    return out


def toggle_favorite(path):
    with _lock:
        idx = _load()
        k = _key(path)
        meta = idx.get(k, dict(DEFAULT_META))
        meta["favorite"] = not meta.get("favorite", False)
        idx[k] = meta
        _save(idx)
        return meta["favorite"]


def set_tags(path, tags):
    return record(path, tags=[t.strip() for t in tags if t.strip()])


def set_rating(path, rating):
    return record(path, rating=max(0, min(5, int(rating))))


def all_tags():
    idx = _load()
    tags = set()
    for meta in idx.values():
        for t in meta.get("tags", []):
            tags.add(t)
    return sorted(tags)


def is_favorite(path):
    return get(path).get("favorite", False)


# =========================
# RENAME / DELETE SYNC
# =========================
def on_rename(old, new):
    with _lock:
        idx = _load()
        ko, kn = _key(old), _key(new)
        if ko in idx:
            idx[kn] = idx.pop(ko)
            _save(idx)


def on_delete(path):
    with _lock:
        idx = _load()
        k = _key(path)
        if k in idx:
            idx.pop(k)
            _save(idx)


# =========================
# STORAGE GUARDRAILS
# =========================
def enforce_storage(settings, game_folder=None):
    """
    Apply max_shots_per_game and max_disk_mb. Deletes oldest, never favorites.
    Returns number of files removed.
    """
    removed = 0
    base = config.get_screenshot_folder(settings)
    exts = {".png", ".jpg", ".jpeg", ".webp"}

    max_per_game = int(settings.get("max_shots_per_game", 0) or 0)
    max_disk_mb = int(settings.get("max_disk_mb", 0) or 0)
    if max_per_game <= 0 and max_disk_mb <= 0:
        return 0

    def shots_in(folder):
        out = []
        if not os.path.isdir(folder):
            return out
        for root, dirs, files in os.walk(folder):
            if ".thumbs" in root:
                continue
            for fn in files:
                if os.path.splitext(fn)[1].lower() in exts:
                    p = os.path.join(root, fn)
                    try:
                        out.append((p, os.path.getmtime(p), os.path.getsize(p)))
                    except OSError:
                        pass
        return out

    # Per-game cap
    if max_per_game > 0 and game_folder and os.path.isdir(game_folder):
        files = sorted(shots_in(game_folder), key=lambda x: x[1])  # oldest first
        keepers = [f for f in files if not is_favorite(f[0])]
        excess = len(files) - max_per_game
        for p, _, _ in keepers[:max(0, excess)]:
            removed += _delete_with_thumb(p, settings)

    # Total disk cap
    if max_disk_mb > 0:
        files = sorted(shots_in(base), key=lambda x: x[1])
        total = sum(f[2] for f in files)
        limit = max_disk_mb * 1024 * 1024
        for p, _, sz in files:
            if total <= limit:
                break
            if is_favorite(p):
                continue
            total -= sz
            removed += _delete_with_thumb(p, settings)

    return removed


def _delete_with_thumb(path, settings):
    try:
        os.remove(path)
        on_delete(path)
        # remove thumbnail mirror
        base = config.get_screenshot_folder(settings)
        try:
            rel = os.path.relpath(path, base)
            thumb = os.path.join(base, ".thumbs", os.path.splitext(rel)[0] + ".jpg")
            if os.path.exists(thumb):
                os.remove(thumb)
        except ValueError:
            pass
        return 1
    except OSError:
        return 0
