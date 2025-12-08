# Photo Metadata Editor

A professional macOS application for editing photo metadata (EXIF and XMP) and batch renaming files.

## ⚡ Quick Install (macOS)

Install with a single command:

```bash
sudo curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/Install.sh | bash
```

This will:
- Install dependencies (Git, Python 3)
- Clone the repository
- Build the macOS app
- Install it to your Applications folder

## Features

- **EXIF Metadata Editing**: Edit standard EXIF tags (camera, lens, copyright, etc.)
- **Embedded XMP Support**: Read and write XMP metadata directly in JPEG files
- **Template System**: Create reusable metadata templates
- **Batch Renaming**: Rename multiple files with custom patterns
- **Drag & Drop**: Simple drag and drop file management
- **Undo Support**: Undo last operation with automatic backups
- **Import/Export**: Share templates and naming conventions as JSON

## Manual Installation

### Requirements
- macOS 10.15 or later
- Python 3.8 or later

### Install from source:

```bash
# Clone the repository
git clone https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git
cd Photo_Metadata_App_By_Gledhill

# Install dependencies
pip3 install -r requirements.txt

# Run the application
python3 main.py
```

### Build as macOS App:

```bash
# Install py2app
pip3 install py2app

# Build the app
python3 setup.py py2app

# The app will be in the dist/ folder
# Copy it to Applications:
cp -R "dist/Photo Metadata Editor.app" /Applications/
```

## Usage

### Basic Workflow

1. **Open Files**: Click "Open Files" or drag & drop images
2. **Create Template**: Click "Create Template" to define metadata fields
3. **Create Naming Convention**: Click "Create Naming" to define filename patterns
4. **Select Template & Naming**: Choose from the lists on the right
5. **Apply**: Click "APPLY TEMPLATE & RENAME"

### Metadata Templates

Templates support:
- **EXIF Tags**: Artist, Copyright, ImageDescription, Make, Model, LensModel, etc.
- **XMP Properties**: 
  - Dublin Core (dc:): title, creator, description, subject, rights
  - Photoshop (photoshop:): Credit, AuthorsPosition, CaptionWriter
  - XMP (xmp:): CreatorTool, Rating

### Naming Conventions

Use tokens in your patterns:
- `{date}` - Date in YYYY-MM-DD format
- `{datetime:%Y%m%d_%H%M%S}` - Custom datetime format
- `{title}` - XMP/EXIF title
- `{camera_model}` - Camera model
- `{sequence:03d}` - Sequential number (001, 002, etc.)
- `{original_name}` - Original filename
- `{userid}` - Custom user ID

Example: `{userid}_{date}_{original_name}` → `MGledhill_2025-12-08_IMG_1234.jpg`

### Import/Export Templates

- **Export**: Edit a template/naming and click "Export as JSON"
- **Import**: Click "Import" and select a JSON file or paste JSON

JSON Format for templates:
```json
{
  "name": "My Template",
  "exif": {
    "Artist": "John Doe",
    "Copyright": "© 2025 John Doe"
  },
  "xmp": {
    "dc:creator": "John Doe",
    "dc:rights": "© 2025 John Doe"
  }
}
```

## Troubleshooting

### Application won't open
- Right-click the app → Open → Open (bypasses Gatekeeper)
- Or: System Settings → Privacy & Security → Allow "Photo Metadata Editor"

### Metadata not saving
- Ensure files are not read-only
- Check you have write permissions for the directory
- Try "View Metadata" to see current values

### Build errors
```bash
# Clean build
rm -rf build dist
python3 setup.py py2app
```

## Uninstall

Simply delete the app from your Applications folder, or run:
```bash
rm -rf "/Applications/Photo Metadata Editor.app"
```

## License

© 2025 Michael Gledhill

## Support

For issues or questions, please open an issue on GitHub.
