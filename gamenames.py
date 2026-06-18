"""
ShotTaker — friendly game-name resolution.

Turns ugly executable names into readable titles:
  user override  >  folder-name hint (from scan)  >  prettified exe name

Stored in data/game_names.json: { "overrides": {...}, "hints": {...} }
"""

import re
import threading

import config

_lock = threading.Lock()


def _load():
    data = config.read_json(config.NAMEMAP_FILE, {}) or {}
    data.setdefault("overrides", {})
    data.setdefault("hints", {})
    return data


def _save(data):
    config.write_json(config.NAMEMAP_FILE, data)


def update_hints(hints):
    """Merge freshly scanned folder-name hints (don't clobber existing)."""
    if not hints:
        return
    with _lock:
        data = _load()
        for exe, name in hints.items():
            data["hints"].setdefault(exe.lower(), name)
        _save(data)


def set_override(exe, name):
    with _lock:
        data = _load()
        exe = exe.lower()
        if name and name.strip():
            data["overrides"][exe] = name.strip()
        else:
            data["overrides"].pop(exe, None)
        _save(data)


_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def prettify(exe):
    name = exe
    if name.lower().endswith(".exe"):
        name = name[:-4]
    name = name.replace("_", " ").replace("-", " ").replace(".", " ")
    name = _CAMEL.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    # Common suffixes that aren't part of the title
    for junk in (" win64 shipping", " win64", " shipping", " x64", " x86", " 64", " client"):
        if name.lower().endswith(junk):
            name = name[: -len(junk)]
    name = name.strip()
    return name.title() if name and name.islower() else (name or exe)


def friendly(exe):
    if not exe:
        return ""
    data = _load()
    e = exe.lower()
    if e in data["overrides"]:
        return data["overrides"][e]
    if e in data["hints"]:
        return data["hints"][e]
    return prettify(exe)


def resolve_all(exes):
    return {e: friendly(e) for e in exes}
