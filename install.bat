@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Always run from the folder this script lives in
cd /d "%~dp0"

echo.
echo === Stock Analytics Installer (Windows) ===
echo Repo: %CD%
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python is not installed or not on PATH.
  echo Install Python 3.10+ and check "Add Python to PATH".
  pause
  exit /b 1
)

REM Create venv if missing
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment in .\venv ...
  python -m venv venv
  if errorlevel 1 (
    echo ERROR: Failed to create venv.
    pause
    exit /b 1
  )
) else (
  echo Found existing venv.
)

REM Activate venv
call "venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: Failed to activate venv.
  pause
  exit /b 1
)

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found in repo root.
  pause
  exit /b 1
)

echo.
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
  pause
  exit /b 1
)

echo.
echo Verifying key packages...
python -c "import numpy, pandas, sklearn; import streamlit; print('OK: numpy/pandas/sklearn/streamlit installed')"
if errorlevel 1 (
  echo ERROR: Verification failed.
  pause
  exit /b 1
)

echo.
echo ✅ Install complete.
echo.
echo Next:
echo   1) (venv is active in THIS window)
echo   2) Run training:
echo        python main.py --symbol RTX
echo   3) Run dashboard:
echo        streamlit run Dashboard\dashboard.py -- --symbol RTX
echo.
pause
endlocal