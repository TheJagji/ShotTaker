# ShotTaker — Change Log (Rust Edition)

All changes made from the baseline v1.3.0 to the current Rust edition release.

---

## New Files

- **`rust_capture/Cargo.toml`** — Rust extension project config (pyo3 0.24, windows 0.58)
- **`rust_capture/src/lib.rs`** — Native capture engine: DXGI desktop duplication (Windows), stub backends for Linux/Mac, frame diff scoring, quality gate, monitor listing — all exposed to Python via pyo3
- **`start_rust.bat`** — All-in-one launcher: checks Python, installs deps, builds Rust extension if needed, launches app. Skips rebuild on subsequent runs.
- **`build_rust.bat`** — Standalone Rust extension builder (for manual rebuilds)
- **`.gitignore`** — Ignores `user_data/`, `rust_capture/target/`, `*.pyd`, `__pycache__/`, build artifacts, IDE files

---

## Modified Files

### `branding.py`
- Version updated to `1.3.0-r` to distinguish the Rust edition

### `config.py` *(complete rewrite)*
- **`user_data/` folder separation** — all generated/user files now live under `user_data/` (gitignored). Static shipped data stays in `data/`
- New constants: `USER_DATA_DIR`, `STATIC_DATA_DIR`, `SOUNDS_DIR` (moved to `user_data/sounds/`)
- `ABOUT_FILE` now points to `data/about.txt` (shipped, not user-generated)
- `BLACKLIST_DEFAULT_FILE` moved to `STATIC_DATA_DIR`
- Default screenshot folder now `user_data/Screenshots/`
- `force_mss` and `cloud_folder` / `cloud_popup_enabled` added to `DEFAULTS`
- `write_json()` now retries `os.replace()` up to 5 times with 50ms delay to handle WinError 5 file lock race on Windows
- `import time` added for retry logic
- `ensure_dirs()` seeds `focus.flag` alongside `scan.flag` and `reload.flag`

### `frames.py` *(complete rewrite)*
- **Dual backend** — tries `import rust_capture` first, falls back to mss if not available
- `_force_mss()` reads `user_data/data/settings.json` at import time — if `force_mss: true`, skips Rust and uses mss
- All analysis functions (`score_diff`, `mean_luminance`, `detail_score`, `is_letterboxed`, `quality_reject`) delegate to Rust when available, fall back to numpy
- `grab()` accepts `sct=None` when Rust is active (no mss context needed)
- `list_monitors()` returns monitor list from either Rust or mss
- **Performance tracker** (`PERF`) — logs grab time, diff time, and CPU usage every 50 captures to the detection log
- `pick_monitor()` kept for mss fallback compatibility

### `capture_manager.py`
- `capture_screenshot()` skips the mss context when `frames.RUST_AVAILABLE` is True
- Counter keys now use `.casefold()` instead of `.lower()` (Bug #4 fix — prevents duplicate counter series)

### `change_detector.py`
- `_loop()` runs without an mss context when Rust is active
- Falls back to `with mss.mss() as sct:` only when mss backend is in use

### `scanner.py`
- Removed `scan_count` increment (Bug #5 — was hitting 11,485, meaningless metric)

### `achievement_detector.py`
- `fire_achievement_burst` arg order confirmed correct (game, platform, settings)

### `requirements.txt`
- Added `mss`, `numpy`, `requests` (Bug #3 fix — without mss/numpy capture silently did nothing on clean install)

### `launch.py`
- **Single instance check** — reads `user_data/shottaker.lock`. If another instance is running, writes `focus.flag` and exits instead of spawning a duplicate
- Writes own PID to lock file on successful launch
- `launch_error.log` now writes to `user_data/` instead of project root

### `main.py`
- `command_loop()` now handles `focus.flag` — calls `window_manager.show()` to bring the existing window to front when a second launch is attempted

### `webserver.py`
- Port changed to `5051` (Dev build stays on `5050` — both can run simultaneously)
- New routes:
  - `GET /api/about` — serves `data/about.txt`
  - `POST /api/about` — saves `data/about.txt`
  - `GET /api/cloud/copy` — copies selected screenshots to configured cloud folder
  - `GET /api/game/icon/<exe>` — serves Steam game icon from local cache
  - `GET /user_data/sounds/<file>` — serves uploaded notification sounds
- `/api/sound/upload` and `/api/sound/delete` updated to use `user_data/sounds/`
- `last_capture.json` path fixed to use `STATUS_DIR`
- `write_json()` retry logic applied throughout

### `export.py`
- `Exports/` folder moved to `user_data/Exports/`

### `app_window.py`
- URL changed to `http://127.0.0.1:5051`

### `static/app.js` *(major rewrite)*

**Navigation & structure:**
- Sidebar: `Games` → `Scanned Lists` (new `page-scanned` tab)
- `TITLES` updated, `switchTab` handles both `games` and `scanned` for backward compat

**Dashboard:**
- Removed "Now playing" panel and Detection Log panel
- Added mini stats: 6 stat cards, colour-coded sparkline, top games by shots bar chart
- Dashboard auto-refreshes every 30 seconds

**Scanned Lists (replaces Games tab):**
- Two sub-tabs: Games List and Blacklist
- Games list shows Steam icons (lazy-loaded with 30ms stagger to avoid hammering Flask)
- Blacklist manageable inline — Restore (moves back to game list) and Remove buttons
- Both sub-tabs share the same page

**Gallery:**
- **Right-click context menu** — Favorite, Rate 1–5, Tag, Open file, Send to cloud folder, Delete
- **Click to select** in select mode (no longer requires hitting the checkbox)
- Icons lazy-load with staggered delay

**Settings restructure:**
- Three parent groups: **Shot Settings**, **App Settings**, **Dev Info**
- Sub-tabs per group:
  - Shot Settings: Capture, Quality, Achievements, Storage, Folders
  - App Settings: Notifications, Window, Privacy, Advanced
  - Dev Info: Feedback, About
- `settingsGroups` row above sub-tabs
- `buildSettingsTabs()`, `switchSettingsGroup()`, `setSettingsTab()` all handle the two-level structure
- Settings body always cleared before rendering to prevent stale content

**Capture tab:**
- Action sensitivity moved here (was in Quality) as a proper range **slider** (5–100)
- Action cooldown moved here from Quality tab

**Quality tab:**
- Duplicate threshold moved here from Output/Capture
- Resolution scale moved here

**Storage tab:**
- Cloud folder path setting added
- Cloud popup toggle added

**Advanced tab:**
- `force_mss` toggle — labelled "Use standard capture engine (mss)" for clarity

**Feedback section (new):**
- Bug report / feature request form with type selector and message textarea
- Attach detection log checkbox
- Send via mailto (email address configured via `FEEDBACK_EMAIL` constant)
- Detection log display with Refresh and Copy to clipboard buttons
- Debug mode toggle

**About section:**
- Content driven by `data/about.txt` — read-only in UI (edit button removed)
- Sysinfo table from `/api/sysinfo`

**Cloud folder:**
- After game session closes, if cloud folder is set and popup enabled, shows session screenshots to pick from
- `openCloudPopup()`, `toggleCloudItem()`, `doCloudCopy()`, `triggerCloudPopup()`

**Setup wizard:**
- New step 2: **Capture engine selection** — Rust/DXGI (recommended, pre-selected) vs Standard (mss)
- Engine choice saved as `force_mss` on wizard completion
- Step numbers updated accordingly

**Stats page:**
- Added Shot Types panel and Sessions Per Game panel
- Sparkline bars now colour-coded (one colour per game, matching top games chart)

**Bug fixes:**
- `getKey`, `setKey`, `saveSettings` restored after being dropped in a large section replacement
- Nested template literals replaced with string concatenation throughout (pywebview's Chromium engine rejects nested backticks)
- `$("lightbox")` null check added to keydown handler
- Global `contextmenu` prevention removed (was blocking F12/devtools)
- `buildSettingsTabs()` null-checks `settingsGroups` element for backward compat with old index.html
- Monitor label fallback added (`m.label` doesn't exist in Rust extension output)
- `renderField()` wrapped in try-catch — errors show as visible red rows instead of blanking the tab
- `pollCaptureToast` interval staggered 2 seconds after init to avoid startup request pile-up

### `static/style.css`
- Range/slider styling added (brand primary colour thumb, cross-browser)
- Context menu styles (`.ctx-item`, `.ctx-danger`, `.ctx-disabled`, `.ctx-divider`)
- Stars alignment fixed (`align-items: center`, `line-height: 1`)

### `templates/index.html`
- Sidebar: `data-tab="games"` → `data-tab="scanned"`
- Dashboard: removed Now Playing and Detection Log panels, added `dashMiniStats` container
- New `page-scanned` section with Games List / Blacklist tab switcher
- Stats page: added Shot Types and Sessions Per Game panels
- Settings page: added `settingsGroups` row
- Context menu `div` added
- Cloud upload modal added
- Setup wizard: new capture engine selection step (step 2)

---

## Bug Fixes (from PROJECT_STATUS.md)

| Bug | Fix |
|---|---|
| #1 `fire_achievement_burst` wrong args | Confirmed correct in this codebase |
| #2 `extra` vs `extra_games` key | Already correct in this codebase |
| #3 `mss`/`numpy` missing from requirements | Added to `requirements.txt` and `start.bat` |
| #4 Shot counter case inconsistency | Changed to `.casefold()` in `capture_manager.py` |
| #5 `scan_count` runaway | Removed from `scanner.py` |
| WinError 5 file lock race | Retry logic in `config.write_json()` |
| Multiple instance launches | Single instance check in `launch.py` + focus flag |
