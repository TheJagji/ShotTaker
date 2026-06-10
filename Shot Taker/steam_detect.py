import os
import re


def detect_steam_libraries():

    found = []

    possible = [

        r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
        r"C:\Program Files\Steam\steamapps\libraryfolders.vdf",
    ]

    for vdf in possible:

        if not os.path.exists(vdf):
            continue

        try:

            with open(vdf, "r", encoding="utf8", errors="ignore") as f:
                text = f.read()

            matches = re.findall(r'"path"\s+"([^"]+)"', text)

            for m in matches:

                path = m.replace("\\\\", "\\")

                steam_common = os.path.join(
                    path,
                    "steamapps",
                    "common"
                )

                if os.path.exists(steam_common):
                    found.append(steam_common)

        except:
            pass

    return sorted(list(set(found)))