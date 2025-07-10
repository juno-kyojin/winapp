#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Script Execution

This script tests the ScriptVerifier's ability to execute scripts
and helps debug execution issues.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.script_verifier import ScriptVerifier


def test_lan_script_execution():
    """Test LAN script execution."""
    print("🧪 Testing LAN Script Execution")
    print("=" * 50)
    
    # Mock result data for LAN test
    mock_result_data = {
        "summary": {
            "total_test_cases": 1,
            "passed": 1,
            "failed": 0,
            "script": {
                "cmd": "lan_edit_leasetime.py",
                "input": ["43200"]
            }
        }
    }
    
    print("📋 Mock result data:")
    print(f"   Script: {mock_result_data['summary']['script']['cmd']}")
    print(f"   Input: {mock_result_data['summary']['script']['input']}")
    
    # Test ScriptVerifier
    verifier = ScriptVerifier()
    
    print(f"\n📁 ToolWL path: {verifier.toolwl_path}")
    print(f"📍 Path exists: {verifier.toolwl_path.exists()}")
    
    if verifier.toolwl_path.exists():
        # List ToolWL contents
        print("\n📋 ToolWL Contents:")
        for item in verifier.toolwl_path.iterdir():
            if item.is_file():
                print(f"   📄 {item.name}")
    
    print("\n🔍 Running script verification...")
    verification_needed, message, verification_passed = verifier.verify_test_result(mock_result_data)
    
    print(f"\n📊 Results:")
    print(f"   Verification needed: {verification_needed}")
    print(f"   Message: {message}")
    print(f"   Verification passed: {verification_passed}")
    
    return verification_needed and verification_passed


def test_simple_script():
    """Test with a simple script."""
    print("\n🧪 Testing Simple Script")
    print("=" * 50)
    
    # Create a simple test script
    simple_script_path = Path("test_case_manager_v3/ToolWL/simple_test.py")
    
    simple_script_content = '''#!/usr/bin/env python3
# Simple test script
import sys

if __name__ == "__main__":
    try:
        with open("input.txt", "r", encoding="utf-8") as f:
            input_data = f.read().strip()
        
        print(f"Received input: {input_data}")
        
        # Always pass for testing
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("1")
        
        print("Simple test completed successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("0")
'''
    
    # Write simple script
    with open(simple_script_path, "w", encoding="utf-8") as f:
        f.write(simple_script_content)
    
    print(f"✅ Created simple test script: {simple_script_path}")
    
    # Test with simple script
    mock_result_data = {
        "summary": {
            "script": {
                "cmd": "simple_test.py",
                "input": ["test_input"]
            }
        }
    }
    
    verifier = ScriptVerifier()
    verification_needed, message, verification_passed = verifier.verify_test_result(mock_result_data)
    
    print(f"\n📊 Simple Script Results:")
    print(f"   Verification needed: {verification_needed}")
    print(f"   Message: {message}")
    print(f"   Verification passed: {verification_passed}")
    
    return verification_needed and verification_passed


if __name__ == "__main__":
    print("🚀 Script Execution Debug Test")
    print("=" * 70)
    
    # Test 1: LAN script
    result1 = test_lan_script_execution()
    
    # Test 2: Simple script
    result2 = test_simple_script()
    
    print("\n" + "=" * 70)
    print("📊 Final Results:")
    print(f"   LAN script test: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"   Simple script test: {'✅ PASS' if result2 else '❌ FAIL'}")
    
    if result1 and result2:
        print("\n🎉 All tests passed! Script execution is working.")
    else:
        print("\n⚠️  Some tests failed. Check the logs for details.")
