@echo off
cd /d %~dp0

echo ============================
echo  ShotTaker ^— Rust Edition
echo ============================
echo.

:: -------------------------------------------------------
:: 1. Check Python
:: -------------------------------------------------------
echo [1/4] Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download it from https://python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        %%v


:: -------------------------------------------------------
:: 2. Install / update Python dependencies
:: -------------------------------------------------------
echo.
echo [2/4] Installing Python dependencies...
python -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo        Done.


:: -------------------------------------------------------
:: 3. Build rust_capture (skip if already up to date)
:: -------------------------------------------------------
echo.
echo [3/4] Building Rust capture engine...

:: Check Rust is available
cargo --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Rust is not installed or not in PATH.
    echo Download it from https://rustup.rs
    pause
    exit /b 1
)

:: Check maturin is available, install if not
python -m maturin --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo        maturin not found - installing...
    python -m pip install maturin --quiet
)

:: Check if rust_capture is already built and importable
python -c "import rust_capture" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%b in ('python -c "import rust_capture; print(rust_capture.__backend__)"') do echo        rust_capture already built ^(%%b^) - skipping rebuild.
    goto :launch
)

:: Build
cd rust_capture
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
python -m maturin build --release
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Rust build failed. See output above.
    cd ..
    pause
    exit /b 1
)

:: Install the built wheel
for /f "delims=" %%f in ('dir /b /s target\wheels\*.whl 2^>nul') do (
    python -m pip install --force-reinstall "%%f" --quiet
)
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Wheel install failed.
    cd ..
    pause
    exit /b 1
)
cd ..
echo        rust_capture built and installed OK.


:: -------------------------------------------------------
:: 4. Launch ShotTaker
:: -------------------------------------------------------
:launch
echo.
echo [4/4] Starting ShotTaker...
echo.
python launch.py
