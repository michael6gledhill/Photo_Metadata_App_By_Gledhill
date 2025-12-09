📖 **[Full Documentation](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/)**

# Photo Metadata Editor

A professional application for editing photo metadata (EXIF and XMP) and batch renaming files. Works on macOS (Intel & M1), Windows, and Linux.

## ⚡ Quick Install

### macOS (Intel) - GUI Installer (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_gui.sh | bash
```

This launches a graphical installer that handles everything for you.
If the GUI installer fails to launch on your Mac, use the CLI fallback:
```bash
cd ~/App/Photo_Metadata_App_By_Gledhill && python3 main.py
```
That runs the app directly without the bundled .app wrapper.

### macOS (M1/M2/M3) - Single-Command Installer

For Apple Silicon, use this PyInstaller-based installer:

```bash
curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_m1.py | python3
```


### Windows - GUI Installer

**Option 1: PowerShell (Recommended)**
1. Right-click PowerShell and select "Run as administrator"
2. Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/Install.ps1'))
```

**Option 2: Command Prompt**
1. Right-click cmd.exe and select "Run as administrator"
2. Download and run: `Install.bat` from the [GitHub repository](https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill)

### Linux

For detailed Linux installation, see the **[Installation Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/INSTALL_GUIDE.html)**

## What It Does

- Edit EXIF metadata (camera, lens, copyright, etc.)
- Read and write XMP metadata directly in JPEG files
- Create reusable metadata templates
- Batch rename files with custom patterns
- Import/export templates and naming conventions as JSON

## Documentation

For detailed information, visit the **[GitHub Pages documentation](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/)**:

- **[Installation Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/INSTALL_GUIDE.html)** – Complete setup instructions for all platforms
- **[Naming Conventions Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/NAMING_CONVENTIONS.html)** – Token reference and patterns
- **[Metadata Fields Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/METADATA_GUIDE.html)** – Supported EXIF and XMP fields

## License

© 2025 Michael Gledhill


