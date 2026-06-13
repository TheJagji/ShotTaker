"""
ShotTaker — platform install-path auto-detection (path-based, no registry).
Probes common locations across all fixed drives.
"""

import os
import string


def _drives():
    found = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            found.append(letter)
    return found


def _probe(subpaths):
    """Return existing paths formed by joining each drive with each subpath."""
    out = []
    for d in _drives():
        for sub in subpaths:
            p = os.path.join(f"{d}:\\", sub)
            if os.path.exists(p):
                out.append(p)
    return sorted(set(out))


PROBES = {
    "steam":     [r"Program Files (x86)\Steam", r"Program Files\Steam", "Steam", r"SteamLibrary"],
    "gog":       ["GOG Games", r"GOG Galaxy\Games", r"Program Files (x86)\GOG Galaxy\Games"],
    "epic":      [r"Program Files\Epic Games", "Epic Games", r"Program Files (x86)\Epic Games"],
    "ubisoft":   [r"Program Files (x86)\Ubisoft", r"Program Files\Ubisoft", "Ubisoft Games"],
    "ea":        ["EA Games", r"Program Files\EA Games", r"Program Files\Electronic Arts", "Origin Games"],
    "xbox":      ["XboxGames", r"Program Files\WindowsApps"],
    "battlenet": [r"Program Files (x86)\Battle.net", r"Program Files\Battle.net", "Games"],
    "riot":      [r"Riot Games", r"Program Files\Riot Games"],
    "rockstar":  [r"Program Files\Rockstar Games", r"Program Files (x86)\Rockstar Games"],
    "itch":      [os.path.join(os.path.expandvars(r"%APPDATA%"), "itch", "apps")],
}


def detect(platform):
    return _probe(PROBES.get(platform, []))


def run_detection(selected):
    results = {}
    for key in PROBES:
        if selected.get(key):
            results[key] = detect(key)
    return results
