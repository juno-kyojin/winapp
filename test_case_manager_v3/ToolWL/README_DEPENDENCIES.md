# ToolWL Folder - Verification Scripts Dependencies Guide

## Overview
This folder contains verification scripts that are executed automatically by Test Case Manager v1.0 when test cases require PC-side verification.

## Script Interface Standard
All scripts in this folder must follow the standardized interface:

### Input
- Read parameters from `input.txt` (one parameter per line)
- Parameters are provided by the test case response

### Output
- Write result to `output.txt`
- `"1"` = Verification PASSED
- `"0"` = Verification FAILED

### Example Script Structure
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    try:
        # Read input parameters
        with open("input.txt", "r", encoding="utf-8") as f:
            params = [line.strip() for line in f.readlines()]
        
        # Your verification logic here
        result = perform_verification(params)
        
        # Write output
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("1" if result else "0")
            
    except Exception as e:
        print(f"Error: {e}")
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("0")

if __name__ == "__main__":
    main()
```

## Dependency Management

### 1. Standard Python Libraries
Scripts can use any standard Python libraries (os, sys, subprocess, etc.) without additional setup.

### 2. Custom Modules (Included)
The following custom modules are included in this folder:
- `wifi_connect/` - WiFi connection utilities for wireless verification
- `module.py` - Common utilities for network operations

### 3. Adding New Dependencies

#### Option A: Include Module in ToolWL
For custom modules, copy them directly to the ToolWL folder:
```
ToolWL/
├── your_script.py
├── your_module/
│   ├── __init__.py
│   └── core.py
└── another_dependency.py
```

#### Option B: System-wide Installation
For external packages, install them on the target system:
```bash
pip install package_name
```

#### Option C: Bundled Dependencies
For complex dependencies, create a subfolder structure:
```
ToolWL/
├── your_script.py
├── dependencies/
│   ├── package1/
│   └── package2/
└── requirements.txt
```

## Current Scripts

### 1. lan_edit_leasetime.py
- **Purpose**: Verify DHCP lease time configuration
- **Dependencies**: `module.py` (included)
- **Input**: Lease time in seconds
- **Verification**: Checks actual lease time vs configured value

### 2. lan_edit_ip_start.py
- **Purpose**: Verify LAN IP range start configuration
- **Dependencies**: `module.py` (included)
- **Input**: IP start address
- **Verification**: Checks if PC gets IP in correct range

### 3. wireless_edit_ap.py
- **Purpose**: Verify wireless AP configuration
- **Dependencies**: `wifi_connect/` module (included)
- **Input**: SSID, Password
- **Verification**: Attempts to connect to created AP

## Best Practices

### 1. Error Handling
Always include try-catch blocks and write "0" to output.txt on errors.

### 2. Timeout Considerations
Scripts should complete within 60 seconds (system timeout).

### 3. Unicode Support
Use UTF-8 encoding for all file operations to support international characters.

### 4. Logging
Use print statements for debugging - they will appear in Test Case Manager logs.

### 5. Working Directory
Scripts execute with ToolWL as the working directory.

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure dependencies are in ToolWL folder or system PATH
2. **Permission Errors**: Run Test Case Manager as administrator if needed
3. **Timeout Errors**: Optimize script performance or reduce verification scope
4. **Unicode Errors**: Use UTF-8 encoding for all text operations

### Debug Mode
To debug scripts manually:
1. Navigate to ToolWL folder
2. Create test input.txt with parameters
3. Run: `python your_script.py`
4. Check output.txt for results

## Adding New Scripts

1. Create your script following the interface standard
2. Test it manually in ToolWL folder
3. Ensure all dependencies are included or documented
4. Add script name to test case response `script.cmd` field
5. No rebuild of Test Case Manager required!

## Support
For issues with script execution, check Test Case Manager logs for detailed error messages.
