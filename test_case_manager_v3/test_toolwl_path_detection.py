#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test ToolWL Path Detection for Built Executable

This script tests the ScriptVerifier's _find_toolwl_directory() method
to ensure it works correctly in both development and built executable scenarios.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.script_verifier import ScriptVerifier


def test_development_mode():
    """Test ToolWL detection in development mode."""
    print("🧪 Testing Development Mode Path Detection")
    print("=" * 60)
    
    verifier = ScriptVerifier()
    
    print(f"📁 Detected ToolWL path: {verifier.toolwl_path}")
    print(f"📍 Path exists: {verifier.toolwl_path.exists()}")
    print(f"📍 Path is absolute: {verifier.toolwl_path.is_absolute()}")
    
    if verifier.toolwl_path.exists():
        print("✅ ToolWL directory found in development mode")
        
        # List some contents
        scripts = [f for f in verifier.toolwl_path.iterdir() if f.suffix == '.py']
        print(f"📋 Found {len(scripts)} Python scripts:")
        for script in scripts[:5]:  # Show first 5
            print(f"   📄 {script.name}")
        
        return True
    else:
        print("❌ ToolWL directory not found in development mode")
        return False


def simulate_executable_mode():
    """Simulate how path detection would work in built executable."""
    print("\n🧪 Simulating Built Executable Mode")
    print("=" * 60)
    
    # Simulate sys.frozen attribute (set by PyInstaller)
    original_frozen = getattr(sys, 'frozen', False)
    original_executable = sys.executable
    
    try:
        # Simulate PyInstaller environment
        sys.frozen = True
        
        # Simulate executable path (would be in release folder)
        simulated_exe_path = Path(__file__).parent / "release" / "TestCaseManager.exe"
        sys.executable = str(simulated_exe_path)
        
        print(f"🔧 Simulated executable path: {sys.executable}")
        print(f"🔧 Simulated frozen state: {sys.frozen}")
        
        # Test path detection
        verifier = ScriptVerifier()
        
        print(f"📁 Detected ToolWL path: {verifier.toolwl_path}")
        print(f"📍 Expected path: {simulated_exe_path.parent / 'ToolWL'}")
        
        expected_path = simulated_exe_path.parent / "ToolWL"
        if verifier.toolwl_path == expected_path:
            print("✅ Path detection logic correct for executable mode")
            return True
        else:
            print("❌ Path detection logic incorrect for executable mode")
            return False
            
    finally:
        # Restore original values
        if original_frozen:
            sys.frozen = original_frozen
        else:
            delattr(sys, 'frozen')
        sys.executable = original_executable


def test_fallback_scenarios():
    """Test fallback scenarios for path detection."""
    print("\n🧪 Testing Fallback Scenarios")
    print("=" * 60)
    
    # Test with custom path
    custom_path = Path(__file__).parent / "ToolWL"
    verifier = ScriptVerifier(toolwl_path=str(custom_path))
    
    print(f"📁 Custom ToolWL path: {verifier.toolwl_path}")
    print(f"📍 Custom path exists: {verifier.toolwl_path.exists()}")
    
    if verifier.toolwl_path == custom_path:
        print("✅ Custom path override working correctly")
        return True
    else:
        print("❌ Custom path override not working")
        return False


def test_script_execution_capability():
    """Test actual script execution capability."""
    print("\n🧪 Testing Script Execution Capability")
    print("=" * 60)
    
    # Create a simple test script
    test_script_content = '''#!/usr/bin/env python3
import sys
import os

try:
    # Read input
    with open("input.txt", "r", encoding="utf-8") as f:
        data = f.read().strip()
    
    print(f"Test script received: {data}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    
    # Write success output
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write("1")
    
    print("Test script completed successfully")
    
except Exception as e:
    print(f"Test script error: {e}")
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write("0")
'''
    
    # Write test script
    test_script_path = Path(__file__).parent / "ToolWL" / "test_path_detection.py"
    with open(test_script_path, "w", encoding="utf-8") as f:
        f.write(test_script_content)
    
    print(f"✅ Created test script: {test_script_path}")
    
    # Test script execution
    mock_result_data = {
        "summary": {
            "script": {
                "cmd": "test_path_detection.py",
                "input": ["path_detection_test"]
            }
        }
    }
    
    verifier = ScriptVerifier()
    verification_needed, message, verification_passed = verifier.verify_test_result(mock_result_data)
    
    print(f"📊 Script Execution Results:")
    print(f"   Verification needed: {verification_needed}")
    print(f"   Message: {message}")
    print(f"   Verification passed: {verification_passed}")
    
    # Clean up test script
    if test_script_path.exists():
        test_script_path.unlink()
        print("🧹 Cleaned up test script")
    
    return verification_needed and verification_passed


def main():
    """Run all path detection tests."""
    print("🚀 ToolWL Path Detection Test Suite")
    print("=" * 80)
    
    results = []
    
    # Run all tests
    results.append(test_development_mode())
    results.append(simulate_executable_mode())
    results.append(test_fallback_scenarios())
    results.append(test_script_execution_capability())
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary:")
    print(f"   Development mode detection: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   Executable mode simulation: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"   Fallback scenarios: {'✅ PASS' if results[2] else '❌ FAIL'}")
    print(f"   Script execution capability: {'✅ PASS' if results[3] else '❌ FAIL'}")
    
    overall_success = all(results)
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🚀 ToolWL path detection is ready for built executable!")
        print("\n📋 Next Steps:")
        print("   1. Run build.bat to create standalone executable")
        print("   2. Test actual script execution from built .exe")
        print("   3. Verify ToolWL folder structure in release/")
    else:
        print("\n⚠️  Issues detected. Please review the failed tests.")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
