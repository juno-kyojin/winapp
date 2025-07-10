# Core - Business Logic Engine

**Core business logic và test execution engine cho Test Case Manager v1.0**

## Tổng quan

Module `core` chứa logic chính của Test Case Manager v1.0, bao gồm test case loading, result management, configuration và constants. Module này cung cấp foundation cho toàn bộ hệ thống.

## Cấu trúc Module

```
src/core/
├── README.md              # Tài liệu này
├── __init__.py           # Module initialization (empty)
├── constants.py          # System constants và default values
├── config.py             # Configuration classes
├── exceptions.py         # Custom exception classes
├── test_case_loader.py   # Test case loading và template management
├── test_case_manager.py  # Test case management operations
└── result_manager.py     # Result storage và retrieval
```

**Lưu ý**: Test execution engine thực tế nằm trong `src/network/test_executor.py`

## Core Components

### 1. Constants (`constants.py`)
**Chức năng**: Định nghĩa system constants và default values

**Key Constants**:
- `TEST_TIMEOUT_DEFAULT = 120` seconds
- `TEST_TIMEOUT_NETWORK = 300` seconds
- `TEST_QUEUE_MAX_SIZE = 100`
- `RESULT_CHECK_INTERVAL = 3` seconds
- Default HTTP port: `6262`

### 2. Configuration (`config.py`)
**Chức năng**: Configuration classes cho system settings

**Classes**:
- `TestConfig`: Test execution configuration
  - `default_timeout = 120`
  - `retry_attempts = 3`
  - `retry_delay = 5`
- `ConnectionConfig`: Connection settings
- `LoggingConfig`: Logging configuration

### 3. Test Case Loader (`test_case_loader.py`)
**Chức năng**: Load và manage test case templates

**Class**: `TestCaseLoader`
**Key Methods**:
- `get_categories()`: Lấy danh sách categories
- `get_templates_for_category(category)`: Lấy templates theo category
- `load_test_case(test_id, category)`: Load test case data
- `get_categories_with_templates()`: Lấy tất cả categories với test cases

**Features**:
- Dynamic category discovery từ `data/templates/`
- Network-affecting test detection
- Template metadata management

### 4. Result Manager (`result_manager.py`)
**Chức năng**: Quản lý test results và storage

**Class**: `ResultManager`
**Key Methods**:
- `save_result(test_id, status, result_data)`: Lưu test result
- `load_result(result_file)`: Load result từ file
- `get_results(test_id, status, limit)`: Query results với filters
- `get_test_statistics(timeframe_days)`: Thống kê test execution

**Features**:
- Unique filename generation với UUID
- Result status validation
- Automatic metadata tracking
- Statistics calculation

## Network-Affecting Test Detection

Test Case Loader có khả năng phát hiện tests có thể ảnh hưởng đến network connectivity:

**Detection Logic** (trong `get_categories_with_templates()`):
```python
affects_network = (
    service in ["wan", "network"] or
    "restart" in action or
    "reboot" in action
)
```

**Criteria**:
- Service: `wan`, `network`
- Actions chứa: `restart`, `reboot`
- Được đánh dấu trong test metadata với `impacts_network: true`

## Result Processing

Result Manager xử lý test results với các features:

### Result Storage
- **Filename format**: `{test_id}_{unique_id}_{status}.json`
- **Unique ID**: 8-character UUID để tránh conflicts
- **Metadata tracking**: Automatic timestamp, test_id, status
- **Status validation**: Kiểm tra failed tests trong summary

### Result Retrieval
- **Filtering**: Theo test_id, status, timeframe
- **Sorting**: Theo modification time
- **Pagination**: Limit số lượng results
- **Statistics**: Success rate, test counts theo timeframe

## Exception Handling

Core module định nghĩa custom exceptions trong `exceptions.py`:

### Exception Classes
- `TemplateNotFoundError`: Template file không tìm thấy
- `FileOperationError`: Lỗi file operations (read/write)
- `ValidationError`: Validation errors
- `ConfigurationError`: Configuration issues

### Error Handling Patterns
- **Graceful degradation**: Continue operation khi có non-critical errors
- **Detailed logging**: Log errors với context information
- **User-friendly messages**: Return meaningful error messages
- **Fallback values**: Provide defaults khi có errors

## Template Structure

Test case templates được organize theo categories trong `data/templates/`:

### Directory Structure
```
data/templates/
├── lan/           # LAN test cases
├── wan/           # WAN test cases
├── wireless/      # Wireless test cases
└── network/       # Network test cases
```

### Template Format
Templates là JSON files với structure:
- **name**: Test case name
- **description**: Human-readable description
- **service**: Target service (lan, wan, wireless, network)
- **action**: Action type (get, set, create, delete, etc.)
- **parameters**: Required parameters với validation rules

## Integration với Other Modules

### Network Module
- Test execution thực tế được handle bởi `src/network/test_executor.py`
- Core module cung cấp test case data và result storage
- Network module sử dụng constants từ `core/constants.py`

### GUI Module
- Templates được load bởi Core và display trong Templates tab
- Results được store bởi Core và display trong Stream/Logs tabs
- Configuration từ Core được sử dụng trong Connection tab

### Utils Module
- Core sử dụng file utilities từ Utils module
- Exception handling được share giữa modules
- Logging configuration được centralized trong Utils

## Liên kết

- [Network Documentation](../network/README.md) - Test execution engine và HTTP communication
- [GUI Documentation](../gui/README.md) - User interface integration
- [Utils Documentation](../utils/README.md) - File utilities và logging
- [ToolWL Documentation](../../ToolWL/README.md) - Verification scripts
- [Main README](../../README.md) - Tổng quan hệ thống
