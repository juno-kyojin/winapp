# Test Case Manager v3.0

Ứng dụng quản lý và thực thi test case toàn diện cho việc kiểm thử thiết bị OpenWrt.

## Tổng Quan Ứng Dụng

Test Case Manager v3.0 là một công cụ GUI chạy trên Windows được thiết kế để:

- **Tạo và quản lý test cases** cho các thiết bị OpenWrt
- **Thực thi test cases** từ xa thông qua giao thức HTTP
- **Theo dõi real-time** quá trình thực thi test
- **Phân tích kết quả** và báo cáo chi tiết
- **Hỗ trợ batch execution** cho nhiều test cases cùng lúc

### Kiến Trúc Hệ Thống

```
[Test Case Manager v3.0 - Windows PC] ←→ HTTP ←→ [OpenWrt Device - rnd_autotest]
```

- **APP (PC side)**: Giao diện người dùng để tạo test và nhận kết quả
- **auto_test (Device side)**: Component thực thi test trên thiết bị OpenWrt
- **communicate (Device side)**: HTTP server xử lý giao tiếp giữa APP và device

### Tính Năng Chính

- **Transaction ID Tracking**: Mỗi test có identifier duy nhất để mapping kết quả
- **Wireless Test Support**: Hỗ trợ đặc biệt cho wireless tests với extended timeout
- **Real-time Monitoring**: Theo dõi tiến trình test execution trong Stream tab
- **Queue Management**: Quản lý hàng đợi test cases và batch execution
- **Error Handling**: Xử lý lỗi và retry mechanisms cho network issues

## Cài Đặt và Thiết Lập

### Yêu Cầu Hệ Thống

- **Windows 10/11** (64-bit)
- **Python 3.8+**
- **Network connectivity** đến thiết bị OpenWrt
- **Port 6262** phải được mở trên thiết bị OpenWrt

### Cài Đặt Dependencies

```bash
# Clone repository
git clone https://github.com/juno-kyojin/winapp.git
cd winapp/test_case_manager_v3

# Cài đặt Python dependencies
pip install -r requirements.txt
```

### Thiết Lập Kết Nối Server

1. **Mở ứng dụng**:
   ```bash
   python main.py
   ```

2. **Cấu hình connection** trong Settings panel:
   - **Server IP**: Địa chỉ IP của thiết bị OpenWrt (ví dụ: `192.168.1.4`)
   - **Port**: `6262` (default port của communicate server)
   - **Timeout**: `30` seconds (khuyến nghị cho wireless tests)

3. **Test connection**: Click "Test Connection" để xác minh kết nối

### Thiết Lập Device Side

Trên thiết bị OpenWrt, đảm bảo:

```bash
# Chạy communicate server
cd /path/to/rnd_autotest/communicate
./communicate

# Chạy auto_test component
cd /path/to/rnd_autotest
./auto_test
```
## Định Dạng Test Case

### Cấu Trúc JSON Cơ Bản

Mỗi test case phải tuân theo định dạng JSON sau:

```json
{
  "test_cases": [
    {
      "service": "tên_service",
      "action": "tên_action",
      "params": {
        "parameter1": "value1",
        "parameter2": "value2"
      }
    }
  ]
}
```

### Các Trường Bắt Buộc

#### Test Cases Array
- **service** (string): Tên service cần test (ping, wireless, lan, etc.)
- **action** (string): Action cụ thể trong service (optional, default: "default")
- **params** (object): Parameters cho test case



### Transaction ID Handling

Transaction ID được tự động tạo với format:
```
YYYYMMDDHHMMSS_microseconds_uuid8chars
Ví dụ: 20250703095644_3041bf28
```

- **Tự động tạo**: Không cần chỉ định trong test case JSON
- **Unique identification**: Đảm bảo mỗi test có ID duy nhất
- **Result mapping**: Dùng để map kết quả từ device về client


### Ví Dụ Test Cases Theo Service

#### 1. Network Tests

**Ping Test:**
```json
{
  "test_cases": [
    {
      "service": "ping",
      "params": {
        "host1": "google.com",
        "host2": "8.8.8.8",
        "count": 4
      }
    }
  ]
}
```

**Speed Test:**
```json
{
  "test_cases": [
    {
      "service": "speedtest",
      "params": {
        "server": "auto",
        "duration": 30
      }
    }
  ],
  "metadata": {
    "name": "Internet Speed Test",
    "description": "Đo tốc độ internet upload/download",
    "version": "1.0.0",
    "tags": ["network", "speed", "bandwidth"],
    "category": "network"
  }
}
```

#### 2. Wireless Tests

**WiFi Configuration Test:**
```json
{
  "test_cases": [
    {
      "service": "wireless",
      "action": "wireless_edit_ap",
      "params": {
        "ssid": "TestNetwork_5G",
        "password": "testpassword123",
        "encryption": "psk2",
        "channel": "auto",
        "bandwidth": "80"
      }
    }
  ],
  "metadata": {
    "name": "WiFi AP Configuration Test",
    "description": "Cấu hình và test WiFi Access Point",
    "version": "1.0.0",
    "tags": ["wireless", "wifi", "ap", "configuration"],
    "category": "wireless"
  }
}
```

**⚠️ Lưu Ý Wireless Tests:**
- Wireless tests có **extended timeout** (30+ retries, 2+ second delays)
- Có thể gây **service restart** → mất kết nối tạm thời
- Cần **thời gian chờ lâu hơn** để hoàn thành

#### 3. System Tests

**System Information:**
```json
{
  "test_cases": [
    {
      "service": "system",
      "action": "get_info",
      "params": {
        "include_hardware": true,
        "include_network": true
      }
    }
  ],
  "metadata": {
    "name": "System Information Test",
    "description": "Lấy thông tin hệ thống và hardware",
    "version": "1.0.0",
    "tags": ["system", "info", "hardware"],
    "category": "system"
  }
}
```

## Hướng Dẫn Sử Dụng

### Tạo và Thêm Test Cases

1. **Tạo file JSON** theo định dạng đã mô tả ở trên
2. **Lưu file** trong thư mục `data/templates/`
3. **Refresh Templates** trong Templates tab
4. **Add to Queue** để thêm vào hàng đợi thực thi

### Thực Thi Test Cases

#### Individual Test Execution:
1. **Chọn test case** trong Templates tab
2. **Click "Add to Queue"**
3. **Click "Execute"** trong Queue tab
4. **Theo dõi progress** trong Stream tab

#### Batch Execution:
1. **Add multiple tests** vào Queue
2. **Click "Execute All"**
3. **Monitor real-time progress** trong Stream tab
4. **View results** khi hoàn thành

### Hiểu Stream Tab

Stream tab hiển thị real-time test execution flow:

```
[09:30:26] 🔄 Executing test 1/3: Network Connectivity Test
[09:30:26] 📤 Sending test to device (Transaction: 20250703095644_3041bf28)
[09:30:28] ⏳ Waiting for result... (Attempt 1/30)
[09:30:30] ⏳ Waiting for result... (Attempt 2/30)
[09:30:32] ✅ Test 1/3 completed successfully (Execution time: 6.2s)
[09:30:32] 🔄 Executing test 2/3: WiFi AP Configuration Test
```

### Timing và Flow

- **Pre-execution delay**: 15s (để device chuẩn bị)
- **Post-execution delay**: 25s cho network tests (để network ổn định)
- **Wireless tests**: Extended timeout với 30+ retries
- **Transaction polling**: Mỗi 2 giây check kết quả

## Best Practices

### Naming Conventions

- **File names**: `service_action_description.json`
  - Ví dụ: `network_ping_connectivity.json`
  - Ví dụ: `wireless_edit_ap_5g_config.json`

- **Test names**: Descriptive và specific
  - ✅ "WiFi 5G AP Configuration Test"
  - ❌ "WiFi Test"

### Test Case Structure

#### Recommended Structure:
```json
{
  "test_cases": [
    {
      "service": "service_name",
      "action": "specific_action",
      "params": {
        // Chỉ include parameters cần thiết
        // Sử dụng meaningful parameter names
        // Provide default values khi có thể
      }
    }
  ],
  "metadata": {
    "name": "Descriptive Test Name",
    "description": "Chi tiết về test case này làm gì, expected behavior",
    "version": "1.0.0",
    "tags": ["relevant", "tags", "for", "categorization"],
    "category": "network|wireless|system"
  }
}
```

### Wireless Test Handling

#### Đặc Biệt Lưu Ý:
- **Extended timeouts**: Wireless tests cần thời gian lâu hơn
- **Service restarts**: Có thể gây mất kết nối tạm thời
- **Sequential execution**: Không chạy parallel wireless tests
- **Post-test delays**: Cần delay sau wireless tests

#### Best Practices:
```json
{
  "test_cases": [
    {
      "service": "wireless",
      "action": "wireless_edit_ap",
      "params": {
        // Luôn specify đầy đủ parameters
        "ssid": "clear_descriptive_name",
        "password": "secure_password_min_8_chars",
        "encryption": "psk2", // Recommended
        "channel": "auto", // Let device choose optimal
        "bandwidth": "80" // Specify bandwidth
      }
    }
  ]
}
```

### Error Handling và Troubleshooting

#### Common Issues và Solutions:

**1. Connection Timeout:**
```
Error: Connection timeout to 192.168.1.4:6262
```
**Solutions:**
- Kiểm tra device IP address
- Verify port 6262 đang mở
- Check network connectivity
- Restart communicate server trên device

**2. Transaction Stuck "Processing":**
```
[09:30:26] ⏳ Waiting for result... (Attempt 15/30)
```
**Solutions:**
- Wait thêm (wireless tests cần thời gian lâu)
- Check device logs để xem test execution status
- Verify auto_test component đang chạy
- Restart device components nếu cần

**3. "Unknown" Status Response:**
```
Status: unknown - Transaction still processing
```
**Solutions:**
- Normal behavior - device chưa hoàn thành test
- Wait for completion (especially wireless tests)
- Check device-side result file creation

**4. JSON Parse Error:**
```
Error: Invalid JSON format in test case
```
**Solutions:**
- Validate JSON syntax using online validator
- Check for missing commas, brackets
- Ensure proper string escaping

#### Debugging Tips:

1. **Enable verbose logging** trong Settings
2. **Check Stream tab** cho real-time status
3. **Monitor device logs** để xem server-side execution
4. **Test connection** trước khi execute tests
5. **Use simple test cases** để debug connectivity issues

## Developer Guidelines

### Code Contribution Standards

#### Code Style:
- **Python PEP 8** compliance
- **Type hints** cho tất cả functions
- **Docstrings** cho classes và methods
- **Error handling** với proper exception types

#### Example Code Structure:
```python
from typing import Optional, Dict, Any, Tuple

class TestExecutor:
    """Execute test cases against OpenWrt devices."""

    def execute_test(self, test_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], str]:
        """
        Execute a single test case.

        Args:
            test_data: Test case data in JSON format

        Returns:
            Tuple of (success, result_data, error_message)
        """
        try:
            # Implementation here
            return True, result_data, ""
        except Exception as e:
            return False, None, str(e)
```

### Extending với New Test Types

#### 1. Add New Service Support:

**Client-side** (`http_client.py`):
```python
def _is_new_service_test(self, test_data: Dict[str, Any]) -> bool:
    """Check if test involves new service."""
    test_cases = test_data.get("test_cases", [])
    return any(tc.get("service") == "new_service" for tc in test_cases)
```

**Device-side** (không được sửa `rnd_autotest/src/`):
- Chỉ có thể modify `rnd_autotest/communicate/` components
- New service logic phải implement trong device auto_test

#### 2. Add New GUI Components:

**Panel Structure**:
```python
# gui/panels/new_panel.py
import tkinter as tk
from tkinter import ttk

class NewPanel(ttk.Frame):
    """New functionality panel."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup panel UI components."""
        # Implementation here
```

### Architecture Overview

#### High-Level Design:
```
┌─────────────────────────────────────┐
│        Test Case Manager v3.0       │
│             (Windows PC)            │
├─────────────────────────────────────┤
│  GUI Layer (Tkinter)               │
│  ├── Templates Panel               │
│  ├── Queue Panel                   │
│  ├── Stream Panel                  │
│  └── Settings Panel                │
├─────────────────────────────────────┤
│  Business Logic Layer              │
│  ├── Test Case Manager             │
│  ├── HTTP Client                   │
│  ├── Result Manager                │
│  └── Connection Manager            │
├─────────────────────────────────────┤
│  Network Layer                     │
│  └── HTTP Communication            │
└─────────────────────────────────────┘
                  │
                  │ HTTP (Port 6262)
                  │
┌─────────────────────────────────────┐
│         OpenWrt Device              │
├─────────────────────────────────────┤
│  communicate (HTTP Server)         │
│  ├── /check_result endpoint        │
│  ├── POST / endpoint               │
│  └── Transaction ID handling       │
├─────────────────────────────────────┤
│  auto_test (Test Execution)        │
│  ├── Test Case Processing          │
│  ├── Service Execution             │
│  └── Result File Generation        │
└─────────────────────────────────────┘
```

#### Communication Flow:
1. **Client** tạo transaction ID và gửi test data
2. **communicate** nhận request, lưu config file
3. **auto_test** process config file, execute test
4. **auto_test** tạo result file với timestamp
5. **communicate** tìm result file theo transaction ID
6. **Client** poll `/check_result` endpoint để nhận kết quả

### Requirements

- **Python 3.8+**
- **Tkinter** (included with Python)
- **Requests** library for HTTP communication
- **Network access** to OpenWrt device on port 6262

### Installation

```bash
# Clone repository
git clone https://github.com/juno-kyojin/winapp.git
cd winapp/test_case_manager_v3

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Configuration

Application sử dụng configuration file tại `data/config/config.json`:

```json
{
  "server": {
    "host": "192.168.1.4",
    "port": 6262,
    "timeout": 30
  },
  "execution": {
    "pre_delay": 15,
    "post_delay": 25,
    "max_retries": 30,
    "retry_delay": 2
  }
}
```

## License

Copyright © 2025 juno-kyojin

---

**📝 Lưu Ý Quan Trọng:**
- Luôn test connection trước khi execute test cases
- Wireless tests cần thời gian lâu hơn - hãy kiên nhẫn
- Monitor Stream tab để theo dõi real-time progress
- Backup test cases quan trọng
- Follow naming conventions để dễ quản lý

**🔧 Support:**
- Nếu gặp issues, check troubleshooting section trước
- Enable verbose logging để debug
- Monitor device-side logs khi cần thiết
- Contact team để support technical issues
