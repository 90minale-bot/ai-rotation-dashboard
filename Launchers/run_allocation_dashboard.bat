@echo off
setlocal

REM ---- Kill any existing Streamlit sessions (prevents wrong app showing) ----
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

REM ---- Move to project root ----
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

echo.
echo ==========================================
echo      Allocation Dashboard Launcher
echo ==========================================
echo Running from: %CD%
echo.

REM ---- Check venv ----
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: venv not found.
    echo Run install.bat first.
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

REM ---- Check correct file ----
if not exist "Dashboard\allocation_dashboard.py" (
    echo ERROR: allocation_dashboard.py not found in:
    echo %CD%\Dashboard
    pause
    exit /b 1
)

echo Starting Allocation Dashboard on port 8503...
echo.

REM ---- Run on dedicated port ----
python -m streamlit run Dashboard\allocation_dashboard.py --server.port 8503

pause
endlocal