@echo off
chcp 65001 >nul
echo ============================================
echo   CortexPad Build Script
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

:: Check PyInstaller
echo [1/3] Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    pip install pyinstaller
)
echo       PyInstaller ready

:: Install dependencies
echo.
echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet
echo       Dependencies installed

:: Build
echo.
echo [3/3] Building...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

python -m PyInstaller CortexPad.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo ============================================
    echo   Build failed!
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build successful!
echo   Output: dist\CortexPad.exe
echo ============================================
dir dist\CortexPad.exe | findstr "CortexPad.exe"
echo.
echo   Usage:
echo     1. Run CortexPad.exe
echo     2. Scan QR code with your phone
echo     3. Enter the 4-digit pairing code
echo     4. Start controlling your PC!
echo ============================================
pause
