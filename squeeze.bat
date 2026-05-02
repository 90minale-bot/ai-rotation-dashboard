@echo off
cd /d "%~dp0"

echo.
echo === Running Short Interest Screener ===
echo.

python squeeze.py

echo.
pause