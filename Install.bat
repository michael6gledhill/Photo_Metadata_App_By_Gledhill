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

REM Check if running as Administrator (optional for user-mode install/update)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Note: Running without Administrator privileges ^(user-mode install/update^).
)

set "REPO_URL=https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
set "INSTALL_DIR=%USERPROFILE%\Apps"
set "APP_NAME=Photo Metadata Editor"
set "USER_DATA_DIR=%USERPROFILE%\.photo_meta_editor"
set "USER_TEMPLATES_DIR=%USER_DATA_DIR%\templates"
set "USER_NAMING_DIR=%USER_DATA_DIR%\naming"
set "BACKUP_ROOT="

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

REM Clone or reinstall repository (clean install)
if exist "Photo_Metadata_App_By_Gledhill" (
    set /p BACKUP_CHOICE=Backup existing templates/naming before reinstall? [Y/n]: 
    if /I "%BACKUP_CHOICE%"=="" set "BACKUP_CHOICE=Y"
    if /I "%BACKUP_CHOICE%"=="Y" (
        set "BACKUP_ROOT=%TEMP%\photo_meta_backup_%RANDOM%_%RANDOM%"
        mkdir "%BACKUP_ROOT%" >nul 2>&1

        if exist "%USER_TEMPLATES_DIR%" (
            xcopy "%USER_TEMPLATES_DIR%" "%BACKUP_ROOT%\templates\" /E /I /Y >nul
            echo OK Backed up templates
        )
        if exist "%USER_NAMING_DIR%" (
            xcopy "%USER_NAMING_DIR%" "%BACKUP_ROOT%\naming\" /E /I /Y >nul
            echo OK Backed up naming conventions
        )
        echo Backup location: %BACKUP_ROOT%
    )

    echo Existing installation detected. Removing old install for clean reinstall...
    rmdir /s /q "Photo_Metadata_App_By_Gledhill"
    if exist "Photo_Metadata_App_By_Gledhill" (
        echo Error: Could not remove existing installation.
        echo Please close the app if it is running and try again.
        pause
        exit /b 1
    )
)

echo Cloning repository...
git clone %REPO_URL%
if %errorLevel% neq 0 (
    echo Error: Failed to clone repository.
    pause
    exit /b 1
)
cd /d "Photo_Metadata_App_By_Gledhill"

echo.
echo Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not "%BACKUP_ROOT%"=="" (
    echo.
    echo Restoring backed up templates/naming...
    if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

    if exist "%BACKUP_ROOT%\templates" (
        if not exist "%USER_TEMPLATES_DIR%" mkdir "%USER_TEMPLATES_DIR%"
        xcopy "%BACKUP_ROOT%\templates\*" "%USER_TEMPLATES_DIR%\" /E /I /Y >nul
        echo OK Restored templates
    )

    if exist "%BACKUP_ROOT%\naming" (
        if not exist "%USER_NAMING_DIR%" mkdir "%USER_NAMING_DIR%"
        xcopy "%BACKUP_ROOT%\naming\*" "%USER_NAMING_DIR%\" /E /I /Y >nul
        echo OK Restored naming conventions
    )
)

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
