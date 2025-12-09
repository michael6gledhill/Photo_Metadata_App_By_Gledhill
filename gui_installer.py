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
    QGroupBox
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class InstallerSignals(QObject):
    """Signals for installer operations"""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, str)  # success, message
    log = Signal(str)
    step_state = Signal(int, str)  # step index, state: pending|running|ok|fail


class PhotoMetadataInstaller:
    """Handles installation/update operations"""
    
    def __init__(self, signals: InstallerSignals):
        self.signals = signals
        self.repo_url = "https://github.com/michael6gledhill/Photo_Metadata_App_By_Gledhill.git"
        self.install_dir = Path.home() / "App" / "Photo_Metadata_App_By_Gledhill"
        self.app_name = "Photo Metadata Editor.app"
    
    def install(self) -> bool:
        """Perform installation"""
        return self._run_steps(mode="install")
    
    def update(self) -> bool:
        """Perform update"""
        return self._run_steps(mode="update")
    
    # --- Step pipeline ---
    def get_steps(self, mode: str):
        steps = [
            ("Check prerequisites", self._step_prereqs),
            ("Fetch latest code", self._step_clone_or_pull),
            ("Install dependencies", self._step_install_dependencies),
        ]
        if sys.platform == "darwin":
            if self._supports_py2app():
                steps.append(("Build macOS app", self._step_build_app))
                steps.append(("Install to Applications", self._step_install_app))
            else:
                # Fallback: create a launcher script when py2app is unsupported
                steps.append(("Create launcher", self._step_create_launcher))
        else:
            steps.append(("Create launcher", self._step_create_launcher))
        return steps
    
    def _run_steps(self, mode: str) -> bool:
        steps = self.get_steps(mode)
        total = len(steps)
        try:
            for idx, (title, fn) in enumerate(steps):
                self.signals.status.emit(title)
                self.signals.step_state.emit(idx, "running")
                ok = fn(mode)
                if not ok:
                    self.signals.step_state.emit(idx, "fail")
                    self.signals.finished.emit(False, f"Failed: {title}")
                    return False
                self.signals.step_state.emit(idx, "ok")
                progress = int(((idx + 1) / total) * 100)
                self.signals.progress.emit(progress)
            self.signals.finished.emit(True, "All steps completed successfully.")
            return True
        except Exception as e:
            self.signals.log.emit(f"❌ Error: {e}")
            self.signals.finished.emit(False, f"Error: {e}")
            return False
    
    # --- Individual steps ---
    def _step_prereqs(self, mode: str) -> bool:
        self.signals.log.emit("Checking for Git...")
        if not self._check_git():
            self.signals.log.emit("❌ Git not found. Please install Git first.")
            return False
        self.signals.log.emit("✓ Git found")

        self.signals.log.emit("Checking for Python 3...")
        if not self._check_python():
            self.signals.log.emit("❌ Python 3 not found. Please install Python 3.")
            return False
        self.signals.log.emit("✓ Python 3 found")

        if sys.platform == "darwin" and not self._supports_py2app():
            self.signals.log.emit("⚠️ py2app is not supported on this Python version. Will skip app bundle and create a launcher instead.")
        return True

    def _step_clone_or_pull(self, mode: str) -> bool:
        try:
            self.install_dir.parent.mkdir(parents=True, exist_ok=True)
            if self.install_dir.exists():
                self.signals.log.emit("Updating existing repository...")
                result = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=self.install_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                self.signals.log.emit("Cloning repository...")
                result = subprocess.run(
                    ["git", "clone", self.repo_url, str(self.install_dir)],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            if result.returncode != 0:
                self.signals.log.emit(f"❌ Git error: {result.stderr}")
                return False
            self.signals.log.emit("✓ Repository ready")
            return True
        except Exception as e:
            self.signals.log.emit(f"Clone error: {str(e)}")
            return False

    def _step_install_dependencies(self, mode: str) -> bool:
        try:
            cmds = [
                [sys.executable, "-m", "pip", "install", "-q", "--upgrade", "pip"],
                [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            ]
            if sys.platform == "darwin" and self._supports_py2app():
                cmds.append([sys.executable, "-m", "pip", "install", "-q", "py2app"])
            for cmd in cmds:
                result = subprocess.run(
                    cmd,
                    cwd=self.install_dir,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                if result.returncode != 0:
                    self.signals.log.emit(f"❌ Command failed: {' '.join(cmd)}\n{result.stderr}")
                    return False
            self.signals.log.emit("✓ Dependencies installed")
            return True
        except Exception as e:
            self.signals.log.emit(f"Dependency error: {str(e)}")
            return False

    def _step_build_app(self, mode: str) -> bool:
        if sys.platform != "darwin":
            return True
        if not self._supports_py2app():
            return True
        try:
            self.signals.log.emit("Building macOS app (py2app)...")
            result = subprocess.run(
                [sys.executable, "setup.py", "py2app"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                self.signals.log.emit(f"❌ Build failed: {result.stderr}")
                return False
            self.signals.log.emit("✓ Build complete")
            return True
        except Exception as e:
            self.signals.log.emit(f"Build error: {str(e)}")
            return False

    def _step_install_app(self, mode: str) -> bool:
        if sys.platform != "darwin":
            return True
        if not self._supports_py2app():
            return True
        try:
            dist_app = self.install_dir / "dist" / self.app_name
            target_app = Path("/Applications") / self.app_name
            if not dist_app.exists():
                self.signals.log.emit("❌ Built app not found. Build may have failed.")
                return False
            if target_app.exists():
                self.signals.log.emit("Removing existing app...")
                subprocess.run(["rm", "-rf", str(target_app)], check=False)
            self.signals.log.emit("Copying to /Applications (may prompt for permission)...")
            result = subprocess.run(["cp", "-R", str(dist_app), str(target_app)], capture_output=True, text=True)
            if result.returncode != 0:
                self.signals.log.emit("⚠️ Could not copy to /Applications. You may need to run manually:\n"
                                      f"sudo cp -R '{dist_app}' '{target_app}'")
                return False
            self.signals.log.emit("✓ Installed to /Applications")
            return True
        except Exception as e:
            self.signals.log.emit(f"Install error: {str(e)}")
            return False

    def _step_create_launcher(self, mode: str) -> bool:
        try:
            if sys.platform == "win32":
                script = self.install_dir / "run_app.bat"
                content = (
                    "@echo off\n"
                    "cd /d \"%~dp0\"\n"
                    "python main.py\n"
                )
                script.write_text(content, encoding="utf-8")
                self.signals.log.emit(f"✓ Launcher created: {script}")
            else:
                script = self.install_dir / "run_app.sh"
                content = (
                    "#!/usr/bin/env bash\n"
                    "cd \"$(dirname \"$0\")\"\n"
                    "python3 main.py\n"
                )
                script.write_text(content, encoding="utf-8")
                script.chmod(0o755)
                self.signals.log.emit(f"✓ Launcher created: {script}")
            return True
        except Exception as e:
            self.signals.log.emit(f"Launcher error: {str(e)}")
            return False

    # --- Helpers ---
    def _check_git(self) -> bool:
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=5, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_python(self) -> bool:
        try:
            subprocess.run([sys.executable, "--version"], capture_output=True, timeout=5, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _supports_py2app(self) -> bool:
        """Return True if current Python is a version py2app supports (<=3.12 best-effort)."""
        # py2app support for 3.13+/3.14 is unreliable; skip to avoid build crashes
        return sys.version_info < (3, 13)


class InstallerWindow(QMainWindow):
    """Main installer GUI window"""
    
    def __init__(self, mode: str = "install"):
        super().__init__()
        self.mode = mode  # "install" or "update"
        self.signals = InstallerSignals()
        self.installer = PhotoMetadataInstaller(self.signals)
        self.is_running = False
        self.step_labels = []
        self.steps = self.installer.get_steps(self.mode)
        self.progress_target = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(50)  # 20 FPS smoothness
        self.progress_timer.timeout.connect(self._progress_tick)
        
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

        # Step list
        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout()
        for title, _fn in self.steps:
            lbl = QLabel(f"⏺ {title}")
            lbl.setStyleSheet("color: #666;")
            steps_layout.addWidget(lbl)
            self.step_labels.append(lbl)
        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)
        
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
        self.progress_timer.start()
    
    def setup_signals(self):
        """Connect signals"""
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.signals.log.connect(self.log_message)
        self.signals.finished.connect(self.installation_finished)
        self.signals.step_state.connect(self.update_step_state)
    
    def start_installation(self):
        """Start the installation/update process"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.log_text.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_target = 0
        self.status_label.setText("Starting...")
        for lbl in self.step_labels:
            lbl.setText(lbl.text().replace("✅", "⏺").replace("❌", "⏺").replace("⏳", "⏺"))
            lbl.setStyleSheet("color: #666;")
        
        # Run installation in separate thread
        thread = threading.Thread(
            target=self.installer.install if self.mode == "install" else self.installer.update,
            daemon=True
        )
        thread.start()
    
    def update_progress(self, value: int):
        """Update progress target (smooth animation handled by timer)"""
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
        self.progress_target = max(0, min(100, value))
    
    def update_status(self, status: str):
        """Update status label"""
        self.status_label.setText(status)

    def update_step_state(self, idx: int, state: str):
        if idx < 0 or idx >= len(self.step_labels):
            return
        lbl = self.step_labels[idx]
        base_text = lbl.text()
        title = base_text.split(' ', 1)[-1]
        if state == "running":
            lbl.setText(f"⏳ {title}")
            lbl.setStyleSheet("color: #007bff;")
            self.progress.setRange(0, 0)  # indeterminate during long step
        elif state == "ok":
            lbl.setText(f"✅ {title}")
            lbl.setStyleSheet("color: #2e7d32; font-weight: 600;")
            self.progress.setRange(0, 100)
        elif state == "fail":
            lbl.setText(f"❌ {title}")
            lbl.setStyleSheet("color: #c62828; font-weight: 600;")
            self.progress.setRange(0, 100)
        else:
            lbl.setText(f"⏺ {title}")
            lbl.setStyleSheet("color: #666;")
    
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

    def _progress_tick(self):
        # If indeterminate, do nothing (marquee handled by QProgressBar)
        if self.progress.maximum() == 0:
            return
        current = self.progress.value()
        if current < self.progress_target:
            self.progress.setValue(min(current + 1, self.progress_target))


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
