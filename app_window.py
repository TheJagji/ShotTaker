"""
ShotTaker — native window (pywebview), system tray (pystray), and Windows startup.
"""

import os
import sys
import time
import threading
import ctypes

import config
import branding
from branding import BRAND

APP = BRAND["name"]


def _icon_path():
    return branding.generate_icon(out_dir=config.STATIC_DIR)


# =========================
# DARK TITLEBAR (Windows 11)
# =========================
def apply_dark_titlebar(window):
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, APP)
        if not hwnd:
            return
        color = ctypes.c_int(branding.TITLEBAR_BG_COLORREF)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
        text = ctypes.c_int(branding.TITLEBAR_TEXT_COLORREF)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), ctypes.sizeof(text))
    except Exception as e:
        print(f"[WINDOW] Titlebar colour failed (Windows 10?): {e}")


# =========================
# SYSTEM TRAY
# =========================
class TrayManager:
    def __init__(self, window_manager):
        self.wm = window_manager
        self.icon = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            import pystray
            from PIL import Image
            ico = _icon_path()
            img = Image.open(ico).resize((32, 32)) if ico and os.path.exists(ico) \
                else Image.new("RGB", (32, 32), BRAND["colors"]["primary"])
            menu = pystray.Menu(
                pystray.MenuItem(f"Open {APP}", self._on_open, default=True),
                pystray.MenuItem("Rescan Games", self._on_rescan),
                pystray.MenuItem("Pause Capture", self._on_pause, checked=lambda i: config.load_settings().get("capture_paused", False)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._on_exit),
            )
            self.icon = pystray.Icon(APP, img, APP, menu)
            self.icon.run()
        except Exception as e:
            print(f"[TRAY] Failed to start: {e}")

    def _on_open(self):
        self.wm.show()

    def _on_rescan(self):
        try:
            import scanner
            scanner.scan_games()
            self.notify(APP, "Game scan complete.")
        except Exception as e:
            print(f"[TRAY] Rescan error: {e}")

    def _on_pause(self):
        s = config.load_settings()
        config.update_settings(capture_paused=not s.get("capture_paused", False))

    def _on_exit(self):
        print("[TRAY] Exit requested.")
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def notify(self, title, message):
        try:
            if self.icon:
                self.icon.notify(message, title)
        except Exception as e:
            print(f"[TRAY] Notify error: {e}")

    def stop(self):
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass


# =========================
# WINDOW MANAGER
# =========================
class WindowManager:
    def __init__(self):
        self.window = None
        self.tray = TrayManager(self)
        self._visible = True

    def show(self):
        try:
            if self.window:
                self.window.show()
                self.window.restore()
                self._visible = True
        except Exception as e:
            print(f"[WINDOW] Show error: {e}")

    def hide(self):
        try:
            if self.window:
                self.window.hide()
                self._visible = False
        except Exception as e:
            print(f"[WINDOW] Hide error: {e}")

    def on_game_detected(self, exe, platform):
        settings = config.load_settings()
        try:
            import gamenames
            name = gamenames.friendly(exe)
        except Exception:
            name = exe
        self.tray.notify(APP, f"{name} detected ({platform}) — rolling tape.")
        if settings.get("popup_on_game", True):
            self.show()
            if settings.get("minimise_to_tray", False):
                delay = settings.get("popup_duration", 5)

                def auto_hide():
                    time.sleep(delay)
                    if config.load_settings().get("minimise_to_tray", False):
                        self.hide()
                threading.Thread(target=auto_hide, daemon=True).start()


window_manager = WindowManager()


# =========================
# START WINDOW (main thread)
# =========================
def start_window():
    try:
        import webview
        _icon_path()
        icon_png = os.path.join(config.STATIC_DIR, "icon.png")

        window = webview.create_window(
            title=APP, url="http://127.0.0.1:5050",
            width=1080, height=760, min_size=(860, 620), resizable=True,
        )
        window_manager.window = window
        window_manager.tray.start()

        def set_window_icon():
            try:
                ico = os.path.join(config.STATIC_DIR, "icon.ico")
                use = ico if os.path.exists(ico) else icon_png
                for _ in range(5):
                    time.sleep(0.5)
                    hwnd = ctypes.windll.user32.FindWindowW(None, APP)
                    if hwnd and os.path.exists(use):
                        hicon = ctypes.windll.user32.LoadImageW(None, use, 1, 32, 32, 0x10)
                        if hicon:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
                            return
            except Exception as e:
                print(f"[ICON] Error: {e}")

        def on_closing():
            if config.load_settings().get("minimise_to_tray", False):
                window.hide()
                window_manager._visible = False
                return False
            window_manager.tray.stop()
            return True

        def on_loaded():
            apply_dark_titlebar(window)
            threading.Thread(target=set_window_icon, daemon=True).start()

        window.events.closing += on_closing
        window.events.loaded += on_loaded
        webview.start(debug=config.load_settings().get("debug_mode", False))

    except ImportError:
        print("[WINDOW] pywebview not installed — running headless on http://127.0.0.1:5050")
        while True:
            time.sleep(10)
    except Exception as e:
        print(f"[WINDOW] Error: {e}")
        while True:
            time.sleep(10)


# =========================
# WINDOWS STARTUP
# =========================
def get_startup_command():
    if config.is_frozen():
        return f'"{sys.executable}"'
    launch = os.path.join(config.app_dir(), "launch.py")
    return f'"{sys.executable}" "{launch}"'


def is_in_startup():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP)
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[STARTUP] read error: {e}")
        return False


def add_to_startup():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP, 0, winreg.REG_SZ, get_startup_command())
        return True
    except Exception as e:
        print(f"[STARTUP] add failed: {e}")
        return False


def remove_from_startup():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP)
            except FileNotFoundError:
                pass
        return True
    except Exception as e:
        print(f"[STARTUP] remove failed: {e}")
        return False
