@echo off
setlocal
title Nesting Optimizer Dashboard Launcher

echo ======================================================
echo    Starting Furniture Optimizer Dashboard...
echo ======================================================

:: Navigate to the project root directory (where the batch file is)
cd /d "%~dp0"

:: Check if the virtual environment exists
if not exist "venv\Scripts\activate" (
    echo.
    echo [ERROR] Virtual environment 'venv' was not found.
    echo --------------------------------------------------
    echo To fix this, please run:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo --------------------------------------------------
    echo.
    pause
    exit /b
)

:: Activate the project's virtual environment
echo [1/3] Activating virtual environment...
call venv\Scripts\activate

:: Set PYTHONPATH to ensure engine modules are discoverable
set PYTHONPATH=%CD%

:: Automatically open the browser
echo [2/3] Opening dashboard in your default browser...
start "" http://127.0.0.1:5000

:: Start the Flask application
echo [3/3] Launching Flask server (src/app.py)...
echo.
python src/app.py

:: Keep the window open if the server crashes
echo.
echo Server has stopped.
pause
