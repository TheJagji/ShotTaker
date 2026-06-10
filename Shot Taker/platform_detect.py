import os


# =========================
# STEAM
# =========================
def detect_steam():
    found = []
    common = [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam"
    ]
    for p in common:
        if os.path.exists(p):
            found.append(p)
    return found


# =========================
# GOG
# =========================
def detect_gog():
    found = []
    common = [
        r"C:\GOG Games",
        r"D:\GOG Games",
        r"E:\GOG Games"
    ]
    for p in common:
        if os.path.exists(p):
            found.append(p)
    return found


# =========================
# EPIC
# =========================
def detect_epic():
    found = []
    common = [
        r"C:\Program Files\Epic Games",
        r"D:\Epic Games",
        r"E:\Epic Games"
    ]
    for p in common:
        if os.path.exists(p):
            found.append(p)
    return found


# =========================
# UBISOFT
# =========================
def detect_ubisoft():
    found = []
    common = [
        r"C:\Program Files (x86)\Ubisoft",
        r"C:\Program Files\Ubisoft"
    ]
    for p in common:
        if os.path.exists(p):
            found.append(p)
    return found


# =========================
# EA
# =========================
def detect_ea():
    found = []
    common = [
        r"C:\Program Files\EA Games",
        r"D:\EA Games"
    ]
    for p in common:
        if os.path.exists(p):
            found.append(p)
    return found


# =========================
# RUN DETECTION
# =========================
def run_detection(selected):
    results = {}
    if selected.get("steam"):
        results["steam"] = detect_steam()
    if selected.get("gog"):
        results["gog"] = detect_gog()
    if selected.get("epic"):
        results["epic"] = detect_epic()
    if selected.get("ubisoft"):
        results["ubisoft"] = detect_ubisoft()
    if selected.get("ea"):
        results["ea"] = detect_ea()
    return results
