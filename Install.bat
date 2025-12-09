@echo off
REM Photo Metadata Editor - Windows Installation Script (Batch)
REM This is a simpler alternative if PowerShell fails

setlocal enabledelayedexpansion

cls
echo.
echo ========================================
echo Photo Metadata Editor - Installation
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: This script must be run as Administrator.
    echo Please right-click on cmd.exe and select "Run as administrator"
    pause
    exit /b 1
)

set "REPO_URL=https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
set "INSTALL_DIR=%USERPROFILE%\Apps"
set "APP_NAME=Photo Metadata Editor"

REM Create installation directory
echo Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

REM Check and install Git if not present
where git >nul 2>&1
if %errorLevel% neq 0 (
    echo Git not found. Please install Git manually from:
    echo https://git-scm.com/download/win
    echo.
    echo After installing Git, run this script again.
    pause
    exit /b 1
)
echo OK Git is installed

REM Check Python 3
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo Python 3 not found. Please install Python from:
    echo https://www.python.org/downloads/
    echo.
    echo During installation, make sure to check "Add Python to PATH"
    echo After installing Python, run this script again.
    pause
    exit /b 1
)
echo OK Python 3 is installed

REM Clone or update repository
if exist "Photo_Metadata_App_By_Gledhill" (
    echo Repository already exists. Updating...
    cd /d "Photo_Metadata_App_By_Gledhill"
    git pull
) else (
    echo Cloning repository...
    git clone %REPO_URL%
    cd /d "Photo_Metadata_App_By_Gledhill"
)

echo.
echo Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Creating launcher script...
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%\Photo_Metadata_App_By_Gledhill"
    echo python main.py
) > "%INSTALL_DIR%\Photo_Metadata_App_By_Gledhill\run_app.bat"

echo.
echo ========================================
echo OK Installation Complete!
echo ========================================
echo.
echo To launch the app:
echo 1. Open File Explorer and navigate to: %INSTALL_DIR%\Photo_Metadata_App_By_Gledhill
echo 2. Double-click "run_app.bat"
echo.
echo To uninstall, simply delete the folder: %INSTALL_DIR%\Photo_Metadata_App_By_Gledhill
echo.
pause
