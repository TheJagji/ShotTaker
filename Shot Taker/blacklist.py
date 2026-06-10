"""
ShotTaker — blacklist management (user + shipped defaults).
"""

import os

import config


def load_blacklist():
    if not os.path.exists(config.BLACKLIST_FILE):
        return []
    with open(config.BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return [x.strip().lower() for x in f if x.strip()]


def load_default_blacklist():
    if not os.path.exists(config.BLACKLIST_DEFAULT_FILE):
        return []
    with open(config.BLACKLIST_DEFAULT_FILE, "r", encoding="utf-8") as f:
        return [x.strip().lower() for x in f
                if x.strip() and not x.strip().startswith("#")]


def load_full_blacklist():
    return set(load_blacklist()) | set(load_default_blacklist())


def _write(lines):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.BLACKLIST_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def add_to_blacklist(exe):
    exe = exe.lower().strip()
    if not exe:
        return
    lines = load_blacklist()
    if exe not in lines:
        lines.append(exe)
        _write(lines)


def remove_from_blacklist(exe):
    exe = exe.lower().strip()
    _write([x for x in load_blacklist() if x != exe])


def move_to_games(exe):
    exe = exe.lower().strip()
    remove_from_blacklist(exe)
    if os.path.exists(config.DISABLED_FILE):
        with open(config.DISABLED_FILE, "r", encoding="utf-8") as f:
            lines = [x.strip() for x in f if x.strip()]
        with open(config.DISABLED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(x for x in lines if x != exe))
