# Photo Metadata Editor - Setup & Dependency Guide

## Quick Start (Minimal Requirements)

The application requires only these essential packages:

```bash
pip install -r requirements.txt
python3 photo_meta_editor.py
```

**Minimum setup works with**:
- ✅ EXIF reading/writing (via piexif)
- ✅ JPEG and TIFF file support
- ⚠️ Limited XMP support (read-only via exiftool)

---

## Recommended Installation (Full Features)

### Option 1: Use exiftool (Easiest - Recommended)

**exiftool** is the fastest and most compatible solution. Install it via:

#### macOS
```bash
brew install exiftool
```

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get install libimage-exiftool-perl
# or
sudo apt-get install exiftool
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install perl-Image-ExifTool
```

#### Windows
Download installer from: https://exiftool.org/

**After installation**, the app will automatically detect exiftool and use it for all metadata operations.

---

### Option 2: Full Python Support (XMP + EXIF)

For complete XMP support without exiftool, install the C dependencies:

#### macOS
```bash
# Install Exempi (required for libxmp)
brew install exempi

# Install optional Python XMP toolkit
pip install python-xmp-toolkit
```

#### Linux (Debian/Ubuntu)
```bash
# Install Exempi library
sudo apt-get install libexempi-dev

# Install Python package
pip install python-xmp-toolkit
```

#### Linux (Fedora/RHEL)
```bash
# Install Exempi library
sudo dnf install exempi-devel

# Install Python package
pip install python-xmp-toolkit
```

#### Windows
1. Download pre-built wheels from: https://github.com/python-xmp-toolkit/python-xmp-toolkit/releases
2. Or use Windows Subsystem for Linux (WSL) with Linux instructions above
3. Or use exiftool (Option 1) instead

---

## Complete Installation Scripts

### macOS (Complete Setup)
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install exiftool and exempi
brew install exiftool exempi

# Clone or navigate to the project
cd /Users/michael/Documents/GitHub/Photo_Metadata_App_By_Gledhill

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Optional: Install XMP support
pip install python-xmp-toolkit

# Run the application
python3 photo_meta_editor.py
```

### Linux Ubuntu/Debian (Complete Setup)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y exiftool libexempi-dev python3-pip python3-venv

# Navigate to project
cd /Users/michael/Documents/GitHub/Photo_Metadata_App_By_Gledhill

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Optional: Install XMP support
pip install python-xmp-toolkit

# Run the application
python3 photo_meta_editor.py
```

### Windows (Complete Setup)
```powershell
# Install exiftool (using scoop or download manually)
# From: https://exiftool.org/

# Navigate to project
cd C:\Users\YourUsername\Documents\GitHub\Photo_Metadata_App_By_Gledhill

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run the application
python photo_meta_editor.py
```

---

## Verifying Your Installation

### Check which tools are available:
```bash
# Check Python packages
python3 -c "
import sys
print('Python version:', sys.version)
try:
    import PySide6
    print('✓ PySide6 installed')
except:
    print('✗ PySide6 missing')
    
try:
    import piexif
    print('✓ piexif installed')
except:
    print('✗ piexif missing')
    
try:
    from libxmp import XMPMeta
    print('✓ libxmp installed')
except:
    print('⚠ libxmp not available (Exempi needed for full XMP support)')
"

# Check system tools
which exiftool && echo "✓ exiftool installed" || echo "✗ exiftool not found"
```

### Test the application startup:
```bash
cd /Users/michael/Documents/GitHub/Photo_Metadata_App_By_Gledhill
python3 -c "import photo_meta_editor; print('✓ Application imports successfully')"
```

---

## Troubleshooting Dependencies

### Issue: "libxmp.ExempiLoadError: Exempi library not found"

**This is normal** - the application will work fine with exiftool or piexif-only mode.

**To fix**:
1. Install Exempi (recommended): `brew install exempi` (macOS) or `sudo apt-get install libexempi-dev` (Linux)
2. Then install Python package: `pip install python-xmp-toolkit`
3. Or simply use exiftool instead (Option 1 above)

### Issue: "PySide6 not found"

```bash
pip install PySide6
```

### Issue: "exiftool command not found"

Install exiftool:
- macOS: `brew install exiftool`
- Linux: `sudo apt-get install exiftool`
- Windows: Download from https://exiftool.org/

### Issue: Application runs but "piexif not found" error

```bash
pip install piexif
```

---

## Feature Matrix by Installation Type

| Feature | Minimal | exiftool | Full (XMP) |
|---------|---------|----------|-----------|
| EXIF Reading | ✓ | ✓ | ✓ |
| EXIF Writing | ✓ | ✓ | ✓ |
| XMP Reading | - | ✓ | ✓ |
| XMP Writing | - | ✓ | ✓ |
| JPEG Support | ✓ | ✓ | ✓ |
| TIFF Support | ✓ | ✓ | ✓ |
| PNG Support | Limited | ✓ | ✓ |
| Speed | Fast | Very Fast | Fast |
| Reliability | Good | Excellent | Good |

---

## Requirements.txt Customization

### For exiftool-only users (no Python XMP libraries):
```
PySide6>=6.7.0
piexif>=1.1.3
Pillow>=10.0.0
```

### For full Python support:
```
PySide6>=6.7.0
piexif>=1.1.3
python-xmp-toolkit>=2.0.1
Pillow>=10.0.0
```

---

## Virtual Environment Best Practices

```bash
# Create venv
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate when done
deactivate

# List installed packages
pip list

# Export current environment
pip freeze > installed.txt

# Install from file
pip install -r installed.txt
```

---

## Running as Desktop Application

### macOS
Create a shell script launcher:
```bash
#!/bin/bash
cd /Users/michael/Documents/GitHub/Photo_Metadata_App_By_Gledhill
/usr/local/bin/python3 photo_meta_editor.py
```

Save as `photo_meta_editor.sh`, make executable:
```bash
chmod +x photo_meta_editor.sh
```

### Linux
Create `.desktop` file:
```ini
[Desktop Entry]
Type=Application
Name=Photo Metadata Editor
Exec=/usr/bin/python3 /path/to/photo_meta_editor.py
Icon=image
Categories=Graphics;
```

---

## Docker Setup (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y exiftool libexempi-dev
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && pip install python-xmp-toolkit
COPY photo_meta_editor.py .
CMD ["python3", "photo_meta_editor.py"]
```

Build and run:
```bash
docker build -t photo-metadata-editor .
docker run -it -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix photo-metadata-editor
```

---

## Getting Help

If you encounter dependency issues:

1. **Check Python version**: `python3 --version` (requires 3.10+)
2. **Verify pip is current**: `pip install --upgrade pip`
3. **Check application imports**: `python3 -c "import photo_meta_editor"`
4. **Review application logs**: Check console output for error messages
5. **Try minimal setup first**: Run with just requirements.txt, add exiftool if needed

---

## Next Steps

After installation:

1. **Run the application**: `python3 photo_meta_editor.py`
2. **Try the demo**: Use default templates provided
3. **Read the README**: See `README.md` for full usage guide
4. **Create your first template**: Use the "Create Template" button

Enjoy! 📸
