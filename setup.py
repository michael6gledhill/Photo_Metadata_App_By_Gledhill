"""
Setup script for creating macOS .app bundle using py2app

This file is used by py2app to build a standalone macOS application.
It specifies which files to include, app metadata, and build options.

Usage:
    python3 setup.py py2app

The built .app will be placed in the dist/ folder.

Configuration:
- APP: Main Python script to convert to .app
- DATA_FILES: Additional files to include (templates, etc.)
- OPTIONS: py2app build settings including bundle info and optimization

Requirements:
- py2app: Install with 'pip install py2app'
- macOS: This only works on macOS
"""

from setuptools import setup

# Main application script
APP = ['photo_meta_editor.py']

# Data files to include in the app bundle
# Format: (destination_folder, [source_files])
DATA_FILES = [
    ('example_templates', [
        'example_templates/portrait_professional.json',
        'example_templates/travel_photography.json',
        'example_templates/wedding_photography.json',
        'example_templates/event_photography.json',
        'example_templates/stock_photography.json',
        'example_templates/date_sequence.json',
        'example_templates/timestamp_camera.json',
        'example_templates/user_date_title.json',
        'example_templates/original_sequence.json',
        'example_templates/yearmonth_title_seq.json',
        'example_templates/README.md'
    ]),
]

# py2app options
OPTIONS = {
    # App behavior
    'argv_emulation': False,  # Don't emulate command-line arguments (not needed for GUI app)
    'strip': True,  # Strip debug symbols to reduce size
    'optimize': 2,  # Optimize Python bytecode
    
    # Icon (optional - add if you create an .icns file)
    'iconfile': None,  # Set to 'icon.icns' if you create one
    
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
    ],
    
    # Additional modules to include (if needed)
    'includes': [
        'json',
        'pathlib',
        'datetime',
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
    'resources': [],
    
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
