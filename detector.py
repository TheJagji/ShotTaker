import psutil


# =========================
# FIND RUNNING GAME
# =========================
# game_list: dict { "exe.exe": "platform" }
# blacklist: set of exe names to ignore
# Returns (exe_original_case, platform) or (None, None)
def find_game(game_list, blacklist):

    if not game_list:
        return None, None

    blacklist = set(x.lower() for x in blacklist)

    for proc in psutil.process_iter(['name', 'status']):
        try:
            name = proc.info['name']
            if not name:
                continue

            name_lower = name.lower().strip()

            # Skip blacklisted processes
            if name_lower in blacklist:
                continue

            # Skip zombie/dead processes
            status = proc.info.get('status', '')
            if status in ('zombie', 'dead'):
                continue

            # Match against game list (lowercased keys)
            if name_lower in game_list:
                # Return original process name for display/saving
                # but strip .exe for cleaner game name
                original = name.strip()
                return original, game_list[name_lower]

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    return None, None
