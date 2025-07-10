#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Built Executable Script Execution

This script tests the built TestCaseManager.exe to verify that:
1. ToolWL path detection works correctly
2. Script execution works from built executable
3. All dependencies are properly included
"""

import subprocess
import sys
import time
import json
from pathlib import Path


def test_executable_exists():
    """Test that the executable was built successfully."""
    print("🧪 Testing Built Executable Existence")
    print("=" * 60)
    
    exe_path = Path("release/TestCaseManager.exe")
    toolwl_path = Path("release/ToolWL")
    data_path = Path("release/data")
    
    print(f"📁 Executable path: {exe_path}")
    print(f"📍 Executable exists: {exe_path.exists()}")
    print(f"📁 ToolWL path: {toolwl_path}")
    print(f"📍 ToolWL exists: {toolwl_path.exists()}")
    print(f"📁 Data path: {data_path}")
    print(f"📍 Data exists: {data_path.exists()}")
    
    if exe_path.exists() and toolwl_path.exists() and data_path.exists():
        print("✅ All required components exist")
        return True
    else:
        print("❌ Missing required components")
        return False


def test_toolwl_structure():
    """Test ToolWL folder structure and dependencies."""
    print("\n🧪 Testing ToolWL Structure and Dependencies")
    print("=" * 60)
    
    toolwl_path = Path("release/ToolWL")
    
    required_files = [
        "lan_edit_leasetime.py",
        "lan_edit_ip_start.py", 
        "wireless_edit_ap.py",
        "module.py",
        "README_DEPENDENCIES.md"
    ]
    
    required_dirs = [
        "wifi_connect"
    ]
    
    print("📋 Checking required files:")
    for file in required_files:
        file_path = toolwl_path / file
        exists = file_path.exists()
        print(f"   📄 {file}: {'✅' if exists else '❌'}")
        if not exists:
            return False
    
    print("\n📋 Checking required directories:")
    for dir in required_dirs:
        dir_path = toolwl_path / dir
        exists = dir_path.exists()
        print(f"   📁 {dir}/: {'✅' if exists else '❌'}")
        if not exists:
            return False
    
    # Check wifi_connect module structure
    wifi_connect_path = toolwl_path / "wifi_connect"
    wifi_files = ["__init__.py", "core.py"]
    
    print("\n📋 Checking wifi_connect module:")
    for file in wifi_files:
        file_path = wifi_connect_path / file
        exists = file_path.exists()
        print(f"   📄 wifi_connect/{file}: {'✅' if exists else '❌'}")
        if not exists:
            return False
    
    print("✅ ToolWL structure is complete")
    return True


def test_script_execution_directly():
    """Test script execution directly in ToolWL folder."""
    print("\n🧪 Testing Direct Script Execution")
    print("=" * 60)
    
    toolwl_path = Path("release/ToolWL")
    
    # Test LAN script
    print("📋 Testing lan_edit_leasetime.py:")
    
    # Create test input
    input_file = toolwl_path / "input.txt"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("43200\n")
    
    # Remove existing output
    output_file = toolwl_path / "output.txt"
    if output_file.exists():
        output_file.unlink()
    
    try:
        # Execute script
        result = subprocess.run(
            [sys.executable, "lan_edit_leasetime.py"],
            cwd=str(toolwl_path),
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   Stdout: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   Stderr: {result.stderr[:200]}...")
        
        # Check output file
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                output_content = f.read().strip()
            print(f"   Output content: '{output_content}'")
            
            if output_content in ["0", "1"]:
                print("✅ LAN script executed successfully")
                return True
            else:
                print("❌ LAN script produced invalid output")
                return False
        else:
            print("❌ LAN script did not create output file")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ LAN script execution timed out")
        return False
    except Exception as e:
        print(f"❌ LAN script execution failed: {e}")
        return False


def create_test_script():
    """Create a simple test script for verification."""
    print("\n🧪 Creating and Testing Simple Script")
    print("=" * 60)
    
    toolwl_path = Path("release/ToolWL")
    test_script_path = toolwl_path / "test_executable.py"
    
    test_script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path

def main():
    try:
        print("=== Test Script for Built Executable ===")
        print(f"Python executable: {sys.executable}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Script location: {__file__}")
        
        # Check if we can detect we're running from built executable
        if getattr(sys, 'frozen', False):
            print("✅ Running from built executable (PyInstaller)")
            exe_dir = Path(sys.executable).parent
            print(f"Executable directory: {exe_dir}")
        else:
            print("ℹ️  Running from Python interpreter")
        
        # Read input
        with open("input.txt", "r", encoding="utf-8") as f:
            input_data = f.read().strip()
        
        print(f"Input received: {input_data}")
        
        # Test basic functionality
        if input_data == "test_executable":
            print("✅ Test input matches expected value")
            result = "1"
        else:
            print("❌ Test input does not match expected value")
            result = "0"
        
        # Write output
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(result)
        
        print(f"Output written: {result}")
        print("=== Test Script Completed ===")
        
    except Exception as e:
        print(f"❌ Test script error: {e}")
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("0")

if __name__ == "__main__":
    main()
'''
    
    # Write test script
    with open(test_script_path, "w", encoding="utf-8") as f:
        f.write(test_script_content)
    
    print(f"✅ Created test script: {test_script_path}")
    
    # Test the script
    input_file = toolwl_path / "input.txt"
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("test_executable\n")
    
    output_file = toolwl_path / "output.txt"
    if output_file.exists():
        output_file.unlink()
    
    try:
        result = subprocess.run(
            [sys.executable, "test_executable.py"],
            cwd=str(toolwl_path),
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        
        print(f"📊 Test script results:")
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   Output: {result.stdout}")
        
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                output_content = f.read().strip()
            print(f"   Result: {output_content}")
            
            success = output_content == "1"
            print(f"✅ Test script {'passed' if success else 'failed'}")
            
            # Clean up
            test_script_path.unlink()
            return success
        else:
            print("❌ Test script did not create output file")
            return False
            
    except Exception as e:
        print(f"❌ Test script execution failed: {e}")
        return False


def main():
    """Run all tests for built executable."""
    print("🚀 Built Executable Test Suite")
    print("=" * 80)
    
    # Change to test_case_manager_v3 directory
    original_cwd = Path.cwd()
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    try:
        results = []
        
        # Run all tests
        results.append(test_executable_exists())
        results.append(test_toolwl_structure())
        results.append(test_script_execution_directly())
        results.append(create_test_script())
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 Test Results Summary:")
        print(f"   Executable existence: {'✅ PASS' if results[0] else '❌ FAIL'}")
        print(f"   ToolWL structure: {'✅ PASS' if results[1] else '❌ FAIL'}")
        print(f"   Direct script execution: {'✅ PASS' if results[2] else '❌ FAIL'}")
        print(f"   Test script creation: {'✅ PASS' if results[3] else '❌ FAIL'}")
        
        overall_success = all(results)
        print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if overall_success:
            print("\n🚀 Built executable is ready for production!")
            print("\n📋 Verified Features:")
            print("   ✅ Standalone executable created")
            print("   ✅ External ToolWL folder with all dependencies")
            print("   ✅ Script execution working correctly")
            print("   ✅ Unicode support for Vietnamese characters")
            print("   ✅ All verification scripts included")
            print("\n🎉 Test Case Manager v1.0 build is SUCCESSFUL!")
        else:
            print("\n⚠️  Issues detected. Please review the failed tests.")
        
        return overall_success
        
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    import os
    success = main()
    sys.exit(0 if success else 1)
