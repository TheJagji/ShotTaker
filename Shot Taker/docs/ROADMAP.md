# ShotTaker — Product Roadmap

Prioritized plan for evolving ShotTaker from "works" to "genuinely good." Combines the
correctness fixes from `PROJECT_STATUS.md` with the feature wishlist, ordered by leverage.

**Legend** — Impact: 🔴 High / 🟡 Medium / ⚪ Low. Effort: S (hours) / M (a few days) /
L (a week+). Status: ✅ done · ◐ partial · ⬜ not started.

Guiding principle: **fix the core capture loop and its output quality before adding
breadth.** A screenshot tool that saves loading screens, or silently saves nothing, has no
amount of gallery polish that saves it.

---

## Milestone 0 — Stop the bleeding *(ship before anything else)*

Correctness and install bugs that make the app fail silently or behave wrongly. Detailed in
`PROJECT_STATUS.md` §2.

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 0.1 | Add `mss` + `numpy` to `requirements.txt` and `start.bat` (Bug #3) | 🔴 | S | ⬜ |
| 0.2 | Fix `fire_achievement_burst` arg mismatch — pass real game name (Bug #1) | 🔴 | S | ⬜ |
| 0.3 | Unify `extra` vs `extra_games` platform key (Bug #2) | 🟡 | S | ⬜ |
| 0.4 | Normalise game-name casing for counters/filenames (Bug #4) | 🟡 | S | ⬜ |
| 0.5 | Drop/repurpose runaway `scan_count`; evict `_path_cache` (Bugs #5, #6) | ⚪ | S | ⬜ |

**Exit criteria:** a clean install captures screenshots out of the box; achievement and
manual bursts save under the correct game name.

---

## Milestone 1 — Foundations for everything else

Not user-facing, but every later feature is cheaper and safer once these exist.

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 1.1 | Implement `config.py`: single `load/save_settings()`, defaults merge, validation; replace the ~7 duplicate loaders and 2 `sanitise_*` helpers | 🟡 | M | ⬜ |
| 1.2 | **Capture metadata sidecar** — write game/platform/timestamp/reason into EXIF or a per-file `.json` (unblocks reliable gallery, history, search) | 🔴 | M | ⬜ |
| 1.3 | Minimal test suite — scanner filtering, filename parse round-trip, counter logic, `score_diff` (all pure functions) | 🟡 | M | ⬜ |
| 1.4 | Crash recovery / watchdog — restart capture threads if they die mid-session | 🟡 | S | ⬜ |

---

## Milestone 2 — Make the captures actually good 🎯 *(highest product leverage)*

This is the core value. Today Action mode fires on any pixel change and keeps loading
screens; fixing that is what makes the gallery worth opening.

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 2.1 | **Loading-screen / menu / cutscene suppression** — skip static, letterboxed, or menu-like frames | 🔴 | M | ⬜ |
| 2.2 | **Smart moment detection** — scene-cut / HUD-popup heuristics beyond raw MAD diff | 🔴 | L | ⬜ |
| 2.3 | **Near-duplicate pruning** — don't save frames nearly identical to the last keeper | 🔴 | M | ⬜ |
| 2.4 | **Pre-capture buffer** — keep a rolling few seconds so action shots save the frame *before* the change | 🟡 | M | ⬜ |
| 2.5 | Multi-monitor / active-game-window capture (currently primary-only) | 🟡 | M | ◐ |
| 2.6 | Manual global-hotkey capture into the same gallery | 🟡 | S | ⬜ |
| 2.7 | Performance/quiet mode — throttle or disable Action mode to protect FPS | 🟡 | S | ⬜ |

**Exit criteria:** a 1-hour play session yields a gallery of distinct, meaningful moments
with near-zero loading screens or duplicates.

---

## Milestone 3 — Output & storage

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 3.1 | **WebP/AVIF output** (much smaller at equal quality; lossless WebP option) | 🟡 | S | ⬜ |
| 3.2 | Storage guardrails — max disk / max shots per game, auto-rotate or prompt | 🟡 | M | ⬜ |
| 3.3 | Capture resolution / downscale option | ⚪ | S | ⬜ |
| 3.4 | Optional watermark/overlay (game + timestamp), off by default | ⚪ | S | ⬜ |
| 3.5 | HDR-aware tone mapping (HDR games save washed-out today) | 🟡 | L | ⬜ |

---

## Milestone 4 — Library & gallery depth

Builds directly on the §1.2 metadata sidecar.

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 4.1 | Favorites/star + tags + ratings; filter & bulk-export favorites | 🔴 | M | ⬜ |
| 4.2 | Search & sort — date range, game, type, resolution, size | 🟡 | M | ⬜ |
| 4.3 | Compare / cull view for near-dupes (pairs with 2.3) | 🟡 | M | ⬜ |
| 4.4 | Timeline / calendar / per-session browsing | 🟡 | M | ⬜ |
| 4.5 | Basic edit — crop, rotate, annotate before export | ⚪ | M | ⬜ |
| 4.6 | Capture-preview toast (thumbnail when a shot is taken) | ⚪ | S | ⬜ |

---

## Milestone 5 — Games, sessions & identity

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 5.1 | **Full session history** — append every session to `sessions.json` (today only the last is kept) | 🔴 | S | ◐ |
| 5.2 | **Auto game-name resolution** — exe ↔ real title via Steam AppID / install folder / IGDB ("Elden Ring", not "eldenring.exe") | 🔴 | M | ⬜ |
| 5.3 | Cover art / banners for the games list and gallery | 🟡 | M | ⬜ |
| 5.4 | Stats dashboard — playtime, most-played, shots-per-game, when-you-play heatmap | 🟡 | M | ⬜ |
| 5.5 | Per-game profiles/overrides (mode, interval, sensitivity, folder) | 🟡 | M | ⬜ |
| 5.6 | Privacy guard — auto-pause on sensitive apps; global "do not capture" toggle | 🟡 | S | ⬜ |

---

## Milestone 6 — Achievements & events

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 6.1 | Fix + harden Steam achievement detection (depends on 0.2) | 🟡 | S | ◐ |
| 6.2 | Event log — link achievement/level-up/death triggers to the shots they fired | ⚪ | M | ⬜ |
| 6.3 | Achievement detection for GOG / Epic / Ubisoft / EA / Xbox | 🟡 | L | ⬜ |
| 6.4 | RetroAchievements / emulator support | ⚪ | M | ⬜ |

---

## Milestone 7 — Sharing & export *(opt-in only — preserve local-first ethos)*

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 7.1 | One-click export bundle (zip a session or a game's favorites) | 🟡 | S | ⬜ |
| 7.2 | Contact-sheet / collage generator | ⚪ | M | ⬜ |
| 7.3 | Opt-in share to clipboard / Discord webhook / Imgur (never automatic, no account) | 🟡 | M | ⬜ |
| 7.4 | GIF / short-clip mode — stitch a burst or capture a few-second clip on a trigger | 🟡 | L | ⬜ |

---

## Milestone 8 — Platform reach & distribution

| # | Item | Impact | Effort | Status |
|---|---|---|---|---|
| 8.1 | More launchers — Xbox PC/Game Pass, Battle.net, Riot, Rockstar, itch.io, standalone | 🟡 | M | ◐ |
| 8.2 | **PyInstaller single-`.exe`** so users don't need Python | 🔴 | M | ⬜ |
| 8.3 | Auto-update check | 🟡 | S | ⬜ |
| 8.4 | Config import/export & backup (portable settings + blacklist) | ⚪ | S | ⬜ |
| 8.5 | Cross-platform (Mac/Linux) — requires abstracting the Windows layer first | 🟡 | L | ⬜ |
| 8.6 | Light theme + accessibility pass | ⚪ | M | ⬜ |

---

## Suggested release cut

- **v1.3 — "It works."** Milestone 0 + 0.x install fixes. Capture reliably out of the box.
- **v1.4 — "Foundations."** Milestone 1 (config, metadata sidecar, tests, watchdog).
- **v1.5 — "Good shots."** Milestone 2 (suppression, smart detection, dedupe). *The release
  that makes the product actually worth using.*
- **v1.6 — "Good library."** Milestones 3 + 4 + 5.1/5.2 (WebP, favorites, search, session
  history, game-name resolution).
- **v2.0 — "Polished & packaged."** Stats dashboard, remaining achievements, opt-in sharing,
  and the PyInstaller `.exe`.

---

## Top 5 near-term wins (if you only do a handful)

1. **0.1 + 0.2** — make capture and achievements work at all (an afternoon).
2. **2.1 Loading-screen suppression** — biggest jump in gallery quality.
3. **2.3 Dedupe** — second biggest, and pairs naturally with 2.1.
4. **5.1 + 5.2 Session history + real game names** — turns raw files into a usable library.
5. **3.1 WebP output** — cheap, large storage savings for a tool that writes a lot of images.
</content>
