@echo off
cd /d %~dp0

echo Installing dependencies...
python -m pip install -r requirements.txt

echo Starting ShotTaker...
python main.py

pause