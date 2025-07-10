# Test Case Manager v1.0

**Công cụ quản lý và thực thi Test Case toàn diện cho thiết bị OpenWrt**

[![Phiên bản](https://img.shields.io/badge/phiên_bản-1.0-blue.svg)](https://github.com/juno-kyojin/winapp)
[![Nền tảng](https://img.shields.io/badge/nền_tảng-Windows-lightgrey.svg)](https://github.com/juno-kyojin/winapp)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)

## Tổng quan

Test Case Manager v1.0 là ứng dụng Windows chuyên nghiệp được thiết kế để kiểm thử toàn diện các thiết bị OpenWrt. Ứng dụng cung cấp giao diện trực quan với 5 tab chính để tạo, quản lý và thực thi các test case từ xa thông qua giao thức HTTP.

### Tính năng chính

- **Thực thi test từ xa**: Chạy test case trên thiết bị OpenWrt từ máy tính Windows qua HTTP (port 6262)
- **Script verification tự động**: Thực thi script PC-side từ ToolWL folder để xác minh kết quả test (120s timeout)
- **Intelligent retry mechanism**: Phân biệt network errors và application errors với retry logic thông minh
- **Wireless test optimization**: 60 retries với 3s delays cho wireless tests, conservative backoff
- **Giao diện 5 tab**: Connection, Templates, Queue, Stream (placeholder), Logs với chức năng chuyên biệt
- **Ứng dụng độc lập**: Single executable với embedded assets, không cần cài đặt Python
- **Thread-safe operations**: File locking, non-blocking connections, background test execution

## Kiến trúc hệ thống

Test Case Manager v1.0 được xây dựng với kiến trúc modular, mỗi component có chức năng riêng biệt:

```
test_case_manager_v3/
├── src/
│   ├── core/          # Constants, config, test case loading, result management
│   ├── gui/           # MainWindow với 5 tabs, panels, widgets, dialogs
│   ├── network/       # TestExecutor, ConnectionManager, HTTPTestClient
│   └── utils/         # ScriptVerifier, logger, error classification, file utils
├── ToolWL/            # Verification scripts với dependencies
├── data/              # Templates, logs, config, results
├── assets/            # Images và resources (embedded trong .exe)
├── build.bat          # Build script tạo standalone executable
├── run.py             # Entry point cho development
└── requirements.txt   # Python dependencies
```

### Component Documentation

- **[Core Documentation](src/core/README.md)** - TestCaseLoader, ResultManager, configuration, constants
- **[GUI Documentation](src/gui/README.md)** - MainWindow, panels, widgets, dialogs, event handling
- **[Network Documentation](src/network/README.md)** - TestExecutor, HTTP communication, retry mechanisms
- **[Utils Documentation](src/utils/README.md)** - ScriptVerifier, logging, error types, file utilities
- **[ToolWL Documentation](ToolWL/README.md)** - Verification scripts, dependencies, interface standard

## Cài đặt và sử dụng

### Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|-------------|
| **Hệ điều hành** | Windows 10/11 (64-bit) |
| **Python** | 3.8+ (cho ToolWL scripts) |
| **Mạng** | Kết nối TCP đến thiết bị OpenWrt |
| **Cổng** | Cổng 6262 mở trên thiết bị OpenWrt |

### Khởi chạy nhanh

**Cho người dùng cuối:**

1. Tải xuống phiên bản mới nhất từ thư mục `release/`
2. Chạy `TestCaseManager.exe` (single executable, không cần giải nén)
3. **QUAN TRỌNG**: Chạy `ToolWL/install_all_dependencies.bat` để cài đặt Python dependencies
4. Cấu hình kết nối trong tab Connection (IP: 192.168.1.1, Port: 6262)

**Cho nhà phát triển:**

```bash
# Clone repository
git clone https://github.com/juno-kyojin/winapp.git
cd winapp/test_case_manager_v3

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy từ mã nguồn
python run.py

# Build executable
build.bat
```

### Hướng dẫn sử dụng cơ bản

#### 1. Kết nối thiết bị
- Mở tab **Connection**
- Nhập IP thiết bị OpenWrt (ví dụ: `192.168.1.1`)
- Port: `6262`
- Nhấn "Test Connection"

#### 2. Chọn test case
- Chuyển đến tab **Templates**
- Chọn category: LAN/WAN/WIRELESS/NETWORK
- Cấu hình parameters
- Nhấn "Add to Queue"

#### 3. Thực thi test
- Vào tab **Queue** để xem danh sách test
- Nhấn "Execute All" hoặc "Execute Selected"
- Theo dõi tiến trình trong tab **Stream**

#### 4. Xem kết quả
- Tab **Stream**: Placeholder (chưa implement) - sẽ hiển thị real-time progress
- Tab **Logs**: System logs với filtering và search functionality

## Giao thức giao tiếp

### HTTP API Endpoints
- `POST /`: Gửi test case để thực thi
- `GET /check_result/{transaction_id}`: Lấy kết quả test (polling mechanism)

### Cấu trúc Test Case
```json
{
  "test_cases": [
    {
      "service": "wireless",
      "action": "edit",
      "params": {
        "ssid": "TestAP",
        "password": "password123"
      }
    }
  ],
  "metadata": {
    "transaction_id": "20250710143524_77bda9d5"
  }
}
```

### Response Format
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

## Script Verification System

Test Case Manager v1.0 có tính năng **automatic script verification** - tự động thực thi script PC-side để xác minh kết quả test.

### Cách hoạt động
1. **Device Test**: Test được thực thi trên OpenWrt device
2. **Response Analysis**: ScriptVerifier kiểm tra response có field `script` không
3. **Script Execution**: Tự động thực thi script từ ToolWL folder với 120s timeout
4. **Result Combination**: Kết hợp device + PC verification results

### Script Interface Standard
- **Input**: `ToolWL/input.txt` (parameters, một dòng một parameter)
- **Output**: `ToolWL/output.txt` ("1" = pass, "0" = fail)
- **Timeout**: 120 seconds maximum execution time
- **Python Detection**: Tự động tìm Python executable (sys.executable, python, python3)
- **Dependencies**: `pywifi`, `requests`, `psutil` (cài đặt bằng `install_all_dependencies.bat`)

### Generic Framework
ScriptVerifier hỗ trợ bất kỳ script nào trong ToolWL folder, không giới hạn loại test cụ thể.

## Configuration Values

### Network Settings (Thực tế từ source code)
```python
# Default connection settings
DEFAULT_HTTP_PORT = 6262
DEFAULT_SSH_PORT = 22
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 30

# Wireless test optimization
WIRELESS_MAX_RETRIES = 60        # Tăng từ 30
WIRELESS_RETRY_DELAY = 3         # Tăng từ 2 seconds
WIRELESS_BACKOFF_MULTIPLIER = 1.3 # Conservative backoff
WIRELESS_MAX_DELAY = 20          # Cap tại 20 seconds
```

### Logging Configuration
```python
# Logger settings
DEFAULT_LOG_LEVEL = "INFO"
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
LOG_DIR = "data/logs/"
```

## Troubleshooting

### ToolWL Scripts không chạy được
**Nguyên nhân**: Thiếu Python hoặc dependencies

**Giải pháp**:
1. Cài đặt Python 3.8+ từ https://www.python.org/downloads/
2. Chạy `ToolWL/install_all_dependencies.bat` (cài đặt pywifi, requests, psutil)
3. Kiểm tra `ToolWL/output.txt` có được tạo sau khi chạy script

### Connection Failed
**Nguyên nhân**: Không kết nối được đến OpenWrt device

**Giải pháp**:
1. Kiểm tra IP address (default: 192.168.1.1) và port 6262
2. Đảm bảo communicate server đang chạy trên device:
   ```bash
   cd rnd_autotest/communicate
   ./communicate
   ```
3. Test connection trong Connection tab trước khi execute tests

### Wireless Tests Timeout
**Nguyên nhân**: Wireless tests cần thời gian dài để complete

**Giải pháp**:
1. Wireless tests có 60 retries với 3s delays - đây là normal behavior
2. Kiểm tra logs để xem progress
3. Không cancel test quá sớm, wireless operations cần thời gian

## Build từ Source

### Build Process
```bash
# Build single executable với PyInstaller
build.bat

# Build process:
# 1. Verify Python và PyInstaller
# 2. Create directory structure
# 3. Build single executable với embedded assets
# 4. Copy data và ToolWL folders
# 5. Create clean release folder
```

### Release Structure (Thực tế)
```
release/
├── TestCaseManager.exe          # Single executable với embedded assets
├── data/                        # External data folder
│   ├── templates/               # Test case templates
│   ├── logs/                    # Application logs
│   ├── config/                  # Configuration files
│   └── temp/                    # Temporary files
└── ToolWL/                      # Verification scripts (external, modifiable)
    ├── install_all_dependencies.bat
    ├── wireless_edit_ap.py
    ├── wifi_connect.py
    ├── module.py
    └── ...
```

### Build Features
- **Single executable**: Tất cả source code và assets embedded trong .exe
- **No Python required**: Standalone executable không cần Python installation
- **External ToolWL**: Scripts có thể modify sau khi build
- **External data**: Templates và config có thể customize

## Implementation Status

### ✅ Đã hoàn thành
- **Core Module**: TestCaseLoader, ResultManager, configuration, constants
- **Network Module**: TestExecutor, ConnectionManager, HTTPTestClient với wireless optimization
- **Utils Module**: ScriptVerifier, logging framework, error classification, file utilities
- **GUI Module**: MainWindow, ConnectionPanel, TemplatesPanel, QueuePanel, LogsPanel
- **Build System**: Single executable build với PyInstaller
- **Script Verification**: Generic framework với 120s timeout

### 🚧 Đang phát triển
- **Stream Panel**: Hiện tại là placeholder, chưa implement real-time monitoring
- **SSH Connection**: Defined nhưng chưa implement (chỉ có HTTP)

### 📋 Dependencies
- **Core**: `requests>=2.28.0`, `Pillow>=9.0.0`
- **Build**: `pyinstaller>=5.0.0`
- **ToolWL**: `pywifi`, `requests`, `psutil`

## Liên hệ và Hỗ trợ

- **Repository**: https://github.com/juno-kyojin/winapp
- **Issues**: Báo cáo lỗi qua GitHub Issues
- **Documentation**: Xem component READMEs để biết chi tiết implementation

---

**Test Case Manager v1.0** - Công cụ kiểm thử chuyên nghiệp cho thiết bị OpenWrt

Copyright © 2025. Tất cả quyền được bảo lưu.
##junokyojin