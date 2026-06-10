"""Headless smoke test for the ShotTaker backend."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
config.ensure_dirs()

import branding, frames, library, capture_manager, change_detector, screenshots          # noqa
import achievement_detector, gallery_manager, gamenames, scanner, blacklist, detector     # noqa
import state, stats, export, platform_detect, steam_detect, webserver                     # noqa
print("ALL MODULES IMPORT OK")

s = config.load_settings()
s["screenshot_format"] = "webp"
for k in ("suppress_dark_frames", "suppress_loading_screens", "letterbox_suppression", "dedupe_enabled"):
    s[k] = False

p = capture_manager.capture_screenshot("Test Game", "TimeLapse", s, reason="test")
print("captured:", p)
print("exists:", bool(p) and os.path.exists(p))
print("meta:", library.get(p) if p else None)

print("friendly eldenring.exe ->", gamenames.friendly("eldenring.exe"))
print("friendly PathOfExile_x64.exe ->", gamenames.friendly("PathOfExile_x64.exe"))
print("stats keys:", list(stats.summary().keys()))

shots = gallery_manager.list_screenshots()
print("gallery count:", len(shots))
if p:
    print("favorite toggle ->", library.toggle_favorite(p))
print("SMOKE TEST PASSED")
