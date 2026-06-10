"""
ShotTaker — Steam library detection via libraryfolders.vdf, across all drives.
"""

import os
import re
import string


def _vdf_candidates():
    cands = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        for sub in (r"Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
                    r"Program Files\Steam\steamapps\libraryfolders.vdf",
                    r"Steam\steamapps\libraryfolders.vdf",
                    r"SteamLibrary\steamapps\libraryfolders.vdf"):
            cands.append(os.path.join(root, sub))
    return cands


def detect_steam_libraries():
    found = []
    for vdf in _vdf_candidates():
        if not os.path.exists(vdf):
            continue
        try:
            with open(vdf, "r", encoding="utf8", errors="ignore") as f:
                text = f.read()
            for m in re.findall(r'"path"\s+"([^"]+)"', text):
                path = m.replace("\\\\", "\\")
                common = os.path.join(path, "steamapps", "common")
                if os.path.exists(common):
                    found.append(common)
        except OSError:
            pass
    return sorted(set(found))
