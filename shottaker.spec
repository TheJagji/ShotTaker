# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ShotTaker — builds a single windowed .exe.
Build with:  python -m PyInstaller shottaker.spec --noconfirm
"""

block_cipher = None

# Read-only resources bundled into the exe (_MEIPASS at runtime).
datas = [
    ("templates", "templates"),
    ("static", "static"),
    ("data/blacklist_default.txt", "data"),
]

# Local modules imported dynamically (inside functions/threads) so static
# analysis may miss them — list them explicitly.
hiddenimports = [
    "config", "branding", "frames", "library", "capture_manager",
    "change_detector", "achievement_detector", "screenshots", "gallery_manager",
    "gamenames", "stats", "export", "state", "scanner", "blacklist", "detector",
    "platform_detect", "steam_detect", "app_window", "webserver",
    "pystray._win32",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "test", "unittest"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ShotTaker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                # windowed app, no console
    disable_windowed_traceback=False,
    icon="static/icon.ico",
)
