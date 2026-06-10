@echo off
cd /d %~dp0
echo ============================
echo  Building ShotTaker (.exe)
echo ============================

echo Refreshing brand assets...
python branding.py

echo Installing build dependencies...
python -m pip install -r requirements.txt

echo Running PyInstaller...
python -m PyInstaller shottaker.spec --noconfirm --clean

echo ============================
echo  Done. Find ShotTaker.exe in the dist\ folder.
echo ============================
pause
