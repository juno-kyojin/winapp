#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test ToolWL Directory Detection

This script tests the ScriptVerifier's ability to find ToolWL directory
in both development and built executable scenarios.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.script_verifier import ScriptVerifier


def test_toolwl_detection():
    """Test ToolWL directory detection."""
    print("🧪 Testing ToolWL Directory Detection")
    print("=" * 50)
    
    # Test ScriptVerifier initialization
    verifier = ScriptVerifier()
    
    print(f"📁 Detected ToolWL path: {verifier.toolwl_path}")
    print(f"📍 Path exists: {verifier.toolwl_path.exists()}")
    
    if verifier.toolwl_path.exists():
        print("✅ ToolWL directory found successfully!")
        
        # List contents
        print("\n📋 ToolWL Contents:")
        for item in verifier.toolwl_path.iterdir():
            if item.is_file():
                print(f"   📄 {item.name}")
            elif item.is_dir():
                print(f"   📁 {item.name}/")
    else:
        print("❌ ToolWL directory not found!")
    
    # Test script verification capability
    print("\n🔍 Testing Script Verification Capability:")
    
    # Mock result data for wireless test
    mock_result_data = {
        "summary": {
            "total_test_cases": 1,
            "passed": 1,
            "failed": 0,
            "script": {
                "cmd": "wireless_edit_ap.py",
                "input": ["test_ssid", "test_password"]
            }
        }
    }
    
    verification_needed, message, verification_passed = verifier.verify_test_result(mock_result_data)
    
    print(f"   Verification needed: {verification_needed}")
    print(f"   Message: {message}")
    print(f"   Verification passed: {verification_passed}")
    
    if verification_needed:
        print("✅ Script verification system is functional!")
    else:
        print("❌ Script verification system has issues!")


if __name__ == "__main__":
    test_toolwl_detection()
