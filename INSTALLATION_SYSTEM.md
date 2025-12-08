# Installation System Documentation

This document explains how the Photo Metadata Editor installation system works and how to maintain it.

## Overview

The installation system consists of three main components:

1. **`install.py`** - Cross-platform installer script (automated setup)
2. **`setup.py`** - py2app configuration for building macOS .app bundles
3. **`requirements.txt`** - Python package dependencies

## Component Details

### 1. install.py - The Main Installer

**Purpose:** Automates the complete setup process for users on any platform.

**What it does:**
1. Checks system requirements (Git, Python, pip)
2. Clones or updates the GitHub repository
3. Installs Python dependencies
4. (Optional) Builds macOS .app bundle
5. Provides clear success/error messages

**Key Features:**
- ✓ Cross-platform (macOS, Windows, Linux)
- ✓ Never requires sudo/administrator privileges
- ✓ Never modifies system files
- ✓ Provides installation instructions for missing tools
- ✓ Safe for students and beginners
- ✓ Colored terminal output for clarity
- ✓ Comprehensive error handling

**Usage:**
```bash
# Basic installation
python3 install.py

# Install and build macOS app
python3 install.py --build-app

# Install to custom location
python3 install.py --target-dir ~/MyApps

# Show help
python3 install.py --help
```

**Key Functions:**

- `check_git_installed()` - Verifies Git is available
- `print_git_install_instructions()` - Shows platform-specific Git installation steps
- `check_python_version()` - Ensures Python 3.8+
- `check_pip_installed()` - Verifies pip is available
- `clone_or_update_repo()` - Clones repo or pulls latest changes
- `verify_essential_files()` - Checks all required files exist
- `install_requirements()` - Installs Python packages
- `create_setup_py()` - Generates setup.py for py2app
- `build_macos_app()` - Creates .app bundle on macOS

**Safety Measures:**
- No `sudo` or administrator commands
- No system-wide package installations
- No modification of system files
- All operations in user directory
- Clear error messages instead of failures

**Customization:**

To update the repository URL or required files, edit these constants:

```python
REPO_URL = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill"
REPO_NAME = "Photo_Metadata_App_By_Gledhill"
MAIN_SCRIPT = "photo_meta_editor.py"
REQUIREMENTS_FILE = "requirements.txt"

ESSENTIAL_FILES = [
    MAIN_SCRIPT,
    REQUIREMENTS_FILE,
    "example_templates/",
    "test_app.py"
]
```

### 2. setup.py - macOS App Builder

**Purpose:** Configures py2app to create a standalone macOS .app bundle.

**What it does:**
- Specifies the main Python script (`photo_meta_editor.py`)
- Lists data files to include (templates, etc.)
- Configures app metadata (name, version, copyright)
- Sets build options (optimization, exclusions)
- Handles code signing preparation

**Key Sections:**

**APP Definition:**
```python
APP = ['photo_meta_editor.py']  # Main script to convert
```

**DATA_FILES:**
```python
DATA_FILES = [
    ('example_templates', [
        'example_templates/portrait_professional.json',
        # ... more template files
    ]),
]
```
These files are copied into the .app bundle's Resources folder.

**OPTIONS - plist (Bundle Metadata):**
```python
'plist': {
    'CFBundleName': 'Photo Metadata Editor',
    'CFBundleIdentifier': 'com.gledhill.photometadataeditor',
    'CFBundleVersion': '1.0.0',
    # ... more metadata
}
```
This information appears in Finder's "Get Info" and the app's About dialog.

**OPTIONS - packages:**
```python
'packages': ['PySide6', 'piexif', 'PIL']
```
These Python packages are bundled into the app.

**OPTIONS - excludes:**
```python
'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy']
```
These packages are excluded to reduce app size.

**Building the App:**

```bash
# Install py2app
pip install py2app

# Build the app (creates dist/Photo Metadata Editor.app)
python3 setup.py py2app

# Test the app
open "dist/Photo Metadata Editor.app"

# Move to Applications
mv "dist/Photo Metadata Editor.app" /Applications/
```

**Customization:**

To add an icon, create an .icns file and set:
```python
'iconfile': 'icon.icns',
```

To change the app name:
```python
'CFBundleName': 'Your App Name',
'CFBundleDisplayName': 'Your App Name',
```

To support opening files by double-clicking:
```python
'CFBundleDocumentTypes': [
    {
        'CFBundleTypeName': 'JPEG Image',
        'CFBundleTypeRole': 'Editor',
        'LSItemContentTypes': ['public.jpeg'],
    }
]
```

### 3. requirements.txt - Dependencies

**Purpose:** Lists all Python packages required by the application.

**Current Dependencies:**

```
PySide6>=6.7.0    # Qt GUI framework (cross-platform UI)
piexif>=1.1.3     # EXIF metadata reading/writing
Pillow>=10.0.0    # Image processing (optional metadata method)
```

**Optional Dependencies:**

The app also supports these packages if available:
- `python-xmp-toolkit` - XMP metadata (requires libexempi)
- `exiftool` - External tool for advanced metadata

These are optional and detected at runtime.

**Installing:**
```bash
pip install -r requirements.txt
```

**Updating:**

To add a new dependency:
1. Add it to `requirements.txt`
2. Update `setup.py` packages list
3. Update fallback list in `install.py`

## Installation Flow

Here's what happens when a user runs `install.py`:

```
1. User runs: python3 install.py
   ↓
2. Check Git installed → If not, show instructions and exit
   ↓
3. Check Python 3.8+ → If not, show instructions and exit
   ↓
4. Check pip available → If not, show instructions and exit
   ↓
5. Clone/update repository
   ↓
6. Verify essential files exist
   ↓
7. Install packages from requirements.txt
   ↓
8. (Optional) Build macOS .app with py2app
   ↓
9. Show success message with usage instructions
```

**Error Handling:**

At each step, if something fails:
- Clear error message is displayed
- Specific instructions provided for fixing the issue
- Script exits gracefully
- No partial installations left behind

## Platform-Specific Notes

### macOS

**Installation Location:** `~/Applications/Photo_Metadata_App_By_Gledhill/`

**App Bundle:**
- Created with py2app
- Self-contained (includes Python + dependencies)
- Can be moved to `/Applications/`
- Appears like native macOS app

**Considerations:**
- Requires Xcode Command Line Tools for some packages
- May need to allow app in System Preferences → Security

### Windows

**Installation Location:** `%USERPROFILE%\Photo_Metadata_App_By_Gledhill\`

**Considerations:**
- Colored terminal output may not work without ANSICON
- Git installation may require restart
- Python needs to be in PATH

**Running:**
```cmd
python photo_meta_editor.py
```

### Linux

**Installation Location:** `~/Photo_Metadata_App_By_Gledhill/`

**Considerations:**
- Package managers vary by distribution
- May need to install `python3-dev` for some packages
- Qt dependencies may require system libraries

**Running:**
```bash
python3 photo_meta_editor.py
```

## Maintenance Guide

### Updating the Installer

**Adding a new dependency:**

1. Add to `requirements.txt`:
```
new-package>=1.0.0
```

2. Add to `setup.py` packages list:
```python
'packages': ['PySide6', 'piexif', 'PIL', 'new-package']
```

3. Add to `install.py` fallback list:
```python
packages = ['PySide6>=6.7.0', 'piexif>=1.1.3', 'Pillow>=10.0.0', 'new-package>=1.0.0']
```

**Adding a new essential file:**

Edit `install.py`:
```python
ESSENTIAL_FILES = [
    MAIN_SCRIPT,
    REQUIREMENTS_FILE,
    "example_templates/",
    "test_app.py",
    "new_file.py"  # Add here
]
```

**Changing the repository URL:**

Edit `install.py`:
```python
REPO_URL = "https://github.com/your-username/your-repo"
REPO_NAME = "your-repo"
```

### Testing the Installer

**Test on clean system:**

```bash
# Create a fresh directory
mkdir test_install
cd test_install

# Download and run installer
curl -O https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py
python3 install.py

# Verify installation
cd Photo_Metadata_App_By_Gledhill
python3 photo_meta_editor.py
```

**Test without Git:**

```bash
# Temporarily rename git (don't actually do this!)
# Instead, test the instructions output
python3 install.py  # Should show Git install instructions
```

**Test macOS app build:**

```bash
python3 install.py --build-app
open "dist/Photo Metadata Editor.app"
```

### Troubleshooting

**"Git not found"**
- User needs to install Git
- Installer provides platform-specific instructions
- User should run installer again after installing Git

**"Python version too old"**
- User needs Python 3.8 or higher
- Installer shows download links
- User may need to use `python3` instead of `python`

**"pip not available"**
- Usually means Python wasn't installed correctly
- User should reinstall Python with pip included
- On Linux, may need `python3-pip` package

**"Failed to clone repository"**
- Check internet connection
- Check if GitHub is accessible
- Verify repository URL is correct

**"Package installation failed"**
- May need system dependencies (e.g., Qt libraries)
- Check pip is up to date: `pip install --upgrade pip`
- Try manual installation: `pip install -r requirements.txt`

**"py2app build failed"**
- macOS only issue
- May need Xcode Command Line Tools: `xcode-select --install`
- Check all dependencies installed correctly
- Try cleaning: `rm -rf build dist` then rebuild

## Distribution

### For Users

Provide this simple installation command:

```bash
curl -O https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py
python3 install.py
```

Or with auto-download and run:

```bash
python3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py').read())"
```

### For Developers

Clone the repository and install in development mode:

```bash
git clone https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git
cd Photo_Metadata_App_By_Gledhill
pip install -e .
```

## Security Considerations

**What the installer does NOT do:**
- ✗ Never runs with sudo/administrator privileges
- ✗ Never modifies system files or directories
- ✗ Never installs system-wide packages
- ✗ Never executes untrusted code
- ✗ Never collects or transmits user data

**What it DOES do:**
- ✓ Installs only to user directory
- ✓ Uses official package repositories (PyPI)
- ✓ Provides clear instructions for manual steps
- ✓ Shows all commands before running
- ✓ Handles errors gracefully

**For educational environments:**
- Safe for students to use
- No privileged access needed
- All operations are reversible
- Clear logs of all actions

## File Locations

**After Installation:**

```
~/Applications/Photo_Metadata_App_By_Gledhill/  (macOS)
~/Photo_Metadata_App_By_Gledhill/               (Linux/Windows)
├── photo_meta_editor.py          # Main application
├── requirements.txt               # Dependencies
├── setup.py                       # py2app config
├── install.py                     # Installer script
├── test_app.py                    # Tests
├── example_templates/             # Template library
│   ├── portrait_professional.json
│   ├── travel_photography.json
│   └── ...
├── build/                         # Build artifacts (created by py2app)
└── dist/                          # Built .app (macOS only)
    └── Photo Metadata Editor.app
```

**User Data:**

```
~/.photo_meta_editor/              # User configuration
├── templates/                     # User's saved templates
├── naming/                        # User's naming conventions
└── undo/                          # Undo history
```

## Future Enhancements

**Potential improvements:**

1. **Windows .exe build** - Use PyInstaller or cx_Freeze
2. **Linux .AppImage** - Create portable Linux app
3. **Auto-updater** - Check for new versions
4. **Plugin system** - Allow third-party extensions
5. **Cloud sync** - Sync templates across devices
6. **Icon file** - Create and include .icns for macOS
7. **Notarization** - Code sign and notarize for macOS Gatekeeper

## Support

**For installation issues:**
1. Check this documentation
2. Review error messages carefully
3. Ensure all requirements are met
4. Try manual installation as fallback

**For application issues:**
1. Run tests: `python3 test_app.py`
2. Check documentation: https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/
3. Verify dependencies: `pip list`

## License

This installation system is provided as-is for use with the Photo Metadata Editor application.
