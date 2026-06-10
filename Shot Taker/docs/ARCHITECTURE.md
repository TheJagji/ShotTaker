# ShotTaker — Architecture & Developer Reference

> **Status:** Active development. This document originally described the ShotTaker
> direct-capture prototype. As of **ShotTaker 1.3.0** the app was rebranded and the roadmap
> implemented — see the release notes in `PROJECT_STATUS.md`. Key structural changes since
> this doc was first written: a central **`config.py`** (settings + frozen-aware paths) now
> backs every module (the duplicated `load_settings()` is gone); new modules **`branding.py`,
> `frames.py`, `library.py`, `gamenames.py`, `stats.py`, `export.py`**; the platform key is
> **`extra`**; capture saves via the quality gate with WebP/scale/watermark; and the app
> ships as a PyInstaller exe (`shottaker.spec`). The module map below is otherwise accurate.

---

## 1. What ShotTaker Is

ShotTaker is a standalone **Windows** desktop app that runs in the background, detects
when a PC game is running, and **automatically captures screenshots** — with no platform
overlay required. It is built in Python, presents a local web UI rendered in a native
window (pywebview), and lives in the system tray.

**Core philosophy:** local-first. No accounts, no cloud, no telemetry. All state lives
in flat files (`data/`, `status/`) next to the app.

> **Architectural note:** The project began as an AutoHotkey script, then a Python app
> that *pressed platform screenshot hotkeys* (Steam F12, etc.). It has since pivoted to
> **direct capture** using `mss` — ShotTaker grabs the screen itself and writes PNG/JPEG
> files to a folder it controls. Hotkey pressing now survives only as an *optional Steam
> backup* (`steam_hotkey_backup`). Keep this history in mind when reading older comments.

---

## 2. Runtime Model

`main.py` is the entry point. On startup it:

1. `ensure_dirs()` — creates `data/`, `status/`, `commands/`, `static/` and the flag files.
2. Runs an initial `scanner.scan_games()` to build the in-memory `GAME_LIST`.
3. Starts three background daemon threads, then opens the window on the **main thread**
   (pywebview *must* run on the main thread).

| Thread | Function | Cadence | Responsibility |
|---|---|---|---|
| Game loop | `game_loop()` | every 5 s | Detect running games, manage capture sessions, write `state.json` |
| Command loop | `command_loop()` | every 2 s | Watch `commands/*.flag` files for scan/reload triggers |
| Web server | `webserver.run()` | — | Flask on `127.0.0.1:5050` |
| Window (main thread) | `start_window()` | — | pywebview window + system tray (`pystray`) |

Two long-running **detector objects** are started from inside `game_loop()` (so they share
its `current_game`/`current_platform` closure state via callbacks):

- `achievement_detector` (`achievement_detector.py`) — watches Steam stats files.
- `change_detector` (`change_detector.py`) — the Action Shots screen-diff loop.

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

`run_capture_session()` (in `screenshots.py`) reads `capture_mode` and starts the
appropriate worker thread(s):

- **`timelapse`** → `capture_manager.run_timelapse_session()`
- **`action`** → handled by the always-on `change_detector` loop (no new thread)
- **`hybrid`** → both
- Optional **Steam hotkey backup** → `_run_steam_hotkey_session()` (Steam only)

The "is this session still alive?" check is a lambda closure:
`lambda: current_game == cap_exe and event.is_set()`. When the game closes or switches,
`session_active.clear()` makes every worker thread exit its loop on its next tick.

---

## 3. Module Map

| File | Role |
|---|---|
| `main.py` | Entry point, thread orchestration, capture-session spawning |
| `launch.py` | Silent launcher — runs `main.py` with no console window; logs to `launch_error.log` |
| `scanner.py` | Walks configured folders for `.exe` files → `GAME_LIST` + `status/games.json` |
| `detector.py` | `psutil` process scan; matches running procs against `GAME_LIST` |
| `blacklist.py` | User + default blacklist load/add/remove; `load_full_blacklist()` merges both |
| `state.py` | Active-game state, session tracking, writes `state.json` / `last_session.json` |
| `screenshots.py` | Capture-mode router + Steam hotkey backup + achievement burst entry |
| `capture_manager.py` | **Core capture** — `mss` grab, PNG/JPEG save, per-game counters, thumbnails, timelapse loop |
| `change_detector.py` | Action Shots — continuous screen-diff scoring, fires `DynamicShot` captures |
| `achievement_detector.py` | Watches Steam `appcache/stats/*.bin` mtimes; fires achievement burst |
| `gallery_manager.py` | Indexes screenshot folder, parses filenames, thumbnails, bulk rename, pagination |
| `steam_detect.py` | Parses `libraryfolders.vdf` → `steamapps/common` paths |
| `platform_detect.py` | Hard-coded common install paths per launcher (path-based, no registry) |
| `webserver.py` | Flask app — all REST routes + stdout log capture + Steam AppID lookup |
| `app_window.py` | pywebview window, system tray, icon generation, dark titlebar, Windows startup registry |
| `config.py` | **Empty (1 byte)** — reserved; settings are currently loaded ad-hoc per module |
| `templates/index.html` | Single-page UI markup (wizard + tabs) |
| `static/app.js` | All front-end logic (~1500 lines, vanilla JS) |
| `static/style.css` | Styling (~1400 lines) |

### Notable duplication
`load_settings()` is re-implemented independently in **at least 6 modules** (`main`,
`screenshots`, `capture_manager`, `change_detector`, `gallery_manager`, `app_window`,
`webserver`). `sanitise_name`/`sanitise_game_name` exists in both `capture_manager.py`
and `gallery_manager.py` with slightly different behaviour (the capture one strips `.exe`,
the gallery one does not). This is the obvious first refactor target — `config.py` is the
empty home waiting for a shared settings/util module.

---

## 4. Detection Pipeline

### Scanning (`scanner.py`)
- Reads `data/folders.json` (lists of folders per platform key).
- Platform scan order: `steam → gog → epic → ubisoft → ea → extra_games`.
  First platform to claim an `.exe` wins (no duplicates).
- Skips junk dirs (`__pycache__`, `node_modules`, `.git`, `logs`, `cache`,
  `shadercache`, `htmlcache`, `webcache`).
- Skips installer/updater/launcher patterns by substring (`install`, `setup`, `unins`,
  `update`, `updater`, `crashpad`, `crashreport`, `crash_handler`, `redist`, `vcredist`,
  `directx`, `dotnet`, `prereq`, `prerequisite`, `launcher`).
- Filters against the merged blacklist and `data/disabled_games.txt`.
- Output: `{ "exe.exe": "platform" }` → `scanner.GAME_LIST` + `status/games.json`.

> ⚠️ **Key mismatch:** `scanner.py` uses the platform key `extra_games`, but the live
> `data/folders.json` and the front-end use `extra`. See `PROJECT_STATUS.md` → Known Issues.

### Detection (`detector.py`)
- Iterates `psutil.process_iter(['name','status'])` every 5 s.
- Lower-cases process names, skips blacklisted + zombie/dead procs.
- Returns the **original-case** process name and platform on first match.

### Blacklist (`blacklist.py`)
- `data/blacklist.txt` — user-managed, editable from UI.
- `data/blacklist_default.txt` — shipped defaults (system procs, runtimes, debuggers,
  redists, engine helpers); `#` comment lines ignored.
- `load_full_blacklist()` = union of both. Scanner and detector always use the merged set.

---

## 5. Capture System (`capture_manager.py`)

- **Backend:** `mss` grabs `monitors[1]` (primary monitor only), converted to a PIL image.
- **Format:** PNG (default) or JPEG (`screenshot_format`, with `jpeg_quality`).
- **Filenames:** `{GameName}_{ShotType}_{NNN}.{ext}`, e.g. `Hades_TimeLapse_004.png`.
  Shot types: `TimeLapse`, `DynamicShot`, `Achievement`, `Imported`.
- **Counters:** `data/shot_counters.json`, keyed `"{game}_{type}"`, thread-safe via
  `_counter_lock`. Numbers persist and continue across sessions.
- **Folder layout:** `screenshot_folder/GameName/...` when `per_game_folders` is true
  (default), else flat in `screenshot_folder/`.
- **Thumbnails:** generated into `screenshot_folder/.thumbs/` mirroring the relative path,
  always JPEG 400×225 max, quality 82. Generated lazily by the gallery and eagerly after
  each capture (in a background thread).
- **Stats:** every successful capture calls `increment_screenshot_count()` →
  `status/stats.json` `screenshots_taken` + `state.add_session_shot()`.

### Action Shots (`change_detector.py`)
- Always-on loop (runs only when `capture_mode ∈ {action, hybrid}` *and* a game is active).
- Grabs the primary monitor, downscales to 320×180, compares to previous frame.
- **Score** = weighted Mean Absolute Difference: `0.6 * luminance + 0.4 * colour`
  (`score_diff()`; adapted from "DScreenshot").
- Captures a `DynamicShot` when `score >= sensitivity` and `now - last_capture >= cooldown`.
- Foreground-window guard: skips capture if the focused window title looks like desktop /
  taskbar / Task Manager / ShotTaker itself.
- Loop tick ~0.5 s while active. This is the **CPU-heavy** mode.

### Achievement Shots (`achievement_detector.py`)
- **Steam only.** Polls `*.bin` files in Steam's `appcache/stats` folder every 1 s,
  comparing mtimes against a baseline snapshot. Any file growing newer ⇒ achievement.
- Stats folder resolved from `steam_stats_folder` setting, else default path list.
- Baseline is re-snapshotted on each new game (`rescan_folder()`).
- On trigger, fires `fire_achievement_burst(...)` → a burst of N direct captures
  (`achievement_burst.shots` / `.delay`), optionally also pressing the Steam hotkey if
  `steam_hotkey_backup` is on.

> ⚠️ **Live bug:** `fire_achievement_burst` is defined as `(game_name, platform, settings)`
> but called with only `(platform, settings)` from both `achievement_detector._fire()` and
> the `/api/burst/fire` route. See `PROJECT_STATUS.md`.

---

## 6. State & Data Files

### `data/` (configuration — user-owned)
| File | Contents |
|---|---|
| `settings.json` | All user settings (created on wizard finish; absence ⇒ first-run). |
| `folders.json` | Game-folder paths per platform key. |
| `blacklist.txt` | User blacklist (one exe per line). |
| `blacklist_default.txt` | Shipped default blacklist (`#` comments allowed). |
| `disabled_games.txt` | Games excluded from detection (not blacklisted). |
| `shot_counters.json` | Per-game/per-type running screenshot numbers. |

### `status/` (runtime — app-owned, safe to delete)
| File | Contents |
|---|---|
| `state.json` | `{ games, activeGame, activePlatform, gameActive }` |
| `stats.json` | `{ screenshots_taken, scan_count, active_game, uptime }` |
| `games.json` | The scanned `{ exe: platform }` map. |
| `active_game.txt` | Current active exe (or empty). |
| `last_session.json` | `{ game, platform, start, end, shots, timestamp }` after a game closes. |

### `commands/` (IPC via flag files)
Write any non-empty content to a flag; the command loop consumes it (truncates back to
empty) within 2 s:
- `scan.flag` → triggers `scanner.scan_games()`.
- `reload.flag` → currently logs only (placeholder).

### `settings.json` shape (current, superset)
Not all keys are written by the wizard's `/api/setup/complete`; many are saved
incrementally by individual Settings-tab endpoints (`/api/settings` and friends).
Observed/used keys across the codebase:

```jsonc
{
  "interval": 420000,            // ms between timelapse shots
  "first_delay": 10,             // seconds before first shot
  "capture_mode": "timelapse",   // timelapse | action | hybrid
  "screenshot_folder": "screenshots",
  "per_game_folders": true,
  "screenshot_format": "png",    // png | jpeg
  "jpeg_quality": 90,

  "sensitivity": 30.0,           // action-shot diff threshold
  "action_cooldown": 5.0,        // seconds between action shots

  "burst_enabled": false,        // timelapse burst
  "burst_shots": 3,
  "burst_delay": 0.5,

  "achievement_screenshots_enabled": false,
  "achievement_burst": { "shots": 7, "delay": 0.5 },
  "steam_stats_folder": "",
  "steam_hotkey_backup": false,
  "hotkeys": { "steam": "f12", "gog": "f12", "epic": "f13",
               "ubisoft": "f13", "ea": "f13", "extra_games": "f10" },

  "notifications_enabled": true,
  "notification_sound": "",      // "" = built-in; else /static/sounds/notification.<ext>

  "popup_on_game": true,
  "minimise_to_tray": false,
  "popup_duration": 5,

  "open_with": "mspaint",        // gallery "open in app"
  "debug_mode": false,           // pywebview devtools (read once at launch)
  "version": "1.2"
}
```

> The `screenshot_folders` per-platform map and `hotkeys` map are legacy from the
> hotkey/overlay era. Direct capture uses the single `screenshot_folder`. Treat the
> per-platform folder map as deprecated.

---

## 7. Web Server & API (`webserver.py`)

Flask on `http://127.0.0.1:5050`. stdout is wrapped by `LogCapture` so the dashboard can
display recent console lines via `/api/log` (last 200 lines, reversed).

### Routes

**Setup / status**
| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serve UI |
| GET | `/favicon.ico` | Icon |
| GET | `/api/setup/status` | `{ setup_complete }` (true iff `settings.json` exists) |
| POST | `/api/setup/complete` | Save wizard settings, rescan |
| GET | `/api/status` | `state.json` |
| GET | `/api/stats` | `stats.json` |
| GET | `/api/sysinfo` | Version, OS, Python, arch |
| GET | `/api/log` | Recent console lines |

**Games / blacklist / scanning**
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/games` | `games.json` |
| POST | `/api/games/disable` | Add exe to disabled, rescan |
| GET | `/api/blacklist` | User blacklist |
| POST | `/api/blacklist/add` | Add + rescan |
| POST | `/api/blacklist/remove` | Remove |
| POST | `/api/blacklist/move_to_games` | Remove from blacklist, rescan |
| GET | `/api/scan/games` | Trigger scan |

**Folders**
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/folders` | `folders.json` |
| POST | `/api/folders/save` | Overwrite folders.json |
| POST | `/api/folders/autodetect` | Path + VDF detection, merged |
| POST | `/api/folders/add` / `/api/folders/remove` | Per-platform path edit |
| POST | `/api/browse/folder` | tkinter folder picker (60 s timeout) |
| POST | `/api/folders/open` | Open path in Explorer |

**Settings / sound / window / debug**
| Method | Route | Purpose |
|---|---|---|
| GET / POST | `/api/settings` | Read / overwrite settings.json |
| POST | `/api/sound/upload` / `/api/sound/delete` | Custom notification sound |
| GET | `/api/startup/status` | In Windows startup? |
| POST | `/api/startup/enable` / `/api/startup/disable` | Registry Run key |
| GET | `/api/debug/status`, POST `/api/debug/set` | Debug-mode flag |

**Gallery**
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/gallery/screenshots` | Paginated list (filter by game/type) |
| GET | `/api/gallery/games` | Game names present |
| GET | `/api/gallery/file/<h>` | Serve full image (hash → path via `_path_cache`) |
| GET | `/api/gallery/thumb/<h>` | Serve thumbnail (generates on demand) |
| POST | `/api/gallery/open` | Open in configured app |
| POST | `/api/gallery/delete` | Delete file + thumb |
| POST | `/api/gallery/rename` | Bulk rename to convention |
| GET | `/api/session/last` | `last_session.json` |
| GET | `/api/gallery/session` | Screenshots within the last session's time window |

**Steam AppID lookup** (public store API, no key)
| Method | Route | Purpose |
|---|---|---|
| GET | `/api/steam/lookup?appid=` | Single AppID → game name |
| POST | `/api/steam/lookup/batch` | Up to 20 AppIDs (0.5 s spacing) |

> Image serving uses an in-memory `_path_cache` (md5(path) → path) populated when a list
> page is requested. Thumb/file URLs only resolve for paths seen in a prior list call.
> The cache is never evicted (small leak; resets on restart).

---

## 8. Window, Tray & Startup (`app_window.py`)

- **Window:** pywebview 1000×720, min 800×600, points at the Flask URL.
- **Icon:** generated on first run — a 64px "ST" badge → `static/icon.png` + `icon.ico`.
  Applied to the titlebar via repeated `LoadImageW`/`WM_SETICON` WinAPI attempts.
- **Dark titlebar:** Windows 11 DWM `DWMWA_CAPTION_COLOR`/`TEXT_COLOR` (no-op on Win10).
- **Tray:** `pystray` menu — Open / Rescan Games / Exit. Balloon notification on game detect.
- **Close behaviour:** if `minimise_to_tray`, closing hides to tray; otherwise exits.
- **Startup:** `HKCU\...\Run` registry value `ShotTaker` → `python launch.py`.
  `install_startup.bat` / `remove_startup.bat` also exist as manual alternatives.
- **Headless fallback:** if pywebview isn't installed, the process stays alive so Flask
  still serves the UI in a normal browser.

---

## 9. Front-End (`templates/index.html` + `static/app.js`)

Single-page app, vanilla JS, no build step. Two surfaces:

**Setup Wizard** (shown when `setup_complete` is false; re-runnable from Settings).
Step ids: `welcome → platforms → capturemode → shotfolder → interval → actionshots →
achievements → notifications → window → gamefolders → steamstats → done`. The step list is
built dynamically from selected platforms/options (`buildStepList()`), and re-running
pre-fills from existing settings (`prefillWizard()`).

**Main tabs:** Dashboard, Gallery, Games, Blacklist, Settings (with sub-tabs).
Key JS entry points: `loadDashboard`, `loadGallery`/`renderGallery`/`openLightbox`,
`loadGames`/`filterGames`, `loadBlacklist`, `loadSettings`/`saveSettings` (+ granular
`saveCaptureMode`, `saveActionSettings`, `saveAchievementSettings`, `saveHotkeys`,
`saveGallerySettings`, `saveScreenshotFolders`, `saveSteamStatsFolder`),
`checkForNewGame` (polls `/api/status` to drive notifications), `loadLog`.

---

## 10. Installation & Running

```bat
:: First run — installs missing packages, then launches
start.bat
```

- `start.bat` checks/install: flask, psutil, pyautogui, pywebview, pystray, Pillow.
- `Start_distro.bat` runs `pip install -r requirements.txt` then launches.
- `launch.py` starts `main.py` detached (no console).

**Requirements:** Windows 10/11, Python 3.10+.

> ⚠️ **Dependency gap:** the core capture path needs **`mss`** and **`numpy`**, but neither
> `requirements.txt` nor `start.bat` installs them. Without them, `MSS_AVAILABLE` is false
> and *all direct capture silently no-ops*. Add them before relying on capture. See
> `PROJECT_STATUS.md`.

---

## 11. Glossary

- **TimeLapse** — interval-based capture (`interval` ms).
- **DynamicShot / Action Shot** — capture triggered by on-screen change.
- **Achievement burst** — N rapid captures when a Steam achievement unlocks.
- **GAME_LIST** — in-memory `{exe: platform}` map produced by the scanner.
- **Session** — the span between a game being detected and closing; summarised in
  `last_session.json`.
</content>
</invoke>
