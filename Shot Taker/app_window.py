import threading
import time
import os
import sys
import json
import ctypes

# =========================
# ICON GENERATION
# Generates the ST logo as a .ico file on first run
# =========================
def generate_icon():
    icon_path = "static/icon.ico"
    png_path  = "static/icon.png"

    if os.path.exists(icon_path) and os.path.exists(png_path):
        return icon_path

    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark box background
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=10, fill="#1c1c1c")

        # Blue border
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=10,
                                outline="#5a8fff", width=3)

        # "ST" text
        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), "ST", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((size - tw) / 2, (size - th) / 2 - 2), "ST",
                  fill="#5a8fff", font=font)

        os.makedirs("static", exist_ok=True)

        # Save PNG (used by browser notifications)
        img.save(png_path, "PNG")

        # Save ICO (used by tray + window)
        img_ico = img.resize((32, 32), Image.LANCZOS)
        img_ico.save(icon_path, format="ICO", sizes=[(32, 32), (16, 16)])

        return icon_path

    except Exception as e:
        print(f"[ICON] Could not generate icon: {e}")
        return None


# =========================
# LOAD SETTINGS
# =========================
def load_settings():
    try:
        with open("data/settings.json", "r") as f:
            return json.load(f)
    except:
        return {}


# =========================
# APPLY DARK TITLEBAR (Windows 11)
# Uses DWM API to set caption colour to match dark UI
# =========================
def apply_dark_titlebar(window):
    try:
        import webview
        hwnd = None

        # Try to get HWND from pywebview
        if hasattr(window, "native_handle"):
            hwnd = window.native_handle
        else:
            # Fallback: find window by title
            FindWindow = ctypes.windll.user32.FindWindowW
            hwnd = FindWindow(None, "ShotTaker")

        if not hwnd:
            return

        DWMWA_CAPTION_COLOR = 35
        # #1c1c1c as COLORREF (0x00BBGGRR)
        color = ctypes.c_int(0x001c1c1c)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(color),
            ctypes.sizeof(color)
        )

        DWMWA_TEXT_COLOR = 36
        text_color = ctypes.c_int(0x00e0e0e0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_TEXT_COLOR,
            ctypes.byref(text_color),
            ctypes.sizeof(text_color)
        )

    except Exception as e:
        print(f"[WINDOW] Titlebar colour failed (Windows 10?): {e}")


# =========================
# SYSTEM TRAY
# =========================
class TrayManager:

    def __init__(self, window_manager):
        self.wm = window_manager
        self.icon = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import pystray
            from PIL import Image

            icon_path = generate_icon()

            if icon_path and os.path.exists(icon_path):
                img = Image.open(icon_path).resize((32, 32))
            else:
                # Fallback: plain coloured square
                img = Image.new("RGB", (32, 32), "#1c1c1c")

            menu = pystray.Menu(
                pystray.MenuItem("Open ShotTaker", self._on_open, default=True),
                pystray.MenuItem("Rescan Games",   self._on_rescan),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit",           self._on_exit)
            )

            self.icon = pystray.Icon("ShotTaker", img, "ShotTaker", menu)
            self.icon.run()

        except Exception as e:
            print(f"[TRAY] Failed to start: {e}")

    def _on_open(self):
        self.wm.show()

    def _on_rescan(self):
        try:
            import scanner
            scanner.scan_games()
            self.notify("ShotTaker", "Game scan complete.")
        except Exception as e:
            print(f"[TRAY] Rescan error: {e}")

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
        except:
            pass


# =========================
# WINDOW MANAGER
# =========================
class WindowManager:

    def __init__(self):
        self.window   = None
        self.tray     = TrayManager(self)
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
        settings = load_settings()

        # Tray balloon
        self.tray.notify(
            "🎮 ShotTaker",
            f"{exe} detected ({platform})\nScreenshot timer started."
        )

        # Pop-up window briefly if enabled
        if settings.get("popup_on_game", True):
            self.show()

            # Auto-hide back to tray after delay if minimise-to-tray is on
            if settings.get("minimise_to_tray", False):
                delay = settings.get("popup_duration", 5)
                def auto_hide():
                    time.sleep(delay)
                    if load_settings().get("minimise_to_tray", False):
                        self.hide()
                threading.Thread(target=auto_hide, daemon=True).start()


# Shared instance used by main.py
window_manager = WindowManager()


# =========================
# START WINDOW
# Must be called from the main thread
# =========================
def start_window():
    try:
        import webview

        generate_icon()
        settings = load_settings()

        icon_path = os.path.abspath("static/icon.png")

        window = webview.create_window(
            title   = "ShotTaker",
            url     = "http://127.0.0.1:5050",
            width   = 1000,
            height  = 720,
            min_size = (800, 600),
            resizable = True,
        )

        # Set window icon via WinAPI after window is created
        def set_window_icon():
            try:
                if not os.path.exists(icon_path):
                    print("[ICON] Icon file not found.")
                    return

                import ctypes
                import time

                # Try a few times with delays — window may not be ready immediately
                for attempt in range(5):
                    time.sleep(0.5)
                    hwnd = ctypes.windll.user32.FindWindowW(None, "ShotTaker")
                    if hwnd:
                        # Use .ico file for best quality in titlebar
                        ico_path = os.path.abspath("static/icon.ico")
                        use_path = ico_path if os.path.exists(ico_path) else icon_path

                        hicon = ctypes.windll.user32.LoadImageW(
                            None, use_path, 1, 32, 32, 0x10  # IMAGE_ICON, LR_LOADFROMFILE
                        )
                        if hicon:
                            WM_SETICON = 0x0080
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, hicon)  # small
                            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, hicon)  # large
                            print(f"[ICON] Window icon set on attempt {attempt + 1}.")
                            return
                        else:
                            print(f"[ICON] LoadImageW failed on attempt {attempt + 1}.")
                    else:
                        print(f"[ICON] Window not found on attempt {attempt + 1}.")

                print("[ICON] Could not set window icon after 5 attempts.")

            except Exception as e:
                print(f"[ICON] Error: {e}")

        window_manager.window = window
        window_manager.tray.start()

        # Handle window close — minimise to tray if setting is on
        def on_closing():
            if load_settings().get("minimise_to_tray", False):
                window.hide()
                window_manager._visible = False
                return False  # Prevent actual close
            else:
                window_manager.tray.stop()
                return True   # Allow close + exit

        window.events.closing += on_closing

        # Apply dark titlebar after window loads
        def on_loaded():
            apply_dark_titlebar(window)
            # Run icon setting in background thread so delays don't block UI
            threading.Thread(target=set_window_icon, daemon=True).start()

        window.events.loaded += on_loaded

        debug_mode = load_settings().get("debug_mode", False)
        webview.start(debug=debug_mode)

    except ImportError:
        print("[WINDOW] pywebview not installed — running headless.")
        print("[WINDOW] Install with: pip install pywebview")
        # Keep running headlessly so Flask still works
        while True:
            time.sleep(10)

    except Exception as e:
        print(f"[WINDOW] Error: {e}")
        while True:
            time.sleep(10)


# =========================
# STARTUP REGISTRY MANAGEMENT
# =========================
def get_startup_command():
    script = os.path.abspath("launch.py")
    python = sys.executable
    return f'"{python}" "{script}"'


def is_in_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "ShotTaker")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        print(f"[STARTUP] Registry read error: {e}")
        return False


def add_to_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ShotTaker", 0, winreg.REG_SZ, get_startup_command())
        winreg.CloseKey(key)
        print("[STARTUP] Added to Windows startup.")
        return True
    except Exception as e:
        print(f"[STARTUP] Failed to add: {e}")
        return False


def remove_from_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, "ShotTaker")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        print("[STARTUP] Removed from Windows startup.")
        return True
    except Exception as e:
        print(f"[STARTUP] Failed to remove: {e}")
        return False
