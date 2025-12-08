#!/usr/bin/env python3
"""
Photo Metadata Editor - Validation & Testing Script

This script validates that all core functionality works correctly without launching the GUI.
Run this to verify the application is properly installed and functional.

Usage:
    python3 test_app.py
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Test that we can import the application
print("=" * 70)
print("PHOTO METADATA EDITOR - VALIDATION TEST SUITE")
print("=" * 70)

# Test 1: Imports
print("\n[TEST 1] Module Imports")
print("-" * 70)
try:
    from photo_meta_editor import (
        MetadataManager, TemplateManager, NamingEngine,
        PhotoMetadataEditor
    )
    print("✓ Successfully imported all core modules")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: MetadataManager
print("\n[TEST 2] MetadataManager Initialization")
print("-" * 70)
try:
    mm = MetadataManager()
    print(f"✓ MetadataManager initialized")
    print(f"  Method: {mm.method}")
    print(f"  Using exiftool: {mm.use_exiftool}")
except Exception as e:
    print(f"✗ MetadataManager initialization failed: {e}")
    sys.exit(1)

# Test 3: TemplateManager
print("\n[TEST 3] TemplateManager & Default Templates")
print("-" * 70)
try:
    tm = TemplateManager()
    templates = tm.get_templates()
    conventions = tm.get_naming_conventions()
    
    print(f"✓ TemplateManager initialized")
    print(f"  Storage location: {tm.template_dir.parent}")
    print(f"  Templates found: {len(templates)}")
    for name in templates.keys():
        print(f"    - {name}")
    
    print(f"  Naming conventions found: {len(conventions)}")
    for name in conventions.keys():
        print(f"    - {name}")
    
    if len(templates) < 2:
        print("⚠ Warning: Expected at least 2 default templates")
    if len(conventions) < 2:
        print("⚠ Warning: Expected at least 2 default naming conventions")
    
except Exception as e:
    print(f"✗ TemplateManager test failed: {e}")
    sys.exit(1)

# Test 4: NamingEngine - Token Replacement
print("\n[TEST 4] NamingEngine - Token Replacement")
print("-" * 70)
try:
    ne = NamingEngine()
    
    test_cases = [
        {
            "pattern": "{date}_{title}_{sequence:03d}",
            "sequence": 5,
            "expected_parts": ["2025-01-15", "Test", "005"]
        },
        {
            "pattern": "{datetime:%Y%m%d}_{camera_model}",
            "sequence": 1,
            "expected_parts": ["20250115", "Canon"]
        },
        {
            "pattern": "{original_name}_edited",
            "sequence": 1,
            "expected_parts": ["test_edited"]
        }
    ]
    
    metadata = {
        'exif': {
            'DateTime': '2025:01:15 14:30:22',
            'ImageDescription': 'Test Image',
            'Model': 'Canon EOS 5D'
        }
    }
    
    all_passed = True
    for test in test_cases:
        result = ne.generate_filename(
            test["pattern"],
            "/tmp/test.jpg",
            metadata,
            test["sequence"]
        )
        
        # Remove extension for checking
        result_stem = Path(result).stem
        
        # Check if expected parts are in result
        parts_found = all(part in result_stem for part in test["expected_parts"])
        
        status = "✓" if parts_found else "✗"
        print(f"{status} Pattern: {test['pattern']}")
        print(f"  Result: {result}")
        
        if not parts_found:
            all_passed = False
    
    if all_passed:
        print("\n✓ All naming token tests passed!")
    else:
        print("\n✗ Some naming token tests failed")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ NamingEngine test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Template Save/Load
print("\n[TEST 5] Template Persistence (Save/Load)")
print("-" * 70)
try:
    tm = TemplateManager()
    
    # Create a test template
    test_template_data = {
        "EXIF": {"Artist": "Test Artist", "Copyright": "© 2025"},
        "XMP": {"dc:creator": "Test Artist"}
    }
    
    test_template_name = "Test_Validation_Template"
    
    # Save
    saved = tm.save_template(test_template_name, test_template_data["EXIF"], test_template_data["XMP"])
    print(f"✓ Template saved: {test_template_name}")
    
    # Load
    templates = tm.get_templates()
    if test_template_name in templates:
        print(f"✓ Template loaded successfully")
        template = templates[test_template_name]
        print(f"  EXIF tags: {len(template.get('exif', {}))} items")
        print(f"  XMP properties: {len(template.get('xmp', {}))} items")
    else:
        print(f"✗ Template not found after saving")
        sys.exit(1)
    
    # Cleanup
    tm.delete_template(test_template_name)
    print(f"✓ Test template cleaned up")
    
except Exception as e:
    print(f"✗ Template persistence test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Naming Convention Save/Load
print("\n[TEST 6] Naming Convention Persistence (Save/Load)")
print("-" * 70)
try:
    tm = TemplateManager()
    
    test_naming_name = "Test_Validation_Naming"
    test_pattern = "{date}_{sequence:03d}"
    
    # Save
    saved = tm.save_naming(test_naming_name, test_pattern)
    print(f"✓ Naming convention saved: {test_naming_name}")
    
    # Load
    conventions = tm.get_naming_conventions()
    if test_naming_name in conventions:
        print(f"✓ Naming convention loaded successfully")
        convention = conventions[test_naming_name]
        print(f"  Pattern: {convention.get('pattern')}")
    else:
        print(f"✗ Naming convention not found after saving")
        sys.exit(1)
    
    # Cleanup
    tm.delete_naming(test_naming_name)
    print(f"✓ Test naming convention cleaned up")
    
except Exception as e:
    print(f"✗ Naming convention persistence test failed: {e}")
    sys.exit(1)

# Test 7: Configuration Directories
print("\n[TEST 7] Configuration Directory Structure")
print("-" * 70)
try:
    config_base = Path.home() / '.photo_meta_editor'
    
    dirs_to_check = [
        ('templates', 'Metadata templates'),
        ('naming', 'Naming conventions'),
        ('undo', 'Undo history')
    ]
    
    all_exist = True
    for dir_name, description in dirs_to_check:
        dir_path = config_base / dir_name
        exists = dir_path.exists() and dir_path.is_dir()
        status = "✓" if exists else "✗"
        print(f"{status} {description}: {dir_path}")
        if not exists:
            all_exist = False
    
    if not all_exist:
        print("\n✗ Some configuration directories missing")
        sys.exit(1)
    else:
        print("\n✓ All configuration directories properly set up")
    
except Exception as e:
    print(f"✗ Configuration directory test failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED - APPLICATION IS READY TO USE")
print("=" * 70)
print("\nNext steps:")
print("  1. Run: python3 photo_meta_editor.py")
print("  2. Try the default templates and naming conventions")
print("  3. Create your own templates for your workflow")
print("  4. See README.md for complete usage guide")
print("\nFor setup help, see SETUP_GUIDE.md")
print("=" * 70 + "\n")
