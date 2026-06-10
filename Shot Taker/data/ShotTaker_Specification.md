# ShotTaker Specification

Version: 1.2
Status: Active Development

> ⚠️ **OUTDATED — historical reference only.** This v1.2 spec describes the original
> *hotkey-pressing* design (ShotTaker pressing Steam/GOG overlay hotkeys). The app has
> since moved to **direct screen capture** (mss) with Action Shots, achievement detection,
> and a built-in gallery. For the current architecture see `docs/ARCHITECTURE.md`, and for
> status/bugs/roadmap see `docs/PROJECT_STATUS.md`.

---

# Overview

ShotTaker is a standalone Windows application that automatically captures screenshots during gameplay by pressing platform overlay hotkeys on a timed interval.

The project began as an AutoHotkey script and has been rebuilt as a Python application with a local web interface.

**Core philosophy:** ShotTaker is a companion to existing platform overlays (Steam, GOG, Epic, etc.), not a replacement. It presses the screenshot hotkey so the platform overlay captures and saves the screenshot in its own format and location.

---

# Core Design Principles

## Simplicity
Users never need to edit code or config files. Everything is done through the Web UI and Setup Wizard.

## Platform Agnostic
Supported launchers: Steam, GOG Galaxy, Epic Games, Ubisoft Connect, EA App
Planned: Xbox PC, Battle.net

## Local First
No cloud, no accounts, no telemetry. All data stored locally.

## Extensible
New launchers, screenshot methods, and features should be easy to add.

---

# Project Structure

```
ShotTaker/
├── main.py                  ← Entry point, runs all threads
├── scanner.py               ← Scans game folders, builds GAME_LIST dict
├── detector.py              ← Matches running processes to GAME_LIST
├── blacklist.py             ← Blacklist load/add/remove (user + default)
├── state.py                 ← Tracks active game + platform, writes state.json
├── screenshots.py           ← Hotkey pressing logic + direct capture stub
├── steam_detect.py          ← Reads Steam libraryfolders.vdf
├── platform_detect.py       ← Auto-detects platform install paths
├── webserver.py             ← Flask web server and all API routes
├── requirements.txt         ← flask, psutil, pyautogui
├── start.bat                ← Launcher (checks packages, starts app)
├── Start_distro.bat         ← Simple launcher (pip install -r, then run)
│
├── data/
│   ├── folders.json         ← Game folder paths per platform
│   ├── settings.json        ← All user settings
│   ├── blacklist.txt        ← User-managed blacklist
│   ├── blacklist_default.txt← System/runtime/debugger process blacklist
│   └── disabled_games.txt   ← Games excluded from detection (not blacklisted)
│
├── status/
│   ├── games.json           ← Current scanned game list {exe: platform}
│   ├── state.json           ← Active game, platform, game count
│   └── stats.json           ← Screenshot count, scan count
│
├── commands/
│   ├── scan.flag            ← Write anything here to trigger a rescan
│   └── reload.flag          ← Write anything here to trigger a reload
│
├── templates/
│   └── index.html           ← Web UI markup
│
└── static/
    ├── app.js               ← Web UI logic
    ├── style.css            ← Web UI styles
    └── sounds/              ← Custom notification sounds (uploaded by user)
```

---

# Backend Architecture

## main.py — Entry Point

Starts three background threads on launch:

| Thread | Purpose |
|---|---|
| `game_loop` | Detects running games every 5 seconds, manages hotkey sessions |
| `command_loop` | Watches flag files for scan/reload triggers every 2 seconds |
| `start_server` | Runs Flask web server on port 5050 |

On startup: creates required directories, runs initial game scan, logs game count.

---

## scanner.py — Game Scanner

Walks configured folders for `.exe` files and builds a platform-tagged dict.

**Output format:** `{ "exe.exe": "platform" }` — stored in `scanner.GAME_LIST` and `status/games.json`

**Filters out:**
- Full blacklist (user + default merged via `load_full_blacklist()`)
- Disabled games
- Installer/updater patterns: install, setup, unins, update, updater, crashpad, crashreport, crash_handler, redist, vcredist, directx, dotnet, prereq, prerequisite, launcher
- Common junk subdirectories: `__pycache__`, `node_modules`, `.git`, `logs`, `cache`, `shadercache`, `htmlcache`, `webcache`

**Platform scan order:** steam → gog → epic → ubisoft → ea → extra_games
First platform to find an exe wins (no duplicates).

**Triggers:** On startup, after blacklist/disable changes, on wizard completion, via scan.flag file, via `/api/scan/games` route.

---

## detector.py — Game Detection

Uses `psutil` to iterate running processes every 5 seconds.
Compares process names (lowercased) against `scanner.GAME_LIST`.
Skips zombie/dead processes.
Returns `(exe, platform)` tuple, or `(None, None)`.

---

## blacklist.py — Blacklist Management

Two blacklist files:

| File | Purpose |
|---|---|
| `data/blacklist.txt` | User-managed, editable from UI |
| `data/blacklist_default.txt` | System processes, runtimes, debuggers, engine helpers — shipped with ShotTaker |

`load_full_blacklist()` merges both — this is what scanner and detector always use.

Default blacklist covers: Windows system processes, debug/release engine runtimes, installers, VC++ redistributables, .NET/Mono/Java/Python runtimes, crash handlers, debuggers, GPU overlay tools, platform launchers, common game engine helpers.

Comments in `blacklist_default.txt` (lines starting with `#`) are ignored.

---

## state.py — State Tracking

Writes `status/state.json` on every game loop tick:
```json
{
    "games": 142,
    "activeGame": "pathofexile2.exe",
    "activePlatform": "steam",
    "gameActive": true
}
```

---

## screenshots.py — Screenshot System

**Current mode: Hotkey pressing**
Presses the configured platform hotkey at a set interval while a game is active.
Supports single keys (`f12`) and combos (`ctrl+f12`) via `pyautogui.hotkey()`.

**Stub: Direct capture**
`run_direct_session()` is a placeholder for future direct Python screenshot capture. Not currently used.

**Session lifecycle:**
1. Game detected → `run_hotkey_session()` starts in a new thread
2. Waits `first_delay` seconds (default 10) before first press
3. Presses hotkey every `interval` milliseconds
4. Stops when `is_active()` returns False (game closed or switched)

---

## platform_detect.py — Platform Auto-Detection

Checks common Windows install paths per launcher.
Called during wizard game folder scan and Settings auto-scan.
Path-based only — does not use the Windows registry.

---

## steam_detect.py — Steam Library Detection

Reads `libraryfolders.vdf` from default Steam paths.
Extracts all configured Steam library locations.
Returns `steamapps/common` paths.
Used alongside `platform_detect.py` for Steam — both run and results are merged.

---

## webserver.py — Flask Web Server

Runs on `http://127.0.0.1:5050`

### API Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serves web UI |
| GET | `/api/setup/status` | Returns `{setup_complete: bool}` |
| POST | `/api/setup/complete` | Saves all wizard settings, triggers rescan |
| GET | `/api/status` | Returns state.json |
| GET | `/api/stats` | Returns stats.json |
| GET | `/api/games` | Returns games.json dict |
| POST | `/api/games/disable` | Adds exe to disabled_games.txt, rescans |
| GET | `/api/blacklist` | Returns user blacklist |
| POST | `/api/blacklist/add` | Adds exe to blacklist, rescans |
| POST | `/api/blacklist/remove` | Removes exe from blacklist |
| POST | `/api/blacklist/move_to_games` | Removes from blacklist + disabled, rescans |
| GET | `/api/scan/games` | Triggers a game scan |
| GET | `/api/folders` | Returns folders.json |
| POST | `/api/folders/save` | Saves folders.json |
| POST | `/api/folders/autodetect` | Runs platform + VDF detection, merges results |
| POST | `/api/folders/add` | Adds a folder path for a platform |
| POST | `/api/folders/remove` | Removes a folder path for a platform |
| POST | `/api/browse/folder` | Opens tkinter folder picker, returns path |
| POST | `/api/folders/open` | Opens a path in Windows Explorer |
| GET | `/api/settings` | Returns settings.json |
| POST | `/api/settings` | Saves settings.json |
| POST | `/api/sound/upload` | Uploads custom notification sound to static/sounds/ |
| POST | `/api/sound/delete` | Removes custom sound, reverts to built-in |
| GET | `/api/log` | Returns recent console log lines for dashboard display |

---

# Web UI

Single-page app served by Flask. Tab navigation.

## Setup Wizard

Shown on first launch (no `data/settings.json`). Re-runnable from Settings tab.
Pre-fills from existing settings when re-run — does not reset.

### Wizard Steps
1. **Welcome** — explains ShotTaker, browse button note
2. **Platform Select** — which launchers to configure (Steam pre-ticked)
3. **Hotkey Mode** — unified key or per-platform, duplicate screenshot warning
4. **Folder Mode** — unified folder or per-platform, instructions to update in each launcher
5. **Unified Hotkey** *(unified mode only)* — single key input with key capture
6–10. **Per-platform steps** *(one per selected platform)* — hotkey input, folder input, step-by-step instructions for changing settings in that launcher, copy buttons, "Done" + "I'll do this later" checkboxes
11. **Game Folders** — auto-scans on load, shows results per platform, add/remove folders, Browse button
12. **Notifications** — enable/disable, test button, custom sound upload, explanation of what notifications mean
13. **Interval** — screenshot frequency + first delay
14. **Done** — summary of all settings with status per platform

## Dashboard Tab
- Active game + platform
- Total games detected
- Screenshots taken
- Screenshot folder quick-access links (opens in Explorer)
- Detection log (live console output, colour-coded)

## Games Tab
- Search bar (filters by exe name as you type)
- Platform filter buttons (All / Steam / GOG / Epic / Ubisoft / EA / Other)
- Game count display (showing X of Y)
- Per-game: platform tag, Blacklist button, Disable button

## Blacklist Tab
- List of user-blacklisted executables
- Per-entry: Restore button (removes from blacklist, triggers rescan)

## Settings Tab
- Screenshot interval + first delay
- Per-platform hotkeys (key capture inputs)
- Per-platform screenshot folders (Browse + Open buttons)
- Game folder management (add/remove/browse per platform, auto-scan, rescan games)
- Notifications (toggle, custom sound upload, test button)
- Re-run Setup Wizard button

---

# Data Files

## data/settings.json
```json
{
    "interval": 420000,
    "first_delay": 10,
    "hotkey_mode": "unified",
    "folder_mode": "unified",
    "selected_platforms": ["steam"],
    "hotkeys": {
        "steam": "f12",
        "gog": "f12",
        "epic": "f13",
        "ubisoft": "f13",
        "ea": "f13",
        "extra_games": "f10"
    },
    "screenshot_folders": {
        "steam": "",
        "gog": "",
        "epic": "",
        "ubisoft": "",
        "ea": "",
        "custom": []
    },
    "notifications_enabled": true,
    "notification_sound": ""
}
```

## data/folders.json
```json
{
    "steam": ["C:\\Program Files (x86)\\Steam\\steamapps\\common"],
    "gog": [],
    "epic": [],
    "ubisoft": [],
    "ea": [],
    "extra_games": []
}
```

---

# Known Issues / Current Gaps

| Area | Issue |
|---|---|
| screenshots.py | Hotkey press count not yet incremented in stats.json |
| stats.json | Per-game session history not yet tracked |
| Wizard | Steps are dynamic but summary doesn't indicate skipped platforms clearly enough |

---

# Planned Features

## Phase 1 — Core Stability ✅ Complete
- ✅ Game folder scanning with platform tags
- ✅ Process-based game detection
- ✅ Full blacklist system (user + default)
- ✅ Hotkey pressing per platform
- ✅ Web UI with wizard
- ✅ Platform auto-detection
- ✅ Browser notifications with sound
- ✅ Game folder management (add/remove/browse)
- ✅ Games list search + platform filter
- ✅ Detection log on dashboard
- ✅ Screenshot folder quick-access links

## Phase 2 — Stats + History
- ⬜ Increment screenshot counter when hotkey fires
- ⬜ Per-game session log (game, date, duration, screenshot count)
- ⬜ Stats dashboard (total shots, most played game, session history)

## Phase 3 — Achievement Screenshots
- ⬜ Steam achievement detection (via Steam Web API or log watching)
- ⬜ Auto-screenshot on achievement unlock
- ⬜ GOG / Epic / Ubisoft / EA achievement detection

## Phase 4 — Screenshot Gallery
- ⬜ Built-in gallery view in web UI
- ⬜ Per-game screenshot browsing
- ⬜ Thumbnail generation

## Phase 5 — Platform Expansion
- ⬜ Xbox PC
- ⬜ Battle.net

## Phase 6 — Distribution
- ⬜ PyInstaller packaging — single `.exe` for Windows, `.app` for Mac, binary for Linux
- ⬜ Must be built separately per platform (no cross-compilation)
- ⬜ Removes requirement for Python to be installed by end users
- ⬜ Planned when feature set is considered stable

---

# Non-Goals

ShotTaker will NOT:
- Require cloud accounts or subscriptions
- Upload screenshots automatically
- Depend on external online services
- Require users to edit code or config files manually
