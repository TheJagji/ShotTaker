# ShotTaker — Project Status & Known Issues

Companion to `ARCHITECTURE.md`. Last reviewed: 2026-06-13 (Dev branch).

---

## Current Version: 1.3.0 (Dev)

### Changes in this dev branch (on top of 1.3.0 baseline)

- **`user_data/` restructure** — all generated/user files now live under `user_data/`
  (gitignored). Static shipped data stays in `data/`. See `ARCHITECTURE.md §2` for the
  full folder map.
- **Sensitivity slider** — Settings → Capture now has a proper range slider for Action
  Shot sensitivity (was a plain number input). Range 5–100.
- **Settings → Blacklist tab** — user blacklist is now manageable from within the UI.
  Restore button moves an exe back to the game list (`/api/blacklist/move_to_games`).
- **Settings → About tab** — displays `data/about.txt` with an inline editor. Sysinfo
  table (version, OS, Python, arch) shown above it.
- **`/api/about` GET/POST routes** added to `webserver.py`.
- **`user_data/sounds/`** — uploaded notification sounds now go to `user_data/sounds/`
  instead of `static/sounds/`. Served via `/user_data/sounds/<file>` Flask route.
- **Bug fixes from 1.3.0 baseline:**
  - `mss` and `numpy` added to `requirements.txt` (Bug #3).
  - Shot counters now use `.casefold()` for case-insensitive keys (Bug #4).
  - `scan_count` runaway removed from `scanner.py` (Bug #5).
  - `fire_achievement_burst` arg order confirmed correct in `achievement_detector.py`.
  - `extra` platform key consistent throughout (Bug #2 — was already correct in this codebase).
- **`.gitignore`** added.

---

## 1. Feature Inventory

| Feature | Status | Notes |
|---|---|---|
| Game folder scanning (per platform) | ✅ Working | `scanner.py`; junk/installer filtering |
| Process-based game detection | ✅ Working | `detector.py`, 5 s poll via `psutil` |
| User + default blacklist | ✅ Working | merged set used everywhere |
| Blacklist management UI | ✅ Working | Settings → Blacklist tab; Restore + Remove |
| Disabled-games list | ✅ Working | separate from blacklist |
| Direct screen capture (mss) | ✅ Working | `mss` + `numpy` in requirements |
| TimeLapse mode | ✅ Working | interval + optional burst |
| Action Shots (screen-diff) | ✅ Working | `change_detector.py`; sensitivity slider in UI |
| Hybrid mode | ✅ Working | timelapse + action together |
| PNG / JPEG / WebP output | ✅ Working | per-game folders, persistent counters |
| Thumbnails | ✅ Working | `.thumbs/`, lazy + eager generation |
| Built-in gallery (browse/filter/lightbox) | ✅ Working | pagination, per-game/type filter |
| Favorites / tags / ratings | ✅ Working | stored in `library.json` |
| Bulk export (ZIP / contact sheet / GIF) | ✅ Working | `export.py` → `user_data/Exports/` |
| Bulk rename to convention | ✅ Working | moves files + thumbs into per-game folders |
| Recent-session view | ✅ Working | filters by last session's time window |
| Steam AppID lookup | ✅ Working | public store API, no key |
| Steam achievement screenshots | ⚠️ Untested | detection logic looks correct; needs live test |
| Steam hotkey backup mode | ✅ Working | optional, Steam only |
| Setup wizard (dynamic steps) | ✅ Working | re-runnable, pre-fills |
| Local web UI in native window | ✅ Working | pywebview + dark titlebar |
| System tray | ✅ Working | pystray; open/rescan/exit |
| Custom notification sounds | ✅ Working | uploaded to `user_data/sounds/` |
| Launch with Windows | ✅ Working | HKCU Run key |
| Platform auto-detection | ✅ Working | path-based + Steam VDF |
| Per-game profiles | ✅ Working | settings_for_game() layers profile over defaults |
| Session history | ✅ Working | all sessions appended to `sessions.json` |
| Stats dashboard | ✅ Working | playtime, shots-per-game, sparkline, recent sessions |
| Friendly game name resolution | ✅ Working | overrides > hints > prettified exe |
| Privacy guard | ✅ Working | auto-pauses on configured sensitive app titles |
| About section | ✅ Working | `data/about.txt` editable from UI |
| `user_data/` folder separation | ✅ Working | gitignored; all generated data here |
| Achievement detection for GOG/Epic/Ubisoft/EA | ⬜ Missing | Steam only |
| PyInstaller single-exe packaging | ⬜ Missing | `shottaker.spec` exists but untested |
| Mac / Linux support | ⬜ Missing | Windows-only (WinAPI, registry) |

---

## 2. Known Issues

### Issue #1 — Steam achievement detection untested  *(medium)*
The `achievement_detector.py` logic looks correct and the arg order is right, but it
hasn't been tested against a live Steam achievement unlock. The heuristic (any `.bin`
mtime change = achievement) can false-positive on non-achievement stat writes.

### Issue #2 — `_path_cache` never evicted  *(low)*
`webserver._path_cache` grows for every gallery item ever listed and only clears on
restart. Minor memory leak for very large libraries. Consider LRU or signed path tokens.

### Issue #3 — `reload.flag` is a no-op  *(low)*
`command_loop()` detects and consumes `reload.flag` but only logs — no action taken.
Placeholder for a future settings-reload without restart.

### Issue #4 — Action Shots CPU usage  *(known limitation)*
Action / Hybrid mode runs a continuous full-screen grab + resize + numpy diff at ~0.5 s
intervals. This is genuinely CPU-intensive. Documented; future optimisation options include
capture region limiting, frame skip, or event-driven hooks.

### Issue #5 — Achievement detection is Steam-only and heuristic  *(known limitation)*
Any `.bin` mtime change in Steam's `appcache/stats/` triggers a burst. This is a
best-effort heuristic — no GOG/Epic/Ubisoft/EA equivalent exists yet.

### Issue #6 — `start.bat` doesn't install `mss` / `numpy`  *(low)*
`requirements.txt` now includes `mss` and `numpy`, and `Start_distro.bat` uses
`pip install -r requirements.txt`. But `start.bat` checks packages individually and still
doesn't check for `mss` or `numpy`. Update `start.bat` to add these checks.

---

## 3. Architectural Notes

- **Windows-only.** WinAPI icon/titlebar calls, registry startup, tkinter picker, and
  the monitor model all assume Windows.
- **Polling-based.** Game loop 5 s, command loop 2 s, achievement 1 s, action ~0.5 s.
- **Settings are centrally managed** via `config.py` — `load_settings()`, `save_settings()`,
  `settings_for_game()`, and a full `DEFAULTS` dict. No more per-module duplicates.
- **Frozen-aware paths** — `config.py` distinguishes `bundle_dir()` (read-only resources)
  from `app_dir()` (writable user data) for PyInstaller compatibility.

---

## 4. Quick Orientation for a New Contributor

- Start in `main.py` (`game_loop`) to see the whole control flow.
- The capture logic you'll touch most is `capture_manager.py` and `frames.py`.
- The web API and front-end glue are `webserver.py` + `static/app.js`.
- All paths come from `config.py` — never hardcode `data/` or `status/` anywhere.
- `user_data/` is gitignored — the app creates it on first run via `ensure_dirs()`.
- To test capture without a game: temporarily make `is_active()` return `True` and call
  `capture_screenshot("Test", "TimeLapse", config.load_settings())`.
- Logs: dashboard (`/api/log`) or `user_data/launch_error.log` when started via `launch.py`.
