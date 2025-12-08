#!/usr/bin/env python3
"""
Metadata handler module for Photo Metadata Editor.
Handles EXIF (via piexif) and XMP (via sidecar files and libxmp fallback).
Compatible with macOS, Linux, and Windows.
Robust parsing and normalization of metadata values.
"""

import os
import json
import shutil
import logging
import tempfile
import xml.etree.ElementTree as ET
import re
import binascii
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


class MetadataManager:
    """Handles metadata reading/writing using piexif (EXIF) and sidecar XMP."""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.gif', '.bmp'}
    
    def __init__(self):
        """Initialize metadata manager."""
        self.method = "piexif + sidecar XMP"
        logger.info(f"Metadata handling: {self.method}")
    
    def _normalize_value(self, v: Any) -> Any:
        """
        Normalize a metadata value to a JSON/display-friendly Python type.
        Handles bytes, dicts, lists, tuples, and special cases like rationals.
        """
        # bytes -> try to decode with common encodings, strip nulls and non-printables
        if isinstance(v, (bytes, bytearray)):
            for enc in ('utf-8', 'utf-16le', 'utf-16be', 'latin-1'):
                try:
                    s = v.decode(enc)
                    # strip trailing nulls and control characters
                    s = s.rstrip('\x00')
                    s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]+', '', s)
                    if s.strip():
                        return s
                except Exception:
                    continue
            # fallback: show short hex summary
            try:
                return f"<bytes {len(v)} bytes: {binascii.hexlify(v[:16]).decode()}{'...' if len(v)>16 else ''}>"
            except Exception:
                return str(v)

        # dict -> normalize recursively
        if isinstance(v, dict):
            return {self._normalize_value(k): self._normalize_value(val) for k, val in v.items()}

        # lists / tuples -> normalize elements; detect special patterns
        if isinstance(v, (list, tuple)):
            # detect a SINGLE rational (num, den) pair: tuple/list of exactly 2 integers
            if len(v) == 2 and all(isinstance(x, int) for x in v):
                num, den = v[0], v[1]
                try:
                    result = round(num / den if den else 0, 8)  # avoid floating point noise
                    if result != result:  # NaN check
                        return v
                    return result
                except Exception:
                    pass
            
            # detect array of small integers (0-255) -> likely byte data from EXIF, try to decode
            if len(v) > 0 and all(isinstance(x, int) and 0 <= x <= 255 for x in v):
                try:
                    byte_val = bytes(v)
                    # Try UTF-16LE first (common for XP tags), then UTF-8
                    for enc in ('utf-16le', 'utf-8', 'latin-1'):
                        try:
                            s = byte_val.decode(enc)
                            s = s.rstrip('\x00')
                            s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]+', '', s)
                            # If we got a reasonable string, split on common delimiters for multi-value fields
                            if len(s) > 2:
                                parts = [p.strip() for p in re.split(r'[;,\x00]+', s) if p.strip()]
                                return parts if len(parts) > 1 else (parts[0] if parts else s)
                            return s
                        except Exception:
                            continue
                except Exception:
                    pass
            
            # detect sequence of (num, den) pairs (rational numbers) - multiple pairs
            if len(v) > 0 and all(isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(n, int) for n in x) for x in v):
                floats = []
                ok = True
                for num, den in v:
                    try:
                        floats.append(num / den if den else 0)
                    except Exception:
                        ok = False
                        break
                if ok:
                    # common case: GPS lat/long as 3 rationals -> convert DMS to decimal degrees
                    if len(floats) == 3:
                        deg, minute, sec = floats
                        try:
                            return deg + minute / 60.0 + sec / 3600.0
                        except Exception:
                            return floats
                    return floats
            
            # otherwise normalize each element
            return [self._normalize_value(x) for x in v]

        # other primitives: return as-is
        return v

    def _normalize_metadata_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively normalize all values in a metadata dictionary."""
        out: Dict[str, Any] = {}
        for k, v in d.items():
            # normalize key (strip namespaces like {ns}tag)
            key = k
            if isinstance(key, str) and '}' in key:
                key = key.split('}', 1)[1]
            out[key] = self._normalize_value(v)
        return out

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract EXIF and XMP metadata from a file.
        
        Returns:
            dict with 'exif' and 'xmp' keys, each containing tag->value mappings
        """
        metadata = {'exif': {}, 'xmp': {}, 'method': self.method}
        
        try:
            metadata.update(self._get_metadata_python(file_path))
        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")
        
        return metadata

    def _get_metadata_python(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata using piexif (EXIF) and sidecar XMP.
        Robust handling of all tag types and encodings.
        """
        exif_data = {}
        xmp_data = {}
        
        # EXIF via piexif - robust parsing
        if HAS_PIEXIF:
            try:
                img_data = piexif.load(file_path)
                
                # Iterate all dict-like IFDs
                for ifd_name, ifd in img_data.items():
                    if not isinstance(ifd, dict) or ifd_name == 'thumbnail':
                        continue
                    
                    for tag, tag_value in ifd.items():
                        # Resolve friendly tag name
                        try:
                            tag_info = piexif.TAGS.get(ifd_name, {}).get(tag)
                            tag_name = tag_info.get('name') if tag_info else None
                        except Exception:
                            tag_name = None

                        if not tag_name:
                            tag_name = f"{ifd_name}:0x{tag:04X}"

                        # Handle Windows XP* UTF-16LE fields specially
                        try:
                            if tag_name.startswith('XP') or tag_name.lower() in ('xpkeywords', 'xpsubject', 'xptitle', 'xpcomments'):
                                if isinstance(tag_value, (list, tuple)):
                                    try:
                                        tag_value = bytes(tag_value)
                                    except Exception:
                                        tag_value = str(tag_value)
                                if isinstance(tag_value, (bytes, bytearray)):
                                    try:
                                        val = tag_value.decode('utf-16le', errors='ignore').rstrip('\x00')
                                    except Exception:
                                        val = tag_value.decode('utf-8', errors='replace') if isinstance(tag_value, (bytes, bytearray)) else str(tag_value)
                                    parts = [p.strip() for p in re.split(r'[;,\x00]+', val) if p.strip()]
                                    tag_value = parts if len(parts) > 1 else (parts[0] if parts else '')
                            
                            # Handle other byte fields (e.g., UserComment, ImageDescription)
                            elif isinstance(tag_value, (bytes, bytearray)):
                                val = tag_value.decode('utf-8', errors='replace')
                                # Clean up UserComment if it has encoding prefix
                                if tag_name == 'UserComment' and val:
                                    val = re.sub(r'^(ASCII|UNICODE|JIS)\s*\x00+', '', val, flags=re.IGNORECASE)
                                    val = val.rstrip('\x00').strip()
                                tag_value = val
                        except Exception:
                            pass

                        # Record the tag
                        exif_data[tag_name] = tag_value
                
                # Normalize all values
                exif_data = self._normalize_metadata_dict(exif_data)
            except Exception as e:
                logger.debug(f"piexif read error: {e}")
        
        # XMP via sidecar
        sidecar_path = self._xmp_sidecar_path(file_path)
        if sidecar_path.exists():
            try:
                xmp_data.update(self._read_xmp_sidecar(sidecar_path))
            except Exception as e:
                logger.debug(f"sidecar XMP read error: {e}")

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
            
            success = self._set_metadata_python(temp_path, exif_data, xmp_data, merge)
            
            if success:
                shutil.move(temp_path, file_path)
                
                # Also move XMP sidecar if it was created
                temp_xmp = Path(temp_path).parent / (Path(temp_path).name + ".xmp")
                dest_xmp = self._xmp_sidecar_path(file_path)
                if temp_xmp.exists():
                    shutil.move(str(temp_xmp), str(dest_xmp))
                
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")

            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False
    
    def _set_metadata_python(self, file_path: str, exif_data: Dict = None,
                             xmp_data: Dict = None, merge: bool = False) -> bool:
        """
        Write metadata using piexif and sidecar XMP.
        Robust encoding handling and tag mapping.
        """
        try:
            # Write EXIF using piexif
            if HAS_PIEXIF and exif_data:
                try:
                    # Load existing or create new
                    exif_dict = piexif.load(file_path) if merge else {
                        "0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None
                    }

                    # Comprehensive tag mapping
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
                        "XPSubject": ("0th", piexif.ImageIFD.XPSubject),
                        "XPKeywords": ("0th", piexif.ImageIFD.XPKeywords),
                        "XPComment": ("0th", piexif.ImageIFD.XPComment),
                    }

                    for key, value in exif_data.items():
                        if key in tag_map:
                            ifd_name, tag_id = tag_map[key]
                            
                            # Encode value appropriately
                            if isinstance(value, str):
                                # XP* tags use UTF-16LE
                                if key.startswith('XP'):
                                    try:
                                        value_bytes = value.encode('utf-16le')
                                    except Exception:
                                        value_bytes = value.encode('utf-8', errors='ignore')
                                else:
                                    value_bytes = value.encode('utf-8', errors='ignore')
                            else:
                                value_bytes = value
                            
                            # Clean up UserComment prefix
                            if key == "UserComment" and isinstance(value_bytes, bytes):
                                prefix = b"ASCII\x00\x00\x00"
                                if value_bytes.startswith(prefix):
                                    value_bytes = value_bytes[len(prefix):]
                                # Only add prefix if not already there
                                if not value_bytes.startswith(prefix):
                                    value_bytes = prefix + value_bytes
                            
                            exif_dict[ifd_name][tag_id] = value_bytes

                    piexif.insert(piexif.dump(exif_dict), file_path)
                    logger.info(f"Wrote EXIF metadata to {Path(file_path).name}")
                except Exception as e:
                    logger.warning(f"piexif write error: {e}")
            
            # Write XMP sidecar (even if empty, to ensure it exists)
            if xmp_data is not None:
                try:
                    sidecar = self._xmp_sidecar_path(file_path)
                    self._write_xmp_sidecar(sidecar, xmp_data)
                    logger.info(f"Wrote XMP sidecar: {sidecar.name}")
                except Exception as e:
                    logger.warning(f"XMP sidecar write error: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Metadata write error: {e}")
            return False
    
    def delete_metadata(self, file_path: str) -> bool:
        """Remove all EXIF and XMP metadata from a file."""
        temp_fd, temp_path = tempfile.mkstemp(suffix=Path(file_path).suffix)
        try:
            os.close(temp_fd)
            shutil.copy2(file_path, temp_path)
            
            success = False
            if HAS_PIEXIF:
                try:
                    piexif.insert(piexif.dump({
                        "0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None
                    }), temp_path)
                    success = True
                    logger.info(f"Deleted EXIF metadata from {Path(file_path).name}")
                except Exception as e:
                    logger.warning(f"piexif delete error: {e}")
            
            if success:
                shutil.move(temp_path, file_path)
                # Also remove XMP sidecar
                sidecar = self._xmp_sidecar_path(file_path)
                if sidecar.exists():
                    sidecar.unlink()
                    logger.info(f"Deleted XMP sidecar: {sidecar.name}")
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False

    def _xmp_sidecar_path(self, file_path: str) -> Path:
        """Get the path to the XMP sidecar file."""
        return Path(file_path).parent / (Path(file_path).name + ".xmp")

    def _read_xmp_sidecar(self, sidecar_path: Path) -> Dict[str, Any]:
        """Read XMP data from sidecar RDF/XML file."""
        xmp_dict = {}
        try:
            tree = ET.parse(sidecar_path)
            root = tree.getroot()
            
            # Register common namespaces
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
                'xmp': 'http://ns.adobe.com/xap/1.0/',
            }
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)
            
            # Find all Description elements
            descriptions = root.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
            
            for desc in descriptions:
                # Extract attributes
                for attr_name, attr_value in desc.attrib.items():
                    # Strip namespace
                    local_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                    xmp_dict[local_name] = attr_value
                
                # Extract child elements
                for child in desc:
                    tag = child.tag
                    local_name = tag.split('}')[-1] if '}' in tag else tag
                    
                    # Check for Bag/Seq/Alt structures - they wrap li elements
                    li_nodes = child.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
                    if li_nodes:
                        li_texts = [(li.text or '').strip() for li in li_nodes if (li.text or '').strip()]
                        xmp_dict[local_name] = li_texts if len(li_texts) > 1 else (li_texts[0] if li_texts else '')
                    else:
                        # Direct text content (no structure)
                        text = (child.text or '').strip()
                        if text:
                            xmp_dict[local_name] = text
        except Exception as e:
            logger.debug(f"Error reading XMP sidecar: {e}")
        
        return xmp_dict

    def _write_xmp_sidecar(self, sidecar_path: Path, xmp_data: Dict[str, Any]):
        """Write XMP data to sidecar RDF/XML file. Creates minimal structure if empty."""
        try:
            # Register namespaces BEFORE creating elements
            namespaces = {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
                'xmp': 'http://ns.adobe.com/xap/1.0/',
            }
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)
            
            # Create RDF structure with proper namespace declarations
            rdf_ns = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
            xmp_ns = 'http://ns.adobe.com/xap/1.0/'
            dc_ns = 'http://purl.org/dc/elements/1.1/'
            ps_ns = 'http://ns.adobe.com/photoshop/1.0/'
            
            # Create root element - namespaces will be added automatically by ET
            xmpmeta = ET.Element('{' + xmp_ns + '}xmpmeta')
            rdf_root = ET.SubElement(xmpmeta, '{' + rdf_ns + '}RDF')
            description = ET.SubElement(rdf_root, '{' + rdf_ns + '}Description')
            
            # Add data elements (if xmp_data is not empty)
            if xmp_data:
                for key, value in xmp_data.items():
                    if not value:
                        continue
                    
                    # Normalize some common variations
                    # "keywords" is a synonym for "subject" in XMP
                    if key == 'keywords':
                        key = 'subject'
                    
                    # Handle list values (Bag/Seq)
                    if isinstance(value, list):
                        # Choose appropriate namespace and container type
                        if key in ('subject',):
                            element = ET.SubElement(description, '{' + dc_ns + '}subject')
                            bag = ET.SubElement(element, '{' + rdf_ns + '}Bag')
                            for item in value:
                                li = ET.SubElement(bag, '{' + rdf_ns + '}li')
                                li.text = str(item)
                        elif key == 'creator':
                            element = ET.SubElement(description, '{' + dc_ns + '}creator')
                            seq = ET.SubElement(element, '{' + rdf_ns + '}Seq')
                            for item in value:
                                li = ET.SubElement(seq, '{' + rdf_ns + '}li')
                                li.text = str(item)
                        else:
                            # Generic list - use Bag
                            element = ET.SubElement(description, '{' + dc_ns + '}' + key)
                            bag = ET.SubElement(element, '{' + rdf_ns + '}Bag')
                            for item in value:
                                li = ET.SubElement(bag, '{' + rdf_ns + '}li')
                                li.text = str(item)
                    else:
                        # Handle string values - some may be comma-separated
                        # If value contains commas, treat as list
                        if isinstance(value, str) and key in ('subject', 'keywords') and ',' in value:
                            element = ET.SubElement(description, '{' + dc_ns + '}subject')
                            bag = ET.SubElement(element, '{' + rdf_ns + '}Bag')
                            for item in [x.strip() for x in value.split(',') if x.strip()]:
                                li = ET.SubElement(bag, '{' + rdf_ns + '}li')
                                li.text = item
                            continue
                        
                        # Handle scalar values
                        if key in ('title', 'description', 'rights'):
                            element = ET.SubElement(description, '{' + dc_ns + '}' + key)
                            alt = ET.SubElement(element, '{' + rdf_ns + '}Alt')
                            li = ET.SubElement(alt, '{' + rdf_ns + '}li')
                            li.set('{http://www.w3.org/XML/1998/namespace}lang', 'x-default')
                            li.text = str(value)
                        elif key == 'creator':
                            element = ET.SubElement(description, '{' + dc_ns + '}creator')
                            seq = ET.SubElement(element, '{' + rdf_ns + '}Seq')
                            li = ET.SubElement(seq, '{' + rdf_ns + '}li')
                            li.text = str(value)
                        elif key in ('headline', 'Headline'):
                            element = ET.SubElement(description, '{' + ps_ns + '}Headline')
                            element.text = str(value)
                        elif key in ('location', 'Location'):
                            element = ET.SubElement(description, '{' + ps_ns + '}Location')
                            element.text = str(value)
                        elif key in ('date_created', 'DateCreated'):
                            element = ET.SubElement(description, '{' + ps_ns + '}DateCreated')
                            element.text = str(value)
                        elif key in ('create_date', 'CreateDate'):
                            element = ET.SubElement(description, '{' + xmp_ns + '}CreateDate')
                            element.text = str(value)
                        else:
                            # Generic element in dc namespace
                            element = ET.SubElement(description, '{' + dc_ns + '}' + key)
                            element.text = str(value)
            
            # Write XML with pretty formatting
            tree = ET.ElementTree(xmpmeta)
            tree.write(sidecar_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Wrote XMP sidecar to {sidecar_path.name}")
        except Exception as e:
            logger.error(f"Error writing XMP sidecar: {e}")
            raise


class TemplateManager:
    """Manages metadata templates and naming conventions."""
    
    def __init__(self):
        """Initialize template manager."""
        self.config_dir = Path.home() / ".photo_meta_editor"
        self.template_dir = self.config_dir / "templates"
        self.naming_dir = self.config_dir / "naming"
        self.metadata_dir = self.config_dir / "metadata"
        
        # Create directories
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.naming_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def get_templates(self) -> Dict[str, Any]:
        """Load all templates from disk."""
        templates = {}
        for template_file in self.template_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    data = json.load(f)
                    templates[data.get('name', template_file.stem)] = data
            except Exception as e:
                logger.warning(f"Error loading template {template_file}: {e}")
        return templates
    
    def save_template(self, name: str, exif_dict: Dict, xmp_dict: Dict) -> bool:
        """Save a template."""
        try:
            template = {
                'name': name,
                'exif': exif_dict,
                'xmp': xmp_dict,
                'created': datetime.now().isoformat(),
            }
            template_file = self.template_dir / f"{name}.json"
            with open(template_file, 'w') as f:
                json.dump(template, f, indent=2)
            logger.info(f"Saved template: {name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {name}: {e}")
            return False
    
    def delete_template(self, name: str) -> bool:
        """Delete a template."""
        try:
            template_file = self.template_dir / f"{name}.json"
            if template_file.exists():
                template_file.unlink()
                logger.info(f"Deleted template: {name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting template {name}: {e}")
            return False
    
    def import_template(self, data: Dict) -> Tuple[bool, str]:
        """Import a template from JSON data."""
        try:
            name = data.get('name')
            if not name:
                return False, "Template must have a 'name' field"
            
            exif = data.get('exif', {})
            xmp = data.get('xmp', {})
            
            return self.save_template(name, exif, xmp), "Template imported successfully"
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def get_naming_conventions(self) -> Dict[str, Any]:
        """Load all naming conventions from disk."""
        conventions = {}
        for naming_file in self.naming_dir.glob("*.json"):
            try:
                with open(naming_file, 'r') as f:
                    data = json.load(f)
                    conventions[data.get('name', naming_file.stem)] = data
            except Exception as e:
                logger.warning(f"Error loading naming convention {naming_file}: {e}")
        return conventions
    
    def save_naming(self, name: str, pattern: str) -> bool:
        """Save a naming convention."""
        try:
            convention = {
                'name': name,
                'pattern': pattern,
                'created': datetime.now().isoformat(),
            }
            naming_file = self.naming_dir / f"{name}.json"
            with open(naming_file, 'w') as f:
                json.dump(convention, f, indent=2)
            logger.info(f"Saved naming convention: {name}")
            return True
        except Exception as e:
            logger.error(f"Error saving naming convention {name}: {e}")
            return False
    
    def delete_naming(self, name: str) -> bool:
        """Delete a naming convention."""
        try:
            naming_file = self.naming_dir / f"{name}.json"
            if naming_file.exists():
                naming_file.unlink()
                logger.info(f"Deleted naming convention: {name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting naming convention {name}: {e}")
            return False
    
    def import_naming(self, data: Dict) -> Tuple[bool, str]:
        """Import a naming convention from JSON data."""
        try:
            name = data.get('name')
            pattern = data.get('pattern')
            
            if not name or not pattern:
                return False, "Naming convention must have 'name' and 'pattern' fields"
            
            return self.save_naming(name, pattern), "Naming convention imported successfully"
        except Exception as e:
            return False, f"Import failed: {str(e)}"
    
    def _normalize_template_data(self, template: Dict) -> Dict:
        """Normalize template data for consistency. Strips namespace prefixes from XMP keys."""
        xmp_data = template.get('xmp', {})
        
        # Strip namespace prefixes from XMP keys (e.g., "dc:creator" -> "creator")
        normalized_xmp = {}
        for key, value in xmp_data.items():
            # Remove namespace prefix if present
            clean_key = key.split(':')[-1] if ':' in key else key
            normalized_xmp[clean_key] = value
        
        return {
            'exif': template.get('exif', {}),
            'xmp': normalized_xmp,
        }


class NamingEngine:
    """Generates filenames using template patterns with token replacement."""
    
    TOKENS = {
        'date': lambda fp, m, i: datetime.now().strftime('%Y-%m-%d'),
        'datetime': lambda fp, m, i: datetime.now().isoformat(),
        'title': lambda fp, m, i: m.get('xmp', {}).get('title') or m.get('exif', {}).get('ImageDescription') or '',
        'camera_model': lambda fp, m, i: m.get('exif', {}).get('Model') or 'Unknown',
        'original_name': lambda fp, m, i: Path(fp).stem,
        'userid': lambda fp, m, i: os.environ.get('USER') or 'user',
    }
    
    def generate_filename(self, pattern: str, file_path: str, metadata: Dict = None, sequence: int = 1) -> str:
        """
        Generate a new filename based on pattern and metadata.
        
        Tokens:
            {date} -> YYYY-MM-DD
            {datetime:%Y%m%d_%H%M%S} -> custom strftime format
            {title} -> image title/description
            {camera_model} -> camera model
            {sequence:03d} -> sequence number with padding
            {original_name} -> original filename without extension
            {userid} -> current user
        """
        if not metadata:
            metadata = {'exif': {}, 'xmp': {}}
        
        result = pattern
        
        # Handle {datetime:%format} - strftime formatting
        datetime_match = re.search(r'\{datetime:([^}]+)\}', result)
        if datetime_match:
            fmt = datetime_match.group(1)
            try:
                value = datetime.now().strftime(fmt)
            except Exception:
                value = datetime.now().isoformat()
            result = result.replace(datetime_match.group(0), value)
        
        # Handle {sequence:format} - format string for sequence number
        seq_match = re.search(r'\{sequence:([^}]+)\}', result)
        if seq_match:
            fmt = seq_match.group(1)
            try:
                value = fmt % sequence
            except Exception:
                value = str(sequence)
            result = result.replace(seq_match.group(0), value)
        
        # Handle standard tokens
        for token, func in self.TOKENS.items():
            placeholder = '{' + token + '}'
            if placeholder in result:
                try:
                    value = func(file_path, metadata, sequence)
                    result = result.replace(placeholder, str(value))
                except Exception as e:
                    logger.debug(f"Error generating token {token}: {e}")
                    result = result.replace(placeholder, '')
        
        # Append original extension
        ext = Path(file_path).suffix
        return result + ext
