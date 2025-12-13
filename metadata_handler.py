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
        self.method = "piexif + embedded XMP"

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract EXIF and XMP metadata from a file.
        Returns:
            dict with 'exif' and 'xmp' keys, each containing tag->value mappings
        """
        metadata = {'exif': {}, 'xmp': {}, 'method': 'piexif + embedded XMP'}
        try:
            metadata.update(self._get_metadata_python(file_path))
        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")
        return metadata


    def _get_metadata_python(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata using piexif (EXIF) and XMP (sidecar and embedded).
        Robust handling of all tag types and encodings.
        """
        exif_data = {}
        xmp_data = {}

        # EXIF via piexif - robust parsing
        if HAS_PIEXIF:
            try:
                img_data = piexif.load(file_path)
                for ifd_name, ifd in img_data.items():
                    if not isinstance(ifd, dict) or ifd_name == 'thumbnail':
                        continue
                    for tag, tag_value in ifd.items():
                        try:
                            tag_info = piexif.TAGS.get(ifd_name, {}).get(tag)
                            tag_name = tag_info.get('name') if tag_info else None
                        except Exception:
                            tag_name = None
                        if not tag_name:
                            tag_name = f"{ifd_name}:0x{tag:04X}"
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
                            elif isinstance(tag_value, (bytes, bytearray)):
                                val = tag_value.decode('utf-8', errors='replace')
                                if tag_name == 'UserComment' and val:
                                    val = re.sub(r'^(ASCII|UNICODE|JIS)\s*\x00+', '', val, flags=re.IGNORECASE)
                                    val = val.rstrip('\x00').strip()
                                tag_value = val
                        except Exception:
                            pass
                        exif_data[tag_name] = tag_value
                exif_data = self._normalize_metadata_dict(exif_data)
            except Exception as e:
                logger.debug(f"piexif read error: {e}")

        # Only embedded XMP
        try:
            xmp_data.update(self._read_embedded_xmp(file_path))
        except Exception as e:
            logger.debug(f"embedded XMP read error: {e}")

        return {'exif': exif_data, 'xmp': xmp_data}

    def _read_embedded_xmp(self, file_path: str) -> Dict[str, Any]:
        """
        Extract XMP metadata embedded in JPEG/TIFF files (search for XMP packet in file bytes).
        Returns a dict of XMP fields.
        """
        xmp_dict = {}
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            # XMP packets are between <x:xmpmeta ...> and </x:xmpmeta>
            start = data.find(b'<x:xmpmeta')
            end = data.find(b'</x:xmpmeta>')
            if start != -1 and end != -1:
                xmp_bytes = data[start:end+12]  # 12 = len('</x:xmpmeta>')
                try:
                    xmp_str = xmp_bytes.decode('utf-8', errors='replace')
                except Exception:
                    xmp_str = xmp_bytes.decode('latin-1', errors='replace')
                # Parse XML
                root = ET.fromstring(xmp_str)
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
                    for attr_name, attr_value in desc.attrib.items():
                        local_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                        xmp_dict[local_name] = attr_value
                    for child in desc:
                        tag = child.tag
                        local_name = tag.split('}')[-1] if '}' in tag else tag
                        li_nodes = child.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
                        if li_nodes:
                            li_texts = [(li.text or '').strip() for li in li_nodes if (li.text or '').strip()]
                            xmp_dict[local_name] = li_texts if len(li_texts) > 1 else (li_texts[0] if li_texts else '')
                        else:
                            text = (child.text or '').strip()
                            if text:
                                xmp_dict[local_name] = text
        except Exception as e:
            logger.debug(f"Error reading embedded XMP: {e}")
        return xmp_dict
    
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
            
            # Write embedded XMP
            if xmp_data is not None:
                try:
                    xmp_packet = self._build_xmp_packet(xmp_data)
                    if self._is_jpeg(file_path):
                        self._inject_xmp_into_jpeg(file_path, xmp_packet.encode('utf-8'))
                        logger.info(f"Embedded XMP in JPEG: {Path(file_path).name}")
                    # TODO: Add TIFF embedding if needed
                except Exception as e:
                    logger.warning(f"Embedded XMP write error: {e}")
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
            
            # Delete embedded XMP from JPEG files
            if self._is_jpeg(temp_path):
                try:
                    self._remove_xmp_from_jpeg(temp_path)
                    logger.info(f"Deleted XMP metadata from {Path(file_path).name}")
                except Exception as e:
                    logger.warning(f"XMP deletion error: {e}")
            
            if success:
                shutil.move(temp_path, file_path)
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False

    def _is_jpeg(self, file_path: str) -> bool:
        """Check if file is a JPEG."""
        ext = Path(file_path).suffix.lower()
        return ext in {'.jpg', '.jpeg'}
    
    def _remove_xmp_from_jpeg(self, file_path: str) -> None:
        """Remove embedded XMP metadata from a JPEG file."""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Parse JPEG markers and rebuild without XMP APP1
        new_data = b''
        i = 0
        while i < len(data):
            if data[i:i+2] == b'\xff\xd8':  # SOI
                new_data += data[i:i+2]
                i += 2
            elif data[i:i+2] == b'\xff\xd9':  # EOI
                new_data += data[i:i+2]
                i += 2
            elif data[i] == 0xff and i + 1 < len(data):
                marker = data[i+1]
                # APP1 marker
                if marker == 0xe1 and i + 3 < len(data):
                    length = (data[i+2] << 8) | data[i+3]
                    segment_data = data[i+4:i+2+length]
                    # Check if it's XMP (starts with "http://ns.adobe.com/xap/1.0/\x00")
                    if segment_data.startswith(b'http://ns.adobe.com/xap/1.0/\x00'):
                        # Skip XMP APP1 marker
                        i += 2 + length
                    else:
                        # Keep EXIF APP1 marker
                        new_data += data[i:i+2+length]
                        i += 2 + length
                elif marker in [0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9]:  # RSTn, EOI
                    new_data += data[i:i+2]
                    i += 2
                else:
                    # Other markers with length field
                    if i + 3 < len(data):
                        length = (data[i+2] << 8) | data[i+3]
                        new_data += data[i:i+2+length]
                        i += 2 + length
                    else:
                        new_data += data[i:i+2]
                        i += 2
            else:
                new_data += data[i:i+1]
                i += 1
        
        with open(file_path, 'wb') as f:
            f.write(new_data)

    def _build_xmp_packet(self, xmp_data: Dict[str, Any]) -> str:
        """Build a minimal XMP packet from a dict of fields."""
        import xml.sax.saxutils as sax
        def _escape(s): return sax.escape(str(s))
        
        lines = [
            '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>',
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
            '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" '
            'xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
        ]
        
        # Dublin Core fields
        if 'title' in xmp_data:
            lines.append(f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{_escape(xmp_data["title"])}</rdf:li></rdf:Alt></dc:title>')
        if 'description' in xmp_data:
            lines.append(f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{_escape(xmp_data["description"])}</rdf:li></rdf:Alt></dc:description>')
        if 'creator' in xmp_data:
            creators = xmp_data['creator']
            if not isinstance(creators, list): 
                creators = [creators]
            creator_items = ''.join([f'<rdf:li>{_escape(c)}</rdf:li>' for c in creators if c])
            lines.append(f'<dc:creator><rdf:Seq>{creator_items}</rdf:Seq></dc:creator>')
        if 'subject' in xmp_data:
            subjects = xmp_data['subject']
            if not isinstance(subjects, list): 
                subjects = [subjects]
            subj_items = ''.join([f'<rdf:li>{_escape(s)}</rdf:li>' for s in subjects if s])
            lines.append(f'<dc:subject><rdf:Bag>{subj_items}</rdf:Bag></dc:subject>')
        if 'rights' in xmp_data:
            lines.append(f'<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{_escape(xmp_data["rights"])}</rdf:li></rdf:Alt></dc:rights>')
        
        # Photoshop fields
        if 'Headline' in xmp_data:
            lines.append(f'<photoshop:Headline>{_escape(xmp_data["Headline"])}</photoshop:Headline>')
        if 'DateCreated' in xmp_data:
            lines.append(f'<photoshop:DateCreated>{_escape(xmp_data["DateCreated"])}</photoshop:DateCreated>')
        
        # XMP fields
        if 'CreateDate' in xmp_data:
            lines.append(f'<xmp:CreateDate>{_escape(xmp_data["CreateDate"])}</xmp:CreateDate>')
        
        lines.append('</rdf:Description>')
        lines.append('</rdf:RDF>')
        lines.append('</x:xmpmeta>')
        lines.append('<?xpacket end="w"?>')
        
        return '\n'.join(lines)

    def _inject_xmp_into_jpeg(self, file_path: str, xmp_packet: bytes):
        """Inject XMP packet into JPEG file as APP1 marker."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # JPEG structure: FFD8 (SOI) followed by markers
            # APP1 marker for XMP: FFE1 [length] "http://ns.adobe.com/xap/1.0/\x00" [XMP packet]
            XMP_NAMESPACE = b'http://ns.adobe.com/xap/1.0/\x00'
            
            # Remove existing XMP if present
            output = bytearray()
            pos = 0
            
            if data[0:2] != b'\xff\xd8':
                raise ValueError("Not a valid JPEG file")
            
            output.extend(data[0:2])  # SOI marker
            pos = 2
            
            xmp_injected = False
            
            while pos < len(data) - 1:
                if data[pos] != 0xFF:
                    # No more markers, rest is image data
                    output.extend(data[pos:])
                    break
                
                marker = data[pos+1]
                pos += 2
                
                # Skip existing XMP APP1 markers
                if marker == 0xE1:  # APP1
                    if pos + 2 <= len(data):
                        length = (data[pos] << 8) | data[pos+1]
                        if pos + length <= len(data):
                            segment_data = data[pos+2:pos+length]
                            if segment_data.startswith(XMP_NAMESPACE):
                                # Skip this XMP marker
                                pos += length
                                continue
                
                # For markers with length
                if marker in [0xC0, 0xC2, 0xC4, 0xDB, 0xDD, 0xDA, 0xFE] or (0xE0 <= marker <= 0xEF):
                    if pos + 2 > len(data):
                        break
                    length = (data[pos] << 8) | data[pos+1]
                    
                    # Inject XMP after first APP0/APP1 marker (before other data)
                    if not xmp_injected and marker in [0xE0, 0xE1]:
                        output.append(0xFF)
                        output.append(marker)
                        output.extend(data[pos:pos+length])
                        pos += length
                        
                        # Now inject our XMP
                        xmp_data = XMP_NAMESPACE + xmp_packet
                        xmp_length = len(xmp_data) + 2
                        if xmp_length <= 0xFFFF:
                            output.append(0xFF)
                            output.append(0xE1)
                            output.append((xmp_length >> 8) & 0xFF)
                            output.append(xmp_length & 0xFF)
                            output.extend(xmp_data)
                            xmp_injected = True
                        continue
                    
                    output.append(0xFF)
                    output.append(marker)
                    output.extend(data[pos:pos+length])
                    pos += length
                elif marker == 0xD9:  # EOI
                    # If we haven't injected yet, do it before EOI
                    if not xmp_injected:
                        xmp_data = XMP_NAMESPACE + xmp_packet
                        xmp_length = len(xmp_data) + 2
                        if xmp_length <= 0xFFFF:
                            output.append(0xFF)
                            output.append(0xE1)
                            output.append((xmp_length >> 8) & 0xFF)
                            output.append(xmp_length & 0xFF)
                            output.extend(xmp_data)
                            xmp_injected = True
                    output.append(0xFF)
                    output.append(marker)
                    break
                else:
                    # Standalone marker
                    output.append(0xFF)
                    output.append(marker)
            
            # Write modified JPEG
            with open(file_path, 'wb') as f:
                f.write(output)
                
        except Exception as e:
            raise Exception(f"Failed to inject XMP: {str(e)}")
    
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
    
    def _parse_field_value(self, value: Any) -> Any:
        """
        Parse field values with pipe (|) as array separator.
        E.g., "subject, fun, cap, test" -> ["Subject", "fun", "cap", "test"]
        E.g., "fun, at the park | Love | I have a cat" -> ["fun, at the park", "Love", "I have a cat"]
        """
        if not isinstance(value, str):
            return value
        
        # Check if pipe separator is used
        if '|' in value:
            # Split by pipe and strip whitespace, capitalize first element
            items = [item.strip() for item in value.split('|')]
            return items
        
        # Otherwise, assume comma-separated and split by commas
        if ',' in value:
            items = [item.strip() for item in value.split(',')]
            # Capitalize the first item
            if items and items[0]:
                items[0] = items[0].capitalize()
            return items
        
        return value


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


class TemplateManager:
    """Manages template storage and retrieval."""
    def __init__(self):
        self.template_dir = Path.home() / '.photo_meta_editor' / 'templates'
        self.naming_dir = Path.home() / '.photo_meta_editor' / 'naming'
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.naming_dir.mkdir(parents=True, exist_ok=True)
        self._create_default_templates()

    def _create_default_templates(self):
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
        path = self.template_dir / filename
        if not path.exists():
            with open(path, 'w') as f:
                json.dump(template, f, indent=2)

    def _save_naming_if_not_exists(self, filename: str, naming: Dict):
        path = self.naming_dir / filename
        if not path.exists():
            with open(path, 'w') as f:
                json.dump(naming, f, indent=2)

    def get_templates(self) -> Dict[str, Dict]:
        templates = {}
        try:
            for file in self.template_dir.glob('*.json'):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        normalized = self._normalize_template_data(data)
                        templates[normalized.get('name', file.stem)] = normalized
                except Exception as e:
                    logger.warning(f"Error loading template {file}: {e}")
        except Exception as e:
            logger.error(f"Error reading templates: {e}")
        return templates

    def get_naming_conventions(self) -> Dict[str, Dict]:
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
        try:
            for file in self.naming_dir.glob('*.json'):
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('name') == name:
                        file.unlink()
                        return True
        except Exception as e:
            logger.error(f"Error deleting naming convention {name}: {e}")
        return False

    def import_template(self, data: Dict) -> Tuple[bool, str]:
        try:
            if 'name' not in data:
                return False, "Template must have a 'name' field"
            normalized = self._normalize_template_data(data)
            name = normalized['name']
            exif = normalized.get('exif', {})
            xmp = normalized.get('xmp', {})
            if self.save_template(name, exif, xmp):
                return True, f"Template '{name}' imported successfully"
            else:
                return False, "Failed to save template"
        except Exception as e:
            return False, f"Import error: {str(e)}"

    def import_naming(self, data: Dict) -> Tuple[bool, str]:
        try:
            if 'name' not in data:
                return False, "Naming convention must have a 'name' field"
            if 'pattern' not in data:
                return False, "Naming convention must have a 'pattern' field"
            name = data['name']
            pattern = data['pattern']
            if self.save_naming(name, pattern):
                return True, f"Naming convention '{name}' imported successfully"
            else:
                return False, "Failed to save naming convention"
        except Exception as e:
            return False, f"Import error: {str(e)}"

    @staticmethod
    def _normalize_template_data(data: Dict) -> Dict:
        exif = data.get('exif') or data.get('EXIF') or {}
        xmp = data.get('xmp') or data.get('XMP') or {}
        name = data.get('name') or data.get('Name') or ''
        data['exif'] = exif
        data['xmp'] = xmp
        data['name'] = name
        return data
