# Photo Metadata Editor - Quick Reference

## Installation (30 seconds)

```bash
cd /Users/michael/Documents/GitHub/Photo_Metadata_App_By_Gledhill
pip install -r requirements.txt
python3 photo_meta_editor.py
```

**That's it!** The app creates default templates and naming conventions automatically on first run.

---

## First Steps

1. **Drag a photo** into the window (or click "Open Files")
2. Click **"View Metadata"** to see EXIF and XMP tags
3. Select a **template** from the right panel
4. Select a **naming convention** from the right panel
5. Click the green **"APPLY TEMPLATE & RENAME"** button
6. Done! Photo is updated with metadata and renamed

---

## Default Templates (Pre-Created)

### Portrait Template
- Artist: Photographer Name
- Copyright: © 2025 Photographer Name
- Description: Professional portrait photography

### Travel Log
- Artist: Travel Photographer
- Description: Travel documentation

---

## Default Naming Conventions (Pre-Created)

### Date + Title
Pattern: `{date}_{title}_{sequence:03d}`
Example: `2025-01-15_My Portrait_001.jpg`

### Timestamp + Camera
Pattern: `{datetime:%Y%m%d_%H%M%S}_{camera_model}`
Example: `20250115_143022_Canon EOS 5D.jpg`

---

## Quick Operations

| Action | Steps |
|--------|-------|
| **View metadata** | Select file → "View Metadata" |
| **Delete metadata** | Select file → "Delete Metadata" |
| **Create template** | "Create Template" → Add EXIF/XMP → Save |
| **Create naming** | "Create Naming Convention" → Enter pattern → Save |
| **Apply template** | Select file + template + naming → Click green button |
| **Undo last** | Click "Undo Last Operation" |

---

## Naming Tokens

```
{date}                     → 2025-01-15
{datetime:%Y%m%d_%H%M%S}  → 20250115_143022
{title}                    → Photo Title
{camera_model}             → Canon EOS 5D
{sequence:03d}             → 001, 002, 003...
{original_name}            → IMG_1234
{userid}                   → your_username
```

**Example patterns:**
- `{date}_{title}` → `2025-01-15_My Photo`
- `Trip_{datetime:%B%d}_{sequence:02d}` → `Trip_January15_01`
- `{camera_model}_{sequence:04d}` → `Canon_EOS_0042`

---

## Common Issues

| Problem | Solution |
|---------|----------|
| App won't start | Check: `python3 test_app.py` |
| "libxmp not found" | This is OK - use exiftool instead: `brew install exiftool` |
| Metadata won't apply | Check file permissions: `ls -la yourfile.jpg` |
| Files not renaming | Verify naming convention pattern is valid |

---

## Tips & Tricks

✅ **Batch operations**: Select multiple files, apply template to all at once

✅ **Merge mode**: Check "Merge metadata" to keep existing EXIF, add new XMP

✅ **Dry run**: Check "Dry run" to preview changes without modifying files

✅ **Template export**: Templates are just JSON files in `~/.photo_meta_editor/templates/` - copy/share them!

✅ **Undo anytime**: Just hit "Undo Last Operation" - safe!

---

## File Organization

```
~/.photo_meta_editor/
├── templates/          ← Your saved metadata templates
├── naming/             ← Your naming conventions
└── undo/               ← Operation history for undo
```

You can manually edit JSON files in these folders to create templates!

---

## Example Workflow

**Scenario**: You're processing travel photos

1. Create template "Travel 2025":
   - Artist: "Your Name"
   - Copyright: "© 2025 Your Name"
   - Keywords: "travel, [location]"

2. Create naming "Travel Dates":
   - Pattern: `Travel_{datetime:%B%d}_{sequence:03d}`

3. Drag all photos from your trip
4. Select template + naming
5. Click "APPLY TEMPLATE & RENAME"
6. Photos are now organized with consistent metadata and names!

---

## Advanced Usage

### Custom DateTime Formats
```
{datetime:%A, %B %d, %Y}      → Monday, January 15, 2025
{datetime:%Y-%m-%d %H:%M:%S}  → 2025-01-15 14:30:22
{datetime:%Y}                  → 2025
{datetime:%U}                  → Week number
```

See Python's strftime docs for all format codes.

### Creating Complex Patterns
```
Before: IMG_1234.jpg
Pattern: {datetime:%Y}/{datetime:%m} - {title}/{sequence:05d}
Result: 2025/01 - My Photos/00001.jpg
```

---

## Uninstall / Reset

**Reset app settings** (keeps photos safe):
```bash
rm -rf ~/.photo_meta_editor
```

Restart the app and defaults are recreated.

**Full uninstall**:
```bash
pip uninstall PySide6 piexif Pillow
rm -rf photo_meta_editor.py
```

---

## Need Help?

📖 Full documentation: See `README.md`
🔧 Setup issues: See `SETUP_GUIDE.md`
✅ Verify installation: Run `python3 test_app.py`
🐛 Bug reports: Check application log output

---

## Keyboard Shortcuts (Coming Soon)

- `Ctrl+O` - Open files
- `Ctrl+S` - Save template
- `Ctrl+Z` - Undo
- `Tab` - Navigate dialogs

---

**Ready to go!** Start the app: `python3 photo_meta_editor.py`
