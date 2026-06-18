@echo off
cd /d %~dp0
echo Adding ShotTaker to Windows startup...
python -c "from app_window import add_to_startup; add_to_startup()"
echo Done. ShotTaker will now start with Windows.
pause
