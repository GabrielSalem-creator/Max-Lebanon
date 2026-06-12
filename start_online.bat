@echo off
title MAX Online Launcher
cd /d "%~dp0"

echo ============================================
echo   MAX - Starting...
echo ============================================
echo.

REM Check Python
where python >nul 2>&1 || (echo Python not found. Install Python 3.10+ first. && pause && exit)

REM Create required dirs
if not exist data mkdir data
if not exist static\img mkdir static\img
if not exist static\files mkdir static\files

REM Start MAX server in background
echo [1/2] Starting MAX server on port 8000...
start "MAX Server" /min cmd /c "python main.py > data\max.log 2>&1"
timeout /t 2 /nobreak >nul

REM Check if MAX started
curl -s http://localhost:8000 >nul 2>&1
if errorlevel 1 (
    echo Waiting for MAX to start...
    timeout /t 3 /nobreak >nul
)

REM Start ngrok tunnel
echo [2/2] Starting ngrok tunnel...
echo.
echo ============================================
echo  Your MAX URL will appear below.
echo  Share it or open it in any browser.
echo  Press Ctrl+C to stop.
echo ============================================
echo.
ngrok http 8000 --log=stdout
