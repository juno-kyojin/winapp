# GUI - User Interface Components

**Giao diện người dùng cho Test Case Manager v1.0**

## Tổng quan

Module `gui` chứa toàn bộ giao diện người dùng của Test Case Manager v1.0, được xây dựng bằng tkinter với 5 tab chính. Module được organize theo pattern MVC với panels, widgets và dialogs riêng biệt.

## Cấu trúc Module

```
src/gui/
├── README.md              # Tài liệu này
├── __init__.py           # Module exports MainWindow
├── main_window.py        # Main application window
├── panels/               # Tab panels
│   ├── connection_panel.py    # Connection management
│   ├── templates_panel.py     # Template selection và editing
│   ├── queue_panel.py         # Test queue management
│   ├── stream_panel.py        # Real-time execution monitoring
│   ├── logs_panel.py          # System logs display
│   ├── history_panel.py       # Test history (unused)
│   └── test_results_panel.py  # Results display (unused)
├── widgets/              # Reusable UI components
│   ├── status_bar.py          # Application status bar
│   ├── parameter_editor.py    # Parameter input widgets
│   └── queue_manager.py       # Queue management widgets
└── dialogs/              # Dialog windows
    ├── about_dialog.py        # About application dialog
    ├── preferences_dialog.py  # Settings dialog
    ├── parameter_dialog.py    # Parameter input dialog
    └── test_details_dialog.py # Test details dialog
```

## Main Window Architecture

### MainWindow Class (`main_window.py`)
**Chức năng**: Central application window với 5-tab interface

**Core Components**:
- `TestCaseLoader`: Load templates từ data/templates/
- `ResultManager`: Manage test results
- `ConnectionManager`: Handle device connections
- `TestExecutor`: Execute tests
- `ScriptVerifier`: Automatic script verification

**Tab Structure**:
```python
self.notebook.add(self.connection_tab, text="Connection")
self.notebook.add(self.templates_tab, text="Templates")
self.notebook.add(self.queue_tab, text="Queue")
self.notebook.add(self.stream_tab, text="Stream")
self.notebook.add(self.logs_tab, text="Logs")
```

## Panel Components

### 1. Connection Panel (`panels/connection_panel.py`)
**Class**: `ConnectionPanel`
**Chức năng**: Quản lý kết nối đến thiết bị OpenWrt

**Tính năng chính**:
- **Hỗ trợ 2 loại kết nối**: HTTP và SSH
- **Giá trị mặc định**: HTTP (192.168.1.1:6262), SSH (192.168.1.1:22)
- **Kết nối không đồng bộ**: Kết nối trong background thread
- **Lưu cài đặt**: Tự động load/save từ AppConfig
- **Cập nhật trạng thái**: Hiển thị trạng thái kết nối real-time

**Biến kết nối**:
- `connection_type_var`: "http" hoặc "ssh"
- `host_var`: Địa chỉ IP (mặc định: "192.168.1.1")
- `http_port_var`: Cổng HTTP (mặc định: 6262)
- `ssh_port_var`: Cổng SSH (mặc định: 22)
- `connection_status_var`: Hiển thị trạng thái kết nối

### 2. Templates Panel (`panels/templates_panel.py`)
**Class**: `TemplatesPanel`
**Chức năng**: Chọn template, chỉnh sửa và quản lý queue

**Tính năng chính**:
- **Tổ chức theo danh mục**: Tự động load categories từ TestCaseLoader
- **Chỉnh sửa template**: JSON editor với syntax highlighting
- **Trích xuất tham số**: Tự động phát hiện parameters từ template
- **Tích hợp queue**: Thêm trực tiếp vào queue
- **Kiểm tra template**: Phân tích và validate JSON

**Phương thức chính**:
- `_load_categories()`: Load danh mục từ test_loader
- `_load_templates_for_category()`: Load templates cho danh mục đã chọn
- `_load_template()`: Load nội dung template cụ thể
- `get_selected_template()`: Lấy template hiện tại đang chọn
- `add_to_queue()`: Thêm template vào queue panel

**Tích hợp Template**:
- Sử dụng `TestCaseLoader.get_categories()` để lấy danh mục có sẵn
- Sử dụng `TestCaseLoader.get_templates_for_category()` để load templates
- Tích hợp với `QueuePanel` thông qua parent reference

### 3. Queue Panel (`panels/queue_panel.py`)
**Class**: `QueuePanel`
**Chức năng**: Quản lý hàng đợi test và thực thi hàng loạt

**Tính năng chính**:
- **Thao tác hàng đợi**: Thêm, xóa, sắp xếp lại test cases
- **Thực thi hàng loạt**: Chạy tất cả tests tuần tự
- **Lưu trữ queue**: Lưu/load trạng thái hàng đợi
- **Theo dõi trạng thái**: Theo dõi tình trạng thực thi từng test
- **Xử lý network tests**: Xử lý đặc biệt cho tests ảnh hưởng mạng

**Phương thức chính**:
- `add_to_queue()`: Thêm test case vào queue
- `remove_from_queue()`: Xóa test đã chọn
- `execute_all()`: Thực thi tất cả tests trong queue
- `clear_queue()`: Xóa tất cả tests
- `move_up()/move_down()`: Sắp xếp lại thứ tự tests

**Tích hợp**:
- Nhận tests từ TemplatesPanel
- Sử dụng TestExecutor để thực thi tests
- Tích hợp với Stream panel để hiển thị tiến trình

### 4. Stream Panel (`panels/stream_panel.py`)
**Class**: `StreamPanel`
**Chức năng**: Giám sát thực thi test real-time

**Tính năng chính**:
- **Theo dõi tiến trình**: Progress bars và cập nhật trạng thái
- **Logs thực thi**: Hiển thị log trực tiếp với timestamps
- **Kết quả test**: Tóm tắt kết quả thực thi tests
- **Tự động cuộn**: Tự động cuộn đến log entries mới nhất
- **Mã màu**: Màu sắc khác nhau cho các mức log khác nhau

**Trạng thái**: Hiện tại hiển thị placeholder - chưa hoàn thành

### 5. Logs Panel (`panels/logs_panel.py`)
**Class**: `LogsPanel`
**Chức năng**: Hiển thị logs hệ thống tập trung

**Tính năng chính**:
- **Lọc logs**: Lọc theo level, component, thời gian
- **Tìm kiếm**: Tìm kiếm trong log entries
- **Xuất file**: Xuất logs ra file
- **Tự động làm mới**: Cập nhật logs real-time
- **Mức logs**: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Tích hợp**: Nhận logs từ hệ thống logging tập trung

## Widgets và Dialogs

### Status Bar (`widgets/status_bar.py`)
**Class**: `StatusBar`
**Chức năng**: Hiển thị trạng thái ứng dụng

**Tính năng**:
- Hiển thị trạng thái kết nối
- Hiển thị thao tác hiện tại
- Thông tin tiến trình
- Hiển thị timestamp

### Dialogs
- **About Dialog** (`dialogs/about_dialog.py`): Thông tin ứng dụng
- **Preferences Dialog** (`dialogs/preferences_dialog.py`): Cấu hình cài đặt
- **Parameter Dialog** (`dialogs/parameter_dialog.py`): Nhập tham số
- **Test Details Dialog** (`dialogs/test_details_dialog.py`): Chi tiết kết quả test

### Parameter Editor (`widgets/parameter_editor.py`)
**Chức năng**: Widgets nhập tham số động

**Tính năng**:
- Tạo form động dựa trên template parameters
- Kiểm tra đầu vào
- Xử lý các loại tham số (string, number, boolean)
- Hỗ trợ giá trị mặc định

## Xử lý sự kiện và Tích hợp

### Giao tiếp giữa các Panel
MainWindow đóng vai trò điều phối trung tâm cho giao tiếp giữa các panel:

**Luồng Template to Queue**:
```python
# TemplatesPanel → MainWindow → QueuePanel
self.templates_panel.parent = self  # Thiết lập parent reference
self.templates_panel.add_to_queue = new_add_to_queue  # Override method
```

**Cập nhật trạng thái kết nối**:
```python
# ConnectionPanel → MainWindow → StatusBar
self.connection_panel = ConnectionPanel(
    self.connection_tab,
    self.test_executor,
    self.config,
    self._update_status  # Status callback
)
```

### Threading
- **Thử kết nối**: Kiểm tra kết nối không chặn UI
- **Thực thi test**: Chạy test trong background
- **Cập nhật UI**: Cập nhật UI thread-safe từ background threads

## Cấu hình và Cài đặt

### Cấu hình cửa sổ
- **Kích thước tối thiểu**: Định nghĩa trong `WINDOW_MIN_WIDTH`, `WINDOW_MIN_HEIGHT`
- **Kích thước mặc định**: 1200x800 pixels
- **Có thể thay đổi kích thước**: Có, với ràng buộc tối thiểu
- **Grid layout**: Layout responsive với resizing phù hợp

### Lưu trữ cài đặt
- **Cài đặt kết nối**: Lưu trong AppConfig
- **Trạng thái cửa sổ**: Lưu vị trí và kích thước
- **Tùy chọn panel**: Cài đặt riêng cho từng panel
- **Hỗ trợ theme**: Có thể cấu hình UI themes

### Hệ thống Menu
**File Menu**:
- New Template
- Open Template
- Export Results
- Exit

**Edit Menu**:
- Preferences

**Help Menu**:
- Documentation
- About

## Xử lý lỗi

### Quản lý Exception
- **Degradation nhẹ nhàng**: Panels hiển thị placeholders khi khởi tạo thất bại
- **Thông báo thân thiện**: MessageBox dialogs cho lỗi người dùng
- **Tích hợp logging**: Tất cả lỗi được log với context
- **Cơ chế phục hồi**: Retry logic cho các thao tác thất bại

### Kiểm tra đầu vào
- **Tham số kết nối**: Kiểm tra IP address và port
- **Nội dung template**: Kiểm tra JSON
- **Đầu vào tham số**: Kiểm tra theo từng loại
- **Thao tác file**: Kiểm tra đường dẫn và quyền

## Tích hợp với các Module khác

### Tích hợp Core Module
```python
# MainWindow sử dụng core components
self.test_loader = TestCaseLoader()          # Template loading
self.result_manager = ResultManager()        # Result storage
```

### Tích hợp Network Module
```python
# Kết nối và thực thi
self.connection_manager = ConnectionManager()
self.test_executor = TestExecutor(self.connection_manager)
```

### Tích hợp Utils Module
```python
# Utilities và verification
self.script_verifier = ScriptVerifier()      # Script verification
# Logger integration through get_logger()
```

## Liên kết

- [Core Documentation](../core/README.md) - TestCaseLoader, ResultManager integration
- [Network Documentation](../network/README.md) - ConnectionManager, TestExecutor integration
- [Utils Documentation](../utils/README.md) - ScriptVerifier, logging integration
- [Main README](../../README.md) - Tổng quan hệ thống
