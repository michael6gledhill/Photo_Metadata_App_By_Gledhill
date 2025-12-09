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
    Write-Host "❌ Error: This script must be run as Administrator."
    Write-Host "Please right-click on PowerShell and select 'Run as administrator'."
    exit 1
}

$REPO_URL = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
$INSTALL_DIR = "$env:USERPROFILE\Apps"
$APP_NAME = "Photo Metadata Editor"

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
        choco install git -y
    }
} else {
    Write-Host "✓ Git already installed"
}

# Check Python 3
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 not found. Installing Python 3..."
    choco install python -y
} else {
    Write-Host "✓ Python 3 already installed ($(python --version))"
}

# Clone or update repository
$REPO_PATH = Join-Path $INSTALL_DIR "Photo_Metadata_App_By_Gledhill"
if (Test-Path $REPO_PATH) {
    Write-Host "Repository already exists. Updating..."
    Set-Location $REPO_PATH
    git pull
} else {
    Write-Host "Cloning repository..."
    git clone $REPO_URL
    Set-Location $REPO_PATH
}

Write-Host ""
Write-Host "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

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
$Shortcut.IconLocation = "$(python -c 'import sys; print(sys.executable)')"
$Shortcut.Save()

Write-Host ""
Write-Host "========================================"
Write-Host "✓ Installation Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "A shortcut has been created on your Desktop: '$APP_NAME'"
Write-Host "Click it to launch the application."
Write-Host ""
Write-Host "To uninstall, simply delete the folder: $LAUNCHER_DIR"
Write-Host ""
