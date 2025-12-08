"""
Setup script for creating macOS .app bundle using py2app

This file is used by py2app to build a standalone macOS application.
It specifies which files to include, app metadata, and build options.

Usage:
    python3 setup.py py2app

The built .app will be placed in the dist/ folder and includes:
- All three Python modules (photo_meta_editor.py, gui.py, metadata_handler.py)
- Assets folder with icon
- Storage folder for user templates/naming conventions
- Example templates
- All dependencies

Configuration:
- APP: Main Python script to convert to .app
- DATA_FILES: Additional files to include (templates, assets, storage)
- OPTIONS: py2app build settings including bundle info and optimization

Requirements:
- py2app: Install with 'pip install py2app'
- macOS: This only works on macOS
"""

from setuptools import setup
from pathlib import Path
import glob

# Main application script
APP = ['photo_meta_editor.py']

# Data files to include in the app bundle
# Format: (destination_folder, [source_files])

# Collect all example templates dynamically
example_templates = glob.glob('example_templates/*.json') + ['example_templates/README.md']

DATA_FILES = [
    ('example_templates', example_templates),
    ('storage', ['storage/.keep']),
    ('assets', ['assets/icon.icns'] if Path('assets/icon.icns').exists() else []),
    # Include the other Python modules as resources
    ('', ['gui.py', 'metadata_handler.py', 'requirements.txt']),
]

# py2app options
ICON_FILE = 'assets/icon.icns'
ICON_FILE = ICON_FILE if Path(ICON_FILE).exists() else None

OPTIONS = {
    # App behavior
    'argv_emulation': False,  # Don't emulate command-line arguments (not needed for GUI app)
    'strip': True,  # Strip debug symbols to reduce size
    'optimize': 2,  # Optimize Python bytecode
    
    # Icon (optional - add if you create an .icns file)
    'iconfile': ICON_FILE,  # Uses generated icon when present
    
    # Bundle metadata (shown in Finder, About dialog, etc.)
    'plist': {
        'CFBundleName': 'Photo Metadata Editor',
        'CFBundleDisplayName': 'Photo Metadata Editor',
        'CFBundleIdentifier': 'com.gledhill.photometadataeditor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 Michael Gledhill',
        'LSMinimumSystemVersion': '10.13.0',  # Minimum macOS version
        'NSHighResolutionCapable': True,  # Support Retina displays
        
        # Document types (optional - specify if app can open specific file types)
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Image Files',
                'CFBundleTypeRole': 'Editor',
                'LSItemContentTypes': [
                    'public.jpeg',
                    'public.tiff',
                    'public.png'
                ],
                'LSHandlerRank': 'Alternate'
            }
        ]
    },
    
    # Python packages to include
    'packages': [
        'PySide6',  # Qt GUI framework
        'piexif',   # EXIF metadata handling
        'PIL',      # Image processing (Pillow)
        'xml.etree.ElementTree',  # XMP sidecar parsing
        'pathlib',  # Path handling
        'json',     # Template/config handling
    ],
    
    # Additional modules to include (if needed)
    'includes': [
        'gui',              # GUI module
        'metadata_handler', # Metadata handler module
    ],
    
    # Modules to exclude (reduces app size)
    'excludes': [
        'tkinter',      # Not using Tkinter
        'matplotlib',   # Not using matplotlib
        'numpy',        # Not using numpy
        'scipy',        # Not using scipy
        'pandas',       # Not using pandas
        'pytest',       # Don't need testing framework in app
        'unittest',     # Don't need testing framework in app
    ],
    
    # Resource files
    'resources': ['assets/', 'storage/'],
    
    # Framework options
    'frameworks': [],
    
    # Build mode: 'alias' for development (faster), omit for production
    # 'alias': True,  # Uncomment for development builds
}

# Setup configuration
setup(
    name='Photo Metadata Editor',
    version='1.0.0',
    author='Michael Gledhill',
    description='Edit EXIF and XMP metadata in photos with templates and batch processing',
    
    # Application files
    app=APP,
    data_files=DATA_FILES,
    
    # py2app options
    options={'py2app': OPTIONS},
    
    # Build requirements
    setup_requires=['py2app'],
    
    # Runtime requirements
    install_requires=[
        'PySide6>=6.7.0',
        'piexif>=1.1.3',
        'Pillow>=10.0.0',
    ],
)
