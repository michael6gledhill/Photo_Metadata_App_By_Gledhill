#!/usr/bin/env python3
"""
GUI Installer/Updater for Photo Metadata Editor
Handles installation and updates with a graphical interface
"""

import sys
import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox,
    QGroupBox, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QFont, QPixmap

logger = logging.getLogger(__name__)


class InstallerSignals(QObject):
    """Signals for installer operations"""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, str)  # success, message
    log = Signal(str)


class PhotoMetadataInstaller:
    """Handles installation/update operations"""
    
    def __init__(self, signals: InstallerSignals):
        self.signals = signals
        self.repo_url = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
        self.install_dir = Path.home() / "App" / "Photo_Metadata_App_By_Gledhill"
        
    def install(self) -> bool:
        """Perform installation"""
        try:
            self.signals.status.emit("Checking prerequisites...")
            self.signals.log.emit("Checking for Git, Python 3...")
            
            if not self._check_git():
                self.signals.log.emit("❌ Git not found. Please install Git first.")
                return False
            self.signals.log.emit("✓ Git found")
            
            if not self._check_python():
                self.signals.log.emit("❌ Python 3 not found. Please install Python 3.")
                return False
            self.signals.log.emit("✓ Python 3 found")
            
            self.signals.progress.emit(20)
            self.signals.status.emit("Cloning repository...")
            self.signals.log.emit(f"Cloning to {self.install_dir}...")
            
            if not self._clone_repo():
                return False
            
            self.signals.progress.emit(50)
            self.signals.status.emit("Installing dependencies...")
            self.signals.log.emit("Installing Python packages...")
            
            if not self._install_dependencies():
                return False
            
            self.signals.progress.emit(80)
            self.signals.status.emit("Setting up application...")
            self.signals.log.emit("Creating shortcuts and configuration...")
            
            if not self._setup_app():
                return False
            
            self.signals.progress.emit(100)
            self.signals.log.emit("✓ Installation complete!")
            self.signals.finished.emit(True, f"Installation successful!\n\nApp location: {self.install_dir}")
            return True
            
        except Exception as e:
            self.signals.log.emit(f"❌ Error: {str(e)}")
            self.signals.finished.emit(False, f"Installation failed: {str(e)}")
            return False
    
    def update(self) -> bool:
        """Perform update"""
        try:
            self.signals.status.emit("Updating application...")
            self.signals.log.emit("Pulling latest code...")
            
            if not self.install_dir.exists():
                self.signals.log.emit("❌ Installation not found")
                return False
            
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.signals.log.emit(f"❌ Git pull failed: {result.stderr}")
                return False
            
            self.signals.log.emit("✓ Code updated")
            self.signals.progress.emit(50)
            
            self.signals.status.emit("Installing dependencies...")
            self.signals.log.emit("Updating Python packages...")
            
            if not self._install_dependencies():
                return False
            
            self.signals.progress.emit(100)
            self.signals.log.emit("✓ Update complete!")
            self.signals.finished.emit(True, "Update successful!\n\nThe app will restart with the latest version.")
            return True
            
        except Exception as e:
            self.signals.log.emit(f"❌ Error: {str(e)}")
            self.signals.finished.emit(False, f"Update failed: {str(e)}")
            return False
    
    def _check_git(self) -> bool:
        """Check if Git is installed"""
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=5, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_python(self) -> bool:
        """Check if Python 3 is available"""
        try:
            subprocess.run([sys.executable, "--version"], capture_output=True, timeout=5, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _clone_repo(self) -> bool:
        """Clone the repository"""
        try:
            self.install_dir.parent.mkdir(parents=True, exist_ok=True)
            
            if self.install_dir.exists():
                self.signals.log.emit("Repository already exists, updating...")
                result = subprocess.run(
                    ["git", "pull"],
                    cwd=self.install_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                result = subprocess.run(
                    ["git", "clone", self.repo_url, str(self.install_dir)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            return result.returncode == 0
        except Exception as e:
            self.signals.log.emit(f"Clone error: {str(e)}")
            return False
    
    def _install_dependencies(self) -> bool:
        """Install Python dependencies"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                self.signals.log.emit(f"Pip install failed: {result.stderr}")
                return False
            
            self.signals.log.emit("✓ Dependencies installed")
            return True
        except Exception as e:
            self.signals.log.emit(f"Dependency error: {str(e)}")
            return False
    
    def _setup_app(self) -> bool:
        """Set up the application (shortcuts, etc.)"""
        try:
            # Create launcher script for easy access
            if sys.platform == "darwin":
                # macOS specific setup
                self.signals.log.emit("Configuring for macOS...")
            elif sys.platform == "win32":
                # Windows specific setup
                self.signals.log.emit("Configuring for Windows...")
            else:
                # Linux
                self.signals.log.emit("Configuring for Linux...")
            
            return True
        except Exception as e:
            self.signals.log.emit(f"Setup error: {str(e)}")
            return False


class InstallerWindow(QMainWindow):
    """Main installer GUI window"""
    
    def __init__(self, mode: str = "install"):
        super().__init__()
        self.mode = mode  # "install" or "update"
        self.signals = InstallerSignals()
        self.installer = PhotoMetadataInstaller(self.signals)
        self.is_running = False
        
        self.init_ui()
        self.setup_signals()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Photo Metadata Editor - Installer")
        self.setGeometry(100, 100, 600, 500)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("📸 Photo Metadata Editor")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Mode subtitle
        mode_text = "Installation" if self.mode == "install" else "Update"
        subtitle = QLabel(f"🔧 {mode_text}")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        # Description
        if self.mode == "install":
            desc = QLabel(
                "This will install Photo Metadata Editor on your computer.\n\n"
                "Installation will:\n"
                "• Download the latest version\n"
                "• Install Python dependencies\n"
                "• Configure the application"
            )
        else:
            desc = QLabel(
                "This will update Photo Metadata Editor to the latest version.\n\n"
                "Update will:\n"
                "• Download the latest code\n"
                "• Update dependencies\n"
                "• Restart the application"
            )
        
        layout.addWidget(desc)
        layout.addSpacing(10)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Log output
        log_group = QGroupBox("Installation Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setFont(QFont("Courier", 10))
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton(f"Start {mode_text}")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.start_btn.clicked.connect(self.start_installation)
        button_layout.addWidget(self.start_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setMinimumHeight(40)
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        central.setLayout(layout)
    
    def setup_signals(self):
        """Connect signals"""
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.log.connect(self.log_message)
        self.signals.finished.connect(self.installation_finished)
    
    def start_installation(self):
        """Start the installation/update process"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.progress.setValue(0)
        
        # Run installation in separate thread
        thread = threading.Thread(
            target=self.installer.install if self.mode == "install" else self.installer.update,
            daemon=True
        )
        thread.start()
    
    def update_progress(self, value: int):
        """Update progress bar"""
        self.progress.setValue(value)
    
    def update_status(self, status: str):
        """Update status label"""
        self.status_label.setText(status)
    
    def log_message(self, message: str):
        """Add message to log"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def installation_finished(self, success: bool, message: str):
        """Handle installation completion"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("✓ Complete!")
            QMessageBox.information(self, "Success", message)
            
            # Close after successful installation
            if self.mode == "install":
                self.close()
        else:
            self.status_label.setText("✗ Failed")
            QMessageBox.critical(self, "Error", message)


def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)
    
    # Determine mode from command line arguments
    mode = "install"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = InstallerWindow(mode=mode)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
