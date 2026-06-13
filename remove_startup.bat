@echo off
cd /d %~dp0
echo Removing ShotTaker from Windows startup...
python -c "from app_window import remove_from_startup; remove_from_startup()"
echo Done. ShotTaker will no longer start with Windows.
pause
