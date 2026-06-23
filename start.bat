@echo off
chcp 65001 >nul 2>&1
title CortexPad Server
echo ============================================
echo   CortexPad - Starting server...
echo ============================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run: python -m venv venv
    echo         Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "venv\Lib\site-packages\fastapi" (
    echo [INFO] Installing dependencies...
    venv\Scripts\pip install -r requirements.txt
)

echo [OK] Starting CortexPad on https://0.0.0.0:8765
echo.
echo Tip: For full functionality, right-click and run as administrator
echo.

venv\Scripts\python.exe main.py
pause
