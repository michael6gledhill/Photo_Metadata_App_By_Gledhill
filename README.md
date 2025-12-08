# Photo Metadata Editor

A professional PySide6 desktop application for editing EXIF and XMP metadata in photos. Includes template system, flexible naming conventions, and comprehensive metadata recommendations for different photography types.

## Installation

### Automated Installation (Recommended)

Use the cross-platform installer script for easy setup:

**One-line (curl + python3):**

```bash
curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py | python3 -
```

If you prefer to download the script first:

```bash
curl -O https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py
python3 install.py
```

Or if you already have the repository:

```bash
python3 install.py
```

**What the installer does:**
- ✓ Checks for required tools (Git, Python, pip)
- ✓ Clones or updates the repository
- ✓ Installs all Python dependencies
- ✓ Verifies all files are present
- ✓ (macOS only) Optionally builds a .app bundle

**Build macOS App (with icon):**
```bash
python3 install.py --build-app
```

This creates `dist/Photo Metadata Editor.app` with a generated "M" icon and includes a `storage/` folder for JSON templates.

The installer is safe for students and hobbyists:
- Never requires sudo or administrator privileges
- Never modifies system files
- Provides clear instructions for missing dependencies
- Works on macOS, Windows, and Linux

### Manual Installation

If you prefer manual setup:

```bash
# Clone the repository
git clone https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git
cd Photo_Metadata_App_By_Gledhill

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 photo_meta_editor.py
```

### macOS App Bundle (Manual)

To create a standalone .app on macOS:

```bash
pip install py2app
python3 setup.py py2app
```

The built app will be in `dist/Photo Metadata Editor.app`

## Quick Start

```bash
python3 photo_meta_editor.py
```

1. Click "Open Files" or drag photos into the window
2. Choose a template or create your own
3. Apply metadata and/or rename files
4. Done!

## Requirements

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Git** (for installer) - [Download Git](https://git-scm.com/downloads)
- **Dependencies** (auto-installed):
  - PySide6 >= 6.7.0 (Qt GUI framework)
  - piexif >= 1.1.3 (EXIF metadata)
  - Pillow >= 10.0.0 (Image processing)

## Documentation

**📖 Full documentation available on [GitHub Pages](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/)**

Documentation covers:
- Getting started and installation
- Complete feature guide with examples
- Metadata best practices for different photo types
- EXIF and XMP field recommendations
- Template examples for common workflows
- Troubleshooting and support

## Key Features

- **Dual Metadata Editing** - EXIF and XMP for JPEG, TIFF, PNG
- **Smart Templates** - Pre-built and custom metadata templates
- **Batch Processing** - Apply metadata to multiple files
- **Flexible Naming** - Token-based renaming with collision handling
- **Safe Operations** - Atomic writes, undo support, dry-run mode
- **Metadata Recommendations** - Best practices for different photo types

## Local Documentation

- **[index.qmd](index.qmd)** - Setup, quick start, features, troubleshooting
- **[Info.qmd](Info.qmd)** - Complete guide, metadata recommendations, usage

## Project Files

- `photo_meta_editor.py` - Main application (1400+ lines)
- `requirements.txt` - Python dependencies
- `test_app.py` - Validation tests

Test: `python3 test_app.py` → ✅ Should pass all tests

## License

Provided as-is for personal and professional use.
