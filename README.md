# Photo Metadata Editor

Edit photo metadata (EXIF and XMP), create reusable templates, and batch rename files. Works on macOS, Windows, and Linux.

📖 **[View Full Documentation](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/)** — Complete guides, reference tables, and examples

---

## ⚡ Quick Install

### macOS (M1/M2/M3 — Apple Silicon)

**Step 1:** Open Terminal using Spotlight Search
- Press `Cmd + Space` to open Spotlight
- Type `Terminal` and press Enter

**Step 2:** Copy and paste this command into Terminal, then press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_m1.py | python3
```

The app will be installed to your Applications folder and launch automatically.

---

### macOS (Intel)

```bash
sudo curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/Install.sh | bash
```

Installs and launches the app via Terminal.

---

### Windows

**PowerShell (Recommended):**
1. Open Windows PowerShell or PowerShell and select "Run as administrator"
2. Run this one-liner:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/Install.ps1'))
```

The PowerShell installer is now Windows-compatible and should work cleanly on Windows PowerShell 5.1 as well as newer PowerShell versions.

**Command Prompt:**
1. Right-click cmd.exe and select "Run as administrator"
2. Download and run `Install.bat` from the [GitHub repository](https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill)

**Fallback:** If your environment blocks `iex` or script download execution, download `Install.ps1` locally and run it from an elevated PowerShell window.

---

### Ubuntu / Linux

```bash
sudo apt-get install python3 python3-pip git
git clone https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git
cd Photo_Metadata_App_By_Gledhill
pip3 install -r requirements.txt
python3 main.py
```

---

## Features

- Edit EXIF metadata (camera, lens, copyright, etc.)
- Read and write XMP metadata in JPEG files
- Create reusable metadata templates
- XMP subject helper: type one-line comma/pipe keywords; they are split into an array when applied (templates remain unchanged)
- Batch rename files with custom patterns
- Import/export templates as JSON

## Documentation

**[Installation Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/INSTALL_GUIDE.html)** — Complete setup instructions for all platforms

**[Naming Conventions Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/NAMING_CONVENTIONS.html)** — Token reference and pattern examples for batch renaming

**[Metadata Fields Guide](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/METADATA_GUIDE.html)** — Full list of supported EXIF and XMP fields

## License

© 2025 Michael Gledhill


