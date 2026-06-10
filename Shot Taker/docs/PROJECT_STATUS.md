# ShotTaker — Project Status, Limitations & Roadmap

Companion to `ARCHITECTURE.md`. This is the working "where things stand" document:
what works, what's broken, what's missing, and what to build next.

Last reviewed against the codebase: 2026-06-10.

---

## 🚀 Release: ShotTaker 1.3.0 (roadmap implementation)

The full roadmap was implemented for the **ShotTaker** 1.3.0 release:

- **Brand** (`branding.py`): name, palette, focus-reticle logo, design tokens; applied
  across the web UI (runtime-themed via `/api/brand`), window, tray, titlebar, and exe icon.
- **Foundation:** central `config.py` (settings + frozen-aware paths), shared `frames.py`,
  screenshot `library.py`, watchdog, capture-metadata index.
- **Milestone 0 bugs fixed:** dependencies (`mss`/`numpy`) added; `fire_achievement_burst`
  now receives the game name; `extra_games`→`extra` unified; counters case-normalised.
- **Capture quality:** loading-screen / dark / letterbox suppression, near-duplicate
  pruning, pre-capture buffer, multi-monitor selection, manual hotkey.
- **Output/storage:** WebP, resolution scaling, watermark, per-game + total-disk caps.
- **Library:** favorites, tags, ratings, search/sort, bulk export (ZIP / contact sheet / GIF).
- **Games/stats:** session history, friendly game-name resolution, per-game profiles,
  stats dashboard, privacy guard, more launchers (Xbox/Battle.net/Riot/Rockstar/itch).
- **Packaging:** PyInstaller single-exe (`shottaker.spec` / `build.bat` → `dist/ShotTaker.exe`).
- **Tests:** `tests/test_core.py`, `tests/api_test.py`, `tests/smoke.py` all green.

The "Known Bugs" and per-milestone tables below are retained as historical record; the
items marked there have been addressed in this release.

---

## 1. Feature Inventory

| Feature | Status | Notes |
|---|---|---|
| Game folder scanning (per platform) | ✅ Working | `scanner.py`; junk/installer filtering |
| Process-based game detection | ✅ Working | `detector.py`, 5 s poll via `psutil` |
| User + default blacklist | ✅ Working | merged set used everywhere |
| Disabled-games list | ✅ Working | separate from blacklist |
| **Direct screen capture (mss)** | ✅ Working* | *requires `mss`+`numpy` — not in requirements |
| TimeLapse mode | ✅ Working | interval + optional burst |
| Action Shots (screen-diff) | ✅ Working | `change_detector.py`, CPU-heavy |
| Hybrid mode | ✅ Working | timelapse + action together |
| PNG / JPEG output + quality | ✅ Working | per-game folders, persistent counters |
| Thumbnails | ✅ Working | `.thumbs/`, lazy + eager generation |
| Built-in gallery (browse/filter/lightbox) | ✅ Working | pagination, per-game/type filter |
| Bulk rename to convention | ✅ Working | moves files + thumbs into per-game folders |
| Delete / open-in-app | ✅ Working | `open_with` (default mspaint) |
| Recent-session view | ✅ Working | filters by last session's time window |
| Steam AppID lookup (single + batch) | ✅ Working | public store API, no key |
| Steam achievement screenshots | ⚠️ Buggy | see Bug #1 — call signature is wrong; "Untested" per README |
| Steam hotkey backup mode | ✅ Working | optional, Steam only |
| Setup wizard (dynamic steps) | ✅ Working | re-runnable, pre-fills |
| Local web UI in native window | ✅ Working | pywebview + dark titlebar |
| System tray | ✅ Working | pystray; open/rescan/exit |
| Browser + tray notifications | ✅ Working | custom sound upload |
| Launch with Windows | ✅ Working | HKCU Run key |
| Platform auto-detection | ✅ Working | path-based + Steam VDF |
| Per-game session history / stats dashboard | ⬜ Missing | only *last* session is stored |
| Achievement detection for GOG/Epic/Ubisoft/EA | ⬜ Missing | Steam only |
| PyInstaller packaging | ⬜ Missing | still Python-source distribution |
| Mac / Linux support | ⬜ Missing | Windows-only (WinAPI, registry, mss monitor) |
| Xbox PC / Battle.net platforms | ⬜ Missing | not in scan order |

---

## 2. Known Bugs (concrete, found in code)

### Bug #1 — `fire_achievement_burst` called with wrong arguments  *(high)*
`screenshots.py` defines:
```python
def fire_achievement_burst(game_name, platform, settings): ...
```
But **both** callers pass only two arguments:
- `achievement_detector.py` → `_fire()`: `args=(platform, settings)`
- `webserver.py` → `/api/burst/fire`: `args=(platform, settings)`

Result: `game_name` receives the *platform string*, `platform` receives the *settings dict*,
and `settings` is missing → `TypeError` (missing positional arg) or, if defaults were added,
captures saved under a game named "steam". **Achievement bursts and the manual burst button
do not work correctly.** Fix by threading the active game name through to both callers (the
game name is available in `state.ACTIVE_GAME` / the achievement detector's closure).

### Bug #2 — `folders.json` platform-key mismatch (`extra` vs `extra_games`)  *(medium)*
`scanner.py` scans the key `extra_games`; the live `data/folders.json` and the UI use
`extra`. Any folders the user adds under "extra/other" are **never scanned**. Pick one key
and use it consistently across scanner, folders.json, settings `hotkeys`, and the front-end.

### Bug #3 — Missing core dependencies in install scripts  *(high)*
`mss` and `numpy` are required by `capture_manager.py` and `change_detector.py`, but are
absent from both `requirements.txt` and `start.bat`. On a clean install, `MSS_AVAILABLE`
is false and **all direct capture silently does nothing** — the app appears to run but
saves no screenshots. Add `mss` and `numpy` to both.

### Bug #4 — Shot-counter / filename case inconsistency  *(low–medium)*
`shot_counters.json` already contains both `pathofexilesteam_DynamicShot` and
`PathOfExileSteam_DynamicShot`. Counters are keyed by the sanitised game name, which
preserves whatever case the source produced (detector returns original process case;
gallery rename uses the user-typed name). Different cases ⇒ divergent counters and possible
filename collisions on case-insensitive NTFS. Normalise the counter key (e.g. casefold)
or canonicalise game names once.

### Bug #5 — `scan_count` runaway  *(low)*
`status/stats.json` shows `scan_count: 11485`. `scanner.scan_games()` increments it on every
scan, and scans are triggered liberally (startup, flag files, every blacklist/disable/folder
change, wizard). Not harmful, but the number is meaningless as a metric. Consider dropping it
or repurposing it.

### Bug #6 — `_path_cache` never evicted  *(low)*
`webserver._path_cache` grows for every gallery item ever listed and is only cleared on
restart. Minor memory leak for very large libraries. Consider an LRU or deriving the path
from a signed/relative token instead of caching.

### Bug #7 — `config.py` is empty but imported nowhere  *(cleanup)*
1-byte placeholder. Intended as the shared config/util home; currently dead.

---

## 3. Architectural Limitations

- **Primary monitor only.** Capture and diff both use `mss` `monitors[1]`. No multi-monitor
  selection and no per-game-window capture (a full-screen game on monitor 2 is missed).
- **Windows-only.** WinAPI icon/titlebar calls, registry startup, tkinter picker, and the
  monitor model assume Windows. Mac/Linux would need real abstraction.
- **Polling everywhere.** Game loop 5 s, command loop 2 s, achievement 1 s, action ~0.5 s.
  Works, but Action/Hybrid mode is genuinely CPU-intensive (continuous full-screen grab +
  resize + numpy diff). Documented as such; could be optimised (capture region, frame skip,
  GPU, or event-driven hooks).
- **Settings loading is duplicated** across ~7 modules with no schema or validation. No
  central defaults merge, so a partially-written `settings.json` relies on per-call
  `.get(default)` scattered through the code. First refactor: a single `config.py` with
  `load_settings()`/`save_settings()` and a defaults merge.
- **No automated tests.** There is no test suite, CI, or linting config.
- **`reload.flag` is a no-op** beyond logging.
- **Achievement detection is heuristic** (any `.bin` mtime change = achievement) and Steam-
  specific; it can false-positive on non-achievement stat writes.

---

## 4. Roadmap

The full prioritized product roadmap (impact/effort ratings, milestones, and suggested
release cuts) lives in **`docs/ROADMAP.md`**. In short:

- **Milestone 0 — Stop the bleeding:** the install/correctness bugs in §2 above (deps,
  burst args, `extra_games` key, counter casing). Do these first.
- **Milestone 1 — Foundations:** shared `config.py`, capture-metadata sidecar, tests, watchdog.
- **Milestone 2 — Make captures good:** loading-screen suppression, smart moment detection,
  near-duplicate pruning. *Highest product leverage.*
- **Milestones 3–8:** output/storage (WebP, guardrails), gallery depth (favorites, search),
  session history + real game-name resolution + stats, achievements, opt-in sharing, and
  packaging/platform reach.

See `docs/ROADMAP.md` for the per-item breakdown and the top-5 near-term wins.

---

## 5. Quick Orientation for a New Contributor

- Start in `main.py` (`game_loop`) to see the whole control flow.
- The capture logic you'll touch most is `capture_manager.py`.
- The web API and the front-end glue are `webserver.py` + `static/app.js`.
- Settings flow: wizard → `/api/setup/complete`, then granular saves via `/api/settings`.
- To test capture without a game: temporarily make `is_active()` return `True` and call
  `capture_screenshot("Test", "TimeLapse", load_settings())`.
- Logs: in-app dashboard (`/api/log`) or `launch_error.log` when started via `launch.py`.
</content>
