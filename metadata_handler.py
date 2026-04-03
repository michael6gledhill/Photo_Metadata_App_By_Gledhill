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
    piexif = None
    HAS_PIEXIF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

logger = logging.getLogger(__name__)


class MetadataManager:
    """Handles metadata reading/writing using piexif (EXIF) and sidecar XMP."""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.gif', '.bmp'}

    def __init__(self):
        self.method = "piexif + embedded XMP"
        self.naming_dir = Path.home() / '.photo_meta_editor' / 'naming'
        self.naming_dir.mkdir(parents=True, exist_ok=True)

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract EXIF and XMP metadata from a file.
        Returns:
            dict with 'exif' and 'xmp' keys, each containing tag->value mappings
        """
        metadata = {'exif': {}, 'xmp': {}, 'method': 'piexif + embedded XMP'}
        try:
            metadata.update(self._get_metadata_python(file_path, comprehensive=False))
        except Exception as e:
            logger.warning(f"Error reading metadata from {file_path}: {e}")
        return metadata

    def get_metadata_for_view(self, file_path: str) -> Dict[str, Any]:
        """
        Read metadata using a comprehensive, view-only strategy.
        This is intentionally separate from write/apply logic so the viewer can
        expose as much on-disk metadata as possible.
        """
        metadata = {'exif': {}, 'xmp': {}, 'method': 'comprehensive view read'}
        try:
            metadata.update(self._get_metadata_python(file_path, comprehensive=True))
        except Exception as e:
            logger.warning(f"Error reading metadata for view from {file_path}: {e}")
        return metadata


    def _get_metadata_python(self, file_path: str, comprehensive: bool = False) -> Dict[str, Any]:
        """
        Extract metadata using piexif (EXIF) and XMP (sidecar and embedded).
        Robust handling of all tag types and encodings.
        """
        exif_data = {}
        xmp_data = {}

        # EXIF via piexif - robust parsing
        if HAS_PIEXIF and piexif is not None:
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

        # Embedded XMP
        try:
            xmp_data.update(self._read_embedded_xmp(file_path))
        except Exception as e:
            logger.debug(f"embedded XMP read error: {e}")

        # Sidecar XMP (view mode only)
        if comprehensive:
            try:
                xmp_data.update(self._read_sidecar_xmp(file_path))
            except Exception as e:
                logger.debug(f"sidecar XMP read error: {e}")

            # Pillow-level metadata often exposes additional fields not surfaced by piexif
            if HAS_PIL and Image is not None:
                try:
                    with Image.open(file_path) as img:
                        # EXIF via Pillow map
                        try:
                            pil_exif = img.getexif()
                            if pil_exif:
                                for tag_id, value in pil_exif.items():
                                    tag_name = f"PIL:0x{int(tag_id):04X}"
                                    exif_data.setdefault(tag_name, value)
                        except Exception:
                            pass

                        # Generic info dict may include textual metadata chunks
                        try:
                            for k, v in (img.info or {}).items():
                                key = str(k)
                                if key.lower() in {"xmp", "xml:com.adobe.xmp", "raw profile type exif", "exif"}:
                                    continue
                                exif_data.setdefault(f"ImageInfo:{key}", v)
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"Pillow comprehensive read error: {e}")

        return {'exif': exif_data, 'xmp': xmp_data}

    def _read_sidecar_xmp(self, file_path: str) -> Dict[str, Any]:
        """Read sidecar XMP metadata from <image>.xmp when present."""
        sidecar = Path(file_path).with_suffix('.xmp')
        if not sidecar.exists():
            return {}

        try:
            text = sidecar.read_text(encoding='utf-8', errors='replace')
            root = ET.fromstring(text)
        except Exception:
            return {}

        xmp_dict: Dict[str, Any] = {}
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
                    values = [(li.text or '').strip() for li in li_nodes if (li.text or '').strip()]
                    xmp_dict[local_name] = values if len(values) > 1 else (values[0] if values else '')
                else:
                    text_value = (child.text or '').strip()
                    if text_value:
                        xmp_dict[local_name] = text_value
        return xmp_dict

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

    @staticmethod
    def _normalize_metadata_dict(values: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata values into JSON/view friendly scalar or list forms."""
        normalized: Dict[str, Any] = {}
        for key, value in values.items():
            if isinstance(value, bytes):
                normalized[key] = value.decode('utf-8', errors='replace').rstrip('\x00')
            elif isinstance(value, tuple):
                normalized[key] = [str(v) for v in value]
            elif isinstance(value, list):
                normalized[key] = [str(v) for v in value]
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def _canonical_xmp_key(key: str) -> str:
        key_str = str(key)
        key_str = key_str.split(':')[-1] if ':' in key_str else key_str
        return key_str.strip().lower()

    @staticmethod
    def _normalize_compare_value(value: Any) -> Any:
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace').strip()
        if isinstance(value, list):
            return [str(v).strip() for v in value]
        if isinstance(value, tuple):
            return [str(v).strip() for v in value]
        return str(value).strip() if value is not None else ""

    def verify_metadata(self, file_path: str, expected_exif: Dict[str, Any], expected_xmp: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verify that written metadata matches expected values."""
        issues: List[str] = []
        actual = self.get_metadata_for_view(file_path)
        actual_exif = actual.get('exif', {}) or {}
        actual_xmp = actual.get('xmp', {}) or {}

        ext = Path(file_path).suffix.lower()
        supports_exif_verify = ext in {'.jpg', '.jpeg'}
        supports_xmp_verify = ext in {'.jpg', '.jpeg'}

        if supports_exif_verify:
            for key, expected in (expected_exif or {}).items():
                if key not in actual_exif:
                    issues.append(f"EXIF missing: {key}")
                    continue
                actual_value = self._normalize_compare_value(actual_exif.get(key))
                expected_value = self._normalize_compare_value(expected)
                if actual_value != expected_value:
                    issues.append(f"EXIF mismatch: {key} (expected '{expected_value}', got '{actual_value}')")

        canonical_actual_xmp = {
            self._canonical_xmp_key(k): v for k, v in actual_xmp.items()
        }
        if supports_xmp_verify:
            for key, expected in (expected_xmp or {}).items():
                canonical = self._canonical_xmp_key(key)
                if canonical not in canonical_actual_xmp:
                    issues.append(f"XMP missing: {key}")
                    continue
                actual_value = self._normalize_compare_value(canonical_actual_xmp.get(canonical))
                expected_value = self._normalize_compare_value(expected)
                if actual_value != expected_value:
                    issues.append(f"XMP mismatch: {key} (expected '{expected_value}', got '{actual_value}')")

        return len(issues) == 0, issues
    
    def set_metadata(self, file_path: str, exif_data: Optional[Dict] = None, xmp_data: Optional[Dict] = None,
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
                os.replace(temp_path, file_path)
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")

            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False
    
    def _set_metadata_python(self, file_path: str, exif_data: Optional[Dict] = None,
                             xmp_data: Optional[Dict] = None, merge: bool = False) -> bool:
        """
        Write metadata using piexif and sidecar XMP.
        Robust encoding handling and tag mapping.
        """
        try:
            # Write EXIF using piexif
            if HAS_PIEXIF and piexif is not None and exif_data:
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
            if self._is_jpeg(temp_path):
                # JPEG path: prefer Pillow rewrite for stability, then clear EXIF/XMP leftovers.
                if HAS_PIL and Image is not None:
                    try:
                        self._strip_metadata_with_pillow(temp_path)
                        success = True
                    except Exception as e:
                        logger.warning(f"Pillow JPEG delete error: {e}")

                if not success and HAS_PIEXIF and piexif is not None:
                    try:
                        piexif.insert(piexif.dump({
                            "0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None
                        }), temp_path)
                        success = True
                    except Exception as e:
                        logger.warning(f"piexif JPEG delete error: {e}")

                if success:
                    try:
                        self._remove_xmp_from_jpeg(temp_path)
                    except Exception as e:
                        logger.warning(f"JPEG XMP delete error: {e}")

            elif HAS_PIL and Image is not None:
                try:
                    self._strip_metadata_with_pillow(temp_path)
                    success = True
                    logger.info(f"Deleted metadata from {Path(file_path).name} using Pillow")
                except Exception as e:
                    logger.warning(f"Pillow delete error: {e}")

            # Remove sidecar XMP, if present
            sidecar = Path(file_path).with_suffix('.xmp')
            if sidecar.exists():
                try:
                    sidecar.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove sidecar XMP {sidecar.name}: {e}")

            # Verify temp image is still readable before replacing original
            if success and not self._is_readable_image(temp_path):
                logger.error(f"Metadata delete produced unreadable file for {Path(file_path).name}; rolling back")
                success = False
            
            if success:
                os.replace(temp_path, file_path)
                return True
            else:
                os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False

    def _is_readable_image(self, file_path: str) -> bool:
        """Best-effort validation to avoid committing corrupted image output."""
        path = Path(file_path)
        if not path.exists() or path.stat().st_size == 0:
            return False

        if HAS_PIL and Image is not None:
            try:
                with Image.open(file_path) as img:
                    img.verify()
                return True
            except Exception as e:
                logger.warning(f"Image readability check failed for {path.name}: {e}")
                return False

        # If Pillow isn't available, at least require non-empty file
        return True

    def _strip_jpeg_metadata_segments(self, file_path: str) -> None:
        """Remove APPn and COM segments from JPEG while preserving image scan data."""
        with open(file_path, 'rb') as f:
            data = f.read()

        if len(data) < 4 or data[0:2] != b'\xff\xd8':
            raise ValueError("Not a valid JPEG file")

        out = bytearray(data[0:2])  # SOI
        pos = 2

        while pos < len(data):
            if pos + 1 >= len(data):
                break

            if data[pos] != 0xFF:
                # Unexpected raw data before SOS; keep remaining bytes
                out.extend(data[pos:])
                break

            # Skip padding FF bytes
            while pos < len(data) and data[pos] == 0xFF:
                pos += 1
            if pos >= len(data):
                break

            marker = data[pos]
            pos += 1

            # Markers without length
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                out.extend([0xFF, marker])
                if marker == 0xD9:
                    break
                continue

            if pos + 1 >= len(data):
                break

            seg_len = (data[pos] << 8) | data[pos + 1]
            if seg_len < 2 or pos + seg_len > len(data):
                break

            segment_start = pos - 1  # marker byte position
            segment_end = pos + seg_len

            # Start of scan: keep SOS + entropy data through EOI as-is
            if marker == 0xDA:
                out.extend(data[segment_start:segment_end])
                out.extend(data[segment_end:])
                break

            # Drop APPn (E0-EF) and COM (FE), keep others
            if not ((0xE0 <= marker <= 0xEF) or marker == 0xFE):
                out.extend(data[segment_start:segment_end])

            pos = segment_end

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

    def _strip_metadata_with_pillow(self, file_path: str) -> None:
        """Strip metadata from non-JPEG images by re-saving via Pillow."""
        if not HAS_PIL or Image is None:
            raise RuntimeError("Pillow is not available")

        ext = Path(file_path).suffix.lower()
        with Image.open(file_path) as img:
            fmt = (img.format or "").upper()

            # Rebuild image from pixels to avoid carrying metadata dict/info chunks.
            # This is more stable than passing format-specific metadata kwargs.
            if fmt == "GIF":
                # Keep first frame only for metadata stripping consistency.
                clean = img.convert("RGBA")
                clean.save(file_path, format="GIF", save_all=False)
                return

            clean = Image.new(img.mode, img.size)
            pixel_data = [px for px in img.getdata()]
            clean.putdata(pixel_data)

            save_kwargs: Dict[str, Any] = {}
            if ext in {'.jpg', '.jpeg'} or fmt == "JPEG":
                save_kwargs.update({"quality": 95, "subsampling": 0, "optimize": True})
                clean = clean.convert("RGB")
                clean.save(file_path, format="JPEG", **save_kwargs)
                return

            if ext == '.png' or fmt == "PNG":
                clean.save(file_path, format="PNG", optimize=True)
                return

            if ext in {'.tif', '.tiff'} or fmt == "TIFF":
                clean.save(file_path, format="TIFF")
                return

            if ext == '.bmp' or fmt == "BMP":
                clean.save(file_path, format="BMP")
                return

            # Generic fallback
            clean.save(file_path)

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
    
    def generate_filename(self, pattern: str, file_path: str, metadata: Optional[Dict] = None, sequence: int = 1) -> str:
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
        
        # Handle {sequence} and {sequence:NNd} for zero-padded numbering
        def _seq_repl(match: re.Match) -> str:
            width = match.group(1)
            if width:
                try:
                    return f"{sequence:0{int(width)}d}"
                except Exception:
                    return str(sequence)
            return str(sequence)
        result = re.sub(r"\{sequence(?::(\d+)d)?\}", _seq_repl, result)
        
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
            target_name = name.strip()
            target_stem = target_name.lower().replace(' ', '_')
            for file in self.template_dir.glob('*.json'):
                with open(file, 'r') as f:
                    data = json.load(f)
                    file_name = data.get('name', file.stem)
                    if file_name == target_name or file.stem == target_stem or file_name.lower().replace(' ', '_') == target_stem:
                        file.unlink()
                        return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
        return False

    def delete_naming(self, name: str) -> bool:
        try:
            target_name = name.strip()
            target_stem = target_name.lower().replace(' ', '_')
            for file in self.naming_dir.glob('*.json'):
                with open(file, 'r') as f:
                    data = json.load(f)
                    file_name = data.get('name', file.stem)
                    if file_name == target_name or file.stem == target_stem or file_name.lower().replace(' ', '_') == target_stem:
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
        raw_xmp = data.get('xmp') or data.get('XMP') or {}
        xmp = {}
        for key, value in raw_xmp.items():
            clean_key = str(key).split(':')[-1] if ':' in str(key) else str(key)
            xmp[clean_key] = value
        name = data.get('name') or data.get('Name') or ''
        data['exif'] = exif
        data['xmp'] = xmp
        data['name'] = name
        return data
