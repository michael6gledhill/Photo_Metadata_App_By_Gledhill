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
    QTableWidgetItem, QCheckBox, QGroupBox, QFormLayout, QTabWidget
)
from PySide6.QtCore import Qt, QSize, QMimeData, QPoint, QItemSelectionModel
from PySide6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QFont, QPixmap

from metadata_handler import MetadataManager, TemplateManager, NamingEngine

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
            tag = self.exif_table.item(row, 0).text().strip()
            value = self.exif_table.item(row, 1).text().strip()
            if tag and value:
                exif_data[tag] = value
        
        xmp_data = {}
        for row in range(self.xmp_table.rowCount()):
            prop = self.xmp_table.item(row, 0).text().strip()
            value = self.xmp_table.item(row, 1).text().strip()
            if prop and value:
                xmp_data[prop] = value
        
        if not exif_data and not xmp_data:
            QMessageBox.warning(self, "Error", "Please add at least one EXIF tag or XMP property.")
            return
        
        if self.is_editing:
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
        
        self.selected_files = []
        self.selected_template = None
        self.selected_naming = None
        self.last_operation = None
        self.preview_index = 0
        
        self.init_ui()
        self.setAcceptDrops(True)
        
        logger.info("Photo Metadata Editor started")
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
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
