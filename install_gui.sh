#!/bin/bash

# Photo Metadata Editor - GUI Installer Bootstrap
# This script downloads and runs the GUI installer

set -e

REPO_URL="https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
TEMP_DIR=$(mktemp -d)
INSTALL_DIR="$HOME/App/Photo_Metadata_App_By_Gledhill"

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

echo "========================================="
echo "Photo Metadata Editor - GUI Installer"
echo "========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo ""
    echo "macOS: brew install python@3"
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    echo "Windows: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3 found"

# Check if Git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed."
    echo ""
    echo "macOS: brew install git"
    echo "Ubuntu/Debian: sudo apt-get install git"
    echo "Windows: https://git-scm.com/download/win"
    exit 1
fi

echo "✓ Git found"
echo ""

# Check for PySide6
echo "Checking for PySide6..."
if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "Installing PySide6 (this may take a minute)..."
    python3 -m pip install -q PySide6 2>/dev/null || {
        echo "❌ Failed to install PySide6"
        echo "Try installing manually: pip3 install PySide6"
        exit 1
    }
fi

echo "✓ PySide6 available"
echo ""

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --rebase --autostash origin main >/dev/null 2>&1 || true
    MODE="update"
else
    echo "Downloading installation files..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null || {
        echo "❌ Failed to clone repository"
        exit 1
    }
    cd "$INSTALL_DIR"
    MODE="install"
fi

# Ensure gui_installer.py exists (for older clones)
if [ ! -f "gui_installer.py" ]; then
    echo "Fetching GUI installer..."
    curl -fsSL "https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/gui_installer.py" -o gui_installer.py || {
        echo "❌ Could not download gui_installer.py"
        exit 1
    }
fi

echo ""
echo "Launching GUI installer..."
echo ""

# Run the GUI installer
python3 gui_installer.py "$MODE"
