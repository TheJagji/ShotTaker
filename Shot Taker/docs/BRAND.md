# ShotTaker — Brand Guide

The brand is defined in code in [`branding.py`](../branding.py) (the single source of
truth). The web UI pulls these values at runtime via `/api/brand` and applies them as CSS
variables, so changing `branding.py` re-themes the entire app.

## Name & voice
- **Name:** ShotTaker (a blend of *snap* + *capture*).
- **Tagline:** *Every moment worth keeping.*
- **Voice:** friendly, low-friction, privacy-respecting. Local-first; never "uploads."

## Logo
A **focus reticle** — four rounded corner brackets framing a centre shutter dot — on a
rounded square with an electric gradient. It reads instantly as "capture/screenshot" and
renders crisply from 16px (tray/favicon) to 256px. Generated programmatically by
`branding.render_logo()` / `generate_icon()` → `static/icon.png` + `static/icon.ico`.

Regenerate assets any time with:

```
python branding.py
```

## Colour palette

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0d0e13` | App background |
| `--surface` | `#161922` | Cards, panels, sidebar |
| `--raised` | `#1f2330` | Controls, hovers |
| `--border` | `#2a2f3d` | Dividers, outlines |
| `--primary` | `#7c5cff` | **Brand accent** (electric violet) |
| `--primary2` | `#4ea8ff` | Gradient partner (sky blue) |
| `--cyan` | `#22d3ee` | Secondary accent |
| `--text` | `#e8e9f0` | Primary text |
| `--muted` | `#9aa0b4` | Secondary text |
| `--success` / `--warn` / `--danger` | `#34d399` / `#fbbf24` / `#f87171` | Status |

**Signature gradient:** `135deg, var(--primary) → var(--primary2)` — used on the wordmark,
the active nav item, primary buttons, and stat highlights.

A **light theme** is provided via `[data-theme="light"]` overrides and is user-toggleable in
Settings → Window.

## Iconography
No emoji anywhere. A custom **line-style SVG icon set** lives as an inline `<symbol>` sprite at
the top of `templates/index.html` and is referenced via the `ic(name)` helper in `app.js`
(`<svg class="ic"><use href="#i-name"/></svg>`). Icons are stroke-based on `currentColor`, so
they inherit theme + active-state colours automatically. The set deliberately echoes the
focus-reticle logo (the **capture** icon *is* the reticle + shutter dot) and nods to gaming
heritage (a classic **gamepad** for Games). To add an icon: drop a new `<g id="i-foo">` in the
sprite and call `ic("foo")`.

## Voice
Written by players, for players — a mix of old-school and modern PC-gaming slang, used sparingly
so it stays charming, not noisy. Examples in the wild: the boot banner ("press start"), the
detection log ("GL HF", "Action cam armed", "Trophy watch online", "Roster locked", "GG —
session saved"), empty states ("No loot yet"), the setup wizard ("Player one, ready?", "Insert
coin"), and the footer ("No cloud, no kill-cam"). Keep functional log tags (`[CAP] [ACT] [ACH]`
etc.) intact — the dashboard log colour-codes on them.

## Typography
System UI stack (`Segoe UI`, system-ui, Roboto…) for zero-dependency crispness. Monospace
(`Cascadia Code`, Consolas) for the detection log.

## Applying the brand elsewhere
- **Window & tray:** title and icon come from `branding.py` (`app_window.py`).
- **Dark titlebar:** `branding.TITLEBAR_*_COLORREF` feed the Windows 11 DWM caption colour.
- **Exe icon:** `shottaker.spec` points at `static/icon.ico`.
