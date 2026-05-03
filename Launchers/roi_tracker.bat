@echo off
REM ================================
REM ROI Tracker Dashboard Launcher
REM Works from Launchers folder
REM ================================

setlocal

REM ---- Go to ROI project folder ----
cd /d C:\Users\90min\test_final\initial-stock-project-working

echo.
echo ==========================================
echo        ROI Tracker Dashboard Launcher
echo ==========================================
echo Running from: %CD%
echo.

REM ---- Check venv ----
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: venv not found in ROI project folder.
    echo Run install.bat in that project first.
    pause
    exit /b 1
)

REM ---- Activate venv ----
call venv\Scripts\activate.bat

REM ---- Check dashboard file ----
if not exist "ai_roi_tracker\roi_dashboard.py" (
    echo ERROR: ai_roi_tracker\roi_dashboard.py not found.
    pause
    exit /b 1
)

REM ---- Launch dashboard ----
echo Starting ROI Tracker Dashboard...
echo.

python -m streamlit run ai_roi_tracker\roi_dashboard.py

echo.
echo ROI dashboard session ended.
pause
endlocal