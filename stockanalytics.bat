@echo off
REM ================================
REM Stock Analytics Auto Launcher
REM ================================

setlocal

REM ---- Go to project folder ----
cd /d "%~dp0"

REM ---- Activate virtual environment ----
call venv\Scripts\activate.bat

REM ---- Ask user for stock symbol ----
echo.
set /p STOCK=Enter stock symbol (default AAPL): 

REM Default if empty
if "%STOCK%"=="" set STOCK=AAPL

REM Remove accidental spaces
set STOCK=%STOCK: =%

REM Convert to uppercase (PowerShell trick)
for /f %%A in ('powershell -NoProfile -Command "\"%STOCK%\".ToUpper()"') do set STOCK=%%A

echo.
echo ================================
echo Selected stock: %STOCK%
echo ================================
echo.

REM ---- Train model ----
echo Training model for %STOCK%...
python main.py --symbol %STOCK%

REM ---- Launch dashboard (run from project root so Models\ resolves correctly) ----
echo.
echo Launching dashboard for %STOCK%...
streamlit run Dashboard\dashboard.py -- --symbol %STOCK%

REM ---- Keep window open ----
pause
endlocal