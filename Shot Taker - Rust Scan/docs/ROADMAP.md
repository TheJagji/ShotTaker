# ShotTaker — Product Roadmap

Last updated: 2026-06-13 (Dev branch).

**Legend** — Impact: 🔴 High / 🟡 Medium / ⚪ Low. Effort: S (hours) / M (a few days) /
L (a week+). Status: ✅ done · ◐ partial · ⬜ not started.

---

## Completed (1.3.0 + Dev branch)

| Item | Notes |
|---|---|
| ✅ Direct screen capture (mss) | PNG / JPEG / WebP, per-game folders |
| ✅ TimeLapse / Action Shots / Hybrid modes | |
| ✅ Smart quality gate | Dark frames, loading screens, letterbox, dedupe |
| ✅ Pre-capture buffer | Save frame before the change |
| ✅ Multi-monitor selection | auto / all / specific index |
| ✅ Manual hotkey capture | Default F9 |
| ✅ Action sensitivity slider | Settings → Capture, range 5–100 |
| ✅ WebP output | Smallest file size option |
| ✅ Resolution scaling | Downscale to save space |
| ✅ Watermark | Game name + date, off by default |
| ✅ Storage guardrails | Max shots per game / max disk, auto-rotate |
| ✅ Favorites / tags / ratings | Stored in library.json |
| ✅ Gallery with search, filter, sort | Per-game / type / favorites |
| ✅ Bulk export | ZIP / contact sheet / GIF |
| ✅ Bulk rename | Import files into ShotTaker naming convention |
| ✅ Session history | All sessions in sessions.json |
| ✅ Stats dashboard | Playtime, shots-per-game, sparkline |
| ✅ Friendly game name resolution | Overrides > hints > prettified exe |
| ✅ Per-game profiles | Different settings per title |
| ✅ Privacy guard | Auto-pause on sensitive app titles |
| ✅ Steam achievement detection | Heuristic, burst capture on unlock |
| ✅ More launchers | Xbox / Battle.net / Riot / Rockstar / itch added |
| ✅ Watchdog | Restarts dead core threads |
| ✅ Config import / export | Settings, folders, profiles & names |
| ✅ Blacklist management UI | Settings → Blacklist; Restore from blacklist |
| ✅ About section | data/about.txt, editable inline |
| ✅ Custom notification sounds | Uploaded to user_data/sounds/ |
| ✅ user_data/ folder separation | Gitignored; all generated data here |
| ✅ .gitignore | user_data/ and standard Python/build noise excluded |
| ✅ mss + numpy in requirements | Clean install now captures correctly |
| ✅ Counter case normalisation | casefold() keys prevent duplicate series |

---

## Near-term

| # | Item | Impact | Effort |
|---|---|---|---|
| N1 | Fix `start.bat` — add `mss` and `numpy` individual checks | 🔴 | S |
| N2 | Test Steam achievement detection live | 🟡 | S |
| N3 | LRU eviction for `webserver._path_cache` | ⚪ | S |
| N4 | Implement `reload.flag` (reload settings without restart) | ⚪ | S |
| N5 | PyInstaller build test (`shottaker.spec` / `build.bat`) | 🟡 | M |

---

## Milestone A — Gallery depth

| # | Item | Impact | Effort |
|---|---|---|---|
| A1 | Compare / cull view for near-dupes | 🟡 | M |
| A2 | Timeline / calendar / per-session browsing | 🟡 | M |
| A3 | Basic edit — crop, rotate, annotate before export | ⚪ | M |
| A4 | Cover art / banners for games list | 🟡 | M |

---

## Milestone B — Achievements & events

| # | Item | Impact | Effort |
|---|---|---|---|
| B1 | Harden Steam achievement detection (reduce false positives) | 🟡 | S |
| B2 | Event log — link achievement triggers to the shots they fired | ⚪ | M |
| B3 | Achievement detection for GOG / Epic / Ubisoft / EA / Xbox | 🟡 | L |
| B4 | RetroAchievements / emulator support | ⚪ | M |

---

## Milestone C — Sharing & export

| # | Item | Impact | Effort |
|---|---|---|---|
| C1 | Opt-in Discord webhook / Imgur share (never automatic) | 🟡 | M |
| C2 | GIF / short-clip from a burst or timed window | 🟡 | L |

---

## Milestone D — Platform reach & distribution

| # | Item | Impact | Effort |
|---|---|---|---|
| D1 | PyInstaller single-`.exe` distribution | 🔴 | M |
| D2 | Auto-update check | 🟡 | S |
| D3 | Cross-platform (Mac/Linux) — requires abstracting the Windows layer | 🟡 | L |

---

## Non-goals

ShotTaker will NOT:
- Require cloud accounts or subscriptions
- Upload screenshots automatically
- Depend on external online services
- Require users to edit code or config files manually
