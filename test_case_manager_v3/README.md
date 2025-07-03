# Test Case Manager v3.0

A robust application for managing and executing test cases against network devices.

## Features

### Core Features
- Execute test cases against network devices via HTTP
- Support for multiple test case formats (JSON templates)
- Batch execution of test cases
- Result management and reporting
- Basic HTTP-level retry mechanisms

### New in v3.0
- **Simplified Architecture**: Streamlined system with reduced complexity
- **Network Test Handling**: Special handling for tests that affect network connectivity
- **Transaction ID Tracking**: Unique identification for concurrent test execution
- **Basic Error Handling**: Simple and reliable error reporting

## System Architecture

The Test Case Manager v3.0 follows a simplified client-server architecture:

### Components

1. **Test Case Manager (Client)**: Windows GUI application for test management
2. **RnD AutoTest (Server)**: OpenWrt-based test execution system
3. **HTTP Communication**: Simple request-response protocol on port 6262

### Key Features

- **Transaction ID Tracking**: Each test gets a unique identifier for result matching
- **File-based Processing**: Server processes tests via JSON files
- **Concurrent Support**: Multiple tests can be handled simultaneously
## Test Execution Flow

1. **Test Preparation**: Basic server connectivity check
2. **Transaction ID Assignment**: Unique identifier for each test
3. **HTTP Request**: Send test data to OpenWrt device
4. **Result Processing**: Receive and parse response
5. **Next Test**: Continue to next test case

## Error Handling

The system includes basic error handling mechanisms:

1. **HTTP-level Retries**: Built into the requests library for network issues
2. **Connection Verification**: Basic ping check before sending tests
3. **Transaction Tracking**: Unique IDs help match requests with responses



## Usage

```python
from network.test_executor import TestExecutor

# Create executor
executor = TestExecutor()

# Connect to device
executor.connect("192.168.1.1", port=6262)

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
