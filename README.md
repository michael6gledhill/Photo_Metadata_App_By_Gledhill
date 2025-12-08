# Photo Metadata Editor

Edit EXIF and XMP metadata in your photos with an easy-to-use desktop app. Save templates, batch process, and organize your photo library.

## Quick Install

**macOS/Linux/Windows:**
```bash
curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install.py | python3 -
```

This installs everything and builds a macOS .app if applicable.

**Manual:**
```bash
git clone https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git
cd Photo_Metadata_App_By_Gledhill
pip install -r requirements.txt
python3 main.py
```

## How to Use

### 1. Open Photos
- Click "Open Files" or drag photos into the window
- Works with JPEG, TIFF, PNG

### 2. Add Metadata

**Using Templates:**
- Select a template from the dropdown (e.g., "Portrait Template")
- Templates contain pre-configured EXIF and XMP fields
- Click "Apply" to write metadata to your photos

**Creating Custom Templates:**
- Click "Manage Templates" → "Create Template"
- Add EXIF fields (Artist, Copyright, etc.)
- Add XMP fields (title, description, creator, subject, etc.)
- Save with a name for reuse

**Manual Entry:**
- Use the EXIF and XMP tabs to add fields directly
- EXIF: Artist, Copyright, ImageDescription, DateTimeOriginal, etc.
- XMP: title, description, creator, subject, rights, Headline, DateCreated, etc.

### 3. Supported Metadata Fields

**EXIF (Camera/Technical Data):**
- `Artist` - Photographer name
- `Copyright` - Copyright notice
- `ImageDescription` - Photo description
- `DateTime` - Date/time modified
- `DateTimeOriginal` - Date/time taken
- `Make` / `Model` - Camera info
- `UserComment` - Comments

**XMP (Professional Metadata):**
- `title` - Photo title
- `description` - Detailed description
- `creator` - Photographer/creator name(s)
- `subject` - Keywords/tags (list)
- `rights` - Rights/usage statement
- `Headline` - Short headline (Photoshop)
- `DateCreated` - Creation date (Photoshop)
- `CreateDate` - Creation timestamp (XMP)

### 4. Examples

**Portrait Photography:**
```json
{
  "name": "Portrait Session",
  "exif": {
    "Artist": "Jane Photographer",
    "Copyright": "© 2025 Jane Photographer"
  },
  "xmp": {
    "creator": "Jane Photographer",
    "subject": ["portrait", "professional"],
    "Headline": "Professional Portrait Session"
  }
}
```

**Travel Photography:**
```json
{
  "name": "Travel Photos",
  "exif": {
    "Artist": "Your Name",
    "ImageDescription": "Travel photography"
  },
  "xmp": {
    "title": "Travel Adventure",
    "description": "Photos from my trip",
    "subject": ["travel", "adventure", "landscape"],
    "rights": "All rights reserved"
  }
}
```

## Key Features

- **Embedded XMP** - All XMP metadata is embedded directly in JPEG files (no sidecar files)
- **EXIF Editing** - Full EXIF support for camera data, copyright, and more
- **Templates** - Save and reuse metadata configurations
- **Batch Processing** - Apply metadata to multiple files at once
- **File Renaming** - Use patterns like `{date}_{title}_{sequence}`
- **Safe Operations** - Atomic writes protect your original files

## Requirements

- Python 3.8+
- PySide6 (GUI)
- piexif (EXIF)
- Pillow (images)

Auto-installed by the installer.

## Troubleshooting

**No metadata showing:**
- Make sure your image has embedded XMP (this app reads embedded XMP only)
- EXIF should always work for JPEG/TIFF files

**Changes not saving:**
- Check the status area for error messages
- Ensure the file is not read-only
- JPEGs support both EXIF and XMP; PNGs support XMP only

**Need help?**
- Check `test_app.py` to verify your installation
- Review example templates in `example_templates/`

## License

Free for personal and professional use.
