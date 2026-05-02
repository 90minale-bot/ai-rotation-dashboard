@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Always run from this script's directory
cd /d "%~dp0"

echo.
echo ===============================
echo   SQUEEZE DASHBOARD LAUNCHER
echo ===============================
echo.

REM --- Step 0: Check Python ---
where python >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python not found in PATH.
    echo Install Python 3.10+ and check "Add to PATH".
    pause
    exit /b 1
)

REM --- Step 1: Create venv if missing ---
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [1/7] Creating virtual environment...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
) ELSE (
    echo [1/7] Virtual environment already exists.
)

REM --- Step 2: Activate venv ---
echo [2/7] Activating virtual environment...
call "venv\Scripts\activate.bat"

IF ERRORLEVEL 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo Active Python:
where python
python --version
echo.

REM --- Step 3: Upgrade pip ---
echo [3/7] Upgrading pip...
python -m pip install --upgrade pip

REM --- Step 4: Install dependencies ---
echo [4/7] Installing dependencies...
pip install streamlit pandas yfinance yahooquery tabulate

echo.
echo ===============================
echo   SELECT SCAN MODE
echo ===============================
echo.
echo 1 - Run DEFAULT watchlist only
echo 2 - Run ALL stocks (no filters)
echo 3 - Skip scan and open dashboard
echo.

set /p MODE=Enter choice 1, 2, or 3: 

IF "%MODE%"=="1" (
    echo.
    echo [5/7] Running DEFAULT watchlist scan...
    python squeeze.py
)

IF "%MODE%"=="2" (
    echo.
    echo [5/7] Running ALL-STOCK scan...
    echo This may take a while...
    python squeeze.py --all
)

IF "%MODE%"=="3" (
    echo.
    echo [5/7] Skipping scan...
)

IF NOT "%MODE%"=="1" IF NOT "%MODE%"=="2" IF NOT "%MODE%"=="3" (
    echo Invalid selection.
    pause
    exit /b 1
)

IF ERRORLEVEL 1 (
    echo ERROR: Squeeze scan failed.
    pause
    exit /b 1
)

REM --- Check dashboard file ---
IF NOT EXIST "streamlit_squeeze.py" (
    echo ERROR: streamlit_squeeze.py not found.
    echo Current directory:
    cd
    pause
    exit /b 1
)

REM --- Optional: Check results file ---
IF NOT EXIST "squeeze_results.csv" (
    echo WARNING: squeeze_results.csv not found.
    echo Dashboard may show empty results.
    echo.
)

echo.
echo [6/7] Starting Streamlit dashboard...
echo.

REM --- Launch Streamlit (safe for spaces in path) ---
start "Squeeze Dashboard Server" cmd /k ^
"cd /d ""%~dp0"" && call ""venv\Scripts\activate.bat"" && python -m streamlit run streamlit_squeeze.py --server.headless false --server.port 8501"

REM --- Wait longer for server ---
echo Waiting for Streamlit to start...
timeout /t 8 /nobreak >nul

REM --- Open browser ---
echo Opening browser...
start "" http://localhost:8501

echo.
echo If browser did not open, go to:
echo http://localhost:8501
echo.

pause