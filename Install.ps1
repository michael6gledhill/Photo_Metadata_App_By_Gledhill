# Photo Metadata Editor - Windows Installation Script (PowerShell)
# Run as Administrator

Write-Host "========================================"
Write-Host "Photo Metadata Editor - Installation"
Write-Host "========================================"
Write-Host ""

# Check if running as Administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: This script must be run as Administrator."
    Write-Host "Please right-click on PowerShell and select 'Run as administrator'."
    exit 1
}

$REPO_URL = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
$INSTALL_DIR = "$env:USERPROFILE\Apps"
$APP_NAME = "Photo Metadata Editor"
$CHOCO_EXE = Join-Path $env:ProgramData "chocolatey\bin\choco.exe"
$USER_DATA_ROOT = Join-Path $env:USERPROFILE ".photo_meta_editor"
$USER_TEMPLATES_DIR = Join-Path $USER_DATA_ROOT "templates"
$USER_NAMING_DIR = Join-Path $USER_DATA_ROOT "naming"
$BACKUP_ROOT = $null

# Create installation directory
Write-Host "Creating installation directory..."
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR | Out-Null
}
Set-Location $INSTALL_DIR

# Check and install Git if not present
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git not found. Installing Git..."

    # Try to install via Chocolatey first
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install git -y
    } else {
        # Install Chocolatey first
        Write-Host "Installing Chocolatey package manager..."
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        & $CHOCO_EXE install git -y
    }
} else {
    Write-Host "OK Git already installed"
}

# Check Python 3
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 not found. Installing Python 3..."
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install python -y
    } else {
        & $CHOCO_EXE install python -y
    }
} else {
    Write-Host ("OK Python 3 already installed ({0})" -f ((python --version) 2>&1))
}

# Clone or reinstall repository (clean install)
$REPO_PATH = Join-Path $INSTALL_DIR "Photo_Metadata_App_By_Gledhill"
if (Test-Path $REPO_PATH) {
    $backupChoice = Read-Host "Backup existing templates/naming before reinstall? [Y/n]"
    if ([string]::IsNullOrWhiteSpace($backupChoice) -or $backupChoice.Trim().ToLower() -eq "y" -or $backupChoice.Trim().ToLower() -eq "yes") {
        $BACKUP_ROOT = Join-Path $env:TEMP ("photo_meta_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
        New-Item -ItemType Directory -Path $BACKUP_ROOT -Force | Out-Null

        if (Test-Path $USER_TEMPLATES_DIR) {
            Copy-Item -Path $USER_TEMPLATES_DIR -Destination (Join-Path $BACKUP_ROOT "templates") -Recurse -Force
            Write-Host "OK Backed up templates"
        }
        if (Test-Path $USER_NAMING_DIR) {
            Copy-Item -Path $USER_NAMING_DIR -Destination (Join-Path $BACKUP_ROOT "naming") -Recurse -Force
            Write-Host "OK Backed up naming conventions"
        }
        Write-Host ("Backup location: {0}" -f $BACKUP_ROOT)
    }

    Write-Host "Existing installation detected. Removing old install for clean reinstall..."
    try {
        Remove-Item -Path $REPO_PATH -Recurse -Force -ErrorAction Stop
        Write-Host "OK Previous installation removed"
    }
    catch {
        Write-Host "Error: Could not remove existing installation at: $REPO_PATH"
        Write-Host "Please close the app if it is running and try again."
        Write-Host ("Details: {0}" -f $_.Exception.Message)
        exit 1
    }

    if (Test-Path $REPO_PATH) {
        Write-Host "Error: Existing installation still present after delete attempt."
        exit 1
    }
}

Write-Host "Cloning repository..."
git clone $REPO_URL $REPO_PATH
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to clone repository."
    exit 1
}
Set-Location $REPO_PATH

Write-Host ""
Write-Host "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ($BACKUP_ROOT -and (Test-Path $BACKUP_ROOT)) {
    Write-Host ""
    Write-Host "Restoring backed up templates/naming..."

    if (-not (Test-Path $USER_DATA_ROOT)) {
        New-Item -ItemType Directory -Path $USER_DATA_ROOT -Force | Out-Null
    }

    $BACKUP_TEMPLATES = Join-Path $BACKUP_ROOT "templates"
    $BACKUP_NAMING = Join-Path $BACKUP_ROOT "naming"

    if (Test-Path $BACKUP_TEMPLATES) {
        if (-not (Test-Path $USER_TEMPLATES_DIR)) {
            New-Item -ItemType Directory -Path $USER_TEMPLATES_DIR -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $BACKUP_TEMPLATES "*") -Destination $USER_TEMPLATES_DIR -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "OK Restored templates"
    }

    if (Test-Path $BACKUP_NAMING) {
        if (-not (Test-Path $USER_NAMING_DIR)) {
            New-Item -ItemType Directory -Path $USER_NAMING_DIR -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $BACKUP_NAMING "*") -Destination $USER_NAMING_DIR -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "OK Restored naming conventions"
    }
}

Write-Host ""
Write-Host "Creating desktop shortcut..."

# Create a batch file launcher
$LAUNCHER_DIR = "$env:USERPROFILE\Apps\Photo_Metadata_App_By_Gledhill"
$LAUNCHER_SCRIPT = @"
@echo off
cd /d "$LAUNCHER_DIR"
python main.py
pause
"@

$LAUNCHER_PATH = "$LAUNCHER_DIR\run_app.bat"
$LAUNCHER_SCRIPT | Out-File -FilePath $LAUNCHER_PATH -Encoding ASCII

# Create desktop shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "$APP_NAME.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LAUNCHER_PATH
$Shortcut.WorkingDirectory = $LAUNCHER_DIR
$Shortcut.Description = "Photo Metadata Editor"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCommand) {
    $Shortcut.IconLocation = $PythonCommand.Source
}

$Shortcut.Save()

Write-Host ""
Write-Host "========================================"
Write-Host "Installation Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "A shortcut has been created on your Desktop: '$APP_NAME'"
Write-Host "Click it to launch the application."
Write-Host ""
Write-Host ("To uninstall, simply delete the folder: {0}" -f $LAUNCHER_DIR)
Write-Host ""