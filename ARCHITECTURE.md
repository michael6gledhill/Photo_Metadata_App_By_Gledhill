# Photo Metadata Editor - Clean Architecture

## Overview
The application is now split into **three clean files** with clear separation of concerns:

### 1. `photo_meta_editor.py` (31 lines - Launcher)
- **Purpose**: Entry point for the application
- **Content**: Simple import and main() call
- **Dependencies**: gui.py
- **Usage**: `python3 photo_meta_editor.py`

### 2. `metadata_handler.py` (644 lines - Logic)
- **Purpose**: All metadata operations (EXIF, XMP, templates, naming)
- **Classes**:
  - `MetadataManager`: Read/write EXIF and XMP metadata
  - `TemplateManager`: Save/load/import templates and naming conventions
  - `NamingEngine`: Generate filenames with token replacement

- **Key Features**:
  - **EXIF handling**: Via `piexif` library (pure Python)
  - **XMP handling**: Sidecar `.xmp` files with RDF/XML format
  - **No external tools**: No subprocess calls, no exiftool dependency
  - **Template system**: JSON-based templates stored in `~/.photo_meta_editor/templates/`
  - **Naming engine**: Supports tokens like `{date}`, `{datetime:%fmt}`, `{camera_model}`, etc.

- **Dependencies**:
  - `piexif` (EXIF)
  - `pathlib`, `json`, `xml.etree.ElementTree` (stdlib)
  - Optional: `PIL` (for image preview in GUI)

### 3. `gui.py` (936 lines - Interface)
- **Purpose**: All GUI components and user interaction
- **Classes**:
  - `TemplateDialog`: Create/edit templates
  - `ImportDialog`: Import templates or naming conventions from JSON
  - `NamingDialog`: Create/edit naming conventions
  - `MetadataViewDialog`: View metadata (with EXIF, XMP, JSON tabs)
  - `PhotoMetadataEditor`: Main window with all controls

- **Features**:
  - Drag-and-drop file selection
  - Image preview with navigation
  - Template management (create/edit/import/delete)
  - Naming convention management
  - Batch apply metadata + rename
  - Metadata viewer with JSON debugging tab
  - Merge or overwrite metadata options
  - Dry-run preview mode
  - Status logging with timestamps

- **Dependencies**:
  - `PySide6` (GUI framework)
  - `metadata_handler` (metadata operations)
  - Standard library (pathlib, traceback, etc.)

## Architecture Diagram

```
User
  ↓
photo_meta_editor.py (launcher)
  ↓
gui.py (PhotoMetadataEditor main window)
  ├─ TemplateDialog → metadata_handler.TemplateManager
  ├─ ImportDialog → metadata_handler.TemplateManager
  ├─ NamingDialog → metadata_handler.TemplateManager
  ├─ MetadataViewDialog ← metadata_handler.MetadataManager
  └─ PhotoMetadataEditor main window
      ├─ Opens files → metadata_handler.MetadataManager.get_metadata()
      ├─ Applies templates → metadata_handler.MetadataManager.set_metadata()
      ├─ Generates names → metadata_handler.NamingEngine.generate_filename()
      └─ Deletes metadata → metadata_handler.MetadataManager.delete_metadata()
```

## File Dependencies

```
photo_meta_editor.py
  └─ imports gui.py
      └─ imports metadata_handler.py
          └─ imports piexif, pathlib, json, xml.etree.ElementTree
```

## macOS Compatibility

✓ **Pure Python** - No native dependencies like Exempi or libxmp  
✓ **No subprocess** - No exiftool external tool calls  
✓ **Standard library** - Uses pathlib, json, xml.etree.ElementTree  
✓ **Easy install** - Just `pip install -r requirements.txt`  

## Requirements

```
PySide6>=6.0.0
piexif>=1.1.3
Pillow>=9.0.0
```

## Installation

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python3 photo_meta_editor.py
```

## Code Statistics

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `photo_meta_editor.py` | 31 | 1.0 KB | Launcher |
| `metadata_handler.py` | 644 | 23.6 KB | Metadata logic |
| `gui.py` | 936 | 36.5 KB | User interface |
| **Total** | **1,611** | **61.1 KB** | Complete app |

## Testing

All modules tested and verified:
- ✓ Syntax validation: All files parse correctly
- ✓ Import validation: All imports work
- ✓ Instantiation: All classes instantiate successfully
- ✓ Integration: gui.py correctly imports metadata_handler.py

## Development Notes

### Adding Features
1. **New metadata feature?** → Add to `MetadataManager` in `metadata_handler.py`
2. **New template feature?** → Add to `TemplateManager` in `metadata_handler.py`
3. **New UI element?** → Add to appropriate dialog or main window in `gui.py`
4. **New naming token?** → Add to `NamingEngine.generate_filename()` in `metadata_handler.py`

### Debugging
- **Metadata issues?** Use the JSON tab in MetadataViewDialog to see raw metadata
- **XMP not saving?** Check `~/.photo_meta_editor/metadata/` for sidecar .xmp files
- **Template issues?** Check `~/.photo_meta_editor/templates/` for saved JSON

### Performance
- Metadata operations are single-threaded (acceptable for typical usage)
- Batch operations use progress dialogs to show feedback
- Image preview uses PIL scaling for smooth performance
