#!/usr/bin/env python3
"""
Photo Metadata Editor - Cross-Platform Installer
=================================================

This script automates the setup process for the Photo Metadata Editor application.
It works on macOS, Windows, and Linux without requiring administrator privileges.

What it does:
1. Checks for Git (provides install instructions if missing)
2. Clones or updates the GitHub repository
3. Verifies Python and pip are available
4. Installs required Python packages
5. (macOS only) Optionally builds a .app bundle with py2app

Usage:
    python3 install.py                    # Standard installation (builds .app on macOS)
    python3 install.py --no-build-app     # Skip .app build on macOS
    python3 install.py --help             # Show help message

Requirements:
- Python 3.8 or higher
- Git (instructions provided if not installed)
- pip (usually comes with Python)

Safety:
- Never requires sudo or administrator privileges
- Never modifies system files
- All files installed in user directory
- Safe for students and hobbyists
"""

import os
import sys
import subprocess
import platform
import shutil
import argparse
import tempfile
from pathlib import Path
from typing import Tuple, Optional, List


# ============================================================================
# Configuration
# ============================================================================

REPO_URL = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill"
REPO_NAME = "Photo_Metadata_App_By_Gledhill"
MAIN_SCRIPT = "photo_meta_editor.py"
REQUIREMENTS_FILE = "requirements.txt"
ICON_REL_PATH = Path("assets") / "icon.icns"

# Minimal list of files/folders needed for the app to run
ESSENTIAL_FILES = [
    MAIN_SCRIPT,
    REQUIREMENTS_FILE,
    "example_templates/",
    "test_app.py",
    "storage/.keep",
]

# Color codes for terminal output (works on most terminals)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        """Disable colors on Windows if not supported."""
        Colors.HEADER = ''
        Colors.OKBLUE = ''
        Colors.OKCYAN = ''
        Colors.OKGREEN = ''
        Colors.WARNING = ''
        Colors.FAIL = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


# ============================================================================
# Utility Functions
# ============================================================================

def print_header(message: str):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def run_command(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> Tuple[bool, str]:
    """
    Run a shell command and return success status and output.
    
    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        check: Whether to raise exception on failure
        
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except Exception as e:
        return False, str(e)


def ensure_storage_folder(repo_path: Path):
    """Ensure storage folder exists (for bundled JSON files)."""
    storage_dir = repo_path / 'storage'
    storage_dir.mkdir(parents=True, exist_ok=True)
    keep_file = storage_dir / '.keep'
    if not keep_file.exists():
        keep_file.write_text('Placeholder to keep storage folder in bundle\n')


def generate_mac_icon(repo_path: Path) -> bool:
    """Generate a simple macOS .icns with an 'M' logo if missing.

    Uses Pillow to draw a letter on a colored background, then iconutil to
    package it into an .icns. Works only on macOS. If iconutil is missing,
    this will skip with a warning.
    """
    if platform.system() != "Darwin":
        return False

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print_warning("Pillow not available; cannot auto-generate icon")
        return False

    # Check iconutil availability
    success, _ = run_command(['which', 'iconutil'], check=False)
    if not success:
        print_warning("iconutil not available; skipping icon generation")
        return False

    assets_dir = repo_path / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)
    icon_path = assets_dir / 'icon.icns'

    base_size = 1024
    background = (15, 48, 92)  # dark navy
    foreground = (255, 255, 255)

    # Create base image with centered 'M'
    img = Image.new('RGBA', (base_size, base_size), background)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Arial.ttf", 720)
    except Exception:
        font = ImageFont.load_default()
    text = "M"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    draw.text(((base_size - text_w) / 2, (base_size - text_h) / 2), text, fill=foreground, font=font)

    # Create iconset directory
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = Path(tmpdir) / 'icon.iconset'
        iconset.mkdir(parents=True, exist_ok=True)

        sizes = [
            (16, 1), (16, 2),
            (32, 1), (32, 2),
            (128, 1), (128, 2),
            (256, 1), (256, 2),
            (512, 1), (512, 2),
            (1024, 1)
        ]

        for size, scale in sizes:
            scaled = img.resize((size * scale, size * scale), Image.LANCZOS)
            name = f"icon_{size}x{size}" + ("@2x" if scale == 2 else "") + ".png"
            scaled.save(iconset / name)

        # Build icns
        success, output = run_command([
            'iconutil', '-c', 'icns', '-o', str(icon_path), str(iconset)
        ], check=False)

        if success and icon_path.exists():
            print_success(f"Generated icon: {icon_path}")
            return True
        else:
            print_warning(f"iconutil failed: {output}")
            return False


def get_system_info() -> dict:
    """Get information about the current system."""
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'machine': platform.machine(),
        'python_version': platform.python_version(),
    }


# ============================================================================
# Git Detection and Instructions
# ============================================================================

def check_git_installed() -> bool:
    """
    Check if Git is installed on the system.
    
    Returns:
        True if Git is available, False otherwise
    """
    success, _ = run_command(['git', '--version'], check=False)
    return success


def print_git_install_instructions():
    """Print platform-specific instructions for installing Git."""
    system = platform.system()
    
    print_error("Git is not installed on your system.")
    print("\nGit is required to download the application. Please install it first:\n")
    
    if system == "Darwin":  # macOS
        print(f"{Colors.BOLD}macOS Installation Options:{Colors.ENDC}")
        print("\n1. Using Homebrew (recommended):")
        print("   brew install git")
        print("\n2. Using Xcode Command Line Tools:")
        print("   xcode-select --install")
        print("\n3. Download installer:")
        print("   https://git-scm.com/download/mac")
        
    elif system == "Windows":
        print(f"{Colors.BOLD}Windows Installation:{Colors.ENDC}")
        print("\n1. Download Git for Windows:")
        print("   https://git-scm.com/download/win")
        print("\n2. Run the installer and follow the setup wizard")
        print("3. After installation, restart this script")
        
    elif system == "Linux":
        print(f"{Colors.BOLD}Linux Installation:{Colors.ENDC}")
        print("\nUbuntu/Debian:")
        print("   sudo apt-get update")
        print("   sudo apt-get install git")
        print("\nFedora/RHEL/CentOS:")
        print("   sudo dnf install git")
        print("\nArch Linux:")
        print("   sudo pacman -S git")
    else:
        print(f"{Colors.BOLD}Installation:{Colors.ENDC}")
        print("\nVisit: https://git-scm.com/downloads")
    
    print(f"\n{Colors.WARNING}After installing Git, run this script again.{Colors.ENDC}")


# ============================================================================
# Python and Pip Verification
# ============================================================================

def check_python_version() -> Tuple[bool, str]:
    """
    Check if Python version meets minimum requirements.
    
    Returns:
        Tuple of (meets_requirements: bool, version: str)
    """
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    # Require Python 3.8+
    if version.major >= 3 and version.minor >= 8:
        return True, version_str
    else:
        return False, version_str


def check_pip_installed() -> bool:
    """Check if pip is available."""
    success, _ = run_command([sys.executable, '-m', 'pip', '--version'], check=False)
    return success


def print_python_install_instructions():
    """Print instructions for installing/upgrading Python."""
    system = platform.system()
    
    print_error("Python 3.8 or higher is required.")
    print("\nPlease install or upgrade Python:\n")
    
    if system == "Darwin":  # macOS
        print(f"{Colors.BOLD}macOS Installation:{Colors.ENDC}")
        print("\n1. Using Homebrew:")
        print("   brew install python@3.11")
        print("\n2. Download from python.org:")
        print("   https://www.python.org/downloads/macos/")
        
    elif system == "Windows":
        print(f"{Colors.BOLD}Windows Installation:{Colors.ENDC}")
        print("\n1. Download from python.org:")
        print("   https://www.python.org/downloads/windows/")
        print("\n2. Run installer and check 'Add Python to PATH'")
        
    elif system == "Linux":
        print(f"{Colors.BOLD}Linux Installation:{Colors.ENDC}")
        print("\nMost distributions include Python 3. If not:")
        print("   sudo apt-get install python3 python3-pip  # Ubuntu/Debian")
        print("   sudo dnf install python3 python3-pip      # Fedora/RHEL")
    else:
        print("\nVisit: https://www.python.org/downloads/")


# ============================================================================
# Repository Management
# ============================================================================

def clone_or_update_repo(target_dir: Path) -> bool:
    """
    Clone the repository if it doesn't exist, or update it if it does.
    
    Args:
        target_dir: Directory where the repo should be cloned
        
    Returns:
        True if successful, False otherwise
    """
    repo_path = target_dir / REPO_NAME
    
    if repo_path.exists():
        print_info(f"Repository already exists at: {repo_path}")
        print_info("Updating repository...")
        
        # Check if it's a valid git repo
        if not (repo_path / ".git").exists():
            print_error(f"Directory exists but is not a git repository: {repo_path}")
            print_warning("Please remove this directory or choose a different location.")
            return False
        
        # Try to pull latest changes
        success, output = run_command(['git', 'pull'], cwd=repo_path, check=False)
        
        if success:
            print_success("Repository updated successfully")
            return True
        else:
            print_warning(f"Could not update repository: {output}")
            print_info("Continuing with existing version...")
            return True
    else:
        print_info(f"Cloning repository to: {repo_path}")
        
        # Clone the repository
        success, output = run_command(
            ['git', 'clone', REPO_URL, str(repo_path)],
            cwd=target_dir,
            check=False
        )
        
        if success:
            print_success("Repository cloned successfully")
            return True
        else:
            print_error(f"Failed to clone repository: {output}")
            return False


def verify_essential_files(repo_path: Path) -> bool:
    """
    Verify that all essential files exist in the repository.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        True if all essential files exist, False otherwise
    """
    print_info("Verifying essential files...")
    
    all_exist = True
    for file_path in ESSENTIAL_FILES:
        full_path = repo_path / file_path
        if full_path.exists():
            print_success(f"Found: {file_path}")
        else:
            print_error(f"Missing: {file_path}")
            all_exist = False
    
    return all_exist


# ============================================================================
# Package Installation
# ============================================================================

def install_requirements(repo_path: Path) -> bool:
    """
    Install required Python packages using pip.
    
    Args:
        repo_path: Path to the repository containing requirements.txt
        
    Returns:
        True if successful, False otherwise
    """
    requirements_path = repo_path / REQUIREMENTS_FILE
    
    if not requirements_path.exists():
        print_error(f"Requirements file not found: {requirements_path}")
        print_info("Using fallback package list...")
        
        # Fallback: Install packages directly
        packages = ['PySide6>=6.7.0', 'piexif>=1.1.3', 'Pillow>=10.0.0']
        for package in packages:
            print_info(f"Installing {package}...")
            success, output = run_command(
                [sys.executable, '-m', 'pip', 'install', package],
                check=False
            )
            if not success:
                print_error(f"Failed to install {package}: {output}")
                return False
        
        print_success("All packages installed successfully")
        return True
    
    print_info(f"Installing packages from {REQUIREMENTS_FILE}...")
    
    success, output = run_command(
        [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path)],
        check=False
    )
    
    if success:
        print_success("All packages installed successfully")
        return True
    else:
        print_error(f"Failed to install packages: {output}")
        return False


# ============================================================================
# macOS App Bundle Creation (py2app)
# ============================================================================

def create_setup_py(repo_path: Path) -> bool:
    """
    Create a setup.py file for py2app with all components.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        True if successful, False otherwise
    """
    setup_content = '''"""
Setup script for creating macOS .app bundle using py2app
"""
from setuptools import setup
from pathlib import Path
import glob

APP = ['photo_meta_editor.py']

# Collect all example templates dynamically
example_templates = glob.glob('example_templates/*.json') + ['example_templates/README.md']

DATA_FILES = [
    ('example_templates', example_templates),
    ('storage', ['storage/.keep']),
    ('assets', ['assets/icon.icns'] if Path('assets/icon.icns').exists() else []),
    # Include the other Python modules as resources
    ('', ['gui.py', 'metadata_handler.py', 'requirements.txt']),
]

OPTIONS = {
    'argv_emulation': False,  # Don't emulate command line arguments
    'iconfile': 'assets/icon.icns' if Path('assets/icon.icns').exists() else None,
    'plist': {
        'CFBundleName': 'Photo Metadata Editor',
        'CFBundleDisplayName': 'Photo Metadata Editor',
        'CFBundleIdentifier': 'com.gledhill.photometadataeditor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 Michael Gledhill',
        'LSMinimumSystemVersion': '10.13.0',  # macOS 10.13 or higher
        'NSHighResolutionCapable': True,
    },
    'packages': ['PySide6', 'piexif', 'PIL', 'xml.etree.ElementTree', 'pathlib', 'json'],
    'includes': ['gui', 'metadata_handler'],
    'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'pytest', 'unittest'],
    'resources': ['assets/', 'storage/'],
}

setup(
    name='Photo Metadata Editor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
'''
    
    setup_path = repo_path / 'setup.py'
    
    try:
        with open(setup_path, 'w') as f:
            f.write(setup_content)
        print_success(f"Created setup.py at {setup_path}")
        return True
    except Exception as e:
        print_error(f"Failed to create setup.py: {e}")
        return False


def build_macos_app(repo_path: Path) -> bool:
    """
    Build a macOS .app bundle using py2app.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        True if successful, False otherwise
    """
    if platform.system() != "Darwin":
        print_warning("py2app only works on macOS. Skipping .app creation.")
        return False
    
    print_info("Installing py2app...")
    success, output = run_command(
        [sys.executable, '-m', 'pip', 'install', 'py2app'],
        check=False
    )
    
    if not success:
        print_error(f"Failed to install py2app: {output}")
        return False
    
    # Create setup.py if it doesn't exist
    setup_path = repo_path / 'setup.py'
    if not setup_path.exists():
        if not create_setup_py(repo_path):
            return False

    # Ensure icon exists (auto-generate simple M logo if missing)
    icon_path = repo_path / ICON_REL_PATH
    if not icon_path.exists():
        generate_mac_icon(repo_path)
    if not icon_path.exists():
        print_warning("Icon file missing; build will proceed without custom icon")
    
    print_info("Building .app bundle (this may take a few minutes)...")
    
    # Clean previous builds
    for dir_name in ['build', 'dist']:
        dir_path = repo_path / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
    
    # Build the app
    success, output = run_command(
        [sys.executable, 'setup.py', 'py2app'],
        cwd=repo_path,
        check=False
    )
    
    if success:
        app_path = repo_path / 'dist' / 'Photo Metadata Editor.app'
        if app_path.exists():
            print_success(f"macOS app created successfully!")
            print_success(f"Location: {app_path}")
            print_info("You can now drag this app to your Applications folder.")
            return True
        else:
            print_error("Build completed but .app not found in dist/")
            return False
    else:
        print_error(f"Failed to build .app: {output}")
        print_info("You can still run the app using: python3 photo_meta_editor.py")
        return False


# ============================================================================
# Main Installation Flow
# ============================================================================

def main():
    """Main installation function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Install Photo Metadata Editor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--no-build-app',
        action='store_true',
        help='Skip building macOS .app bundle (default is to build on macOS)'
    )
    parser.add_argument(
        '--build-app',
        action='store_true',
        help='Force build .app bundle (deprecated: now default on macOS)'
    )
    parser.add_argument(
        '--target-dir',
        type=Path,
        default=Path.home() / 'Applications' if platform.system() == 'Darwin' else Path.home(),
        help='Directory where the app will be installed (default: ~/Applications on macOS, ~ elsewhere)'
    )
    
    args = parser.parse_args()
    
    # Disable colors on Windows if not supported
    if platform.system() == "Windows" and not os.environ.get('ANSICON'):
        Colors.disable()
    
    # Determine if we should build the app
    should_build_app = platform.system() == 'Darwin' and not args.no_build_app
    
    # Print welcome message
    print_header("Photo Metadata Editor - Installer")
    
    system_info = get_system_info()
    print(f"Operating System: {system_info['os']} {system_info['machine']}")
    print(f"Python Version: {system_info['python_version']}")
    print()
    
    # Step 1: Check Git
    print_header("Step 1: Checking Git Installation")
    if not check_git_installed():
        print_git_install_instructions()
        return 1
    print_success("Git is installed")
    
    # Step 2: Check Python version
    print_header("Step 2: Verifying Python Version")
    python_ok, python_version = check_python_version()
    if not python_ok:
        print_error(f"Python version {python_version} is too old")
        print_python_install_instructions()
        return 1
    print_success(f"Python {python_version} meets requirements")
    
    # Step 3: Check pip
    print_header("Step 3: Checking pip Installation")
    if not check_pip_installed():
        print_error("pip is not available")
        print_info("pip usually comes with Python. Try reinstalling Python.")
        return 1
    print_success("pip is available")
    
    # Step 4: Clone or update repository
    print_header("Step 4: Downloading Application")
    target_dir = args.target_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    if not clone_or_update_repo(target_dir):
        print_error("Failed to download application")
        return 1
    
    repo_path = target_dir / REPO_NAME
    
    # Step 5: Verify files
    print_header("Step 5: Verifying Files")
    ensure_storage_folder(repo_path)
    if not verify_essential_files(repo_path):
        print_error("Some essential files are missing")
        print_warning("The application may not work correctly")
    
    # Step 6: Install packages
    print_header("Step 6: Installing Python Packages")
    if not install_requirements(repo_path):
        print_error("Failed to install required packages")
        return 1
    
    # Step 7: Build macOS app (default on macOS)
    if should_build_app:
        print_header("Step 7: Building macOS App Bundle")
        print_info("Building .app with all components, assets, and storage...")
        build_macos_app(repo_path)
    elif platform.system() == "Darwin":
        print_info("\nSkipped .app build (use without --no-build-app to build)")
    
    # Success!
    print_header("Installation Complete!")
    print_success("Photo Metadata Editor has been installed successfully!\n")
    
    print(f"{Colors.BOLD}Application Location:{Colors.ENDC}")
    print(f"  {repo_path}\n")
    
    print(f"{Colors.BOLD}To run the application:{Colors.ENDC}")
    print(f"  cd {repo_path}")
    print(f"  python3 {MAIN_SCRIPT}\n")
    
    if should_build_app and platform.system() == "Darwin":
        app_path = repo_path / 'dist' / 'Photo Metadata Editor.app'
        if app_path.exists():
            print(f"{Colors.BOLD}macOS App Bundle Created:{Colors.ENDC}")
            print(f"  {app_path}")
            print(f"  Includes: photo_meta_editor.py, gui.py, metadata_handler.py")
            print(f"  Includes: assets/, storage/, example_templates/")
            print(f"  (Drag to Applications folder to install)\n")
    
    print(f"{Colors.BOLD}Documentation:{Colors.ENDC}")
    print(f"  https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/\n")
    
    print(f"{Colors.BOLD}Example Templates:{Colors.ENDC}")
    print(f"  {repo_path / 'example_templates'}\n")
    
    print(f"{Colors.OKGREEN}Enjoy using Photo Metadata Editor!{Colors.ENDC}")
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Installation cancelled by user.{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
