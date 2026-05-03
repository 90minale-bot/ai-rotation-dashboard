@echo off
REM ================================
REM Stock Analytics Auto Launcher
REM Works from Launchers folder
REM ================================

setlocal ENABLEDELAYEDEXPANSION

REM ---- Go to parent project folder ----
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

echo.
echo ==========================================
echo        Stock Analytics Launcher
echo ==========================================
echo Running from: %CD%
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: venv not found.
    echo Run install.bat from this folder first:
    echo %CD%
    pause
    exit /b 1
)

call "venv\Scripts\activate.bat"

if not exist "main.py" (
    echo ERROR: main.py not found in:
    echo %CD%
    pause
    exit /b 1
)

if not exist "Dashboard\dashboard.py" (
    echo ERROR: Dashboard\dashboard.py not found.
    pause
    exit /b 1
)

echo.
set /p STOCK=Enter stock symbol default AAPL: 

if "%STOCK%"=="" set STOCK=AAPL
set STOCK=%STOCK: =%

for /f %%A in ('powershell -NoProfile -Command "\"%STOCK%\".ToUpper()"') do set STOCK=%%A

echo.
echo Selected stock: %STOCK%
echo.

echo Training model for %STOCK%...
python main.py --symbol %STOCK%

if errorlevel 1 (
    echo ERROR: Training failed.
    pause
    exit /b 1
)

echo.
echo Launching dashboard for %STOCK%...
python -m streamlit run Dashboard\dashboard.py -- --symbol %STOCK%

pause
endlocal