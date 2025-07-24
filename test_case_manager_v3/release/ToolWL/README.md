# ToolWL - Verification Scripts

**Hệ thống script verification tự động cho Test Case Manager v1.0**

## Tổng quan

ToolWL (Tool Verification Library) là thư mục chứa các script verification được thực thi tự động bởi Test Case Manager v1.0 khi test case yêu cầu xác minh PC-side. Hệ thống này cho phép kết hợp kết quả test từ thiết bị OpenWrt với verification từ máy tính để đảm bảo tính chính xác.

## Cấu trúc thư mục

```
ToolWL/
├── README.md                    # Tài liệu này
├── install_all_dependencies.bat # Script cài đặt dependencies
├── input.txt                    # File input cho scripts (tự động tạo)
├── output.txt                   # File output từ scripts (tự động tạo)
├── wireless_edit_ap.py          # Verification cho WiFi tests
├── lan_edit_leasetime.py        # Verification cho LAN DHCP tests
├── lan_edit_ip_start.py         # Verification cho LAN IP tests
├── module.py                    # Common utilities
└── wifi_connect/                # WiFi connection utilities
    ├── __init__.py
    └── core.py
```

## Script Interface Standard

Tất cả verification scripts phải tuân theo interface chuẩn:

### Input Interface
- **File**: `input.txt`
- **Format**: Một parameter mỗi dòng
- **Encoding**: UTF-8
- **Tự động tạo**: Bởi ScriptVerifier trước khi execute

### Output Interface
- **File**: `output.txt`
- **Format**: 
  - `"1"` = Verification PASSED
  - `"0"` = Verification FAILED
- **Encoding**: UTF-8
- **Bắt buộc**: Script phải tạo file này

### Template Script

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Template cho ToolWL verification script
"""

def main():
    try:
        # Đọc input parameters
        with open("input.txt", "r", encoding="utf-8") as f:
            param1 = f.readline().strip()
            param2 = f.readline().strip()
        
        # Thực hiện verification logic
        success = your_verification_logic(param1, param2)
        
        # Ghi kết quả
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("1" if success else "0")
            
    except Exception as e:
        # Ghi fail nếu có lỗi
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("0")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

## Dependencies Management

### Cài đặt tự động
```bash
# Chạy script cài đặt dependencies
install_all_dependencies.bat
```

### Dependencies hiện tại
- **pywifi**: Cho wireless verification
- **requests**: Cho network operations  
- **psutil**: Cho system monitoring
- **wifi_connect**: Local module cho WiFi utilities

### Thêm dependency mới
1. Thêm vào `install_all_dependencies.bat`:
```bat
python -m pip install new_library
if %ERRORLEVEL% NEQ 0 set INSTALL_FAILED=1
```

2. Test trong script:
```bat
python -c "import new_library; print('new_library OK')" 2>nul || set TEST_FAILED=1
```

## Verification Scripts hiện có

### wireless_edit_ap.py
**Mục đích**: Verify WiFi AP configuration và connection test

**Input parameters**:
1. SSID name
2. Password

**Logic**: 
- Sử dụng pywifi để scan và connect đến AP
- Timeout: 20 seconds
- Max retries: 10

**Dependencies**: pywifi, wifi_connect module

### lan_edit_leasetime.py
**Mục đích**: Verify LAN DHCP lease time configuration

**Input parameters**:
1. Expected lease time (seconds)

**Logic**: Kiểm tra DHCP lease time configuration

### lan_edit_ip_start.py  
**Mục đích**: Verify LAN IP range configuration

**Input parameters**:
1. Start IP address
2. End IP address

**Logic**: Kiểm tra IP range configuration

## Cách hoạt động

### 1. Trigger từ Test Response
Khi OpenWrt device trả về response chứa field `script`:
```json
{
  "summary": {
    "total_test_cases": 1,
    "passed": 1,
    "failed": 0
  },
  "script": "wireless_edit_ap.py",
  "script_params": ["TestAP", "password123"]
}
```

### 2. Script Execution Flow
1. **ScriptVerifier** nhận response từ device
2. **Extract script info**: script name và parameters
3. **Write input.txt**: Ghi parameters vào file
4. **Execute script**: Chạy Python script trong ToolWL directory
5. **Read output.txt**: Đọc kết quả verification
6. **Combine results**: Device result + PC verification = Final result

### 3. Result Logic
```
Device: SUCCESS + PC Verification: SUCCESS = Final: SUCCESS
Device: SUCCESS + PC Verification: FAIL    = Final: FAIL  
Device: FAIL    + PC Verification: ANY     = Final: FAIL
```

## Troubleshooting

### Script không chạy được
**Symptoms**: Scripts fail to execute, output.txt missing

**Solutions**:
1. Chạy `install_all_dependencies.bat`
2. Kiểm tra Python installation: `python --version`
3. Test script manually: `python wireless_edit_ap.py`
4. Chạy Test Case Manager as Administrator

### Import Errors
**Symptoms**: `ModuleNotFoundError: No module named 'pywifi'`

**Solutions**:
```bash
# Cài đặt thủ công
pip install pywifi requests psutil

# Kiểm tra
python -c "import pywifi; print('OK')"
```

### Wireless Verification Fails
**Symptoms**: Wireless tests always fail verification

**Solutions**:
1. Kiểm tra WiFi adapter enabled
2. Verify AP đang broadcast
3. Tăng timeout trong script
4. Kiểm tra security type compatibility

### Permission Errors
**Symptoms**: Cannot write to output.txt

**Solutions**:
1. Run as Administrator
2. Check antivirus exclusions
3. Verify file permissions

## Thêm Script mới

### 1. Tạo script file
```python
# new_verification.py
with open("input.txt", "r") as f:
    param = f.readline().strip()

# Your verification logic here
success = verify_something(param)

with open("output.txt", "w") as f:
    f.write("1" if success else "0")
```

### 2. Test script
```bash
cd ToolWL
echo "test_param" > input.txt
python new_verification.py
type output.txt
```

### 3. Integrate với Test Case Manager
Script sẽ tự động được gọi khi OpenWrt response chứa:
```json
{
  "script": "new_verification.py",
  "script_params": ["test_param"]
}
```

## Best Practices

1. **Error Handling**: Luôn có try-catch và ghi "0" khi lỗi
2. **Timeout**: Implement timeout cho operations có thể hang
3. **Logging**: Sử dụng print() để debug, logs sẽ được capture
4. **Dependencies**: Minimize external dependencies
5. **Testing**: Test script độc lập trước khi integrate

## Liên kết

- [Core Documentation](../src/core/README.md) - Test execution engine
- [Utils Documentation](../src/utils/README.md) - ScriptVerifier implementation
- [Main README](../README.md) - Tổng quan hệ thống
