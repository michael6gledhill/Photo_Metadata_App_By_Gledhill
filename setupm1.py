#!/usr/bin/env python3
"""
Build Photo Metadata Editor as a macOS app bundle on Apple Silicon using PyInstaller.
Use this instead of py2app when building on M1/M2/M3 Macs.
"""

import shutil
import sys
from pathlib import Path
import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
APP_NAME = "Photo Metadata Editor"
ICON = ROOT / "icon.icns"
ENTRY = ROOT / "main.py"
ASSETS = ROOT / "assets"
STORAGE = ROOT / "storage"
VERSION_FILE = ROOT / "version.txt"

def main():
    if not ENTRY.exists():
        sys.exit("main.py not found; run from repository root")

    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"
    # Clean previous build outputs for a fresh bundle
    for path in (dist_dir, build_dir):
        if path.exists():
            shutil.rmtree(path)

    data_args = []
    if ASSETS.exists():
        data_args += [f"{ASSETS}:assets"]
    if STORAGE.exists():
        data_args += [f"{STORAGE}:storage"]
    if VERSION_FILE.exists():
        data_args += [f"{VERSION_FILE}:."]

    PyInstaller.__main__.run([
        str(ENTRY),
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--icon", str(ICON),
        "--hidden-import", "metadata_handler",
        "--hidden-import", "gui",
        "--hidden-import", "update_checker",
        *[arg for data in data_args for arg in ("--add-data", data)],
    ])

if __name__ == "__main__":
    main()
