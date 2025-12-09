#!/usr/bin/env python3
"""
GUI for Photo Metadata Editor.
macOS/Linux/Windows compatible.
"""

import sys
import json
import shutil
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QTextEdit, QDialog, QSplitter,
    QProgressDialog, QMessageBox, QAbstractItemView, QLineEdit, QTableWidget, 
    QTableWidgetItem, QCheckBox, QGroupBox, QFormLayout, QTabWidget, QToolBar, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QMimeData, QPoint, QItemSelectionModel, Signal, QObject
from PySide6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QFont, QPixmap

from metadata_handler import MetadataManager, TemplateManager, NamingEngine
from update_checker import UpdateChecker

logger = logging.getLogger(__name__)


class TemplateDialog(QDialog):
    """Dialog for creating/editing templates."""
    
    def __init__(self, parent=None, template_manager=None, template_name=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.template_name = template_name
        self.is_editing = template_name is not None
        self.init_ui()
        if self.is_editing:
            self.load_template(template_name)
    
    def init_ui(self):
        self.setWindowTitle("Edit Template" if self.is_editing else "Create Template")
        self.setGeometry(100, 100, 600, 500)
        
        layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Template Name:"))
        self.name_input = QLineEdit()
        if self.is_editing:
            self.name_input.setReadOnly(True)
        name_layout.addWidget(self.name_input)
        
        if self.is_editing:
            self.rename_input = QLineEdit()
            self.rename_input.setPlaceholderText("Enter new name to rename...")
            name_layout.addWidget(QLabel("Rename to:"))
            name_layout.addWidget(self.rename_input)
        
        layout.addLayout(name_layout)
        
        layout.addWidget(QLabel("EXIF Tags:"))
        self.exif_table = QTableWidget(0, 2)
        self.exif_table.setHorizontalHeaderLabels(["Tag", "Value"])
        layout.addWidget(self.exif_table)
        
        exif_btn_layout = QHBoxLayout()
        add_exif_btn = QPushButton("Add EXIF Tag")
        add_exif_btn.clicked.connect(self.add_exif_row)
        remove_exif_btn = QPushButton("Remove")
        remove_exif_btn.clicked.connect(lambda: self.remove_row(self.exif_table))
        exif_btn_layout.addWidget(add_exif_btn)
        exif_btn_layout.addWidget(remove_exif_btn)
        layout.addLayout(exif_btn_layout)
        
        layout.addWidget(QLabel("XMP Properties:"))
        self.xmp_table = QTableWidget(0, 2)
        self.xmp_table.setHorizontalHeaderLabels(["Property", "Value"])
        layout.addWidget(self.xmp_table)
        
        xmp_btn_layout = QHBoxLayout()
        add_xmp_btn = QPushButton("Add XMP Property")
        add_xmp_btn.clicked.connect(self.add_xmp_row)
        remove_xmp_btn = QPushButton("Remove")
        remove_xmp_btn.clicked.connect(lambda: self.remove_row(self.xmp_table))
        xmp_btn_layout.addWidget(add_xmp_btn)
        xmp_btn_layout.addWidget(remove_xmp_btn)
        layout.addLayout(xmp_btn_layout)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Template")
        save_btn.clicked.connect(self.save_template)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        
        if self.is_editing:
            export_btn = QPushButton("Export as JSON")
            export_btn.clicked.connect(self.export_template)
            button_layout.addWidget(export_btn)
        
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.add_exif_row()
        self.add_xmp_row()
    
    def add_exif_row(self):
        row = self.exif_table.rowCount()
        self.exif_table.insertRow(row)
        self.exif_table.setItem(row, 0, QTableWidgetItem(""))
        self.exif_table.setItem(row, 1, QTableWidgetItem(""))
    
    def add_xmp_row(self):
        row = self.xmp_table.rowCount()
        self.xmp_table.insertRow(row)
        self.xmp_table.setItem(row, 0, QTableWidgetItem(""))
        self.xmp_table.setItem(row, 1, QTableWidgetItem(""))
    
    def remove_row(self, table: QTableWidget):
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
    
    def load_template(self, template_name: str):
        templates = self.template_manager.get_templates()
        if template_name in templates:
            template = templates[template_name]
            self.name_input.setText(template_name)
            
            for tag, value in template.get('exif', {}).items():
                row = self.exif_table.rowCount()
                self.exif_table.insertRow(row)
                self.exif_table.setItem(row, 0, QTableWidgetItem(tag))
                self.exif_table.setItem(row, 1, QTableWidgetItem(str(value)))
            
            for prop, value in template.get('xmp', {}).items():
                row = self.xmp_table.rowCount()
                self.xmp_table.insertRow(row)
                self.xmp_table.setItem(row, 0, QTableWidgetItem(prop))
                self.xmp_table.setItem(row, 1, QTableWidgetItem(str(value)))
    
    def save_template(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a template name.")
            return
        
        exif_data = {}
        for row in range(self.exif_table.rowCount()):
            tag = self.exif_table.item(row, 0)
            value = self.exif_table.item(row, 1)
            if tag and value and tag.text().strip() and value.text().strip():
                exif_data[tag.text().strip()] = value.text().strip()
        
        xmp_data = {}
        for row in range(self.xmp_table.rowCount()):
            prop = self.xmp_table.item(row, 0)
            value = self.xmp_table.item(row, 1)
            if prop and value and prop.text().strip() and value.text().strip():
                xmp_data[prop.text().strip()] = value.text().strip()
        
        if not exif_data and not xmp_data:
            QMessageBox.warning(self, "Error", "Please add at least one EXIF tag or XMP property.")
            return
        
        if self.is_editing:
            # Check if renaming
            new_name = self.rename_input.text().strip() if hasattr(self, 'rename_input') else ""
            if new_name and new_name != name:
                if self.template_manager.get_templates().get(new_name):
                    QMessageBox.warning(self, "Error", f"Template '{new_name}' already exists.")
                    return
                # Delete old, save as new name
                if self.template_manager.delete_template(name):
                    if self.template_manager.save_template(new_name, exif_data, xmp_data):
                        QMessageBox.information(self, "Success", f"Template renamed to '{new_name}' and updated!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save renamed template.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to rename template.")
            else:
                # Update existing
                if self.template_manager.delete_template(name):
                    if self.template_manager.save_template(name, exif_data, xmp_data):
                        QMessageBox.information(self, "Success", f"Template '{name}' updated!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save template.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to update template.")
        else:
            if self.template_manager.save_template(name, exif_data, xmp_data):
                QMessageBox.information(self, "Success", f"Template '{name}' saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save template.")
    
    def export_template(self):
        """Export template as JSON file."""
        name = self.name_input.text().strip()
        templates = self.template_manager.get_templates()
        
        if name not in templates:
            QMessageBox.warning(self, "Error", f"Template '{name}' not found.")
            return
        
        template_data = templates[name]
        export_data = {
            "name": name,
            "exif": template_data.get("exif", {}),
            "xmp": template_data.get("xmp", {})
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Template", f"{name}.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                QMessageBox.information(self, "Success", f"Template exported to {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export template: {str(e)}")


class ImportDialog(QDialog):
    """Dialog for importing templates or naming conventions."""
    
    def __init__(self, import_type: str, parent=None):
        super().__init__(parent)
        self.import_type = import_type
        self.import_data = None
        self.init_ui()
    
    def init_ui(self):
        type_name = "Template" if self.import_type == 'template' else "Naming Convention"
        self.setWindowTitle(f"Import {type_name}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        instructions = QLabel(f"Import a {type_name.lower()} by selecting a JSON file or pasting JSON below.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        file_btn = QPushButton("Select JSON File...")
        file_btn.clicked.connect(self.select_file)
        layout.addWidget(file_btn)
        
        separator = QLabel("— OR —")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)
        
        layout.addWidget(QLabel("Paste JSON here:"))
        self.json_text = QTextEdit()
        self.json_text.setPlaceholderText("Paste your JSON here...")
        layout.addWidget(self.json_text)
        
        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.do_import)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.json_text.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")
    
    def do_import(self):
        json_text = self.json_text.toPlainText().strip()
        
        if not json_text:
            QMessageBox.warning(self, "No Data", "Please select a file or paste JSON.")
            return
        
        try:
            self.import_data = json.loads(json_text)
            
            if self.import_type == 'template':
                if 'name' not in self.import_data:
                    raise ValueError("Template must have a 'name' field")
            else:
                if 'name' not in self.import_data or 'pattern' not in self.import_data:
                    raise ValueError("Naming convention must have 'name' and 'pattern' fields")
            
            self.accept()
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Invalid JSON", f"Failed to parse JSON: {str(e)}")
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Format", str(e))


class NamingDialog(QDialog):
    """Dialog for creating/editing naming conventions."""
    
    def __init__(self, parent=None, template_manager=None, naming_name=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.naming_name = naming_name
        self.is_editing = naming_name is not None
        self.init_ui()
        if self.is_editing:
            self.load_naming(naming_name)
    
    def init_ui(self):
        self.setWindowTitle("Edit Naming Convention" if self.is_editing else "Create Naming Convention")
        self.setGeometry(100, 100, 600, 300)
        
        layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Convention Name:"))
        self.name_input = QLineEdit()
        if self.is_editing:
            self.name_input.setReadOnly(True)
        name_layout.addWidget(self.name_input)
        
        if self.is_editing:
            self.rename_input = QLineEdit()
            self.rename_input.setPlaceholderText("Enter new name to rename...")
            name_layout.addWidget(QLabel("Rename to:"))
            name_layout.addWidget(self.rename_input)
        
        layout.addLayout(name_layout)
        
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("{userid}_{date}_{original_name}")
        pattern_layout.addWidget(self.pattern_input)
        layout.addLayout(pattern_layout)
        
        info = QLabel("Tokens: {date}, {datetime:%Y%m%d_%H%M%S}, {title}, {camera_model}, {sequence:03d}, {original_name}, {userid}")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Convention")
        save_btn.clicked.connect(self.save_convention)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        
        if self.is_editing:
            export_btn = QPushButton("Export as JSON")
            export_btn.clicked.connect(self.export_naming)
            button_layout.addWidget(export_btn)
        
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_naming(self, naming_name: str):
        namings = self.template_manager.get_naming_conventions()
        if naming_name in namings:
            naming = namings[naming_name]
            self.name_input.setText(naming_name)
            self.pattern_input.setText(naming.get('pattern', ''))
    
    def save_convention(self):
        name = self.name_input.text().strip()
        pattern = self.pattern_input.text().strip()
        
        if not name or not pattern:
            QMessageBox.warning(self, "Error", "Please enter both name and pattern.")
            return
        
        if self.is_editing:
            # Check if renaming
            new_name = self.rename_input.text().strip() if hasattr(self, 'rename_input') else ""
            if new_name and new_name != name:
                if self.template_manager.get_naming_conventions().get(new_name):
                    QMessageBox.warning(self, "Error", f"Naming convention '{new_name}' already exists.")
                    return
                # Delete old, save as new name
                if self.template_manager.delete_naming(name):
                    if self.template_manager.save_naming(new_name, pattern):
                        QMessageBox.information(self, "Success", f"Naming convention renamed to '{new_name}' and updated!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save renamed convention.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to rename convention.")
            else:
                # Update existing
                if self.template_manager.delete_naming(name):
                    if self.template_manager.save_naming(name, pattern):
                        QMessageBox.information(self, "Success", f"Naming convention '{name}' updated!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to update.")
        else:
            if self.template_manager.save_naming(name, pattern):
                QMessageBox.information(self, "Success", f"Naming convention '{name}' saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save.")
    
    def export_naming(self):
        """Export naming convention as JSON file."""
        name = self.name_input.text().strip()
        namings = self.template_manager.get_naming_conventions()
        
        if name not in namings:
            QMessageBox.warning(self, "Error", f"Naming convention '{name}' not found.")
            return
        
        naming_data = namings[name]
        export_data = {
            "name": name,
            "pattern": naming_data.get("pattern", "")
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Naming Convention", f"{name}.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                QMessageBox.information(self, "Success", f"Naming convention exported to {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export naming convention: {str(e)}")


class MetadataViewDialog(QDialog):
    """Dialog for viewing metadata."""
    
    def __init__(self, parent=None, file_path: str = "", metadata: Dict = None):
        super().__init__(parent)
        self.file_path = file_path
        self.metadata = metadata or {}
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Metadata Viewer - {Path(self.file_path).name}")
        self.setGeometry(100, 100, 700, 600)
        
        layout = QVBoxLayout()
        
        tabs = QTabWidget()
        
        # EXIF tab
        exif_table = QTableWidget()
        exif_table.setColumnCount(2)
        exif_table.setHorizontalHeaderLabels(["Tag", "Value"])
        exif_data = self.metadata.get('exif', {})
        exif_table.setRowCount(len(exif_data))
        for row, (tag, value) in enumerate(exif_data.items()):
            exif_table.setItem(row, 0, QTableWidgetItem(str(tag)))
            exif_table.setItem(row, 1, QTableWidgetItem(str(value)[:200]))
        exif_table.resizeColumnsToContents()
        tabs.addTab(exif_table, "EXIF")
        
        # XMP tab
        xmp_table = QTableWidget()
        xmp_table.setColumnCount(2)
        xmp_table.setHorizontalHeaderLabels(["Property", "Value"])
        xmp_data = self.metadata.get('xmp', {})
        xmp_table.setRowCount(len(xmp_data))
        for row, (prop, value) in enumerate(xmp_data.items()):
            xmp_table.setItem(row, 0, QTableWidgetItem(str(prop)))
            xmp_table.setItem(row, 1, QTableWidgetItem(str(value)[:200]))
        xmp_table.resizeColumnsToContents()
        tabs.addTab(xmp_table, "XMP")

        # JSON tab
        json_view = QTextEdit()
        json_view.setReadOnly(True)
        json_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        json_view.setFontFamily("Menlo")
        json_view.setFontPointSize(10)
        json_text = json.dumps({
            'exif': exif_data,
            'xmp': xmp_data
        }, indent=2, ensure_ascii=False)
        json_view.setText(json_text)
        tabs.addTab(json_view, "JSON")
        
        layout.addWidget(tabs)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class PhotoMetadataEditor(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Metadata Editor")
        self.setGeometry(100, 100, 1400, 900)
        
        self.metadata_manager = MetadataManager()
        self.template_manager = TemplateManager()
        self.naming_engine = NamingEngine()
        self.update_checker = UpdateChecker()
        
        self.selected_files = []
        self.selected_template = None
        self.selected_naming = None
        self.last_operation = None
        self.preview_index = 0
        self.update_available = False
        
        self.init_ui()
        self.setAcceptDrops(True)
        
        # Check for updates in background
        self.check_for_updates_background()
        
        logger.info("Photo Metadata Editor started")
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Create toolbar (align controls to the right/top area)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        # Add stretch spacer first so following widgets sit on the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Update status label (compact)
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("font-size: 11px; margin-right: 4px;")
        toolbar.addWidget(self.update_status_label)

        # Info button (links to GitHub Pages homepage)
        info_btn = QPushButton("ℹ️")
        info_btn.setToolTip("Help & Documentation")
        info_btn.setMaximumWidth(32)
        info_btn.setMaximumHeight(24)
        info_btn.setStyleSheet("padding: 2px; font-size: 13px;")
        info_btn.clicked.connect(self.open_documentation)
        toolbar.addWidget(info_btn)

        # Update button
        self.update_btn = QPushButton("🔄")
        self.update_btn.setToolTip("Check for Updates")
        self.update_btn.setMaximumWidth(32)
        self.update_btn.setMaximumHeight(24)
        self.update_btn.setStyleSheet("padding: 2px; font-size: 13px;")
        self.update_btn.clicked.connect(self.handle_update)
        toolbar.addWidget(self.update_btn)
        
        main_layout = QHBoxLayout()
        
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Selected Files:"))
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.file_list_widget.setMaximumHeight(100)
        self.file_list_widget.itemSelectionChanged.connect(self.update_preview)
        file_layout.addWidget(self.file_list_widget)
        
        open_btn = QPushButton("Open Files")
        open_btn.clicked.connect(self.open_files)
        file_layout.addWidget(open_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_files)
        file_layout.addWidget(clear_btn)
        
        left_layout.addLayout(file_layout)
        
        # Operations
        control_group = QGroupBox("Operations")
        control_layout = QVBoxLayout()
        
        for btn_text, callback in [
            ("Create Template", self.create_template),
            ("Create Naming", self.create_naming),
            ("View Metadata", self.view_metadata),
            ("Delete Metadata", self.delete_metadata),
            ("Undo Last", self.undo_last),
        ]:
            btn = QPushButton(btn_text)
            btn.clicked.connect(callback)
            control_layout.addWidget(btn)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        self.merge_checkbox = QCheckBox("Merge metadata (don't overwrite)")
        options_layout.addWidget(self.merge_checkbox)
        self.dry_run_checkbox = QCheckBox("Dry run (preview only)")
        options_layout.addWidget(self.dry_run_checkbox)
        options_group.setLayout(options_layout)
        left_layout.addWidget(options_group)
        
        # Image Preview
        preview_group = QGroupBox("Image Preview")
        preview_layout = QVBoxLayout()
        self.image_preview_label = QLabel("No image selected")
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setMinimumHeight(180)
        self.image_preview_label.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        preview_layout.addWidget(self.image_preview_label)
        
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(QPushButton("Prev", clicked=self.preview_prev))
        nav_layout.addWidget(QPushButton("Next", clicked=self.preview_next))
        preview_layout.addLayout(nav_layout)
        preview_group.setLayout(preview_layout)
        left_layout.addWidget(preview_group)
        
        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        
        # Right panel - Templates and Naming
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Templates
        templates_group = QGroupBox("Templates")
        templates_layout = QVBoxLayout()
        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        templates_layout.addWidget(self.template_list)
        
        template_btns = QHBoxLayout()
        template_btns.addWidget(QPushButton("Import", clicked=self.import_template))
        template_btns.addWidget(QPushButton("Edit", clicked=self.edit_template))
        template_btns.addWidget(QPushButton("Export", clicked=self.export_template_main))
        template_btns.addWidget(QPushButton("Remove", clicked=self.delete_template))
        templates_layout.addLayout(template_btns)
        templates_group.setLayout(templates_layout)
        right_layout.addWidget(templates_group)
        
        # Naming
        naming_group = QGroupBox("Naming Conventions")
        naming_layout = QVBoxLayout()
        self.naming_list = QListWidget()
        self.naming_list.itemSelectionChanged.connect(self.on_naming_selected)
        naming_layout.addWidget(self.naming_list)
        
        naming_btns = QHBoxLayout()
        naming_btns.addWidget(QPushButton("Import", clicked=self.import_naming))
        naming_btns.addWidget(QPushButton("Edit", clicked=self.edit_naming))
        naming_btns.addWidget(QPushButton("Export", clicked=self.export_naming_main))
        naming_btns.addWidget(QPushButton("Remove", clicked=self.delete_naming))
        naming_layout.addLayout(naming_btns)
        naming_group.setLayout(naming_layout)
        right_layout.addWidget(naming_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)
        
        right_panel.setLayout(right_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        # Main layout
        main_layout.addWidget(splitter)
        
        # Apply button and status
        main_vertical = QVBoxLayout()
        main_vertical.addLayout(main_layout)
        
        apply_btn = QPushButton("APPLY TEMPLATE & RENAME")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
            }
        """)
        apply_btn.clicked.connect(self.apply_template)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        
        main_vertical.addWidget(apply_btn)
        main_vertical.addWidget(self.status_text)
        
        central.setLayout(main_vertical)
        self.statusBar().showMessage(f"Using: {self.metadata_manager.method}")
        
        self.refresh_templates()
        self.refresh_namings()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files(files)
    
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Image Files", "",
            "Image Files (*.jpg *.jpeg *.tiff *.tif *.png);;All Files (*)"
        )
        if files:
            self.add_files(files)
    
    def add_files(self, files: List[str]):
        for file in files:
            if Path(file).exists() and Path(file).is_file():
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    item = QListWidgetItem(Path(file).name)
                    item.setData(Qt.ItemDataRole.UserRole, file)
                    self.file_list_widget.addItem(item)
        
        self.log_status(f"Added {len(files)} file(s)")
        self.preview_index = 0
        self.update_preview()
    
    def clear_files(self):
        self.selected_files.clear()
        self.file_list_widget.clear()
        self.preview_index = 0
        self.update_preview()
    
    def create_template(self):
        dialog = TemplateDialog(self, self.template_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_templates()
            self.log_status("Template created")
    
    def create_naming(self):
        dialog = NamingDialog(self, self.template_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_namings()
            self.log_status("Naming convention created")
    
    def edit_template(self):
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template.")
            return
        
        template_name = current_item.text()
        dialog = TemplateDialog(self, self.template_manager, template_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_templates()
            self.log_status(f"Template '{template_name}' updated")
    
    def edit_naming(self):
        current_item = self.naming_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a naming convention.")
            return
        
        naming_name = current_item.text()
        dialog = NamingDialog(self, self.template_manager, naming_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_namings()
            self.log_status(f"Naming '{naming_name}' updated")
    
    def import_template(self):
        dialog = ImportDialog('template', self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, message = self.template_manager.import_template(dialog.import_data)
            if success:
                self.refresh_templates()
                self.log_status(message)
            else:
                QMessageBox.critical(self, "Import Failed", message)
    
    def import_naming(self):
        dialog = ImportDialog('naming', self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, message = self.template_manager.import_naming(dialog.import_data)
            if success:
                self.refresh_namings()
                self.log_status(message)
            else:
                QMessageBox.critical(self, "Import Failed", message)
    
    def export_template_main(self):
        """Export selected template as JSON from main window."""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to export.")
            return
        
        name = current_item.text()
        templates = self.template_manager.get_templates()
        
        if name not in templates:
            QMessageBox.warning(self, "Error", f"Template '{name}' not found.")
            return
        
        template_data = templates[name]
        export_data = {
            "name": name,
            "exif": template_data.get("exif", {}),
            "xmp": template_data.get("xmp", {})
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Template", f"{name}.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.log_status(f"Template exported to {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export template: {str(e)}")
    
    def export_naming_main(self):
        """Export selected naming convention as JSON from main window."""
        current_item = self.naming_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a naming convention to export.")
            return
        
        name = current_item.text()
        namings = self.template_manager.get_naming_conventions()
        
        if name not in namings:
            QMessageBox.warning(self, "Error", f"Naming convention '{name}' not found.")
            return
        
        naming_data = namings[name]
        export_data = {
            "name": name,
            "pattern": naming_data.get("pattern", "")
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Naming Convention", f"{name}.json", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                self.log_status(f"Naming convention exported to {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export naming convention: {str(e)}")
    
    def delete_template(self):
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template.")
            return
        
        if QMessageBox.question(self, "Confirm", "Delete this template?") == QMessageBox.StandardButton.Yes:
            if self.template_manager.delete_template(current_item.text()):
                self.refresh_templates()
                self.log_status("Template deleted")
    
    def delete_naming(self):
        current_item = self.naming_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a naming convention.")
            return
        
        if QMessageBox.question(self, "Confirm", "Delete this naming convention?") == QMessageBox.StandardButton.Yes:
            if self.template_manager.delete_naming(current_item.text()):
                self.refresh_namings()
                self.log_status("Naming convention deleted")
    
    def view_metadata(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select a file.")
            return
        
        file_path = self.selected_files[0]
        metadata = self.metadata_manager.get_metadata(file_path)
        dialog = MetadataViewDialog(self, file_path, metadata)
        dialog.exec()
    
    def delete_metadata(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select at least one file.")
            return
        
        if QMessageBox.question(self, "Confirm", f"Delete metadata from {len(self.selected_files)} file(s)?") != QMessageBox.StandardButton.Yes:
            return
        
        progress = QProgressDialog("Deleting metadata...", None, 0, len(self.selected_files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        success_count = 0
        for i, file_path in enumerate(self.selected_files):
            if self.metadata_manager.delete_metadata(file_path):
                success_count += 1
            progress.setValue(i + 1)
            QApplication.processEvents()
        
        progress.close()
        self.log_status(f"Metadata deletion complete: {success_count}/{len(self.selected_files)} successful")
    
    def on_template_selected(self):
        current_item = self.template_list.currentItem()
        if current_item:
            self.selected_template = current_item.text()
            self.update_preview()
    
    def on_naming_selected(self):
        current_item = self.naming_list.currentItem()
        if current_item:
            self.selected_naming = current_item.text()
            self.update_preview()
    
    def refresh_templates(self):
        self.template_list.clear()
        for name in self.template_manager.get_templates().keys():
            self.template_list.addItem(name)
    
    def refresh_namings(self):
        self.naming_list.clear()
        for name in self.template_manager.get_naming_conventions().keys():
            self.naming_list.addItem(name)
    
    def _get_primary_file(self) -> Optional[str]:
        if not self.selected_files:
            return None
        self.preview_index = max(0, min(self.preview_index, len(self.selected_files) - 1))
        file_path = self.selected_files[self.preview_index]
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self.file_list_widget.setCurrentItem(item, QItemSelectionModel.ClearAndSelect)
                break
        return file_path
    
    def _update_image_preview(self):
        file_path = self._get_primary_file()
        if not file_path:
            self.image_preview_label.setText("No image selected")
            self.image_preview_label.setPixmap(QPixmap())
            return
        
        pix = QPixmap(file_path)
        if pix.isNull():
            self.image_preview_label.setText("Preview unavailable")
            self.image_preview_label.setPixmap(QPixmap())
            return
        
        target_size = self.image_preview_label.size()
        if pix.width() > target_size.width() or pix.height() > target_size.height():
            pix = pix.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self.image_preview_label.setPixmap(pix)
        
        metadata = self.metadata_manager.get_metadata(file_path)
        tooltip_lines = [f"File: {Path(file_path).name}"]
        for key in ['Artist', 'Model', 'DateTime', 'ImageDescription']:
            if key in metadata.get('exif', {}):
                tooltip_lines.append(f"EXIF {key}: {metadata['exif'][key]}")
        for key in ['dc:creator', 'dc:description']:
            if key in metadata.get('xmp', {}):
                tooltip_lines.append(f"XMP {key}: {metadata['xmp'][key]}")
        self.image_preview_label.setToolTip("\n".join(tooltip_lines))
    
    def preview_next(self):
        if self.selected_files:
            self.preview_index = (self.preview_index + 1) % len(self.selected_files)
            self.update_preview()
    
    def preview_prev(self):
        if self.selected_files:
            self.preview_index = (self.preview_index - 1) % len(self.selected_files)
            self.update_preview()
    
    def update_preview(self):
        preview = []
        self._update_image_preview()
        
        if self.selected_template:
            template = self.template_manager.get_templates().get(self.selected_template, {})
            preview.append(f"Template: {self.selected_template}\n")
            preview.append("EXIF:\n")
            for key, value in template.get('exif', {}).items():
                preview.append(f"  {key}: {value}\n")
            preview.append("\nXMP:\n")
            for key, value in template.get('xmp', {}).items():
                preview.append(f"  {key}: {value}\n")
        
        file_path = self._get_primary_file()
        if self.selected_naming and file_path:
            convention = self.template_manager.get_naming_conventions().get(self.selected_naming, {})
            pattern = convention.get('pattern', '')
            preview.append(f"\nNaming: {self.selected_naming}\n")
            preview.append(f"Pattern: {pattern}\n")
            
            metadata = self.metadata_manager.get_metadata(file_path)
            new_name = self.naming_engine.generate_filename(pattern, file_path, metadata, 1)
            preview.append(f"Result: {new_name}\n")
        
        self.preview_text.setText(''.join(preview))
    
    def apply_template(self):
        if not self.selected_files or not self.selected_template or not self.selected_naming:
            QMessageBox.warning(self, "Warning", "Please select files, template, and naming convention.")
            return
        
        templates = self.template_manager.get_templates()
        template = self.template_manager._normalize_template_data(dict(templates.get(self.selected_template, {})))
        
        conventions = self.template_manager.get_naming_conventions()
        convention = conventions.get(self.selected_naming, {})
        pattern = convention.get('pattern', '')
        
        merge = self.merge_checkbox.isChecked()
        dry_run = self.dry_run_checkbox.isChecked()
        
        action = "preview" if dry_run else "apply"
        if QMessageBox.question(self, "Confirm", f"Apply template to {len(self.selected_files)} file(s)? ({action})") != QMessageBox.StandardButton.Yes:
            return
        
        progress = QProgressDialog("Processing...", None, 0, len(self.selected_files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        success_count = 0
        rename_map = {}
        
        for i, file_path in enumerate(self.selected_files):
            try:
                metadata = self.metadata_manager.get_metadata(file_path)
                new_filename = self.naming_engine.generate_filename(pattern, file_path, metadata, i + 1)
                new_path = Path(file_path).parent / new_filename
                
                if new_path.exists() and str(new_path) != file_path:
                    base = new_path.stem
                    ext = new_path.suffix
                    counter = 1
                    while new_path.exists():
                        new_path = Path(file_path).parent / f"{base}_{counter}{ext}"
                        counter += 1
                
                if not dry_run:
                    exif = template.get('exif', {})
                    xmp = template.get('xmp', {})
                    
                    if self.metadata_manager.set_metadata(file_path, exif, xmp, merge):
                        if str(new_path) != file_path:
                            shutil.move(file_path, new_path)
                            rename_map[file_path] = str(new_path)
                        success_count += 1
                        self.log_status(f"✓ {Path(file_path).name} → {new_path.name}")
                    else:
                        self.log_status(f"✗ Failed: {Path(file_path).name}")
                else:
                    self.log_status(f"[DRY RUN] {Path(file_path).name} → {new_path.name}")
                    success_count += 1
            
            except Exception as e:
                self.log_status(f"✗ Error: {Path(file_path).name} - {str(e)}")
                logger.error(f"Error processing {file_path}: {e}\n{traceback.format_exc()}")
            
            progress.setValue(i + 1)
            QApplication.processEvents()
        
        progress.close()
        self._refresh_after_renames(rename_map)
        
        if dry_run:
            self.log_status(f"\n[DRY RUN] Would process {success_count}/{len(self.selected_files)} files")
        else:
            self.log_status(f"\nComplete: {success_count}/{len(self.selected_files)} successful")
    
    def undo_last(self):
        QMessageBox.information(self, "Info", "Undo not yet implemented.")
    
    def _refresh_after_renames(self, rename_map: Dict[str, str]):
        if not rename_map:
            return
        
        self.selected_files = [rename_map.get(path, path) for path in self.selected_files]
        
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            old_path = item.data(Qt.ItemDataRole.UserRole)
            if old_path in rename_map:
                new_path = rename_map[old_path]
                item.setData(Qt.ItemDataRole.UserRole, new_path)
                item.setText(Path(new_path).name)
        
        self.update_preview()
    
    def log_status(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        logger.info(message)
    
    def check_for_updates_background(self):
        """Check for updates in background and update UI if available."""
        def callback(result):
            try:
                update_available, latest_version = result
                if update_available:
                    self.update_available = True
                    self.update_btn.setText("✨")
                    self.update_btn.setToolTip(f"Update Available ({latest_version})")
                    self.update_btn.setStyleSheet("padding: 2px; font-size: 14px; background-color: #ff9800; color: white; border-radius: 4px;")
                    self.update_status_label.setText(f"✨ v{latest_version}")
                elif latest_version:
                    self.update_status_label.setText(f"✓ v{latest_version}")
                else:
                    self.update_status_label.setText("⚠️ Offline")
                    if self.update_checker.last_error:
                        logger.warning(f"Update check (background) failed: {self.update_checker.last_error}")
            except Exception as e:
                logger.error(f"Update check callback crashed: {e}")
                self.update_status_label.setText("⚠️ Error")
        
        try:
            self.update_checker.check_for_updates_async(callback)
        except Exception as e:
            logger.error(f"Failed to start update check: {e}")
    
    def open_documentation(self):
        """Open GitHub Pages homepage in browser."""
        import webbrowser
        # Point to index.html which will be the homepage
        url = self.update_checker.get_github_pages_url()
        webbrowser.open(url)
    
    def handle_update(self):
        """Handle update button click."""
        if not self.update_available:
            # Just check for updates
            self.log_status("Checking for updates...")
            self.update_btn.setEnabled(False)
            
            def callback(result):
                try:
                    update_available, latest_version = result
                    self.update_btn.setEnabled(True)
                    
                    if update_available:
                        self.update_available = True
                        self.update_btn.setText("✨")
                        self.update_btn.setToolTip(f"Update Available ({latest_version})")
                        self.update_btn.setStyleSheet("padding: 2px; font-size: 14px; background-color: #ff9800; color: white; border-radius: 4px;")
                        self.log_status(f"✨ Update {latest_version} available! Click the ✨ button to install.")
                        self.update_status_label.setText(f"✨ v{latest_version}")
                    elif latest_version:
                        self.log_status(f"✓ Online latest is v{latest_version}; you have v{self.update_checker.current_version}")
                        self.update_status_label.setText(f"✓ v{latest_version}")
                    else:
                        err = self.update_checker.last_error or "no response"
                        self.log_status(f"⚠️ Update check failed: {err}")
                        self.update_status_label.setText("⚠️ Offline")
                except Exception as e:
                    logger.error(f"Manual update check callback crashed: {e}")
                    self.update_btn.setEnabled(True)
                    self.log_status(f"⚠️ Update check error: {e}")
            
            try:
                self.update_checker.check_for_updates_async(callback)
            except Exception as e:
                logger.error(f"Failed to start manual update check: {e}")
                self.update_btn.setEnabled(True)
                self.log_status(f"⚠️ Could not check for updates: {e}")
        else:
            # Perform update
            reply = QMessageBox.question(
                self,
                "Install Update?",
                f"An update to version {self.update_checker.latest_version} is available.\n\n"
                "The app will close after the update completes and restart automatically.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.perform_update()
    
    def perform_update(self):
        """Perform the actual update by re-running the installer."""
        progress = QProgressDialog(
            "Updating application...",
            None,
            0, 0,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Installing Update")
        progress.setCancelButton(None)
        progress.show()
        QApplication.processEvents()
        
        try:
            # Determine which installer to run based on platform/architecture
            if sys.platform == "darwin":
                import platform
                if platform.machine().lower() in {"arm64", "aarch64"}:
                    # Apple Silicon: run install_m1.py
                    installer_url = "https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_m1.py"
                    subprocess.run(
                        ["curl", "-fsSL", installer_url],
                        stdout=subprocess.PIPE,
                        check=True,
                        timeout=30
                    )
                    # Run the installer in the background (it will rebuild and relaunch)
                    subprocess.Popen(
                        ["bash", "-c", f"curl -fsSL {installer_url} | python3"],
                        start_new_session=True
                    )
                else:
                    # Intel Mac: run install_gui.sh
                    installer_url = "https://raw.githubusercontent.com/michael6gledhill/Photo_Metadata_App_By_Gledhill/main/install_gui.sh"
                    subprocess.Popen(
                        ["bash", "-c", f"curl -fsSL {installer_url} | bash"],
                        start_new_session=True
                    )
            else:
                # Windows/Linux: pull and restart
                repo_path = Path(__file__).parent
                result = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Git pull failed: {result.stderr}")
            
            success = True
        except Exception as e:
            logger.error(f"Update failed: {e}")
            success = False
        
        progress.close()
        
        if success:
            self.log_status("✓ Update started successfully!")
            QMessageBox.information(
                self,
                "Update In Progress",
                "The update installer is running in the background.\n\n"
                "This app will now close. The updated version will launch automatically when ready."
            )
            
            # Close the app; the installer will relaunch the new version
            QApplication.quit()
        else:
            QMessageBox.critical(
                self,
                "Update Failed",
                "Failed to install the update. Please check your internet connection "
                "and try again.\n\nYou can also visit the GitHub repository manually."
            )
            self.log_status("✗ Update failed")



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PhotoMetadataEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    main()
