@echo off
setlocal

echo =====================================
echo Running Short Interest Screener
echo =====================================

cd /d "%~dp0\.."

echo Running from: %CD%
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: venv not found in project root.
    echo Run install.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Searching for squeeze files...
echo.

dir /s /b *squeeze*.py

echo.
echo If the files are listed above, update the paths below in this BAT.
echo.

REM Common expected locations:
if exist "squeeze.py" (
    python squeeze.py
) else if exist "Squeeze\squeeze.py" (
    python Squeeze\squeeze.py
) else if exist "squeeze_dashboard\squeeze.py" (
    python squeeze_dashboard\squeeze.py
) else (
    echo ERROR: Could not find squeeze.py
)

if exist "streamlit_squeeze.py" (
    streamlit run streamlit_squeeze.py
) else if exist "Squeeze\streamlit_squeeze.py" (
    streamlit run Squeeze\streamlit_squeeze.py
) else if exist "squeeze_dashboard\streamlit_squeeze.py" (
    streamlit run squeeze_dashboard\streamlit_squeeze.py
) else (
    echo ERROR: Could not find streamlit_squeeze.py
)

pause