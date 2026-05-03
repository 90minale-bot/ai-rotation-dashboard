@echo off
setlocal

echo.
echo ==========================================
echo        Project Dashboard Launcher
echo ==========================================
echo.
echo 1. Stock Analytics
echo 2. ROI Tracker
echo 3. Allocation Dashboard
echo 4. Squeeze Dashboard
echo 5. Exit
echo.

set /p choice=Select an option 1-5: 

if "%choice%"=="1" goto stock
if "%choice%"=="2" goto roi
if "%choice%"=="3" goto allocation
if "%choice%"=="4" goto squeeze
if "%choice%"=="5" goto end

echo Invalid choice.
pause
exit /b

:stock
call "%~dp0stockanalytics.bat"
exit /b

:roi
call "%~dp0roi_tracker.bat"
exit /b

:allocation
call "%~dp0run_allocation_dashboard.bat"
exit /b

:squeeze
call "%~dp0squeeze.bat"
exit /b

:end
echo Exiting.
pause
exit /b