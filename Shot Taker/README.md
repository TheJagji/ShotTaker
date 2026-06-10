# ShotTaker

**Every moment worth keeping.**

ShotTaker is a standalone Windows screenshot companion for PC gaming. It runs quietly in the
background, detects when you're playing, and **automatically captures your best moments** —
no platform overlay required. Local-first: no accounts, no cloud, no telemetry.

> ShotTaker is the evolved, rebranded successor to the *ShotTaker* prototype — rebuilt around
> a direct-capture engine with smart quality filtering, a full library, stats, and a
> one-file installer.

---

## Features

### Capture
- **Direct screen capture** (no overlay needed) — saves PNG, JPEG, or **WebP**.
- **Three modes:** ⏱ Time Lapse · ⚡ Action Shots (on-screen change) · 🔀 Hybrid.
- **Smart quality gate** — automatically skips loading screens, menus, black frames,
  letterboxed cutscenes, and near-duplicate frames so your gallery is all signal.
- **Pre-capture buffer** — optionally saves the frame *just before* an action moment.
- **Multi-monitor aware** — auto-picks the display your game is on, or pick one / all.
- **Achievement bursts** — fires a burst of shots when a Steam achievement unlocks.
- **Manual hotkey** — grab a shot on demand (default `F9`).
- **Resolution scaling & watermarks** for smaller files / branded shots.

### Library
- **Built-in gallery** — browse, filter (game / type / favorites / tags), search, and sort.
- **Favorites, tags, and star ratings**, stored in a metadata index.
- **Bulk select** → export ZIP, generate a **contact sheet**, or stitch an animated **GIF**.
- **Bulk rename** imported screenshots into the ShotTaker convention.
- **Storage guardrails** — cap shots-per-game or total disk, auto-rotating oldest
  non-favorites.

### Games & stats
- **Auto game detection** across Steam, GOG, Epic, Ubisoft, EA, Xbox, Battle.net, Riot,
  Rockstar, and itch.io.
- **Friendly game names** resolved automatically (with manual overrides).
- **Per-game profiles** — different capture settings per title.
- **Session history & stats dashboard** — playtime, most-played, shots-per-game, a 30-day
  capture sparkline, and an event log.
- **Privacy guard** — auto-pauses capture when a sensitive app is focused.

### App
- **Branded local web UI** in a native window, dark/light themes, system tray.
- **Launch with Windows**, config import/export, and a guided first-run setup.

---

## Quick start (from source)

1. Install Python 3.10+.
2. Double-click **`start.bat`** (installs dependencies on first run and launches ShotTaker).
3. Follow the setup wizard to pick your launchers, capture mode, and screenshot folder.

## Build the standalone .exe

```bat
build.bat
```

This produces **`dist\ShotTaker.exe`** — a single windowed executable with no Python
required on the target machine. User data (settings, screenshots, library) is written next
to the exe.

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — modules, data flow, API, file formats.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — feature status & limitations.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the roadmap this release was built from.
- [`docs/BRAND.md`](docs/BRAND.md) — brand identity & design tokens.

## License

MIT — see [LICENSE](LICENSE).
