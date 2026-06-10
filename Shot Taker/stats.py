"""
ShotTaker — playtime & capture statistics, computed from session history,
the library index, and shot counters.
"""

import time
from collections import defaultdict

import config
import gamenames


def _sessions():
    return config.read_json(config.SESSIONS_FILE, []) or []


def _library():
    return config.read_json(config.LIBRARY_FILE, {}) or {}


def summary():
    sessions = _sessions()
    lib = _library()
    stats = config.read_json(config.STATS_FILE, {}) or {}

    playtime = defaultdict(float)
    sess_count = defaultdict(int)
    for s in sessions:
        g = s.get("game", "")
        playtime[g] += s.get("duration", 0)
        sess_count[g] += 1

    shots_by_game = defaultdict(int)
    shots_by_type = defaultdict(int)
    favorites = 0
    for meta in lib.values():
        shots_by_game[meta.get("game", "Unknown")] += 1
        shots_by_type[meta.get("type", "Unknown")] += 1
        if meta.get("favorite"):
            favorites += 1

    # captures per day (last 30 days)
    per_day = defaultdict(int)
    cutoff = time.time() - 30 * 86400
    for meta in lib.values():
        ts = meta.get("ts", 0)
        if ts >= cutoff:
            per_day[time.strftime("%Y-%m-%d", time.localtime(ts))] += 1

    total_playtime = sum(playtime.values())
    most_played = max(playtime.items(), key=lambda x: x[1])[0] if playtime else ""

    def named(d):
        out = {}
        for exe, v in d.items():
            out[gamenames.friendly(exe) if exe.endswith(".exe") else exe] = v
        return out

    return {
        "total_screenshots": stats.get("screenshots_taken", len(lib)),
        "indexed_screenshots": len(lib),
        "favorites": favorites,
        "total_sessions": len(sessions),
        "total_playtime_seconds": round(total_playtime),
        "most_played_game": gamenames.friendly(most_played) if most_played.endswith(".exe") else most_played,
        "games_played": len(playtime),
        "shots_by_type": dict(shots_by_type),
        "shots_by_game": dict(sorted(named(shots_by_game).items(), key=lambda x: -x[1])[:20]),
        "playtime_by_game": dict(sorted(
            {(gamenames.friendly(k) if k.endswith('.exe') else k): round(v) for k, v in playtime.items()}.items(),
            key=lambda x: -x[1])[:20]),
        "sessions_by_game": dict(named(sess_count)),
        "captures_per_day": dict(sorted(per_day.items())),
        "recent_sessions": list(reversed(sessions[-15:])),
    }
