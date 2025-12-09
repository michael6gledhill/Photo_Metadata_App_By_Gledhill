#!/usr/bin/env python3
"""
Install/Update Photo Metadata Editor on Apple Silicon (M1/M2/M3) using PyInstaller.
- Clones/updates the repo under ~/App/Photo_Metadata_App_By_Gledhill
- Installs required Python deps (PyInstaller, PySide6, Pillow, piexif)
- Builds the app with PyInstaller via setupm1.py
- Replaces the /Applications/Photo Metadata Editor.app bundle
- Launches the app

Usage:
    python3 install_m1.py

One-liner:
    curl -fsSL https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_m1.py | python3
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
INSTALL_DIR = Path.home() / "App" / "Photo_Metadata_App_By_Gledhill"
APP_NAME = "Photo Metadata Editor.app"
TARGET_APP = Path("/Applications") / APP_NAME

REQ_PACKAGES = ["pip", "PyInstaller", "PySide6", "Pillow", "piexif"]


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def ensure_arm_macos():
    if platform.system() != "Darwin":
        sys.exit("This installer is for macOS (Apple Silicon) only.")
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        sys.exit("This installer is intended for Apple Silicon (arm64).")


def ensure_repo():
    INSTALL_DIR.parent.mkdir(parents=True, exist_ok=True)
    if INSTALL_DIR.exists():
        run(["git", "pull", "--rebase", "--autostash", "origin", "main"], cwd=INSTALL_DIR)
    else:
        run(["git", "clone", REPO_URL, str(INSTALL_DIR)])


def ensure_deps():
    run([sys.executable, "-m", "pip", "install", "--upgrade", *REQ_PACKAGES])


def build_app():
    setup_m1 = INSTALL_DIR / "setupm1.py"
    if not setup_m1.exists():
        sys.exit("setupm1.py not found; ensure repository is current.")
    run([sys.executable, str(setup_m1)], cwd=INSTALL_DIR)
    dist_app = INSTALL_DIR / "dist" / APP_NAME
    if not dist_app.exists():
        sys.exit("Build failed: dist app not found.")
    return dist_app


def install_app(dist_app: Path):
    if TARGET_APP.exists():
        shutil.rmtree(TARGET_APP)
    TARGET_APP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(dist_app, TARGET_APP)


def launch_app():
    subprocess.Popen(["open", str(TARGET_APP)])


def main():
    ensure_arm_macos()
    print("✓ Apple Silicon macOS detected")
    ensure_repo()
    print("✓ Repository ready at", INSTALL_DIR)
    ensure_deps()
    print("✓ Dependencies installed")
    dist_app = build_app()
    print("✓ App built at", dist_app)
    install_app(dist_app)
    print("✓ Installed to /Applications")
    launch_app()
    print("✓ Launching app…")


if __name__ == "__main__":
    main()
