@echo off
cd /d %~dp0

echo ============================
echo  ShotTaker Launcher
echo ============================

echo Checking Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH!
    pause
    exit /b
)

echo Checking required packages...
python -c "import flask" >nul 2>&1     || ( echo Installing flask...     & python -m pip install flask )
python -c "import psutil" >nul 2>&1    || ( echo Installing psutil...    & python -m pip install psutil )
python -c "import pyautogui" >nul 2>&1 || ( echo Installing pyautogui... & python -m pip install pyautogui )
python -c "import webview" >nul 2>&1   || ( echo Installing pywebview... & python -m pip install pywebview )
python -c "import pystray" >nul 2>&1   || ( echo Installing pystray...   & python -m pip install pystray )
python -c "from PIL import Image" >nul 2>&1 || ( echo Installing Pillow... & python -m pip install Pillow )
python -c "import mss" >nul 2>&1       || ( echo Installing mss...       & python -m pip install mss )
python -c "import numpy" >nul 2>&1     || ( echo Installing numpy...     & python -m pip install numpy )

echo ============================
echo  Starting ShotTaker...
echo ============================

python launch.py
