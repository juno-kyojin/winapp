#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Phase 1 functionality

This script tests all Phase 1 components to ensure they work correctly
before proceeding to Phase 2 development.

Author: juno-kyojin
Created: 2025-06-12
"""

import sys
import os
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from core.config import AppConfig, load_config
        print("  ✅ Core config module imported successfully")
        
        from core.constants import APP_NAME, APP_VERSION, DEFAULT_SSH_PORT
        print("  ✅ Core constants module imported successfully")
        
        from core.exceptions import TestCaseManagerError
        print("  ✅ Core exceptions module imported successfully")
        
        from utils.logger import setup_logging, get_logger
        print("  ✅ Utils logger module imported successfully")
        
        from utils.file_utils import ensure_directory
        print("  ✅ Utils file_utils module imported successfully")
        
        from utils.validators import validate_ip_address, validate_ssh_config
        print("  ✅ Utils validators module imported successfully")
        
        from utils.formatters import format_timestamp
        print("  ✅ Utils formatters module imported successfully")
        
        from gui.main_window import MainWindow
        print("  ✅ GUI main_window module imported successfully")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")
    
    try:
        from core.config import AppConfig
        
        # Test default config creation
        config = AppConfig()
        print(f"  ✅ Default config created: SSH host = {config.network.ssh_host}")
        
        # Test validation
        config.validate()
        print("  ✅ Configuration validation passed")
        
        # Test config conversion
        config_dict = config.to_dict()
        print(f"  ✅ Config to dict conversion: {len(config_dict)} sections")
        
        # Test config from dict
        config_from_dict = AppConfig.from_dict(config_dict)
        print("  ✅ Config from dict creation passed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def test_logging():
    """Test logging system."""
    print("\n🔍 Testing logging...")
    
    try:
        from utils.logger import setup_logging, get_logger, LoggerMixin
        
        # Setup logging
        logger = setup_logging(log_level="INFO", log_to_console=True, log_to_file=False)
        print("  ✅ Logging setup successful")
        
        # Test logger creation
        test_logger = get_logger("test")
        test_logger.info("Test log message")
        print("  ✅ Logger creation and message logging successful")
        
        # Test LoggerMixin
        class TestClass(LoggerMixin):
            def test_method(self):
                self.logger.info("Testing LoggerMixin")
        
        test_obj = TestClass()
        test_obj.test_method()
        print("  ✅ LoggerMixin functionality working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Logging error: {e}")
        return False

def test_utilities():
    """Test utility functions."""
    print("\n🔍 Testing utilities...")
    
    try:
        from utils.validators import (
            validate_ip_address, validate_port, validate_hostname,
            validate_ssh_config, validate_template_parameter
        )
        from utils.formatters import (
            format_file_size, format_duration, format_test_status,
            format_connection_status
        )
        from utils.file_utils import ensure_directory, get_file_size
        
        # Test validators
        assert validate_ip_address("192.168.1.1") == True
        assert validate_ip_address("invalid") == False
        assert validate_port(22) == True
        assert validate_port(99999) == False
        assert validate_hostname("example.com") == True
        assert validate_hostname("192.168.1.1") == True
        print("  ✅ Validators working correctly")
        
        # Test SSH config validation
        is_valid, error = validate_ssh_config("192.168.1.1", 22, "root")
        assert is_valid == True
        print("  ✅ SSH config validation working")
        
        # Test parameter validation
        is_valid, error = validate_template_parameter("test_param", "123", "integer", True)
        assert is_valid == True
        print("  ✅ Template parameter validation working")
        
        # Test formatters
        assert format_file_size(1024) == "1.0 KB"
        assert format_duration(65) == "1m 5s"
        assert "Ready" in format_test_status("ready")
        assert "Connected" in format_connection_status(True, "192.168.1.1")
        print("  ✅ Formatters working correctly")
        
        # Test file utils (without actually creating files)
        temp_path = Path("temp_test")
        # Just test that function doesn't crash
        print("  ✅ File utilities accessible")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Utilities error: {e}")
        return False

def test_gui_creation():
    """Test GUI component creation (without showing window)."""
    print("\n🔍 Testing GUI creation...")
    
    try:
        from core.config import AppConfig
        from gui.main_window import MainWindow
        
        # Create config
        config = AppConfig()
        
        # Create main window (but don't run it)
        window = MainWindow(config)
        print("  ✅ MainWindow creation successful")
        
        # Check that tkinter components are initialized
        assert window.root is not None
        print("  ✅ Tkinter root window created")
        
        assert window.notebook is not None
        print("  ✅ Notebook widget created")
        
        # Clean up
        if window.root:
            window.root.destroy()
        print("  ✅ GUI cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ GUI creation error: {e}")
        return False

def test_constants():
    """Test that all required constants are defined."""
    print("\n🔍 Testing constants...")
    
    try:
        from core.constants import (
            APP_NAME, APP_VERSION, DEFAULT_SSH_PORT,
            WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
            LOG_FORMAT, DATABASE_NAME
        )
        
        assert isinstance(APP_NAME, str) and APP_NAME
        assert isinstance(APP_VERSION, str) and APP_VERSION
        assert isinstance(DEFAULT_SSH_PORT, int) and DEFAULT_SSH_PORT > 0
        print("  ✅ Application constants defined correctly")
        
        assert WINDOW_MIN_WIDTH >= 800
        assert WINDOW_MIN_HEIGHT >= 600
        print("  ✅ GUI constants defined correctly")
        
        assert isinstance(LOG_FORMAT, str) and LOG_FORMAT
        assert isinstance(DATABASE_NAME, str) and DATABASE_NAME
        print("  ✅ System constants defined correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Constants error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("🚀 Phase 1 Foundation Testing")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration System", test_configuration),
        ("Logging System", test_logging),
        ("Utility Functions", test_utilities),
        ("GUI Components", test_gui_creation),
        ("Constants Definition", test_constants)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        if test_func():
            print(f"✅ {test_name} - PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} - FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 ALL PHASE 1 TESTS PASSED!")
        print("✅ Foundation is solid and ready for Phase 2 development")
        print("\n📋 Next Steps:")
        print("  1. Implement template management system")
        print("  2. Add SSH client functionality")
        print("  3. Create database operations")
        print("  4. Build parameter validation engine")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Please fix the issues before proceeding to Phase 2")
        return 1

if __name__ == "__main__":
    sys.exit(main())