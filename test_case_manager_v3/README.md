# Test Case Manager v3.0

A robust application for managing and executing test cases against network devices.

## Features

### Core Features
- Execute test cases against network devices via HTTP or SSH
- Support for multiple test case formats (JSON templates)
- Batch execution of test cases
- Result management and reporting
- Configurable retry mechanisms and timeouts

### New in v3.0
- **Client-side Validation System**: Verify test results on both server and client sides
- **Dynamic Validator Loading**: Add new validators without modifying core code
- **Enhanced Result Verification**: Ensure test results are properly written before proceeding
- **Network Test Handling**: Special handling for tests that affect network connectivity
- **Improved Error Handling**: Better retry mechanisms and error reporting
- **Empty File Prevention**: Added mechanisms to prevent the "empty file" issue on the server

## Client-side Validation System

The client-side validation system allows for verifying test results beyond what the server reports. This is useful for:

1. Verifying network connectivity after configuration changes
2. Testing actual functionality from the client perspective
3. Providing more detailed error information

### How It Works

1. Add `"client_validation": true` to any test case that requires client-side validation
2. Create a validator function in the `validators` directory
3. The system automatically loads and registers validators
4. After server execution, the client-side validator is called to verify results

### Validator Structure

Validators are organized by service type:
- `validators/lan.py` - LAN-related validators
- `validators/wan.py` - WAN-related validators
- `validators/network.py` - Network test validators (ping, etc.)
- `validators/common.py` - Common validation functions

### Creating Custom Validators

To create a new validator:

1. Add a function to the appropriate validator file (or create a new one)
2. Name your function `validate_<service>_<action>` or `validate_<service>`
3. The function should take `test_data` and `result_data` parameters
4. Return a tuple of `(success: bool, message: str)`

Example:
```python
def validate_ping(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate ping test results by actually pinging the targets."""
    hosts = []
    if "params" in test_data:
        for key, value in test_data["params"].items():
            if key.startswith("host"):
                hosts.append(value)
    
    # Ping each host
    for host in hosts:
        if not ping_host(host):
            return False, f"Client-side validation failed: Cannot ping {host}"
    
    return True, "All hosts are reachable"
```

## Result Verification Mechanism

To ensure test cases are properly processed before moving to the next test:

1. Each test is assigned a unique transaction ID
2. After receiving a response, the system checks if the result has been written
3. For network-affecting tests, additional wait time is added

This prevents race conditions and ensures stable test execution.

## Empty File Issue Prevention

The system includes several mechanisms to prevent the "empty file" issue on the server:

1. **Pre-send Delay**: A delay is added before sending each test to ensure the server has cleared the previous file
2. **Server Readiness Check**: The system pings the server before sending a test to ensure it's responsive
3. **Automatic Retries**: If an empty file error is detected, the system automatically retries with increased delays
4. **Extended Timeouts**: Longer timeouts are used for network-affecting tests
5. **Result Verification**: The system checks that results are properly written before proceeding to the next test
6. **Double Ping Check**: Before sending important tests, the system performs a double ping check to ensure the server is ready
7. **Adaptive Wait Times**: Wait times between tests are increased for network-affecting operations

These mechanisms work together to ensure reliable test execution even when the server is under load or processing multiple requests.

### Understanding the Empty File Issue

The empty file issue occurs when the server receives a test request before it has finished processing the previous request. This can happen because:

1. The server's file handling is not atomic
2. The client sends requests too quickly
3. Network conditions cause delays in file processing

When this happens, the server may read an empty file and return an error. Our system addresses this by:

1. Adding appropriate delays between requests
2. Checking server responsiveness before sending tests
3. Automatically retrying with longer delays if an empty file error is detected
4. Using transaction IDs to track and verify test completion

## Usage

```python
from network.test_executor import TestExecutor

# Create executor
executor = TestExecutor()

# Connect to device
executor.connect("192.168.1.1", port=8080)

# Load and execute test
with open("test_case.json", "r") as f:
    test_data = json.load(f)
    
success, result, message = executor.execute_test(test_data)
print(f"Test {'succeeded' if success else 'failed'}: {message}")
```

## Test Case Format

```json
{
  "test_cases": [
    {
      "service": "ping",
      "client_validation": true,
      "params": {
        "host1": "google.com",
        "host2": "youtube.com"
      }
    }
  ],
  "metadata": {
    "name": "Network Ping Test",
    "description": "Tests network connectivity by pinging a target",
    "version": "1.0.0",
    "tags": ["network", "connectivity", "ping"],
    "category": "network"
  }
}
```

## Architecture

The application is organized into several modules:

- **core**: Core business logic
  - `config.py`: Application configuration
  - `constants.py`: Application constants
  - `exceptions.py`: Custom exceptions
  - `test_case_loader.py`: Load test templates
  - `test_case_manager.py`: Manage test cases
  - `result_manager.py`: Manage test results

- **network**: Network connectivity
  - `connection_manager.py`: Unified connection management
  - `http_client.py`: HTTP client for test execution
  - `ssh_connection.py`: SSH client for test execution
  - `lan_checker.py`: Verify network connectivity
  - `test_executor.py`: Execute tests against devices

- **gui**: User interface
  - `main_window.py`: Main application window
  - **panels**: UI panels for different functions
    - `connection_panel.py`: Connection management
    - `templates_panel.py`: Template management
    - `queue_panel.py`: Test queue management
    - `history_panel.py`: Test history and results
    - `logs_panel.py`: Application logs
  - **dialogs**: Dialog windows
    - `about_dialog.py`: About dialog
    - `preferences_dialog.py`: Application preferences
    - `test_details_dialog.py`: Test details view
    - `parameter_dialog.py`: Parameter editing
  - **widgets**: Reusable UI components
    - `status_bar.py`: Status bar widget
    - `queue_manager.py`: Queue management widget
    - `parameter_editor.py`: Parameter editing widget

- **utils**: Utility functions
  - `file_utils.py`: File operations
  - `formatters.py`: Data formatting
  - `logger.py`: Logging utilities
  - `validators.py`: Data validation

## Requirements

- Python 3.8 or higher
- Tkinter (included with Python)
- Requests library
- Paramiko library (for SSH support)

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python src/main.py
   ```

## Configuration

The application uses a configuration file located at `data/config/config.json`. You can specify a different configuration file using the `--config` command-line argument.

## Command-Line Arguments

- `--config PATH`: Path to configuration file
- `--debug`: Enable debug mode
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--version`: Show version information

## License

Copyright © 2025 juno-kyojin 
