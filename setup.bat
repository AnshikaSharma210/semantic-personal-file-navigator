@echo off
title Semantic File Navigator — Setup
color 0A

echo.
echo  =========================================
echo   Semantic Personal File Navigator
echo   Setting up on your machine...
echo  =========================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo  [1/3] Python found.

:: Install dependencies
echo  [2/3] Installing dependencies ^(this may take a few minutes the first time^)...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to install dependencies.
    echo  Try running this as Administrator, or manually run:
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo  [3/3] Dependencies installed.
echo.
echo  =========================================
echo   Launching File Navigator...
echo   Your browser will open automatically.
echo   Press Ctrl+C in this window to stop.
echo  =========================================
echo.

python run.py

pause
