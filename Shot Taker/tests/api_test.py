"""Exercise the ShotTaker REST API via Flask's test client."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
config.ensure_dirs()
import scanner
scanner.GAME_LIST = {"eldenring.exe": "steam", "pathofexile_x64.exe": "epic"}
config.write_json(config.GAMES_FILE, scanner.GAME_LIST)

import webserver
c = webserver.app.test_client()

CHECKS = [
    ("GET", "/", None), ("GET", "/api/brand", None), ("GET", "/api/settings", None),
    ("GET", "/api/status", None), ("GET", "/api/stats", None), ("GET", "/api/stats/summary", None),
    ("GET", "/api/games", None), ("GET", "/api/gallery/games", None),
    ("GET", "/api/gallery/screenshots?page=1", None), ("GET", "/api/monitors", None),
    ("GET", "/api/sessions", None), ("GET", "/api/events", None), ("GET", "/api/log", None),
    ("GET", "/api/folders", None), ("GET", "/api/profiles", None), ("GET", "/api/sysinfo", None),
    ("GET", "/api/config/export", None),
    ("POST", "/api/settings", {"capture_mode": "hybrid"}),
    ("POST", "/api/capture/pause", {"paused": True}),
    ("POST", "/api/capture/pause", {"paused": False}),
    ("POST", "/api/names/set", {"exe": "eldenring.exe", "name": "Elden Ring"}),
    ("POST", "/api/profiles/save", {"exe": "eldenring.exe", "profile": {"interval": 60000}}),
]

fails = 0
for method, url, body in CHECKS:
    r = c.open(url, method=method, json=body)
    ok = r.status_code == 200
    if not ok:
        fails += 1
    print(f"{'ok ' if ok else 'ERR'} {r.status_code} {method} {url}")

# verify name override + profile merge took effect
g = c.get("/api/games").get_json()
assert g["names"]["eldenring.exe"] == "Elden Ring", "name override failed"
assert config.settings_for_game("eldenring.exe")["interval"] == 60000, "profile merge failed"
print("name override + profile merge: OK")
print("FAILURES:", fails)
sys.exit(1 if fails else 0)
