#!/bin/bash

set -e  # Exit on error

echo "========================================"
echo "Photo Metadata Editor - Installation"
echo "========================================"
echo ""

# Detect username
USERNAME=$(whoami)
INSTALL_DIR="$HOME/App"
REPO_URL="https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
APP_NAME="Photo Metadata Editor"

# Create installation directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Check and install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✓ Homebrew already installed"
fi

# Check and install Git if not present
if ! command -v git &> /dev/null; then
    echo "Git not found. Installing Git via Homebrew..."
    brew install git
else
    echo "✓ Git already installed"
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Installing Python 3 via Homebrew..."
    brew install python@3
else
    echo "✓ Python 3 already installed ($(python3 --version))"
fi

# Clone or update repository
if [ -d "Photo_Metadata_App_By_Gledhill" ]; then
    echo "Repository already exists. Updating..."
    cd Photo_Metadata_App_By_Gledhill
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL"
    cd Photo_Metadata_App_By_Gledhill
fi

echo ""
echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install py2app

echo ""
echo "Building macOS application..."
python3 setup.py py2app

echo ""
echo "Installing application..."
# Remove old version if exists
if [ -d "/Applications/$APP_NAME.app" ]; then
    echo "Removing old version..."
    rm -rf "/Applications/$APP_NAME.app"
fi

# Copy new version
echo "Copying to Applications folder..."
cp -R "dist/$APP_NAME.app" /Applications/

echo ""
echo "========================================"
echo "✓ Installation Complete!"
echo "========================================"
echo ""
echo "You can now find '$APP_NAME' in your Applications folder."
echo "You can also launch it using Spotlight (Cmd+Space)."
echo ""
echo "To uninstall, simply delete the app from Applications."
echo ""

