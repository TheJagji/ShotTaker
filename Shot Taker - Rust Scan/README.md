# ShotTaker

**Every moment worth keeping.**

ShotTaker is a standalone Windows screenshot companion for PC gaming. It runs quietly in the background, detects when you're playing, and automatically captures your best moments — no platform overlay required. Local-first: no accounts, no cloud, no telemetry.

---

## Two editions

| Edition | File | Notes |
|---|---|---|
| **Standard** | `start.bat` | Python + mss. Works on any Python 3.10+ install. |
| **Rust** | `start_rust.bat` | DXGI-accelerated capture via a native Rust extension. Lower CPU, faster grabs. Requires Rust installed. |

Both editions share the same UI and feature set. The Rust edition is the recommended choice if you're comfortable installing Rust.

---

## Quick start — Standard edition

1. Install **Python 3.10+** from [python.org](https://python.org).
2. Double-click **`start.bat`** — it installs dependencies and launches ShotTaker.
3. Follow the setup wizard to pick your game libraries, capture mode, and screenshot folder.

## Quick start — Rust edition

1. Install **Python 3.10+** from [python.org](https://python.org).
2. Install **Rust** from [rustup.rs](https://rustup.rs) (accept defaults).
3. Double-click **`start_rust.bat`** — it installs Python deps, builds the Rust extension, and launches ShotTaker.
4. Follow the setup wizard.

On first launch, `start_rust.bat` compiles the native capture engine — this takes 1–2 minutes. Subsequent launches skip the build automatically.

---

## Features

### Capture
- **Direct screen capture** — saves PNG, JPEG, or WebP. No platform overlay needed.
- **Three modes:** ⏱ Time Lapse · ⚡ Action Shots (on-screen change detection) · 🔀 Hybrid.
- **Adjustable sensitivity slider** — dial in exactly how much the screen needs to change before an Action Shot fires.
- **Smart quality gate** — automatically skips loading screens, menus, black frames, letterboxed cutscenes, and near-duplicate frames.
- **Pre-capture buffer** — optionally saves the frame just before an action moment.
- **Multi-monitor aware** — auto-picks the display your game is on, or pick one / all.
- **Achievement bursts** — fires a burst of shots when a Steam achievement unlocks.
- **Manual hotkey** — grab a shot on demand (default `F9`).
- **Resolution scaling & watermarks** for smaller files / branded shots.
- **Rust/DXGI engine** *(Rust edition)* — uses Windows DXGI desktop duplication for GPU-accelerated, low-CPU capture.

### Library & gallery
- **Built-in gallery** — browse, filter (game / type / favorites / tags), search, and sort.
- **Right-click context menu** — favorite, rate, tag, open, send to cloud folder, or delete without opening the lightbox.
- **Click to select** in select mode — no need to hit a tiny checkbox.
- **Favorites, tags, and star ratings** stored in a metadata index.
- **Bulk select** → export ZIP, generate a contact sheet, or stitch an animated GIF.
- **Bulk rename** imported screenshots into the ShotTaker convention.
- **Storage guardrails** — cap shots-per-game or total disk, auto-rotating oldest non-favorites.

### Cloud folder
- Set a cloud sync folder (Dropbox, OneDrive, Google Drive local folder) in Settings → Storage.
- After a game session closes, an optional popup lets you pick which screenshots to copy there.
- Right-click any screenshot to send it to the cloud folder at any time.
- No API keys, no accounts — ShotTaker just copies files to a folder you point it at.

### Games & stats
- **Auto game detection** across Steam, GOG, Epic, Ubisoft, EA, Xbox, Battle.net, Riot, Rockstar, and itch.io.
- **Friendly game names** resolved automatically (with manual overrides).
- **Per-game profiles** — different capture settings per title.
- **Scanned Lists** — manage your detected games and blacklist from one place.
- **Session history & stats dashboard** — playtime, most-played, shots-per-game, a 30-day capture sparkline with per-game colours, shot type breakdown, and an event log.
- **Performance metrics** *(Rust edition)* — logs grab time, diff time, and CPU usage every 50 captures for comparison.
- **Privacy guard** — auto-pauses capture when a sensitive app is focused.

### App
- **Grouped settings** — Shot Settings / App Settings / Dev Info, with sub-tabs for easy navigation.
- **Branded local web UI** in a native window, dark/light themes, system tray.
- **Feedback section** — built-in bug report / feature request form with log attachment, debug mode toggle, and detection log with copy button.
- **About section** — content driven by `data/about.txt`.
- **Launch with Windows**, config import/export, and a guided first-run setup wizard.

---

## File structure

```
ShotTaker/
├── main.py                  ← Entry point
├── *.py                     ← All backend modules
├── data/                    ← Static shipped data (committed)
│   ├── blacklist_default.txt
│   └── about.txt
├── static/                  ← Front-end assets (committed)
│   ├── app.js
│   ├── style.css
│   └── icon.png / icon.ico
├── templates/
│   └── index.html
├── rust_capture/            ← Rust extension source
│   ├── Cargo.toml
│   └── src/lib.rs
├── docs/                    ← Architecture, status, roadmap
├── tests/
├── requirements.txt
├── start.bat                ← Standard launcher
├── start_rust.bat           ← Rust edition launcher
├── build_rust.bat           ← Build Rust extension only
├── build.bat                ← PyInstaller .exe build
├── install_startup.bat      ← Add to Windows startup
├── remove_startup.bat       ← Remove from Windows startup
└── user_data/               ← Generated at runtime (gitignored)
    ├── data/                ← User settings & generated data
    ├── status/              ← Runtime state
    ├── commands/            ← IPC flag files
    ├── sounds/              ← Uploaded notification sounds
    ├── Screenshots/         ← Default screenshot folder
    └── Exports/             ← ZIP / contact sheet / GIF exports
```

`user_data/` is created automatically on first run and is never committed to the repo.

---

## Build the standalone .exe

```bat
build.bat
```

Produces `dist\ShotTaker.exe` — a single windowed executable requiring no Python on the target machine.

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — modules, data flow, API routes, file formats.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — feature status, known issues, dev branch changes.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — prioritised feature roadmap.
- [`docs/BRAND.md`](docs/BRAND.md) — brand identity and design tokens.

## Requirements

- Windows 10/11
- Python 3.10+
- Rust 1.70+ *(Rust edition only)*
- Dependencies: `flask`, `psutil`, `pyautogui`, `pywebview`, `pystray`, `Pillow`, `mss`, `numpy`, `requests`

## License

MIT — see [LICENSE](LICENSE).
