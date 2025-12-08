#!/usr/bin/env python3
"""
Photo Metadata Editor - A PySide6 GUI application for editing EXIF and XMP metadata in photos.

USAGE:
    python3 photo_meta_editor.py

INSTALLATION:
    1. Create a virtual environment: python3 -m venv venv
    2. Activate: source venv/bin/activate (macOS/Linux) or venv\\Scripts\\activate (Windows)
    3. Install dependencies: pip install -r requirements.txt
    4. Run: python3 photo_meta_editor.py

FEATURES:
    - View and edit EXIF and XMP metadata for JPEG, TIFF, and PNG files
    - Create and save metadata templates as JSON
    - Create and save flexible naming conventions with token replacement
    - Apply templates to single or multiple files with atomic writes
    - Delete all metadata from photos
    - Batch operations with progress tracking
    - Undo last operation
    - Automatic exiftool detection (preferred) with pure-Python fallback
    - Drag-and-drop file selection
    - Dry-run mode to preview changes

EXAMPLE TEMPLATES (auto-created on first run):
    1. "Portrait Template" - Artist, Copyright, Description for portrait photography
    2. "Travel Log" - Creator, Keywords for travel documentation

EXAMPLE NAMING CONVENTIONS (auto-created on first run):
    1. "{date}_{title}_{sequence:03d}" - Date-based with sequence number
    2. "{datetime:%Y%m%d_%H%M%S}_{camera_model}" - Timestamp with camera model

SUPPORTED TOKENS:
    {title} - Image title/description
    {date} - Date in YYYY-MM-DD format
    {datetime:%Y%m%d_%H%M%S} - Custom datetime format (strftime)
    {camera_model} - Camera model from EXIF
    {sequence:03d} - Sequence number with padding
    {original_name} - Original filename without extension
    {userid} - Current system user

KEYBOARD SHORTCUTS:
    Ctrl+O - Open file
    Ctrl+S - Save template
    Ctrl+Z - Undo last operation
"""

import sys
import os
import json
import shutil
import subprocess
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
import traceback

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QTextEdit, QDialog, QFrame, QSplitter,
    QProgressDialog, QMessageBox, QStatusBar, QListWidgetItem, QAbstractItemView,
    QLineEdit, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox, QCheckBox,
    QScrollArea, QGroupBox, QFormLayout, QTabWidget
)
from PySide6.QtCore import Qt, QSize, QMimeData, QPoint, QTimer, QItemSelectionModel
from PySide6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent, QFont, QPixmap

# Optional imports for metadata handling
try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

try:
    from libxmp import XMPMeta
    HAS_LIBXMP = True
except (ImportError, Exception) as e:
    # Catches both ImportError and libxmp.ExempiLoadError
    HAS_LIBXMP = False
    if "Exempi" not in str(e):
        logger.debug(f"libxmp not available: {e}")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class MetadataManager:
    """Handles metadata reading/writing using exiftool or Python libraries."""
    
    def __init__(self):
        """Initialize metadata manager, detect available tools."""
        self.use_exiftool = self._detect_exiftool()
        self.method = "exiftool" if self.use_exiftool else "python-libraries"
        logger.info(f"Metadata handling: {self.method}")
    
    def _detect_exiftool(self) -> bool:
        """Check if exiftool is available in PATH."""
        try:
            result = subprocess.run(['exiftool', '-ver'], capture_output=True, timeout=2)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract EXIF and XMP metadata from a file.
        
        Returns:
            dict with 'exif' and 'xmp' keys, each containing tag->value mappings
        """
        metadata = {'exif': {}, 'xmp': {}, 'method': self.method}
        
        try:
            if self.use_exiftool:
                metadata.update(self._get_metadata_exiftool(file_path))
            else:
                metadata.update(self._get_metadata_python(file_path))
        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")
        
        return metadata
    
    def _get_metadata_exiftool(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using exiftool."""
        try:
            # Get EXIF
            result = subprocess.run(
                ['exiftool', '-j', file_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data:
                    raw = data[0]
                    exif = {}
                    xmp = {}
                    for key, value in raw.items():
                        if key == 'SourceFile':
                            continue
                        if key.lower().startswith('xmp'):
                            xmp[key] = value
                        else:
                            exif[key] = value
                    return {'exif': exif, 'xmp': xmp}
        except Exception as e:
            logger.warning(f"exiftool error: {e}")
        
        return {'exif': {}, 'xmp': {}}
    
    def _get_metadata_python(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using Python libraries."""
        exif_data = {}
        xmp_data = {}
        
        # Try EXIF via piexif
        if HAS_PIEXIF:
            try:
                exif_dict = piexif.load(file_path)
                for ifd in exif_dict:
                    for tag in exif_dict[ifd]:
                        tag_name = piexif.TAGS[ifd][tag]["name"]
                        value = exif_dict[ifd][tag]
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8', errors='ignore')
                            except:
                                value = str(value)
                        exif_data[tag_name] = value
            except Exception as e:
                logger.debug(f"piexif read error: {e}")
        
        # Try XMP via libxmp
        if HAS_LIBXMP:
            try:
                xmp = XMPMeta.from_file(file_path)
                for prop in xmp.properties:
                    xmp_data[prop] = xmp[prop]
            except Exception as e:
                logger.debug(f"libxmp read error: {e}")
        
        return {'exif': exif_data, 'xmp': xmp_data}
    
    def set_metadata(self, file_path: str, exif_data: Dict = None, xmp_data: Dict = None,
                     merge: bool = False) -> bool:
        """
        Write EXIF and XMP metadata to a file.
        
        Args:
            file_path: Path to image file
            exif_data: Dictionary of EXIF tags to set
            xmp_data: Dictionary of XMP properties to set
            merge: If True, merge with existing; if False, overwrite
        
        Returns:
            True if successful, False otherwise
        """
        if not exif_data and not xmp_data:
            return True
        
        # Use temp file for atomic writes
        temp_fd, temp_path = tempfile.mkstemp(suffix=Path(file_path).suffix)
        try:
            os.close(temp_fd)
            shutil.copy2(file_path, temp_path)
            
            success = False
            if self.use_exiftool:
                success = self._set_metadata_exiftool(temp_path, exif_data, xmp_data, merge)
            else:
                success = self._set_metadata_python(temp_path, exif_data, xmp_data, merge)
            
            if success:
                shutil.move(temp_path, file_path)
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False
    
    def _set_metadata_exiftool(self, file_path: str, exif_data: Dict = None,
                               xmp_data: Dict = None, merge: bool = False) -> bool:
        """Write metadata using exiftool."""
        try:
            cmd = ['exiftool', '-overwrite_original']

            # If not merging, clear everything first. If merging, keep existing metadata.
            if not merge:
                cmd.append('-all=')

            # Add EXIF tags (explicit EXIF group)
            if exif_data:
                for key, value in exif_data.items():
                    if isinstance(value, (list, tuple)):
                        value = ', '.join(map(str, value))
                    cmd.append(f'-EXIF:{key}={value}')

            # Add XMP tags (map dc:creator -> XMP-dc:creator)
            if xmp_data:
                for key, value in xmp_data.items():
                    if isinstance(value, (list, tuple)):
                        value = ', '.join(map(str, value))
                    if ':' in key:
                        prefix, prop = key.split(':', 1)
                        cmd.append(f'-XMP-{prefix}:{prop}={value}')
                    else:
                        cmd.append(f'-XMP:{key}={value}')

            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"exiftool write error: {e}")
            return False
    
    def _set_metadata_python(self, file_path: str, exif_data: Dict = None,
                             xmp_data: Dict = None, merge: bool = False) -> bool:
        """Write metadata using Python libraries."""
        try:
            # Write EXIF using piexif
            if HAS_PIEXIF and exif_data:
                try:
                    exif_dict = piexif.load(file_path) if merge else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

                    # Map common tag names to piexif constants
                    tag_map = {
                        "Artist": ("0th", piexif.ImageIFD.Artist),
                        "Copyright": ("0th", piexif.ImageIFD.Copyright),
                        "ImageDescription": ("0th", piexif.ImageIFD.ImageDescription),
                        "Software": ("0th", piexif.ImageIFD.Software),
                        "DateTime": ("0th", piexif.ImageIFD.DateTime),
                        "DateTimeOriginal": ("Exif", piexif.ExifIFD.DateTimeOriginal),
                        "DateTimeDigitized": ("Exif", piexif.ExifIFD.DateTimeDigitized),
                        "Make": ("0th", piexif.ImageIFD.Make),
                        "Model": ("0th", piexif.ImageIFD.Model),
                        "UserComment": ("Exif", piexif.ExifIFD.UserComment),
                    }

                    for key, value in exif_data.items():
                        if key in tag_map:
                            if isinstance(value, str):
                                try:
                                    value_bytes = value.encode('utf-8')
                                except Exception:
                                    value_bytes = str(value).encode('utf-8', errors='ignore')
                            else:
                                value_bytes = value
                            if isinstance(value_bytes, bytes) and key != "UserComment":
                                # Most EXIF ascii fields expect bytes ending with null; piexif handles raw bytes
                                pass
                            if key == "UserComment" and isinstance(value_bytes, bytes):
                                # UserComment should start with charset code; use ASCII prefix
                                value_bytes = b"ASCII\x00\x00\x00" + value_bytes
                            ifd_name, tag_id = tag_map[key]
                            exif_dict[ifd_name][tag_id] = value_bytes

                    piexif.insert(piexif.dump(exif_dict), file_path)
                except Exception as e:
                    logger.warning(f"piexif write error: {e}")
            
            # Write XMP using libxmp
            if HAS_LIBXMP and xmp_data:
                try:
                    xmp = XMPMeta.from_file(file_path) if merge else XMPMeta()
                    
                    for key, value in xmp_data.items():
                        # Normalize lists to comma-separated strings for simplicity
                        if isinstance(value, (list, tuple)):
                            value = ', '.join(map(str, value))
                        xmp[key] = value
                    
                    xmp.serialize_to_file(file_path)
                except Exception as e:
                    logger.warning(f"libxmp write error: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Python libraries write error: {e}")
            return False
    
    def delete_metadata(self, file_path: str) -> bool:
        """Remove all EXIF and XMP metadata from a file."""
        temp_fd, temp_path = tempfile.mkstemp(suffix=Path(file_path).suffix)
        try:
            os.close(temp_fd)
            shutil.copy2(file_path, temp_path)
            
            success = False
            if self.use_exiftool:
                try:
                    cmd = ['exiftool', '-all=', '-overwrite_original', temp_path]
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    success = result.returncode == 0
                except Exception as e:
                    logger.error(f"exiftool delete error: {e}")
            else:
                # Python fallback: overwrite with minimal metadata
                if HAS_PIEXIF:
                    try:
                        piexif.insert(piexif.dump({"0th": {}, "Exif": {}, "GPS": {}}), temp_path)
                        success = True
                    except Exception as e:
                        logger.warning(f"piexif delete error: {e}")
            
            if success:
                shutil.move(temp_path, file_path)
                return True
            else:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False


class TemplateManager:
    """Manages template storage and retrieval."""
    
    def __init__(self):
        """Initialize template manager."""
        self.template_dir = Path.home() / '.photo_meta_editor' / 'templates'
        self.naming_dir = Path.home() / '.photo_meta_editor' / 'naming'
        self.undo_dir = Path.home() / '.photo_meta_editor' / 'undo'
        
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.naming_dir.mkdir(parents=True, exist_ok=True)
        self.undo_dir.mkdir(parents=True, exist_ok=True)
        
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default templates and naming conventions if they don't exist."""
        # Portrait Template
        portrait = {
            "name": "Portrait Template",
            "exif": {
                "Artist": "Photographer Name",
                "Copyright": "© 2025 Photographer Name",
                "ImageDescription": "Professional portrait photography"
            },
            "xmp": {
                "dc:creator": "Photographer Name",
                "dc:description": "Professional portrait",
                "photoshop:Headline": "Portrait Session"
            }
        }
        
        # Travel Log Template
        travel = {
            "name": "Travel Log",
            "exif": {
                "Artist": "Travel Photographer",
                "ImageDescription": "Travel documentation"
            },
            "xmp": {
                "dc:creator": "Travel Photographer",
                "dc:keywords": ["travel", "adventure", "documentation"]
            }
        }
        
        self._save_template_if_not_exists("portrait_template.json", portrait)
        self._save_template_if_not_exists("travel_template.json", travel)
        
        # Default naming conventions
        naming1 = {
            "name": "Date + Title",
            "pattern": "{date}_{title}_{sequence:03d}"
        }
        
        naming2 = {
            "name": "Timestamp + Camera",
            "pattern": "{datetime:%Y%m%d_%H%M%S}_{camera_model}"
        }
        
        self._save_naming_if_not_exists("date_title.json", naming1)
        self._save_naming_if_not_exists("timestamp_camera.json", naming2)
    
    def _save_template_if_not_exists(self, filename: str, template: Dict):
        """Save template if it doesn't already exist."""
        path = self.template_dir / filename
        if not path.exists():
            with open(path, 'w') as f:
                json.dump(template, f, indent=2)
    
    def _save_naming_if_not_exists(self, filename: str, naming: Dict):
        """Save naming convention if it doesn't already exist."""
        path = self.naming_dir / filename
        if not path.exists():
            with open(path, 'w') as f:
                json.dump(naming, f, indent=2)
    
    def get_templates(self) -> Dict[str, Dict]:
        """Get all saved templates."""
        templates = {}
        try:
            for file in self.template_dir.glob('*.json'):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        templates[data.get('name', file.stem)] = data
                except Exception as e:
                    logger.warning(f"Error loading template {file}: {e}")
        except Exception as e:
            logger.error(f"Error reading templates: {e}")
        
        return templates
    
    def get_naming_conventions(self) -> Dict[str, Dict]:
        """Get all saved naming conventions."""
        conventions = {}
        try:
            for file in self.naming_dir.glob('*.json'):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        conventions[data.get('name', file.stem)] = data
                except Exception as e:
                    logger.warning(f"Error loading naming convention {file}: {e}")
        except Exception as e:
            logger.error(f"Error reading naming conventions: {e}")
        
        return conventions
    
    def save_template(self, name: str, exif: Dict, xmp: Dict) -> bool:
        """Save a new template."""
        try:
            template = {
                "name": name,
                "exif": exif,
                "xmp": xmp
            }
            
            filename = name.lower().replace(' ', '_') + '.json'
            path = self.template_dir / filename
            
            with open(path, 'w') as f:
                json.dump(template, f, indent=2)
            
            logger.info(f"Template saved: {name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False
    
    def save_naming(self, name: str, pattern: str) -> bool:
        """Save a new naming convention."""
        try:
            naming = {
                "name": name,
                "pattern": pattern
            }
            
            filename = name.lower().replace(' ', '_') + '.json'
            path = self.naming_dir / filename
            
            with open(path, 'w') as f:
                json.dump(naming, f, indent=2)
            
            logger.info(f"Naming convention saved: {name}")
            return True
        except Exception as e:
            logger.error(f"Error saving naming convention: {e}")
            return False
    
    def delete_template(self, name: str) -> bool:
        """Delete a template."""
        try:
            for file in self.template_dir.glob('*.json'):
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('name') == name:
                        file.unlink()
                        return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
        
        return False
    
    def delete_naming(self, name: str) -> bool:
        """Delete a naming convention."""
        try:
            for file in self.naming_dir.glob('*.json'):
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('name') == name:
                        file.unlink()
                        return True
        except Exception as e:
            logger.error(f"Error deleting naming convention: {e}")
        
        return False
    
    def import_template(self, data: Dict) -> Tuple[bool, str]:
        """Import a template from JSON data.
        
        Args:
            data: Template data dictionary with 'name', 'exif', and 'xmp' keys
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate required keys
            if 'name' not in data:
                return False, "Template must have a 'name' field"
            
            name = data['name']
            exif = data.get('exif', {})
            xmp = data.get('xmp', {})
            
            # Save the template
            if self.save_template(name, exif, xmp):
                return True, f"Template '{name}' imported successfully"
            else:
                return False, "Failed to save template"
                
        except Exception as e:
            return False, f"Import error: {str(e)}"
    
    def import_naming(self, data: Dict) -> Tuple[bool, str]:
        """Import a naming convention from JSON data.
        
        Args:
            data: Naming convention data dictionary with 'name' and 'pattern' keys
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate required keys
            if 'name' not in data:
                return False, "Naming convention must have a 'name' field"
            if 'pattern' not in data:
                return False, "Naming convention must have a 'pattern' field"
            
            name = data['name']
            pattern = data['pattern']
            
            # Save the naming convention
            if self.save_naming(name, pattern):
                return True, f"Naming convention '{name}' imported successfully"
            else:
                return False, "Failed to save naming convention"
                
        except Exception as e:
            return False, f"Import error: {str(e)}"
    
    def save_undo(self, filename: str, original_name: str, metadata_backup: Dict):
        """Save undo information."""
        try:
            undo_data = {
                "timestamp": datetime.now().isoformat(),
                "filename": filename,
                "original_name": original_name,
                "metadata": metadata_backup
            }
            
            undo_file = self.undo_dir / f"undo_{datetime.now().timestamp()}.json"
            with open(undo_file, 'w') as f:
                json.dump(undo_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving undo data: {e}")


class NamingEngine:
    """Handles filename token replacement."""
    
    @staticmethod
    def generate_filename(pattern: str, file_path: str, metadata: Dict, sequence: int = 1) -> str:
        """
        Generate a new filename from a pattern and metadata.
        
        Args:
            pattern: Naming pattern with tokens like {date}, {title}, etc.
            file_path: Original file path
            metadata: Metadata dict with 'exif' and 'xmp' keys
            sequence: Sequence number for {sequence:Nd} tokens
        
        Returns:
            New filename with extension preserved
        """
        original_path = Path(file_path)
        extension = original_path.suffix
        original_name = original_path.stem
        
        # Extract metadata values
        exif = metadata.get('exif', {})
        xmp = metadata.get('xmp', {})
        
        # Map common EXIF keys
        title = exif.get('ImageDescription', xmp.get('dc:description', ''))
        date_str = exif.get('DateTime', datetime.now().strftime('%Y-%m-%d'))
        camera_model = exif.get('Model', 'unknown')
        
        # Parse date if present
        try:
            if isinstance(date_str, str) and ':' in date_str:
                date_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            else:
                date_obj = datetime.now()
        except:
            date_obj = datetime.now()
        
        # Replace tokens
        result = pattern
        result = result.replace('{title}', str(title)[:50])  # Limit title length
        result = result.replace('{date}', date_obj.strftime('%Y-%m-%d'))
        result = result.replace('{camera_model}', str(camera_model)[:30])
        result = result.replace('{original_name}', original_name)
        result = result.replace('{userid}', os.getenv('USER', 'user'))
        
        # Handle {datetime:%format} and {sequence:Nd}
        import re
        
        # DateTime with custom format
        datetime_match = re.search(r'\{datetime:([^}]+)\}', result)
        if datetime_match:
            fmt = datetime_match.group(1)
            try:
                result = result.replace(datetime_match.group(0), date_obj.strftime(fmt))
            except:
                pass
        
        # Sequence with padding
        sequence_match = re.search(r'\{sequence:(\d+)d\}', result)
        if sequence_match:
            padding = int(sequence_match.group(1))
            result = result.replace(sequence_match.group(0), str(sequence).zfill(padding))
        
        # Sanitize filename
        result = result.replace('/', '_').replace('\\', '_')
        result = result.replace(':', '_').replace('?', '')
        
        return result + extension


class TemplateDialog(QDialog):
    """Dialog for creating/editing templates."""
    
    def __init__(self, parent=None, template_manager=None, template_name=None):
        """Initialize template creation/editing dialog."""
        super().__init__(parent)
        self.template_manager = template_manager
        self.template_name = template_name
        self.is_editing = template_name is not None
        self.init_ui()
        if self.is_editing:
            self.load_template(template_name)
    
    def init_ui(self):
        """Build UI for template creation/editing."""
        self.setWindowTitle("Edit Template" if self.is_editing else "Create Template")
        self.setGeometry(100, 100, 600, 500)
        
        layout = QVBoxLayout()
        
        # Template name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Template Name:"))
        self.name_input = QLineEdit()
        if self.is_editing:
            self.name_input.setReadOnly(True)  # Prevent changing name when editing
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # EXIF section
        layout.addWidget(QLabel("EXIF Tags:"))
        self.exif_table = QTableWidget(0, 2)
        self.exif_table.setHorizontalHeaderLabels(["Tag", "Value"])
        layout.addWidget(self.exif_table)
        
        exif_btn_layout = QHBoxLayout()
        add_exif_btn = QPushButton("Add EXIF Tag")
        add_exif_btn.clicked.connect(self.add_exif_row)
        remove_exif_btn = QPushButton("Remove Selected")
        remove_exif_btn.clicked.connect(lambda: self.remove_row(self.exif_table))
        exif_btn_layout.addWidget(add_exif_btn)
        exif_btn_layout.addWidget(remove_exif_btn)
        layout.addLayout(exif_btn_layout)
        
        # XMP section
        layout.addWidget(QLabel("XMP Properties:"))
        self.xmp_table = QTableWidget(0, 2)
        self.xmp_table.setHorizontalHeaderLabels(["Property", "Value"])
        layout.addWidget(self.xmp_table)
        
        xmp_btn_layout = QHBoxLayout()
        add_xmp_btn = QPushButton("Add XMP Property")
        add_xmp_btn.clicked.connect(self.add_xmp_row)
        remove_xmp_btn = QPushButton("Remove Selected")
        remove_xmp_btn.clicked.connect(lambda: self.remove_row(self.xmp_table))
        xmp_btn_layout.addWidget(add_xmp_btn)
        xmp_btn_layout.addWidget(remove_xmp_btn)
        layout.addLayout(xmp_btn_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Template")
        save_btn.clicked.connect(self.save_template)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Add sample rows
        self.add_exif_row()
        self.add_xmp_row()
    
    def add_exif_row(self):
        """Add a row to the EXIF table."""
        row = self.exif_table.rowCount()
        self.exif_table.insertRow(row)
        self.exif_table.setItem(row, 0, QTableWidgetItem(""))
        self.exif_table.setItem(row, 1, QTableWidgetItem(""))
    
    def add_xmp_row(self):
        """Add a row to the XMP table."""
        row = self.xmp_table.rowCount()
        self.xmp_table.insertRow(row)
        self.xmp_table.setItem(row, 0, QTableWidgetItem(""))
        self.xmp_table.setItem(row, 1, QTableWidgetItem(""))
    
    def remove_row(self, table: QTableWidget):
        """Remove selected row from table."""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
    
    def load_template(self, template_name: str):
        """Load existing template for editing."""
        templates = self.template_manager.get_templates()
        if template_name in templates:
            template = templates[template_name]
            self.name_input.setText(template_name)
            
            # Load EXIF data
            exif_data = template.get('exif', {})
            for tag, value in exif_data.items():
                row = self.exif_table.rowCount()
                self.exif_table.insertRow(row)
                self.exif_table.setItem(row, 0, QTableWidgetItem(tag))
                self.exif_table.setItem(row, 1, QTableWidgetItem(str(value)))
            
            # Load XMP data
            xmp_data = template.get('xmp', {})
            for prop, value in xmp_data.items():
                row = self.xmp_table.rowCount()
                self.xmp_table.insertRow(row)
                self.xmp_table.setItem(row, 0, QTableWidgetItem(prop))
                self.xmp_table.setItem(row, 1, QTableWidgetItem(str(value)))
    
    def save_template(self):
        """Save the template."""
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
            # Delete old template and save updated version
            if self.template_manager.delete_template(name):
                if self.template_manager.save_template(name, exif_data, xmp_data):
                    QMessageBox.information(self, "Success", f"Template '{name}' updated successfully!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to save template.")
            else:
                QMessageBox.critical(self, "Error", "Failed to update template.")
        else:
            if self.template_manager.save_template(name, exif_data, xmp_data):
                QMessageBox.information(self, "Success", f"Template '{name}' saved successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save template.")


class ImportDialog(QDialog):
    """Dialog for importing templates or naming conventions."""
    
    def __init__(self, import_type: str, parent=None):
        """
        Args:
            import_type: Either 'template' or 'naming'
            parent: Parent widget
        """
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
        
        # Instructions
        instructions = QLabel(
            f"Import a {type_name.lower()} by selecting a JSON file or pasting JSON text below.\n\n"
            f"Expected format for {type_name.lower()}:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Format example
        example_text = QTextEdit()
        example_text.setReadOnly(True)
        example_text.setMaximumHeight(150)
        
        if self.import_type == 'template':
            example_text.setPlainText(
'''{
  "name": "My Template",
  "exif": {
    "Artist": "Your Name",
    "Copyright": "© 2025 Your Name"
  },
  "xmp": {
    "dc:creator": "Your Name",
    "dc:keywords": ["keyword1", "keyword2"]
  }
}''')
        else:
            example_text.setPlainText(
'''{
  "name": "My Naming Convention",
  "pattern": "{date}_{title}_{sequence:03d}"
}''')
        
        layout.addWidget(example_text)
        
        # File import button
        file_btn = QPushButton("Select JSON File...")
        file_btn.clicked.connect(self.select_file)
        layout.addWidget(file_btn)
        
        # Separator
        separator = QLabel("— OR —")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)
        
        # Text paste area
        paste_label = QLabel("Paste JSON here:")
        layout.addWidget(paste_label)
        
        self.json_text = QTextEdit()
        self.json_text.setPlaceholderText("Paste your JSON template here...")
        layout.addWidget(self.json_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.do_import)
        btn_layout.addWidget(import_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def select_file(self):
        """Open file dialog to select JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON File",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    json_text = f.read()
                    self.json_text.setPlainText(json_text)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {str(e)}")
    
    def do_import(self):
        """Parse and validate the JSON, then accept the dialog."""
        json_text = self.json_text.toPlainText().strip()
        
        if not json_text:
            QMessageBox.warning(self, "No Data", "Please select a file or paste JSON text.")
            return
        
        try:
            self.import_data = json.loads(json_text)
            
            # Validate structure
            if self.import_type == 'template':
                if 'name' not in self.import_data:
                    raise ValueError("Template must have a 'name' field")
            else:  # naming
                if 'name' not in self.import_data or 'pattern' not in self.import_data:
                    raise ValueError("Naming convention must have 'name' and 'pattern' fields")
            
            self.accept()
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Invalid JSON", f"Failed to parse JSON: {str(e)}")
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Format", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")


class NamingDialog(QDialog):
    """Dialog for creating/editing naming conventions."""
    
    def __init__(self, parent=None, template_manager=None, naming_name=None):
        """Initialize naming convention dialog."""
        super().__init__(parent)
        self.template_manager = template_manager
        self.naming_name = naming_name
        self.is_editing = naming_name is not None
        self.init_ui()
        if self.is_editing:
            self.load_naming(naming_name)
    
    def init_ui(self):
        """Build UI for naming convention creation/editing."""
        self.setWindowTitle("Edit Naming Convention" if self.is_editing else "Create Naming Convention")
        self.setGeometry(100, 100, 600, 300)
        
        layout = QVBoxLayout()
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Convention Name:"))
        self.name_input = QLineEdit()
        if self.is_editing:
            self.name_input.setReadOnly(True)  # Prevent changing name when editing
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Pattern
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("{userid}_{date}_{original_name}")
        pattern_layout.addWidget(self.pattern_input)
        layout.addLayout(pattern_layout)
        
        # Info label about custom text
        info_label = QLabel("💡 Tip: Mix tokens with custom text (e.g., {date}_ES-meeting_{sequence:03d})")
        info_label.setStyleSheet("color: #0066cc; font-style: italic;")
        layout.addWidget(info_label)
        
        # Help text
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setText(
            "Available tokens (mix with custom text):\n\n"
            "TOKENS:\n"
            "  {date} - YYYY-MM-DD format\n"
            "  {datetime:%Y%m%d_%H%M%S} - Custom datetime\n"
            "  {title} - Image title/description\n"
            "  {camera_model} - Camera model from EXIF\n"
            "  {sequence:03d} - Sequence number\n"
            "  {original_name} - Original filename\n"
            "  {userid} - System username\n\n"
            "EXAMPLES:\n"
            "  {userid}_{date}_{original_name}\n"
            "  {date}_ES-meeting_{sequence:03d}\n"
            "  {date}_Project-ABC_{title}"
        )
        help_text.setMaximumHeight(200)
        layout.addWidget(help_text)
        
        # Buttons
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
        """Load existing naming convention for editing."""
        namings = self.template_manager.get_namings()
        if naming_name in namings:
            naming = namings[naming_name]
            self.name_input.setText(naming_name)
            self.pattern_input.setText(naming.get('pattern', ''))
    
    def save_convention(self):
        """Save the naming convention."""
        name = self.name_input.text().strip()
        pattern = self.pattern_input.text().strip()
        
        if not name or not pattern:
            QMessageBox.warning(self, "Error", "Please enter both name and pattern.")
            return
        
        if self.is_editing:
            # Delete old naming and save updated version
            if self.template_manager.delete_naming(name):
                if self.template_manager.save_naming(name, pattern):
                    QMessageBox.information(self, "Success", f"Naming convention '{name}' updated!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to save naming convention.")
            else:
                QMessageBox.critical(self, "Error", "Failed to update naming convention.")
        else:
            if self.template_manager.save_naming(name, pattern):
                QMessageBox.information(self, "Success", f"Naming convention '{name}' saved!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save naming convention.")


class MetadataViewDialog(QDialog):
    """Dialog for viewing metadata."""
    
    def __init__(self, parent=None, file_path: str = "", metadata: Dict = None):
        """Initialize metadata view dialog."""
        super().__init__(parent)
        self.file_path = file_path
        self.metadata = metadata or {}
        self.init_ui()
    
    def init_ui(self):
        """Build UI for metadata viewing."""
        self.setWindowTitle(f"Metadata Viewer - {Path(self.file_path).name}")
        self.setGeometry(100, 100, 700, 600)
        
        layout = QVBoxLayout()
        
        # Tabs for EXIF and XMP
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
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class PhotoMetadataEditor(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize the main application window."""
        super().__init__()
        self.setWindowTitle("Photo Metadata Editor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize managers
        self.metadata_manager = MetadataManager()
        self.template_manager = TemplateManager()
        self.naming_engine = NamingEngine()
        
        # State
        self.selected_files = []
        self.selected_template = None
        self.selected_naming = None
        self.last_operation = None
        self.preview_index = 0
        
        # Build UI
        self.init_ui()
        self.setAcceptDrops(True)
        
        logger.info("Photo Metadata Editor started")
    
    def init_ui(self):
        """Build the main user interface."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout()
        
        # Top area - File selection
        top_area = QWidget()
        top_layout = QVBoxLayout()
        
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
        
        top_layout.addLayout(file_layout)
        top_area.setLayout(top_layout)
        
        # Left column - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        control_group = QGroupBox("Operations")
        control_layout = QVBoxLayout()
        
        create_template_btn = QPushButton("Create Template")
        create_template_btn.clicked.connect(self.create_template)
        control_layout.addWidget(create_template_btn)
        
        create_naming_btn = QPushButton("Create Naming Convention")
        create_naming_btn.clicked.connect(self.create_naming)
        control_layout.addWidget(create_naming_btn)
        
        view_metadata_btn = QPushButton("View Metadata")
        view_metadata_btn.clicked.connect(self.view_metadata)
        control_layout.addWidget(view_metadata_btn)
        
        delete_metadata_btn = QPushButton("Delete Metadata")
        delete_metadata_btn.clicked.connect(self.delete_metadata)
        control_layout.addWidget(delete_metadata_btn)
        
        undo_btn = QPushButton("Undo Last Operation")
        undo_btn.clicked.connect(self.undo_last)
        control_layout.addWidget(undo_btn)
        
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

        # Image Preview (selected file)
        preview_image_group = QGroupBox("Image Preview")
        preview_image_layout = QVBoxLayout()
        self.image_preview_label = QLabel("No image selected")
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setMinimumHeight(180)
        self.image_preview_label.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        self.image_preview_label.setScaledContents(False)
        preview_image_layout.addWidget(self.image_preview_label)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Prev")
        self.prev_btn.clicked.connect(self.preview_prev)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.preview_next)
        nav_layout.addWidget(self.next_btn)

        preview_image_layout.addLayout(nav_layout)
        preview_image_group.setLayout(preview_image_layout)
        left_layout.addWidget(preview_image_group)
        
        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        
        # Right column - Templates and Naming
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Templates
        templates_group = QGroupBox("Templates")
        templates_sublayout = QVBoxLayout()
        
        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        templates_sublayout.addWidget(self.template_list)
        
        template_btn_layout = QHBoxLayout()
        import_template_btn = QPushButton("Import")
        import_template_btn.clicked.connect(self.import_template)
        template_btn_layout.addWidget(import_template_btn)
        
        edit_template_btn = QPushButton("Edit")
        edit_template_btn.clicked.connect(self.edit_template)
        template_btn_layout.addWidget(edit_template_btn)
        
        delete_template_btn = QPushButton("Remove")
        delete_template_btn.clicked.connect(self.delete_template)
        template_btn_layout.addWidget(delete_template_btn)
        
        templates_sublayout.addLayout(template_btn_layout)
        
        templates_group.setLayout(templates_sublayout)
        right_layout.addWidget(templates_group)
        
        # Naming Conventions
        naming_group = QGroupBox("Naming Conventions")
        naming_sublayout = QVBoxLayout()
        
        self.naming_list = QListWidget()
        self.naming_list.itemSelectionChanged.connect(self.on_naming_selected)
        naming_sublayout.addWidget(self.naming_list)
        
        naming_btn_layout = QHBoxLayout()
        import_naming_btn = QPushButton("Import")
        import_naming_btn.clicked.connect(self.import_naming)
        naming_btn_layout.addWidget(import_naming_btn)
        
        edit_naming_btn = QPushButton("Edit")
        edit_naming_btn.clicked.connect(self.edit_naming)
        naming_btn_layout.addWidget(edit_naming_btn)
        
        delete_naming_btn = QPushButton("Remove")
        delete_naming_btn.clicked.connect(self.delete_naming)
        naming_btn_layout.addWidget(delete_naming_btn)
        
        naming_sublayout.addLayout(naming_btn_layout)
        
        naming_group.setLayout(naming_sublayout)
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
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        # Main vertical layout
        main_vertical = QVBoxLayout()
        main_vertical.addWidget(top_area)
        main_vertical.addWidget(splitter)
        
        # Bottom area - Apply button and status
        bottom_layout = QVBoxLayout()
        
        apply_btn = QPushButton("APPLY TEMPLATE & RENAME")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        apply_btn.clicked.connect(self.apply_template)
        bottom_layout.addWidget(apply_btn)
        
        # Status/Log area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        bottom_layout.addWidget(self.status_text)
        
        main_vertical.addLayout(bottom_layout)
        
        central.setLayout(main_vertical)
        
        # Status bar
        self.statusBar().showMessage(f"Using metadata method: {self.metadata_manager.method}")
        
        # Refresh lists
        self.refresh_templates()
        self.refresh_namings()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter for file drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop."""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files(files)
    
    def open_files(self):
        """Open file dialog to select image files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image Files",
            "",
            "Image Files (*.jpg *.jpeg *.tiff *.tif *.png);;All Files (*)"
        )
        if files:
            self.add_files(files)
    
    def add_files(self, files: List[str]):
        """Add files to the selected files list."""
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
        """Clear all selected files."""
        self.selected_files.clear()
        self.file_list_widget.clear()
        self.preview_index = 0
        self.update_preview()
    
    def create_template(self):
        """Open template creation dialog."""
        dialog = TemplateDialog(self, self.template_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_templates()
            self.log_status("Template created successfully")
    
    def create_naming(self):
        """Open naming convention dialog."""
        dialog = NamingDialog(self, self.template_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_namings()
            self.log_status("Naming convention created successfully")
    
    def edit_template(self):
        """Edit selected template."""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to edit.")
            return
        
        template_name = current_item.text()
        dialog = TemplateDialog(self, self.template_manager, template_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_templates()
            self.log_status(f"Template '{template_name}' updated successfully")
    
    def edit_naming(self):
        """Edit selected naming convention."""
        current_item = self.naming_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a naming convention to edit.")
            return
        
        naming_name = current_item.text()
        dialog = NamingDialog(self, self.template_manager, naming_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_namings()
            self.log_status(f"Naming convention '{naming_name}' updated successfully")
    
    def import_template(self):
        """Import a template from JSON file or paste."""
        dialog = ImportDialog('template', self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, message = self.template_manager.import_template(dialog.import_data)
            
            if success:
                self.refresh_templates()
                self.log_status(message)
            else:
                QMessageBox.critical(self, "Import Failed", message)
    
    def import_naming(self):
        """Import a naming convention from JSON file or paste."""
        dialog = ImportDialog('naming', self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, message = self.template_manager.import_naming(dialog.import_data)
            
            if success:
                self.refresh_namings()
                self.log_status(message)
            else:
                QMessageBox.critical(self, "Import Failed", message)
    
    def delete_template(self):
        """Delete selected template."""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm", "Delete this template?")
        if reply == QMessageBox.StandardButton.Yes:
            if self.template_manager.delete_template(current_item.text()):
                self.refresh_templates()
                self.log_status("Template deleted")
    
    def delete_naming(self):
        """Delete selected naming convention."""
        current_item = self.naming_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a naming convention to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm", "Delete this naming convention?")
        if reply == QMessageBox.StandardButton.Yes:
            if self.template_manager.delete_naming(current_item.text()):
                self.refresh_namings()
                self.log_status("Naming convention deleted")
    
    def view_metadata(self):
        """View metadata of selected file."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select a file.")
            return
        
        file_path = self.selected_files[0]
        metadata = self.metadata_manager.get_metadata(file_path)
        
        dialog = MetadataViewDialog(self, file_path, metadata)
        dialog.exec()
    
    def delete_metadata(self):
        """Delete metadata from selected file(s)."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select at least one file.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete all metadata from {len(self.selected_files)} file(s)?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        progress = QProgressDialog("Deleting metadata...", None, 0, len(self.selected_files), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        success_count = 0
        for i, file_path in enumerate(self.selected_files):
            if self.metadata_manager.delete_metadata(file_path):
                success_count += 1
                self.log_status(f"Deleted metadata from {Path(file_path).name}")
            else:
                self.log_status(f"Failed to delete metadata from {Path(file_path).name}")
            
            progress.setValue(i + 1)
            QApplication.processEvents()
        
        progress.close()
        self.log_status(f"Metadata deletion complete: {success_count}/{len(self.selected_files)} successful")
    
    def on_template_selected(self):
        """Handle template selection."""
        current_item = self.template_list.currentItem()
        if current_item:
            self.selected_template = current_item.text()
            self.update_preview()
    
    def on_naming_selected(self):
        """Handle naming convention selection."""
        current_item = self.naming_list.currentItem()
        if current_item:
            self.selected_naming = current_item.text()
            self.update_preview()
    
    def refresh_templates(self):
        """Refresh template list."""
        self.template_list.clear()
        templates = self.template_manager.get_templates()
        for name in templates.keys():
            self.template_list.addItem(name)
    
    def refresh_namings(self):
        """Refresh naming convention list."""
        self.naming_list.clear()
        conventions = self.template_manager.get_naming_conventions()
        for name in conventions.keys():
            self.naming_list.addItem(name)

    def _get_primary_file(self) -> Optional[str]:
        """Return the currently selected file path or fallback to first in list."""
        if not self.selected_files:
            return None
        # Clamp index
        self.preview_index = max(0, min(self.preview_index, len(self.selected_files) - 1))
        file_path = self.selected_files[self.preview_index]
        # Sync selection in the list widget
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self.file_list_widget.setCurrentItem(item, QItemSelectionModel.ClearAndSelect)
                break
        return file_path

    def _update_image_preview(self):
        """Update the image preview based on the selected file."""
        file_path = self._get_primary_file()
        if not file_path:
            self.image_preview_label.setText("No image selected")
            self.image_preview_label.setPixmap(QPixmap())
            self.image_preview_label.setToolTip("")
            return

        pix = QPixmap(file_path)
        if pix.isNull():
            self.image_preview_label.setText("Preview unavailable")
            self.image_preview_label.setPixmap(QPixmap())
            self.image_preview_label.setToolTip("")
            return

        # Do not upscale; only scale down if larger than the preview area
        target_size = self.image_preview_label.size()
        if pix.width() > target_size.width() or pix.height() > target_size.height():
            pix = pix.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self.image_preview_label.setPixmap(pix)
        self.image_preview_label.setText("")

        # Tooltip with metadata for this image
        metadata = self.metadata_manager.get_metadata(file_path)
        tooltip_lines = [f"File: {Path(file_path).name}"]
        exif = metadata.get('exif', {})
        xmp = metadata.get('xmp', {})
        for key in ['Artist', 'Model', 'DateTime', 'ImageDescription']:
            if key in exif:
                tooltip_lines.append(f"EXIF {key}: {exif[key]}")
        for key in ['dc:creator', 'dc:description', 'photoshop:Headline']:
            if key in xmp:
                tooltip_lines.append(f"XMP {key}: {xmp[key]}")
        self.image_preview_label.setToolTip("\n".join(tooltip_lines))

    def preview_next(self):
        """Show next selected file in preview."""
        if not self.selected_files:
            return
        self.preview_index = (self.preview_index + 1) % len(self.selected_files)
        self.update_preview()

    def preview_prev(self):
        """Show previous selected file in preview."""
        if not self.selected_files:
            return
        self.preview_index = (self.preview_index - 1) % len(self.selected_files)
        self.update_preview()
    
    def update_preview(self):
        """Update preview of template and naming."""
        preview = []

        # Update image preview pane
        self._update_image_preview()
        
        if self.selected_template:
            templates = self.template_manager.get_templates()
            template = templates.get(self.selected_template, {})
            preview.append(f"Template: {self.selected_template}\n")
            preview.append("EXIF tags:\n")
            for key, value in template.get('exif', {}).items():
                preview.append(f"  {key}: {value}\n")
            preview.append("\nXMP properties:\n")
            for key, value in template.get('xmp', {}).items():
                preview.append(f"  {key}: {value}\n")
        
        file_path_for_naming = self._get_primary_file()
        if self.selected_naming and file_path_for_naming:
            conventions = self.template_manager.get_naming_conventions()
            convention = conventions.get(self.selected_naming, {})
            pattern = convention.get('pattern', '')
            
            preview.append(f"\n\nNaming Convention: {self.selected_naming}\n")
            preview.append(f"Pattern: {pattern}\n")
            preview.append("\nPreview filenames:\n")
            
            metadata = self.metadata_manager.get_metadata(file_path_for_naming)
            new_name = self.naming_engine.generate_filename(pattern, file_path_for_naming, metadata, 1)
            preview.append(f"  {new_name}\n")
        
        self.preview_text.setText(''.join(preview))
    
    def apply_template(self):
        """Apply selected template and naming convention to file(s)."""
        if not self.selected_files:
            QMessageBox.warning(self, "Warning", "Please select at least one file.")
            return
        
        if not self.selected_template:
            QMessageBox.warning(self, "Warning", "Please select a template.")
            return
        
        if not self.selected_naming:
            QMessageBox.warning(self, "Warning", "Please select a naming convention.")
            return
        
        # Get template and naming
        templates = self.template_manager.get_templates()
        template = templates.get(self.selected_template, {})
        
        conventions = self.template_manager.get_naming_conventions()
        convention = conventions.get(self.selected_naming, {})
        pattern = convention.get('pattern', '')
        
        merge = self.merge_checkbox.isChecked()
        dry_run = self.dry_run_checkbox.isChecked()
        
        # Confirm action
        action = "preview" if dry_run else "apply"
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Apply template to {len(self.selected_files)} file(s)? ({action})"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        progress = QProgressDialog(
            "Applying template and renaming...",
            None,
            0,
            len(self.selected_files),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        success_count = 0
        failed_files = []
        operations = []
        rename_map = {}
        
        for i, file_path in enumerate(self.selected_files):
            try:
                # Get metadata
                metadata = self.metadata_manager.get_metadata(file_path)
                
                # Generate new filename
                new_filename = self.naming_engine.generate_filename(pattern, file_path, metadata, i + 1)
                new_path = Path(file_path).parent / new_filename
                
                # Handle collisions
                if new_path.exists() and str(new_path) != file_path:
                    base = new_path.stem
                    ext = new_path.suffix
                    counter = 1
                    while new_path.exists():
                        new_path = Path(file_path).parent / f"{base}_{counter}{ext}"
                        counter += 1
                
                if not dry_run:
                    # Apply metadata
                    exif_data = template.get('exif', {})
                    xmp_data = template.get('xmp', {})
                    
                    if self.metadata_manager.set_metadata(file_path, exif_data, xmp_data, merge):
                        # Rename file
                        if str(new_path) != file_path:
                            shutil.move(file_path, new_path)
                            rename_map[file_path] = str(new_path)
                        
                        success_count += 1
                        self.log_status(f"✓ Processed: {Path(file_path).name} → {new_path.name}")
                        
                        # Save undo info
                        operations.append({
                            'original': file_path,
                            'new': str(new_path),
                            'metadata': metadata
                        })
                    else:
                        failed_files.append(Path(file_path).name)
                        self.log_status(f"✗ Failed: {Path(file_path).name}")
                else:
                    self.log_status(f"[DRY RUN] Would process: {Path(file_path).name} → {new_path.name}")
                    success_count += 1
            
            except Exception as e:
                failed_files.append(Path(file_path).name)
                self.log_status(f"✗ Error: {Path(file_path).name} - {str(e)}")
                logger.error(f"Error processing {file_path}: {e}\n{traceback.format_exc()}")
            
            progress.setValue(i + 1)
            QApplication.processEvents()
        
        progress.close()

        # Update UI selection and list items to point to renamed files
        self._refresh_after_renames(rename_map)
        
        # Summary
        if dry_run:
            self.log_status(f"\n[DRY RUN] Would process {success_count}/{len(self.selected_files)} files")
        else:
            self.log_status(f"\nApply complete: {success_count}/{len(self.selected_files)} successful")
            if failed_files:
                self.log_status(f"Failed files: {', '.join(failed_files)}")
            
            # Save undo point
            if operations:
                self.last_operation = operations
    
    def undo_last(self):
        """Undo the last operation."""
        if not self.last_operation:
            QMessageBox.information(self, "Info", "No operations to undo.")
            return
        
        reply = QMessageBox.question(self, "Confirm", "Undo last operation?")
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        for op in self.last_operation:
            try:
                if Path(op['new']).exists():
                    shutil.move(op['new'], op['original'])
                self.log_status(f"Undone: {Path(op['original']).name}")
            except Exception as e:
                self.log_status(f"Failed to undo: {Path(op['original']).name} - {str(e)}")
        
        self.last_operation = None

    def _refresh_after_renames(self, rename_map: Dict[str, str]):
        """Update selection and list widget to keep tracking renamed files."""
        if not rename_map:
            return

        # Update selected file paths
        self.selected_files = [rename_map.get(path, path) for path in self.selected_files]

        # Update list widget entries
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            old_path = item.data(Qt.ItemDataRole.UserRole)
            if old_path in rename_map:
                new_path = rename_map[old_path]
                item.setData(Qt.ItemDataRole.UserRole, new_path)
                item.setText(Path(new_path).name)

        self.preview_index = max(0, min(self.preview_index, len(self.selected_files) - 1))
        self.update_preview()
        self.log_status("Undo complete")
    
    def log_status(self, message: str):
        """Log a message to the status area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        logger.info(message)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = PhotoMetadataEditor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
