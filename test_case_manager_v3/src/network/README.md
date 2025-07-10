# Network - HTTP Communication Layer

**HTTP communication và connection management cho Test Case Manager v1.0**

## Tổng quan

Module `network` chịu trách nhiệm toàn bộ giao tiếp HTTP giữa Test Case Manager v1.0 và thiết bị OpenWrt. Bao gồm connection management, test execution engine, intelligent retry mechanism và HTTP client.

## Cấu trúc Module

```
src/network/
├── README.md              # Tài liệu này
├── __init__.py           # Module exports: ConnectionManager, HTTPTestClient, TestExecutor
├── connection_manager.py # Quản lý kết nối HTTP/SSH
├── http_client.py        # HTTP client với retry logic
├── test_executor.py      # Test execution engine
└── ssh_connection.py     # SSH connection (chưa implement)
```

## Kiến trúc Network Layer

### Communication Flow
```
GUI → TestExecutor → ConnectionManager → HTTPTestClient → OpenWrt Device
 ↓         ↓              ↓                ↓                ↓
Input → Validation → Connection → HTTP Request → communicate Server
```

## Core Components

### 1. Connection Manager (`connection_manager.py`)
**Class**: `ConnectionManager`
**Chức năng**: Quản lý kết nối thống nhất cho HTTP và SSH

**Tính năng chính**:
- **Dual connection modes**: HTTP và SSH support (SSH chưa implement)
- **Network-affecting test detection**: Phát hiện tests ảnh hưởng mạng
- **Extended timeouts**: Timeout gấp đôi cho network tests
- **Intelligent retry**: Retry với error type classification

**Connection Types**:
- `SSH_MODE = "ssh"`: SSH connection (chưa implement)
- `HTTP_MODE = "http"`: HTTP connection (đã implement)

**Network-affecting Detection**:
```python
def affects_network_connectivity(test_data):
    # Kiểm tra service: network, lan, wan, wireless
    # Kiểm tra action: edit, create, delete
    return service in ["network", "lan", "wan", "wireless"] and action in ["edit", "create", "delete"]
```

### 2. HTTP Test Client (`http_client.py`)
**Class**: `HTTPTestClient`
**Chức năng**: HTTP communication với specialized test handling

**Tính năng chính**:
- **Extended timeouts**: `read_timeout = 60s` cho wireless tests
- **Session management**: Persistent HTTP sessions với retry adapter
- **Transaction tracking**: Theo dõi transaction IDs
- **Wireless test optimization**: Đặc biệt tối ưu cho wireless tests

**Timeout Configuration**:
- `connect_timeout = 5s`: Timeout kết nối
- `read_timeout = 60s`: Timeout đọc response (tăng cho wireless)

**Wireless Test Handling**:
- **Max retries**: 60 attempts cho wireless tests (thay vì 30)
- **Retry delay**: 3 seconds giữa các attempts (thay vì 2)
- **Exponential backoff**: 1.3x multiplier, cap tại 20 seconds

### 3. Test Executor (`test_executor.py`)
**Class**: `TestExecutor`
**Chức năng**: Test execution engine chính

**Tính năng chính**:
- **Connection delegation**: Sử dụng ConnectionManager để kết nối
- **Test validation**: Kiểm tra test data trước khi gửi
- **Transaction ID generation**: Tự động tạo unique transaction IDs
- **Server preparation**: Chuẩn bị server trước khi test

**Core Methods**:
- `connect(host, **kwargs)`: Kết nối đến device
- `execute_test(test_data, affects_network)`: Thực thi test case
- `is_connected()`: Kiểm tra trạng thái kết nối
- `disconnect()`: Ngắt kết nối

**Transaction ID Format**:
```python
transaction_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
# Ví dụ: "20250710143524_77bda9d5"
```

## Intelligent Retry Mechanism

### Error Classification (trong `src/utils/error_types.py`)
Module network sử dụng error classification để quyết định retry:

**Network Errors (Sẽ retry)**:
- `requests.exceptions.ConnectionError`: Lỗi kết nối
- `requests.exceptions.Timeout`: Request timeout
- `ConnectionResetError`: Connection bị reset
- `OSError`: Socket errors

**Application Errors (Không retry)**:
- `requests.exceptions.HTTPError`: HTTP 4xx, 5xx errors
- `json.JSONDecodeError`: Invalid JSON response
- `ValueError`: Invalid data format

### Retry Strategy

**ConnectionManager Retry Logic**:
```python
def send_test_with_retry(self, test_data, affects_network=False, max_retries=3):
    # Enhanced handling cho network-affecting tests
    if affects_network:
        self.logger.info("Detected network-affecting test - using enhanced connectivity handling")

    # Retry chỉ cho network errors, không retry application errors
    # Sử dụng error classification từ utils.error_types
```

**HTTP Client Retry Logic**:
- **Standard tests**: 3 retries với 2s delay
- **Wireless tests**: 60 retries với 3s delay
- **Exponential backoff**: 1.3x multiplier cho wireless, 1.5x cho standard
- **Max delay**: 20s cho wireless, 10s cho standard

### Network-Affecting Test Handling

**Timeout Extension**:
```python
if affects_network:
    http_client.read_timeout = original_timeout * 2  # Gấp đôi timeout
    self.logger.info(f"Extended timeout for network-affecting test: {http_client.read_timeout}s")
```

**Enhanced Retry Parameters**:
- **Max retries**: Tăng từ 3 lên 5 cho network tests
- **Base delay**: Tăng từ 2s lên 5s
- **Connection re-establishment**: Tự động reconnect sau network tests

## Test Execution Flow

### Standard Test Flow
1. **Validation**: Kiểm tra test data không empty
2. **Server preparation**: `_prepare_server_for_test()`
3. **Transaction ID**: Tự động generate nếu chưa có
4. **Send test**: Gửi qua ConnectionManager
5. **Return result**: Success/failure với response data

### Network-Affecting Test Flow
1. **Detection**: `affects_network_connectivity()` function
2. **Extended timeout**: Timeout gấp đôi
3. **Enhanced retry**: 5 retries thay vì 3
4. **Longer delays**: 5s base delay thay vì 2s
5. **Connection recovery**: Tự động reconnect nếu cần

### Wireless Test Optimization
**HTTP Client Level**:
- **60 retries** thay vì 30 cho wireless tests
- **3 second delays** thay vì 2 seconds
- **Conservative backoff**: 1.3x multiplier, cap 20s
- **Extended logging**: Chi tiết về wireless test progress

## API Communication

### HTTP Endpoints
Network module giao tiếp với OpenWrt communicate server qua HTTP:

**Primary Endpoint**: `POST /` - Gửi test cases
**Result Checking**: `GET /check_result/{transaction_id}` - Lấy kết quả

### Request Format
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

### Transaction ID Tracking
- **Format**: `YYYYMMDDHHMMSS_{8-char-uuid}`
- **Purpose**: Unique identification cho mỗi test execution
- **Usage**: Tracking results và debugging

## Session Management

### HTTP Session Configuration
HTTPTestClient sử dụng persistent sessions:

```python
def _setup_session(self):
    # Retry adapter với custom retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    self.session.mount("http://", adapter)
    self.session.mount("https://", adapter)
```

### Connection Management
- **Persistent sessions**: Tái sử dụng connections
- **Automatic reconnection**: `_reconnect()` method khi connection lost
- **Connection state tracking**: `connected` flag
- **Host/port persistence**: Lưu connection parameters cho reconnection

### Timeout Management
**Default Timeouts**:
- `connect_timeout = 5s`: Thời gian kết nối
- `read_timeout = 60s`: Thời gian đọc response (tăng cho wireless)

**Dynamic Timeout Adjustment**:
- Network-affecting tests: Timeout gấp đôi
- Wireless tests: Extended timeouts với conservative backoff

## Error Handling

### Error Classification
Network module sử dụng `src.utils.error_types` để classify errors:

**Network Errors (Retry)**:
- `requests.exceptions.ConnectionError`
- `requests.exceptions.Timeout`
- `ConnectionResetError`
- `OSError`

**Application Errors (No Retry)**:
- `requests.exceptions.HTTPError`
- `json.JSONDecodeError`
- `ValueError`

### Error Recovery Mechanisms

**Connection Recovery**:
```python
def _reconnect(self) -> bool:
    # Attempt reconnection với saved parameters
    return self.connect(
        host=self.host,
        port=self.port,
        connect_timeout=self.connect_timeout,
        read_timeout=self.read_timeout
    )
```

**Graceful Degradation**:
- Connection failures → Return False với error message
- Timeout errors → Automatic retry với exponential backoff
- Invalid responses → Log error và return failure
- Network disruption → Enhanced retry cho network-affecting tests

## SSH Connection Support

### Current Status
SSH connection được define trong `ssh_connection.py` nhưng **chưa được implement**:

```python
# SSH mode not implemented yet
if self._connection_type == self.SSH_MODE:
    self.logger.error("SSH connection mode not implemented yet")
    return False
```

### Planned SSH Features
- **Paramiko-based**: SSH client sử dụng paramiko library
- **SFTP support**: File transfer capabilities
- **Key-based auth**: SSH key authentication
- **Command execution**: Remote command execution

## Configuration Values

### Timeout Settings (Thực tế từ source code)
```python
# HTTPTestClient defaults
connect_timeout = 5      # Connection timeout
read_timeout = 60        # Read timeout (tăng cho wireless)

# Wireless test adjustments
max_retries = 60         # Tăng từ 30 cho wireless tests
retry_delay = 3          # Tăng từ 2 seconds
backoff_multiplier = 1.3 # Conservative backoff
max_delay = 20           # Cap tại 20 seconds
```

### Network Test Delays
```python
# Network-affecting test handling
timeout_multiplier = 2   # Gấp đôi timeout cho network tests
max_retries = 5         # Tăng từ 3 cho network tests
base_delay = 5.0        # Tăng từ 2.0 seconds
```

## Tích hợp với Other Modules

### GUI Module Integration
```python
# TestExecutor được sử dụng trong MainWindow
self.test_executor = TestExecutor(self.connection_manager)

# ConnectionPanel sử dụng TestExecutor để connect
success = self.test_executor.connect(host, **params)
```

### Core Module Integration
```python
# Network module sử dụng error classification từ utils
from src.utils.error_types import ErrorType, should_retry_error

# Transaction ID generation tương tự core module
transaction_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
```

### Utils Module Integration
```python
# Logging integration
self.logger = logging.getLogger(__name__)

# Error type classification
should_retry = should_retry_error(error)
retry_reason = get_retry_reason(error)
```

## Performance Characteristics

### Throughput
- **Standard tests**: ~1-2 tests/minute
- **Network tests**: ~0.5-1 tests/minute (do delays)
- **Wireless tests**: ~0.2-0.5 tests/minute (do extended retries)

### Resource Usage
- **Memory**: Minimal, persistent sessions
- **CPU**: Low, mostly I/O bound
- **Network**: Efficient với connection reuse

## Liên kết

- [Core Documentation](../core/README.md) - Constants và configuration integration
- [GUI Documentation](../gui/README.md) - ConnectionPanel và TestExecutor usage
- [Utils Documentation](../utils/README.md) - Error types và logging integration
- [Main README](../../README.md) - Tổng quan hệ thống
