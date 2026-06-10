import os


BLACKLIST_FILE = "data/blacklist.txt"
BLACKLIST_DEFAULT_FILE = "data/blacklist_default.txt"


# =========================
# LOAD USER BLACKLIST
# =========================
def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r") as f:
        return [x.strip().lower() for x in f if x.strip()]


# =========================
# LOAD DEFAULT BLACKLIST
# =========================
def load_default_blacklist():
    if not os.path.exists(BLACKLIST_DEFAULT_FILE):
        return []
    with open(BLACKLIST_DEFAULT_FILE, "r") as f:
        return [x.strip().lower() for x in f if x.strip() and not x.strip().startswith("#")]


# =========================
# LOAD FULL BLACKLIST (user + default merged)
# This is what scanner and detector should always use
# =========================
def load_full_blacklist():
    user = set(load_blacklist())
    default = set(load_default_blacklist())
    return user | default


# =========================
# ADD TO BLACKLIST
# =========================
def add_to_blacklist(exe):
    exe = exe.lower().strip()
    if not exe:
        return
    lines = load_blacklist()
    if exe not in lines:
        lines.append(exe)
    os.makedirs("data", exist_ok=True)
    with open(BLACKLIST_FILE, "w") as f:
        f.write("\n".join(lines))


# =========================
# REMOVE FROM BLACKLIST
# =========================
def remove_from_blacklist(exe):
    exe = exe.lower().strip()
    lines = load_blacklist()
    lines = [x for x in lines if x != exe]
    with open(BLACKLIST_FILE, "w") as f:
        f.write("\n".join(lines))


# =========================
# MOVE BACK TO GAMES
# Removes from both blacklist and disabled list
# =========================
def move_to_games(exe):
    exe = exe.lower().strip()
    remove_from_blacklist(exe)

    disabled_path = "data/disabled_games.txt"
    if os.path.exists(disabled_path):
        with open(disabled_path, "r") as f:
            lines = [x.strip() for x in f if x.strip()]
        lines = [x for x in lines if x != exe]
        with open(disabled_path, "w") as f:
            f.write("\n".join(lines))
