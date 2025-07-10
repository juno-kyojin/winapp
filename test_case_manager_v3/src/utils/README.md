# Utils - Utility Functions và Helper Modules

**Utility functions, script verification system, logging và helper modules cho Test Case Manager v1.0**

## Tổng quan

Module `utils` chứa các utility functions và helper modules hỗ trợ toàn bộ hệ thống Test Case Manager v1.0. Bao gồm script verification system, logging framework, error classification, file utilities và formatters.

## Cấu trúc Module

```
src/utils/
├── README.md              # Tài liệu này
├── __init__.py           # Module exports: logger, formatters, validators, file_utils
├── script_verifier.py    # Script verification system
├── logger.py             # Centralized logging framework
├── error_types.py        # Error classification system
├── file_utils.py         # File operations với locking
├── validators.py         # Input validation utilities
├── formatters.py         # Display formatting functions
├── file_lock_utils.py    # File locking utilities
└── image_utils.py        # Image processing utilities
```

## Core Utilities

### 1. Script Verifier (`script_verifier.py`)
**Class**: `ScriptVerifier`
**Chức năng**: Automatic script verification system

**Tính năng chính**:
- **Generic framework**: Hỗ trợ bất kỳ script nào trong ToolWL folder
- **Standardized interface**: input.txt/output.txt interface
- **Python detection**: Tự động tìm Python executable
- **Timeout handling**: 120 seconds timeout cho script execution
- **Error handling**: Graceful handling khi script fails

**Core Methods**:
- `verify_test_result(result_data)`: Main verification method
- `execute_verification_script(script_cmd, input_params)`: Execute script
- `_get_python_executable()`: Find Python executable
- `_extract_script_info(result_data)`: Extract script info từ response

**Script Interface Standard**:
- **Input**: `ToolWL/input.txt` (một parameter mỗi dòng)
- **Output**: `ToolWL/output.txt` ("1" = pass, "0" = fail)
- **Timeout**: 120 seconds maximum execution time

### 2. Logger (`logger.py`)
**Functions**: `get_logger()`, `setup_logging()`, `LoggerMixin`
**Chức năng**: Centralized logging framework

**Tính năng chính**:
- **Multiple handlers**: File, console, GUI logging
- **Rotating file logs**: 10MB max size, 5 backup files
- **Colored console output**: Color-coded log levels
- **GUI integration**: Send logs đến Logs tab
- **Logger mixin**: Easy logging cho any class

**Configuration**:
- **Default level**: INFO
- **Log directory**: `data/logs/`
- **Log file**: `test_case_manager.log`
- **Max file size**: 10MB
- **Backup count**: 5 files

**Usage Examples**:
```python
# Get logger
logger = get_logger(__name__)
logger.info("This is an info message")

# Setup logging
setup_logging(log_level="DEBUG", log_to_file=True, log_to_console=True)

# Use mixin
class MyClass(LoggerMixin):
    def my_method(self):
        self.logger.info("Using mixin logger")
```

### 3. Error Types (`error_types.py`)
**Classes**: `ErrorType`, `ErrorClassifier`
**Chức năng**: Error classification system cho retry logic

**Tính năng chính**:
- **Error classification**: Phân loại network vs application errors
- **Retry determination**: Quyết định có nên retry hay không
- **Pattern matching**: Regex patterns để classify errors
- **HTTP status handling**: Xử lý HTTP status codes

**Error Types**:
- `NETWORK_ERROR`: Nên retry (connection issues, timeouts)
- `APPLICATION_ERROR`: Không retry (HTTP 4xx, JSON errors)
- `UNKNOWN_ERROR`: Default, treat conservatively

**Network Errors (Retry)**:
- Connection refused, timeout, reset
- DNS resolution failures
- Socket errors

**Application Errors (No Retry)**:
- HTTP 4xx client errors
- JSON decode errors
- Invalid data format

**Usage**:
```python
from src.utils.error_types import classify_error, should_retry_error

error_type = classify_error("Connection refused")
if should_retry_error(error_type):
    # Retry the operation
    pass
```

### 4. File Utils (`file_utils.py`)
**Functions**: `safe_read_file()`, `safe_write_file()`, `ensure_directory()`
**Chức năng**: Thread-safe file operations với locking

**Tính năng chính**:
- **File locking**: Prevent concurrent access conflicts
- **Safe operations**: Atomic read/write operations
- **Directory creation**: Ensure directories exist
- **Error handling**: Graceful error handling với logging
- **Encoding support**: UTF-8 encoding by default

**Core Functions**:
```python
def safe_read_file(file_path, default_content="", encoding="utf-8"):
    # Thread-safe file reading với file locking

def safe_write_file(file_path, content, encoding="utf-8"):
    # Thread-safe file writing với file locking

def ensure_directory(directory_path):
    # Ensure directory exists, create if needed
```

**File Locking Integration**:
- Sử dụng `file_lock_utils.py` để implement locking
- Prevent race conditions trong multi-threaded environment
- Automatic lock cleanup

### 5. Validators (`validators.py`)
**Functions**: `validate_ip()`, `validate_port()`, `validate_json()`
**Chức năng**: Input validation utilities

**Tính năng chính**:
- **IP validation**: IPv4 address validation
- **Port validation**: Port number range validation (1-65535)
- **JSON validation**: JSON format validation
- **Path validation**: File path validation
- **Network validation**: Host/port combination validation

**Validation Functions**:
```python
def validate_ip(ip_address):
    # Validate IPv4 address format

def validate_port(port):
    # Validate port number (1-65535)

def validate_json(json_string):
    # Validate JSON format

def validate_file_path(file_path):
    # Validate file path exists và readable
```

### 6. Formatters (`formatters.py`)
**Functions**: `format_duration()`, `format_file_size()`, `format_timestamp()`
**Chức năng**: Display formatting functions

**Tính năng chính**:
- **Duration formatting**: Convert seconds to human-readable format
- **File size formatting**: Convert bytes to KB/MB/GB
- **Timestamp formatting**: Consistent timestamp display
- **Status formatting**: Format test status với colors

**Formatting Examples**:
```python
format_duration(125.5)      # "2m 5.5s"
format_file_size(1048576)   # "1.0 MB"
format_timestamp(datetime.now())  # "2025-01-10 14:35:24"
```

### 7. File Lock Utils (`file_lock_utils.py`)
**Classes**: `FileLock`
**Chức năng**: File locking utilities để prevent concurrent access

**Tính năng chính**:
- **Cross-platform locking**: Windows và Unix support
- **Timeout support**: Configurable lock timeout
- **Context manager**: Use với `with` statement
- **Automatic cleanup**: Locks released automatically
- **Deadlock prevention**: Timeout mechanisms

**Usage**:
```python
from src.utils.file_lock_utils import FileLock

with FileLock("data/config.json", timeout=5):
    # File operations here are thread-safe
    content = read_file("data/config.json")
    write_file("data/config.json", modified_content)
```

### 8. Image Utils (`image_utils.py`)
**Functions**: `load_image()`, `resize_image()`, `convert_to_base64()`
**Chức năng**: Image processing utilities cho GUI

**Tính năng chính**:
- **Image loading**: Load images cho GUI components
- **Resizing**: Resize images to fit UI elements
- **Format conversion**: Convert between image formats
- **Base64 encoding**: Encode images cho data storage
- **Error handling**: Graceful handling của image errors

**Supported Formats**: PNG, JPEG, GIF, BMP

## Script Verification System

### Verification Flow
1. **Response Analysis**: Kiểm tra device response có field `script` không
2. **Script Extraction**: Extract script name và parameters
3. **Input Preparation**: Write parameters vào `ToolWL/input.txt`
4. **Script Execution**: Execute Python script với 120s timeout
5. **Output Reading**: Read result từ `ToolWL/output.txt`
6. **Result Combination**: Combine device + verification results

### Python Detection Logic
ScriptVerifier tự động tìm Python executable:
1. **sys.executable**: Current Python interpreter
2. **python**: System PATH lookup
3. **python3**: Alternative Python 3
4. **Fallback**: Use sys.executable nếu không tìm thấy

### Error Handling
- **Script not found**: Return failure với clear message
- **Timeout**: 120 seconds timeout cho script execution
- **No output**: Return failure nếu script không tạo output.txt
- **Invalid output**: Return failure nếu output không phải "0" hoặc "1"
- **Exception**: Catch all exceptions và return failure với error message

### Integration với Test Flow
```python
# Trong TestExecutor
if 'script' in response:
    verification_result = self.script_verifier.verify_test_result(response)
    final_result = combine_results(device_result, verification_result)
```

## Logging Framework

### Multi-Handler Setup
Logger framework hỗ trợ multiple output destinations:

**File Handler**:
- **Location**: `data/logs/test_case_manager.log`
- **Rotation**: 10MB max size, 5 backup files
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Console Handler**:
- **Colored output**: Color-coded log levels
- **Format**: `%(levelname)s - %(name)s - %(message)s`

**GUI Handler** (Optional):
- **Real-time display**: Send logs đến GUI Logs tab
- **Thread-safe**: Safe để call từ background threads

### Logger Mixin
```python
class LoggerMixin:
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

# Usage
class MyClass(LoggerMixin):
    def my_method(self):
        self.logger.info("This is logged automatically")
```

### Log Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General information messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical error messages

## Error Classification System

### Error Type Enum
```python
class ErrorType(Enum):
    NETWORK_ERROR = "network_error"        # Should retry
    APPLICATION_ERROR = "application_error"  # Should NOT retry
    UNKNOWN_ERROR = "unknown_error"        # Default
```

### Classification Logic
ErrorClassifier sử dụng pattern matching để classify errors:

**Network Error Patterns**:
- "connection refused", "connection reset"
- "timeout", "timed out"
- "network unreachable", "host unreachable"
- "name resolution failed"

**Application Error Patterns**:
- "400", "401", "403", "404" (HTTP client errors)
- "json", "decode", "parse" (JSON errors)
- "invalid", "malformed" (Data format errors)

**HTTP Status Code Classification**:
- **2xx**: Success (no error)
- **4xx**: Application error (don't retry)
- **5xx**: Server error (retry)

### Usage trong Network Module
```python
from src.utils.error_types import classify_error, should_retry_error

error_type = classify_error(str(exception))
if should_retry_error(error_type):
    # Perform retry logic
    retry_count += 1
else:
    # Fail immediately
    return False, None, str(exception)
```

### Async Operations
```python
import asyncio

class AsyncFileUtils:
    @staticmethod
    async def async_write_file(file_path: Path, content: str):
        """Async file writing"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            FileUtils.safe_write_file, 
            file_path, 
            content
        )
```

## Tích hợp với Other Modules

### Core Module Integration
```python
# Script verification trong MainWindow
from src.utils.script_verifier import ScriptVerifier
self.script_verifier = ScriptVerifier()

# Logger trong tất cả modules
from src.utils.logger import get_logger
logger = get_logger(__name__)
```

### GUI Module Integration
```python
# Formatters trong GUI display
from src.utils.formatters import format_duration, format_file_size
display_time = format_duration(execution_time)

# Validators trong input validation
from src.utils.validators import validate_ip_address, validate_port
if not validate_ip_address(host_input.get()):
    show_error("Invalid IP address")
```

### Network Module Integration
```python
# Error classification trong retry logic
from src.utils.error_types import classify_error, should_retry_error
error_type = classify_error(str(exception))
if should_retry_error(error_type):
    retry_operation()
```

## Configuration Examples

### Logger Configuration
```json
{
  "logging": {
    "level": "INFO",
    "file_level": "DEBUG",
    "console_level": "INFO",
    "max_file_size": 10485760,
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### Validation Rules
```json
{
  "validation": {
    "ip_address": {
      "allow_private": true,
      "allow_loopback": true
    },
    "port": {
      "min": 1,
      "max": 65535,
      "reserved_ports": [22, 23, 80, 443]
    },
    "ssid": {
      "max_length": 32,
      "forbidden_chars": ["\x00", "\n", "\r", "\t"]
    }
  }
}
```

## Module Exports

### __init__.py Exports
Utils module exports các functions chính qua `__init__.py`:

**Logger Utilities**:
- `get_logger()`: Get logger instance
- `LoggerMixin`: Mixin class cho logging
- `setup_logging()`: Setup logging configuration

**Formatters**:
- `format_timestamp()`: Format timestamps
- `format_file_size()`: Format file sizes
- `format_duration()`: Format time durations
- `format_test_status()`: Format test status
- `format_connection_status()`: Format connection status

**Validators**:
- `validate_ip_address()`: IP validation
- `validate_port()`: Port validation
- `validate_filename()`: Filename validation
- `validate_json_string()`: JSON validation

**File Utilities**:
- `ensure_directory()`: Directory creation
- `read_json_file()`: JSON file reading
- `write_json_file()`: JSON file writing
- `get_file_size()`: File size calculation

## Liên kết

- [Core Documentation](../core/README.md) - Configuration và constants integration
- [GUI Documentation](../gui/README.md) - Logging, formatters, validators integration
- [Network Documentation](../network/README.md) - Error classification integration
- [Main README](../../README.md) - Tổng quan hệ thống
