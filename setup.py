"""
Setup script for building Photo Metadata Editor as a macOS .app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('', ['icon.icns']),
    ('assets', ['assets/icon.icns']),
    ('storage', []),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'Photo Metadata Editor',
        'CFBundleDisplayName': 'Photo Metadata Editor',
        'CFBundleGetInfoString': 'Edit photo metadata and filenames',
        'CFBundleIdentifier': 'com.gledhill.photometadataeditor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 Michael Gledhill',
        'NSHighResolutionCapable': True,
    },
    'packages': ['PySide6', 'PIL', 'piexif'],
    'includes': ['metadata_handler', 'gui'],
    'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy'],
    'optimize': 2,
}

setup(
    name='Photo Metadata Editor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
