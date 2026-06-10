# ShotTaker Beta

A standalone Windows screenshot companion for PC gaming. ShotTaker runs in the background, detects when you're playing a game, and automatically captures screenshots — no platform overlay required.

!\[ShotTaker Dashboard](docs/screenshot.png)

\---

## Features

* **Automatic game detection** — detects running games from Steam, GOG, Epic, Ubisoft Connect, and EA App
* **Three capture modes:**

  * ⏱ **Time Lapse** — screenshots at a set interval (e.g. every 7 minutes)
  * ⚡ **Action Shots** — captures when significant screen changes are detected
  * 🔀 **Hybrid** — both modes simultaneously
* **Achievement screenshots** — burst of screenshots when a Steam achievement unlocks - Untested
* **Built-in gallery** — browse, filter, and manage all your screenshots
* **Bulk rename** — rename imported screenshots to the ShotTaker naming convention
* **Steam AppID lookup** — identify numeric Steam screenshot folders by game name
* **System tray** — runs quietly in the background
* **Local web UI** — control everything from a browser at `http://127.0.0.1:5050`
* **No accounts, no cloud, no telemetry** — everything stays on your PC

\---

## Requirements

* Windows 10 or 11
* Python 3.10+
* The following Python packages (installed automatically by `start.bat`):

  * `flask`, `psutil`, `pyautogui`, `pywebview`, `pystray`, `Pillow`, `mss`, `numpy`

\---

## Installation

1. Download or clone this repository
2. Double-click `start.bat`
3. The first launch will install any missing packages and open the Setup Wizard
4. Follow the wizard to configure your platforms, capture mode, and screenshot folder

\---

## Usage

### Starting ShotTaker

Double-click `start.bat`. After the first run, you can enable **Launch with Windows** in Settings → Window so it starts automatically.

### Capture Modes

|Mode|Description|CPU Usage|
|-|-|-|
|Time Lapse|Screenshot every N minutes|Low|
|Action Shots|Screenshot on screen change|Medium–High|
|Hybrid|Both simultaneously|High|

Action Shots and Hybrid modes monitor your screen continuously. On lower-end systems this may affect game performance.

### Screenshot Naming

Screenshots are saved as:

```
GameName\_TimeLapse\_001.png
GameName\_DynamicShot\_001.png
GameName\_Achievement\_001.png
```

Numbers continue from where they left off across sessions.

### Gallery

Open the Gallery tab to browse your screenshots. You can:

* Filter by game or shot type
* View the **Recent Session** after closing a game
* Select multiple screenshots for bulk rename or delete
* Open screenshots in Paint or another configured app
* Look up Steam AppIDs to identify numeric folder names

### Achievement Screenshots

ShotTaker watches Steam's local stats folder for achievement unlocks and fires a burst of screenshots automatically. Configure the stats folder path in **Settings → Platforms** if Steam is installed on a non-default drive.

\---

## Project Structure

```
ShotTaker/
├── main.py                 # Entry point
├── scanner.py              # Game folder scanner
├── detector.py             # Process-based game detection
├── capture\_manager.py      # Direct screenshot capture
├── change\_detector.py      # Action Shots screen change detection
├── gallery\_manager.py      # Gallery indexing and thumbnail generation
├── achievement\_detector.py # Steam achievement detection
├── screenshots.py          # Session manager (coordinates capture modes)
├── blacklist.py            # Blacklist management
├── state.py                # Active game state tracking
├── steam\_detect.py         # Steam library VDF reader
├── platform\_detect.py      # Platform install path detection
├── webserver.py            # Flask web server and API
├── app\_window.py           # pywebview window + system tray
├── launch.py               # Silent launcher (no console window)
├── start.bat               # First-run launcher with package check
├── data/                   # Configuration files
├── status/                 # Runtime state files
├── templates/              # HTML templates
└── static/                 # CSS and JS
```

\---

## Platform Support

|Platform|Game Detection|Screenshot Capture|Achievement Screenshots|
|-|-|-|-|
|Steam|✅|✅ Direct|✅|
|GOG Galaxy|✅|✅ Direct|⬜ Planned|
|Epic Games|✅|✅ Direct|⬜ Planned|
|Ubisoft Connect|✅|✅ Direct|⬜ Planned|
|EA App|✅|✅ Direct|⬜ Planned|

\---

## Roadmap

* \[ ] Per-game session history and stats
* \[ ] Achievement screenshots for GOG, Epic, Ubisoft, EA
* \[ ] Built-in screenshot gallery with full thumbnail browser
* \[ ] PyInstaller packaging (single `.exe` for Windows, `.app` for Mac)
* \[ ] Mac and Linux support
* \[ ] Xbox PC and Battle.net platform support

\---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

\---

## License

MIT License — see [LICENSE](LICENSE) for details.

