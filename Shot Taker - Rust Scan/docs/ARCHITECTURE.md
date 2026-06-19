# ShotTaker — Architecture & Developer Reference

> **Status:** Active development. Last reviewed: 2026-06-13 (Dev branch).

---

## 1. What ShotTaker Is

ShotTaker is a standalone **Windows** desktop app that runs in the background, detects
when a PC game is running, and **automatically captures screenshots** — with no platform
overlay required. Built in Python, it presents a local web UI rendered in a native window
(pywebview) and lives in the system tray.

**Core philosophy:** local-first. No accounts, no cloud, no telemetry.

> **History note:** The project began as an AutoHotkey script, then a Python app that
> *pressed platform screenshot hotkeys* (Steam F12 etc.). It has since pivoted to
> **direct capture** using `mss`. Hotkey pressing survives only as an optional Steam
> backup (`steam_hotkey_backup`).

---

## 2. Folder Structure

```
ShotTaker/
├── main.py                     ← Entry point
├── *.py                        ← All source modules (see Module Map)
├── data/                       ← Static shipped data (committed to repo)
│   ├── blacklist_default.txt   ← Shipped default blacklist
│   └── about.txt               ← About section content (edit as developer)
├── static/                     ← Front-end assets (committed to repo)
│   ├── app.js
│   ├── style.css
│   └── icon.png / icon.ico
├── templates/
│   └── index.html
├── docs/
├── tests/
├── requirements.txt
├── *.bat
├── shottaker.spec
├── .gitignore
└── user_data/                  ← Generated at runtime (gitignored, never committed)
    ├── data/                   ← User settings and generated data
    │   ├── settings.json
    │   ├── folders.json
    │   ├── profiles.json
    │   ├── shot_counters.json
    │   ├── library.json
    │   ├── game_names.json
    │   ├── blacklist.txt
    │   ├── blacklist_default.txt  ← Seeded from data/ on first run
    │   └── disabled_games.txt
    ├── status/                 ← Runtime state (safe to delete)
    │   ├── state.json
    │   ├── stats.json
    │   ├── games.json
    │   ├── active_game.txt
    │   ├── last_session.json
    │   ├── sessions.json
    │   └── events.json
    ├── commands/               ← IPC flag files
    │   ├── scan.flag
    │   └── reload.flag
    ├── sounds/                 ← User-uploaded notification sounds
    ├── Screenshots/            ← Default screenshot output folder
    ├── Exports/                ← ZIP / contact sheet / GIF exports
    └── launch_error.log        ← Stdout/stderr from launch.py
```

**Key rule:** `data/` is read-only shipped content. `user_data/` is everything the running
app creates or the user generates. Never commit `user_data/`.

---

## 3. Runtime Model

`main.py` is the entry point. On startup it:

1. `ensure_dirs()` — creates all `user_data/` subdirs and seeds flag files + default data.
2. Runs an initial `scanner.scan_games()` to build the in-memory `GAME_LIST`.
3. Starts background daemon threads, then opens the window on the **main thread**
   (pywebview *must* run on the main thread).

| Thread | Function | Cadence | Responsibility |
|---|---|---|---|
| Game loop | `game_loop()` | every 5 s | Detect running games, manage capture sessions, write `state.json` |
| Command loop | `command_loop()` | every 2 s | Watch `user_data/commands/*.flag` for scan/reload triggers |
| Web server | `webserver.run()` | — | Flask on `127.0.0.1:5050` |
| Window (main thread) | `start_window()` | — | pywebview window + system tray (pystray) |
| Watchdog | `watchdog()` | every 10 s | Restarts any dead core thread |

Two long-running **detector objects** start from inside `game_loop()`:
- `achievement_detector` — watches Steam stats files.
- `change_detector` — the Action Shots screen-diff loop.

### Capture session lifecycle

```
game_loop tick (every 5s)
  └─ find_game() → (exe, platform)
       ├─ new game?      → state.set_active(), window_manager.on_game_detected(),
       │                    achievement_detector.rescan_folder(),
       │                    spawn run_capture_session() thread
       ├─ game closed?   → session_active.clear(), state.clear_active()
       └─ unchanged?     → state.write()
```

`run_capture_session()` reads `capture_mode` and starts the appropriate worker(s):

- **`timelapse`** → `capture_manager.run_timelapse_session()`
- **`action`** → handled by the always-on `change_detector` loop
- **`hybrid`** → both
- Optional **Steam hotkey backup** → `_run_steam_hotkey_session()`

---

## 4. Module Map

| File | Role |
|---|---|
| `main.py` | Entry point, thread orchestration, capture-session spawning, watchdog |
| `launch.py` | Silent launcher — runs `main.py` with no console; logs to `user_data/launch_error.log` |
| `config.py` | **Central config** — all paths, settings load/save, defaults merge, `ensure_dirs()` |
| `branding.py` | Brand constants, colour tokens, programmatic logo/icon generation |
| `scanner.py` | Walks configured folders for `.exe` files → `GAME_LIST` + `user_data/status/games.json` |
| `detector.py` | `psutil` process scan; matches running procs against `GAME_LIST` |
| `blacklist.py` | User + default blacklist load/add/remove; `load_full_blacklist()` merges both |
| `state.py` | Active-game state, session tracking, writes `state.json` / `sessions.json` |
| `screenshots.py` | Capture-mode router + Steam hotkey backup + achievement burst entry point |
| `capture_manager.py` | **Core capture** — `mss` grab, quality gate, PNG/JPEG/WebP save, counters, thumbnails |
| `frames.py` | Shared frame helpers — monitor selection, grab, diff scoring, quality gate logic |
| `change_detector.py` | Action Shots — continuous screen-diff, fires `DynamicShot` captures |
| `achievement_detector.py` | Watches Steam `appcache/stats/*.bin` mtimes; fires achievement burst |
| `gallery_manager.py` | Indexes screenshot folder, parses filenames, thumbnails, bulk rename, pagination |
| `library.py` | Screenshot metadata (favorites/tags/ratings), storage guardrails |
| `gamenames.py` | exe → friendly name resolution (overrides > folder hints > prettified exe) |
| `stats.py` | Playtime + capture statistics computed from session history and library index |
| `export.py` | ZIP bundles, contact sheets, animated GIFs → `user_data/Exports/` |
| `steam_detect.py` | Parses `libraryfolders.vdf` → `steamapps/common` paths |
| `platform_detect.py` | Hard-coded common install paths per launcher (path-based, no registry) |
| `webserver.py` | Flask app — all REST routes, stdout log capture, Steam AppID lookup |
| `app_window.py` | pywebview window, system tray, dark titlebar, Windows startup registry |
| `templates/index.html` | Single-page UI markup (wizard + tabs + SVG icon sprite) |
| `static/app.js` | All front-end logic (vanilla JS) |
| `static/style.css` | Design system — brand tokens, light/dark theme, component styles |

---

## 5. Configuration (`config.py`)

Central single source of truth for all paths and settings. Every module imports from here.

### Path helpers

```python
bundle_dir()   # read-only resources (templates, static, seed data)
app_dir()      # writable base — next to exe when frozen, else source dir
res_path()     # path to a bundled read-only resource
data_path()    # path to a writable user-data file/dir
```

### Key path constants

```python
# Static shipped data (repo)
data/blacklist_default.txt
data/about.txt

# User-generated (user_data/, gitignored)
user_data/data/settings.json
user_data/data/folders.json
user_data/data/library.json
user_data/data/game_names.json
user_data/data/blacklist.txt
user_data/status/state.json
user_data/status/sessions.json
user_data/commands/scan.flag
user_data/sounds/
user_data/Screenshots/          ← default screenshot folder
user_data/Exports/
user_data/launch_error.log
```

### Settings

`load_settings()` merges `user_data/data/settings.json` over `DEFAULTS` so missing keys
always resolve. `save_settings()` persists the full merged result atomically (write to
`.tmp`, then `os.replace`). `settings_for_game(exe)` layers a per-game profile on top.

---

## 6. Detection Pipeline

### Scanning (`scanner.py`)
- Reads `user_data/data/folders.json` (lists of folders per platform key).
- Platform scan order: `steam → gog → epic → ubisoft → ea → xbox → battlenet → riot → rockstar → itch → extra`.
  First platform to claim an `.exe` wins.
- Skips junk dirs and installer/updater/launcher patterns.
- Filters against the merged blacklist and `disabled_games.txt`.
- Output: `{ "exe.exe": "platform" }` → `scanner.GAME_LIST` + `user_data/status/games.json`.

### Detection (`detector.py`)
- Iterates `psutil.process_iter` every 5 s.
- Lower-cases process names, skips blacklisted + zombie/dead procs.
- Returns the **original-case** process name and platform on first match.

### Blacklist (`blacklist.py`)
- `user_data/data/blacklist.txt` — user-managed, editable from UI (Settings → Blacklist tab).
- `data/blacklist_default.txt` — shipped defaults; `#` comment lines ignored.
- `load_full_blacklist()` = union of both.

---

## 7. Capture System

### Core capture (`capture_manager.py`)
- **Backend:** `mss` grabs the selected monitor, converted to PIL image.
- **Formats:** PNG (default), JPEG, or WebP (`screenshot_format`).
- **Filenames:** `{GameName}_{ShotType}_{NNN}.{ext}`, e.g. `Hades_TimeLapse_004.png`.
  Shot types: `TimeLapse`, `DynamicShot`, `Achievement`, `Manual`, `Imported`.
- **Counters:** `user_data/data/shot_counters.json`, keyed `"{game_casefold}_{type}"`,
  thread-safe. Numbers persist across sessions.
- **Thumbnails:** `{screenshot_folder}/.thumbs/` mirroring relative path, JPEG 400×225.
- **Quality gate** (`frames.py`): rejects dark frames, low-detail/loading screens,
  letterboxed frames, and near-duplicates before saving.

### Action Shots (`change_detector.py`)
- Always-on loop when `capture_mode ∈ {action, hybrid}` and a game is active.
- Grabs monitor, downscales to 320×180, computes weighted MAD diff against previous frame.
- Captures `DynamicShot` when `score >= sensitivity` and cooldown elapsed.
- **`sensitivity`** (5–100) is user-configurable via slider in Settings → Capture.

### Achievement Shots (`achievement_detector.py`)
- **Steam only.** Polls `*.bin` in Steam's `appcache/stats/` every 1 s.
- Any file with a newer mtime than the baseline snapshot → achievement unlock → burst.

---

## 8. State & Data Files

### `user_data/data/` (user settings — persisted)
| File | Contents |
|---|---|
| `settings.json` | All user settings. Absence = first run → show wizard. |
| `folders.json` | Game-folder paths per platform key. |
| `blacklist.txt` | User blacklist (one exe per line). |
| `blacklist_default.txt` | Seeded from `data/` on first run. |
| `disabled_games.txt` | Games excluded from detection (not blacklisted). |
| `shot_counters.json` | Per-game/per-type running screenshot numbers. |
| `library.json` | Screenshot metadata index (favorites/tags/ratings). |
| `game_names.json` | `{ overrides: {}, hints: {} }` exe → friendly name map. |
| `about.txt` | Seeded from `data/about.txt` — not present here (read from `data/`). |

### `user_data/status/` (runtime — safe to delete)
| File | Contents |
|---|---|
| `state.json` | `{ games, activeGame, activePlatform, gameActive, sessionShots }` |
| `stats.json` | `{ screenshots_taken, games_found }` |
| `games.json` | The scanned `{ exe: platform }` map. |
| `active_game.txt` | Current active exe (or empty). |
| `sessions.json` | Array of all session records (last 1000 kept). |
| `last_session.json` | Most recent session summary. |
| `events.json` | Achievement/capture event log (last 2000 kept). |

### `user_data/commands/` (IPC via flag files)
Write any non-empty content; the command loop consumes it within 2 s:
- `scan.flag` → triggers `scanner.scan_games()`
- `reload.flag` → logs only (placeholder)

---

## 9. Web Server & API (`webserver.py`)

Flask on `http://127.0.0.1:5050`. stdout is wrapped by `LogCapture` so the dashboard
displays recent console lines via `/api/log`.

### Routes

**Setup / status**
| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serve UI |
| GET | `/api/brand` | Brand tokens (name, colours, version) |
| GET | `/api/setup/status` | `{ setup_complete }` |
| POST | `/api/setup/complete` | Save wizard settings, rescan |
| GET | `/api/status` | `state.json` |
| GET | `/api/stats` / `/api/stats/summary` | Stats + computed summary |
| GET | `/api/sysinfo` | Version, OS, Python, arch |
| GET | `/api/log` | Recent console lines |
| GET | `/api/about` | Contents of `data/about.txt` |
| POST | `/api/about` | Save `data/about.txt` |

**Games / blacklist / scanning**
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/games` | games.json + friendly names |
| POST | `/api/games/disable` | Add exe to disabled, rescan |
| GET | `/api/blacklist` | User blacklist |
| POST | `/api/blacklist/add` | Add + rescan |
| POST | `/api/blacklist/remove` | Remove entry |
| POST | `/api/blacklist/move_to_games` | Remove from blacklist + disabled, rescan |
| GET | `/api/scan/games` | Trigger scan |

**Folders / settings / sound**
| Method | Route | Purpose |
|---|---|---|
| GET / POST | `/api/folders` | Read / save `folders.json` |
| POST | `/api/folders/autodetect` | Path + VDF detection |
| POST | `/api/browse/folder` | tkinter folder picker |
| GET / POST | `/api/settings` | Read / save `settings.json` |
| POST | `/api/sound/upload` | Upload to `user_data/sounds/` |
| POST | `/api/sound/delete` | Remove uploaded sound |
| GET | `/user_data/sounds/<file>` | Serve uploaded sound file |

**Gallery**
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/gallery/screenshots` | Paginated list |
| GET | `/api/gallery/games` | Game names present in gallery |
| GET | `/api/gallery/file/<h>` | Serve full image |
| GET | `/api/gallery/thumb/<h>` | Serve/generate thumbnail |
| POST | `/api/gallery/delete` | Delete file + thumb |
| POST | `/api/gallery/rename` | Bulk rename to convention |
| GET | `/api/gallery/session` | Screenshots within last session window |

**Capture / export / profiles**
| Method | Route | Purpose |
|---|---|---|
| POST | `/api/capture/now` | Manual single capture |
| POST | `/api/burst/fire` | Manual achievement burst |
| POST | `/api/capture/pause` | Toggle capture pause |
| POST | `/api/export/zip` | Export selected as ZIP |
| POST | `/api/export/contactsheet` | Generate contact sheet |
| POST | `/api/export/gif` | Stitch animated GIF |
| GET / POST | `/api/profiles` | Per-game profile CRUD |

---

## 10. Front-End (`static/app.js` + `static/style.css`)

Single-page app, vanilla JS, no build step.

**Setup Wizard** — shown when `setup_complete` is false; re-runnable from Settings.

**Main tabs:** Dashboard · Gallery · Games · Stats · Settings

**Settings sub-tabs:** Capture · Quality · Output · Achievements · Hotkeys · Notifications ·
Window · Storage · Privacy · Advanced · Blacklist · About

**Settings → Capture** includes the **Action sensitivity slider** (maps to the `sensitivity`
key, range 5–100, controls the screen-diff threshold in `change_detector.py`).

**Settings → Blacklist** — lists `user_data/data/blacklist.txt` entries with Restore
(moves exe back to game list via `/api/blacklist/move_to_games`) and Remove buttons.

**Settings → About** — displays `data/about.txt` content with an inline editor that
saves back via `/api/about`. Also shows the sysinfo table from `/api/sysinfo`.

---

## 11. Installation & Running

```bat
:: First run — checks/installs packages, then launches
start.bat

:: Simple launcher (pip install -r, then run)
Start_distro.bat
```

`launch.py` starts `main.py` detached (no console window), logging to
`user_data/launch_error.log`.

**Requirements:** Windows 10/11, Python 3.10+.
**Dependencies:** `flask`, `psutil`, `pyautogui`, `pywebview`, `pystray`, `Pillow`,
`mss`, `numpy`, `requests`.

---

## 12. Glossary

- **TimeLapse** — interval-based capture (`interval` ms).
- **DynamicShot / Action Shot** — capture triggered by on-screen change exceeding `sensitivity`.
- **Achievement burst** — N rapid captures when a Steam achievement unlocks.
- **GAME_LIST** — in-memory `{exe: platform}` map produced by the scanner.
- **Session** — the span between a game being detected and closing.
- **user_data/** — the gitignored runtime folder; all generated/user files live here.
