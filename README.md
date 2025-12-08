# Photo Metadata Editor

A professional PySide6 desktop application for editing EXIF and XMP metadata in photos. Includes template system, flexible naming conventions, and comprehensive metadata recommendations for different photography types.

## Quick Start

```bash
pip install -r requirements.txt
python3 photo_meta_editor.py
```

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
