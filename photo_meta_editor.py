#!/usr/bin/env python3
"""
Photo Metadata Editor - A PySide6 GUI application for editing EXIF and XMP metadata in photos.

USAGE:
    python3 photo_meta_editor.py

INSTALLATION:
    1. Create a virtual environment: python3 -m venv venv
    2. Activate: source venv/bin/activate (macOS/Linux) or venv\\Scripts\\activate (Windows)
    3. Install dependencies: pip install -r requirements.txt
    4. Run: python3 photo_meta_editor.py

FEATURES:
    - View and edit EXIF and XMP metadata for JPEG, TIFF, and PNG files
    - Create and save metadata templates as JSON
    - Create and save flexible naming conventions with token replacement
    - Apply templates to single or multiple files with atomic writes
    - Delete all metadata from photos
    - Batch operations with progress tracking

NOTE: This file is now a simple launcher. All logic is in:
    - metadata_handler.py (MetadataManager, TemplateManager, NamingEngine)
    - gui.py (PhotoMetadataEditor, dialogs, main UI)
"""

from gui import main

if __name__ == '__main__':
    main()
