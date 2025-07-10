# Test Case Manager v1.0 - Hướng dẫn sử dụng

**Công cụ quản lý và thực thi Test Case toàn diện cho thiết bị OpenWrt**

[![Phiên bản](https://img.shields.io/badge/phiên_bản-1.0-blue.svg)](https://github.com/juno-kyojin/winapp)
[![Nền tảng](https://img.shields.io/badge/nền_tảng-Windows-lightgrey.svg)](https://github.com/juno-kyojin/winapp)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)

## Mục lục

1. [Tổng quan](#tổng-quan)
2. [Cài đặt và khởi chạy](#cài-đặt-và-khởi-chạy)
3. [Hướng dẫn sử dụng ứng dụng](#hướng-dẫn-sử-dụng-ứng-dụng)
4. [Kiến trúc hệ thống](#kiến-trúc-hệ thống)
5. [Xử lý sự cố](#xử-lý-sự-cố)

## Tổng quan

Test Case Manager v1.0 là ứng dụng Windows chuyên nghiệp được thiết kế để kiểm thử toàn diện các thiết bị OpenWrt. Ứng dụng cung cấp giao diện trực quan với 5 tab chính để tạo, quản lý và thực thi các test case từ xa thông qua giao thức HTTP.

### Tính năng chính

- **Thực thi test từ xa**: Chạy test case trên thiết bị OpenWrt từ máy tính Windows qua HTTP (port 6262)
- **Giám sát thời gian thực**: Theo dõi trực tiếp tiến trình thực thi test trong tab Stream với progress tracking
- **Xử lý hàng loạt**: Thực thi nhiều test case tuần tự với quản lý hàng đợi và reordering
- **Kiểm thử mạng toàn diện**: Hỗ trợ đầy đủ LAN, WAN, WIRELESS, NETWORK test categories
- **Script verification tự động**: Thực thi script PC-side từ ToolWL folder để xác minh kết quả test
- **Intelligent retry mechanism**: Phân biệt network errors và application errors với retry logic thông minh
- **Transaction ID tracking**: Theo dõi từng test với unique transaction ID để đảm bảo kết quả chính xác
- **Giao diện 5 tab**: Connection, Templates, Queue, Stream, Logs với chức năng chuyên biệt
- **Centralized logging**: Real-time system logs với filtering, search và export functionality
- **Ứng dụng độc lập**: Executable hoàn chỉnh không cần cài đặt Python, bao gồm ToolWL verification scripts

## Cài đặt và khởi chạy

### Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|-------------|
| **Hệ điều hành** | Windows 10/11 (64-bit) |
| **Mạng** | Kết nối TCP đến thiết bị OpenWrt |
| **Cổng** | Cổng 6262 mở trên thiết bị OpenWrt |
| **Bộ nhớ** | Tối thiểu 4GB RAM |
| **Dung lượng** | 100MB dung lượng trống |

### Khởi chạy nhanh (Ứng dụng độc lập)

**Dành cho người dùng cuối - Không cần cài đặt Python:**

1. Tải xuống phiên bản mới nhất từ thư mục `release/`
2. Giải nén file nén vào vị trí mong muốn
3. Chạy `TestCaseManager.exe`
4. Cấu hình kết nối thiết bị OpenWrt trong tab Connection

### Chạy từ mã nguồn

**Dành cho nhà phát triển:**

```bash
# Clone repository
git clone https://github.com/juno-kyojin/winapp.git
cd winapp/test_case_manager_v3

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy từ mã nguồn
python run.py
```

### Cấu hình kết nối

#### Thiết lập ứng dụng PC:
1. Khởi chạy ứng dụng Test Case Manager v1.0
2. Chuyển đến tab "Connection"
3. Cấu hình thông tin kết nối:
   - **Host**: Địa chỉ IP thiết bị OpenWrt (ví dụ: `192.168.1.1`)
   - **Port**: `6262` (cổng mặc định của communicate server)
   - **Connect Timeout**: `5` giây (thời gian chờ kết nối)
   - **Read Timeout**: `40` giây (khuyến nghị cho wireless tests)
4. Nhấn "Test Connection" để kiểm tra kết nối
5. Lưu cấu hình bằng nút "Save Settings"

#### Thiết lập thiết bị OpenWrt:
```bash
# Khởi động test execution engine + communicate server
cd /path/to/rnd_autotest
./auto_test
```

**Kiểm tra dịch vụ:**
```bash
# Kiểm tra communicate server đang chạy
netstat -ln | grep 6262

# Kiểm tra auto_test đang giám sát
ps | grep auto_test
```

## Hướng dẫn sử dụng ứng dụng

### Giao diện chính

Ứng dụng Test Case Manager v1.0 có giao diện với 5 tab chính, mỗi tab có chức năng riêng biệt:

#### 1. Tab Connection (Kết nối)
**Mục đích**: Cấu hình và quản lý kết nối đến thiết bị OpenWrt

**Các thành phần**:
- **Connection Type**: Chọn loại kết nối (HTTP - mặc định)
- **Host**: Địa chỉ IP thiết bị OpenWrt
- **Port**: Cổng kết nối (mặc định 6262)
- **Timeout Settings**: Cấu hình thời gian chờ kết nối và đọc dữ liệu
- **Connection Status**: Hiển thị trạng thái kết nối real-time

**Hướng dẫn sử dụng**:
1. Nhập địa chỉ IP thiết bị OpenWrt (ví dụ: `192.168.1.1`)
2. Đảm bảo Port là `6262` (cổng communicate server)
3. Đặt Connect Timeout = `5` giây
4. Đặt Read Timeout = `40` giây (khuyến nghị cho wireless tests)
5. Nhấn "Test Connection" để kiểm tra kết nối
6. Khi kết nối thành công, nhấn "Save Settings" để lưu cấu hình

#### 2. Tab Templates (Mẫu test)
**Mục đích**: Chọn và cấu hình các test case từ template library

**Các thành phần**:
- **Category Selection**: Chọn loại test (LAN, WAN, WIRELESS, NETWORK)
- **Test List**: Danh sách các test case có sẵn trong category
- **Parameter Configuration**: Form cấu hình tham số cho test được chọn
- **Validation**: Kiểm tra tính hợp lệ của tham số
- **Add to Queue**: Thêm test đã cấu hình vào hàng đợi thực thi

**Hướng dẫn sử dụng**:
1. Chọn category từ dropdown (LAN/WAN/WIRELESS/NETWORK)
2. Chọn test case cụ thể từ danh sách
3. Cấu hình các tham số cần thiết trong form (IP, SSID, password, etc.)
4. Kiểm tra validation messages nếu có
5. Nhấn "Add to Queue" để thêm vào hàng đợi
6. Lặp lại để thêm nhiều test case khác nhau

#### 3. Tab Queue (Hàng đợi)
**Mục đích**: Quản lý và thực thi hàng loạt test case

**Các thành phần**:
- **Queue List**: Danh sách test case trong hàng đợi với thông tin chi tiết
- **Queue Controls**: Các nút điều khiển (Execute All, Execute Selected, Clear Queue)
- **Test Reordering**: Sắp xếp lại thứ tự test (Move Up/Down)
- **Individual Controls**: Xóa, chỉnh sửa từng test riêng lẻ
- **Queue Statistics**: Hiển thị số lượng test trong queue

**Hướng dẫn sử dụng**:
1. Xem danh sách test đã thêm vào queue với tên và category
2. Sử dụng "Move Up"/"Move Down" để sắp xếp thứ tự thực thi
3. Nhấn "Execute All" để chạy tất cả test tuần tự
4. Hoặc chọn test cụ thể và nhấn "Execute Selected"
5. Theo dõi tiến trình thực thi trong tab Stream
6. Sử dụng "Clear Queue" để xóa tất cả test

#### 4. Tab Stream (Giám sát thời gian thực)
**Mục đích**: Theo dõi tiến trình thực thi test và xem kết quả real-time

**Các thành phần**:
- **Current Test Info**: Thông tin test đang chạy với transaction ID và test name
- **Progress Indicators**: Thanh tiến trình với các giai đoạn (preparing, sending, processing, receiving, verification)
- **Execution Log**: Log chi tiết quá trình thực thi, retry attempts và verification steps
- **Results Summary**: Tóm tắt kết quả (Pass/Fail/Total) với execution time cho từng test
- **Queue Progress**: Hiển thị tiến trình khi execute queue (Test 2/5 completed)
- **Verification Status**: Trạng thái script verification với kết quả PC-side verification

**Hướng dẫn sử dụng**:
1. Chuyển đến tab này khi bắt đầu thực thi test để theo dõi real-time
2. Theo dõi "Current Test" name và transaction ID để identify test đang chạy
3. Xem progress bar qua các giai đoạn: preparing → sending → processing → receiving → verification
4. Đọc execution log để hiểu chi tiết retry mechanism và verification process
5. Kiểm tra kết quả cuối cùng (device result + PC verification combined)
6. Xem execution time để đánh giá performance của từng test

#### 5. Tab Logs (Nhật ký hệ thống)
**Mục đích**: Xem centralized system logs và debug chi tiết

**Các thành phần**:
- **Log Level Filter**: Lọc theo mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Real-time Log Display**: Hiển thị log thời gian thực từ tất cả system components
- **Log Search**: Tìm kiếm transaction ID, error messages, test names trong logs
- **Export Functions**: Xuất log ra file để troubleshooting và báo cáo
- **Auto-scroll**: Tự động scroll đến log entry mới nhất
- **Timestamp Display**: Hiển thị thời gian chính xác của mỗi log entry
- **Component Filtering**: Lọc log theo component (Connection Manager, Test Executor, etc.)

**Hướng dẫn sử dụng**:
1. Chọn mức độ log muốn xem (ERROR cho troubleshooting, INFO cho general monitoring)
2. Theo dõi log thời gian thực khi chạy test để debug issues
3. Sử dụng search function để tìm transaction ID cụ thể hoặc error messages
4. Xuất log ra file khi cần báo cáo lỗi hoặc phân tích performance
5. Sử dụng để debug retry mechanism, script verification và connection issues
6. Filter theo component để focus vào specific system parts
### Quy trình làm việc cơ bản

#### Quy trình thực thi test đơn lẻ:
1. **Chuẩn bị**: Kết nối thiết bị OpenWrt và cấu hình connection trong tab Connection
2. **Chọn test**: Vào tab Templates, chọn category (LAN/WAN/WIRELESS/NETWORK) và test case cụ thể
3. **Cấu hình**: Điền các tham số cần thiết cho test (IP addresses, SSID, passwords, etc.)
4. **Thực thi**: Nhấn "Execute Test" để chạy ngay lập tức hoặc "Add to Queue" rồi execute
5. **Theo dõi**: Chuyển sang tab Stream để xem tiến trình real-time với transaction ID
6. **Kết quả**: Xem kết quả test (Pass/Fail), thời gian thực thi và verification status

#### Quy trình thực thi test hàng loạt:
1. **Chuẩn bị**: Đảm bảo kết nối ổn định với thiết bị OpenWrt
2. **Thêm test**: Sử dụng tab Templates để thêm nhiều test case vào Queue
3. **Sắp xếp**: Dùng tab Queue để sắp xếp thứ tự thực thi với Move Up/Down
4. **Thực thi**: Nhấn "Execute All" để chạy tất cả test tuần tự
5. **Giám sát**: Theo dõi tiến trình trong tab Stream với queue progress (Test 2/5)
6. **Phân tích**: Xem tổng kết kết quả, execution times và system logs chi tiết

### Hệ thống Script Verification

Test Case Manager v1.0 có tính năng **automatic script verification** - tự động thực thi script PC-side để xác minh kết quả test.

#### Cách hoạt động:
1. **Device Test**: Test được thực thi trên OpenWrt device trước
2. **Response Analysis**: Hệ thống kiểm tra response có field `script` không
3. **Script Execution**: Nếu có, tự động thực thi script từ ToolWL folder
4. **Result Combination**: Kết hợp kết quả device + PC verification thành final result

#### Ví dụ luồng Wireless Test:
```
1. Device: Cấu hình WiFi AP → SUCCESS
2. Response: {"script": "wireless_edit_ap.py", "script_params": ["TestAP", "password123"]}
3. PC: Chạy wireless_edit_ap.py để verify WiFi connection → SUCCESS/FAIL
4. Final: Device SUCCESS + PC SUCCESS = FINAL SUCCESS
```

#### Script Interface Standard:
- **Input**: Đọc parameters từ `ToolWL/input.txt` (một parameter mỗi dòng)
- **Output**: Ghi kết quả vào `ToolWL/output.txt` ("1" = pass, "0" = fail)
- **Execution**: Synchronous execution sau khi nhận device response
- **Timeout**: Script có timeout để tránh hang indefinitely

#### Các script verification hiện có:
- `wireless_edit_ap.py`: Verify WiFi AP configuration và connection test
- `lan_edit_leasetime.py`: Verify LAN DHCP lease time configuration
- `lan_edit_ip_start.py`: Verify LAN IP range configuration
- `module.py`: Common verification modules và utilities

### Intelligent Retry Mechanism

Hệ thống có cơ chế retry thông minh phân biệt giữa các loại lỗi để tối ưu hóa success rate:

#### Network Errors (Sẽ retry):
- **Connection timeout**: Mạng chậm hoặc tạm thời không khả dụng
- **Connection reset**: Kết nối bị đứt giữa chừng (ConnectionResetError)
- **DNS resolution failed**: Lỗi phân giải tên miền tạm thời
- **Socket errors**: Lỗi socket level và network infrastructure

#### Application Errors (Không retry):
- **HTTP 400 Bad Request**: Test case format không hợp lệ
- **HTTP 404 Not Found**: Endpoint không tồn tại
- **HTTP 500 Server Error**: Lỗi server application logic
- **JSON parsing errors**: Response không phải JSON hợp lệ

#### Retry Strategy:
- **Max retries**: 3 attempts cho network errors only
- **Exponential backoff**: Tăng dần thời gian chờ giữa các retry (2s, 4s, 8s)
- **Network-affecting tests**: Thời gian chờ lâu hơn cho tests ảnh hưởng đến connectivity
- **Transaction ID preservation**: Giữ nguyên transaction ID qua tất cả retry attempts
- **Intelligent detection**: Phân biệt transient vs permanent errors

### 📊 Hiểu kết quả test

#### Trạng thái test:
- **🟢 Success**: Test thực thi thành công, kết quả đạt yêu cầu
- **🔴 Failed**: Test thất bại hoặc không đạt yêu cầu
- **🟡 Timeout**: Test bị timeout, có thể do mạng chậm
- **⚪ Pending**: Test đang chờ trong hàng đợi
- **🔵 Running**: Test đang được thực thi

#### Thông tin kết quả:
- **Execution Time**: Thời gian thực thi test (giây)
- **Transaction ID**: Mã định danh duy nhất của test
- **Response Data**: Dữ liệu phản hồi từ thiết bị
- **Error Messages**: Thông báo lỗi (nếu có)

### Các loại test phổ biến

#### 1. Network Tests (Kiểm thử mạng):
- **Ping Test**: Kiểm tra kết nối internet đến các host (google.com, youtube.com)
- **Speed Test**: Đo tốc độ mạng upload/download
- **DNS Test**: Kiểm tra phân giải tên miền và DNS server response
- **Connectivity Test**: Kiểm tra kết nối tổng thể của thiết bị

#### 2. LAN Tests (Kiểm thử mạng nội bộ):
- **LAN IP Configuration**: Cấu hình địa chỉ IP LAN và subnet mask
- **DHCP Settings**: Cấu hình DHCP server, lease time, IP range
- **Port Forwarding**: Cấu hình chuyển tiếp cổng cho services
- **LAN Interface**: Kiểm tra cấu hình interface LAN

#### 3. WAN Tests (Kiểm thử mạng WAN):
- **WAN Connection**: Kiểm tra kết nối WAN với ISP
- **PPPoE Configuration**: Cấu hình PPPoE với username/password
- **Static IP Setup**: Cấu hình IP tĩnh cho WAN interface
- **WAN Interface**: Kiểm tra cấu hình và status của WAN

#### 4. Wireless Tests (Kiểm thử không dây với verification):
- **WiFi AP Configuration**: Cấu hình Access Point với SSID, password, security
- **WiFi Security**: Kiểm tra các mode bảo mật (WPA2, WPA3)
- **WiFi Channel**: Cấu hình channel và bandwidth
- **Script Verification**: Tự động chạy wireless_edit_ap.py để verify connection từ PC

## Kiến trúc hệ thống

### Tổng quan kiến trúc

Hệ thống Test Case Manager v1.0 bao gồm hai thành phần chính:

1. **Test Case Manager v1.0** (Windows PC): Ứng dụng GUI để quản lý và giám sát test
2. **OpenWrt Device**: Thiết bị chạy các thành phần server và test execution

### Sơ đồ luồng thực thi

Xem file `sequence_diagram.mmd` để có sơ đồ chi tiết về kiến trúc và luồng thực thi của hệ thống.

#### Tóm tắt luồng chính:

1. **Khởi tạo hệ thống**:
   - PC: Test Case Manager v1.0 khởi động và kết nối HTTP Client
   - OpenWrt: auto_test engine khởi động communicate server (port 6262)

2. **Chuẩn bị test case**:
   - User chọn test từ Templates tab với category selection
   - Cấu hình parameters và validation
   - Thêm vào Queue với reordering capability

3. **Thực thi test với retry mechanism**:
   - Test Executor gửi test qua Connection Manager
   - HTTP Client gửi POST request với transaction ID
   - Intelligent retry cho network errors (max 3 attempts)
   - Device thực thi test và tạo result file với transaction ID mapping

4. **Script verification tự động** (nếu cần):
   - Script Verifier kiểm tra response có field 'script'
   - Thực thi verification script từ ToolWL folder
   - Kết hợp kết quả device + PC verification thành final result

5. **Giám sát và logging**:
   - Stream Panel hiển thị progress real-time với execution phases
   - Logs Panel ghi nhận system logs với filtering và search
   - Result Manager lưu trữ kết quả chi tiết với history

### Thành phần hệ thống

#### Phía Windows PC (Test Case Manager v1.0):
- **Main Window**: Giao diện chính với 5 tab (Connection, Templates, Queue, Stream, Logs)
- **Connection Manager**: Quản lý kết nối HTTP với intelligent retry mechanism và error classification
- **HTTP Client**: Client HTTP với session management, timeout handling và transaction ID tracking
- **Test Executor**: Engine thực thi test với network-affecting test detection và verification integration
- **Script Verifier**: Tự động thực thi verification scripts từ ToolWL folder với input/output interface
- **Test Case Loader**: Tải và validate template test cases từ data/templates/
- **Queue Manager**: Quản lý hàng đợi thực thi với reordering, individual controls
- **Stream Panel**: Giám sát real-time progress với execution phases và queue tracking
- **Logs Panel**: Centralized logging với filtering, search và export functionality
- **Result Manager**: Lưu trữ và quản lý kết quả test chi tiết với history và metadata

#### Phía OpenWrt Device:
- **communicate**: HTTP server nhận request từ PC (port 6262) với REST API endpoints
- **auto_test**: Engine thực thi test case trên thiết bị OpenWrt với result file generation
- **Result Files**: File kết quả JSON với transaction ID mapping trong temp directory

#### ToolWL Verification Scripts:
- **Verification Scripts**: Python scripts cho PC-side verification với standardized interface
- **Input/Output Interface**: input.txt/output.txt interface cho parameter passing và result reporting
- **Wireless Scripts**: wireless_edit_ap.py cho WiFi AP verification
- **LAN Scripts**: lan_edit_leasetime.py, lan_edit_ip_start.py cho LAN configuration verification
- **Common Modules**: module.py với shared utilities và helper functions

### Giao thức giao tiếp

#### HTTP API Endpoints:
- `POST /`: Gửi test case để thực thi (root endpoint với JSON payload)
- `GET /check_result/{transaction_id}`: Polling để lấy kết quả test theo transaction ID
- `GET /ping`: Health check endpoint để kiểm tra server status và connectivity

#### Cấu trúc dữ liệu Test Case:
```json
{
  "test_cases": [
    {
      "service": "wireless",
      "action": "edit",
      "params": {
        "ssid": "TestAP",
        "password": "12345678",
        "security": "wpa2"
      }
    }
  ],
  "metadata": {
    "transaction_id": "20250710143524_77bda9d5"
  }
}
```

#### Cấu trúc Response với Script Verification:
```json
{
  "summary": {
    "total_test_cases": 1,
    "passed": 1,
    "failed": 0,
    "failed_services": []
  },
  "script": "wireless_edit_ap.py",
  "script_params": ["TestAP", "12345678"]
}
```

#### Luồng dữ liệu chi tiết:
1. **Test Submission**: PC gửi test case qua HTTP POST với transaction ID và headers
2. **Intelligent Retry**: Retry mechanism phân biệt network vs application errors với exponential backoff
3. **Device Execution**: OpenWrt device thực thi test và tạo result file với transaction ID mapping
4. **Result Polling**: PC polling GET /check_result/{transaction_id} với 2-second intervals
5. **Script Verification**: Tự động thực thi verification script nếu response chứa 'script' field
6. **Final Result**: Kết hợp device result + verification result thành final status (SUCCESS/FAIL)

## Xử lý sự cố

### Lỗi kết nối thường gặp

#### 1. Connection Timeout
**Triệu chứng**: "Connection timeout" trong tab Connection hoặc Stream
**Nguyên nhân**:
- Thiết bị OpenWrt không khả dụng hoặc không chạy communicate server
- Port 6262 bị chặn bởi firewall
- Mạng không ổn định hoặc latency cao
- Địa chỉ IP không chính xác

**Giải pháp**:
```bash
# Kiểm tra kết nối mạng cơ bản
ping 192.168.1.1

# Kiểm tra port 6262 có mở không
telnet 192.168.1.1 6262

# Kiểm tra communicate server đang chạy
netstat -ln | grep 6262

# Khởi động lại auto_test và communicate server
cd /path/to/rnd_autotest
./auto_test
```

#### 2. Test Execution Failed
**Triệu chứng**: Test hiển thị "Failed" trong Stream tab với error message
**Nguyên nhân**:
- Tham số test không hợp lệ hoặc missing required fields
- Thiết bị không hỗ trợ test case cụ thể
- Lỗi trong quá trình thực thi trên device
- Script verification failed (device pass nhưng PC verification fail)
- Network errors không được retry thành công

**Giải pháp**:
1. Kiểm tra detailed logs trong tab Logs với ERROR level
2. Xác minh tham số test trong Templates tab và validation messages
3. Thử test đơn giản trước (ping test) để verify basic connectivity
4. Kiểm tra auto_test process đang chạy trên device
5. Nếu là verification failure, kiểm tra ToolWL scripts và input/output files
6. Xem transaction ID trong logs để trace specific test execution

#### 3. Wireless Test Timeout
**Triệu chứng**: Wireless test bị timeout thường xuyên, đặc biệt với verification
**Nguyên nhân**: Wireless test và verification cần thời gian dài hơn

**Giải pháp**:
1. Tăng Read Timeout lên 60-90 giây trong Connection tab
2. Kiểm tra cường độ tín hiệu WiFi và interference
3. Đảm bảo PC có thể connect đến WiFi AP được tạo
4. Kiểm tra ToolWL/wireless_edit_ap.py script hoạt động độc lập

### Debug và troubleshooting

#### Kiểm tra log hệ thống:
1. Mở tab Logs trong ứng dụng
2. Đặt filter = "ERROR" để xem lỗi, "INFO" để xem general flow
3. Sử dụng search function để tìm transaction ID cụ thể
4. Xuất log ra file để báo cáo chi tiết
5. Theo dõi real-time logs khi reproduce issue

#### Kiểm tra trạng thái device:
```bash
# Kiểm tra communicate process đang chạy
ps | grep communicate

# Kiểm tra auto_test process
ps | grep auto_test

# Kiểm tra port 6262 listening
netstat -ln | grep 6262

# Kiểm tra log device (nếu có)
tail -f /path/to/rnd_autotest/application.log
```

#### Test kết nối thủ công:
```bash
# Test ping endpoint
curl -X GET http://192.168.1.1:6262/ping

# Test gửi test case với transaction ID
curl -X POST http://192.168.1.1:6262/ \
  -H "Content-Type: application/json" \
  -H "X-Transaction-ID: test_20250710_001" \
  -d '{"test_cases":[{"service":"ping","params":{"host":"8.8.8.8"}}],"metadata":{"transaction_id":"test_20250710_001"}}'

# Test lấy kết quả
curl -X GET http://192.168.1.1:6262/check_result/test_20250710_001
```

#### Debug Script Verification:
```bash
# Kiểm tra ToolWL folder structure
ls -la ToolWL/

# Kiểm tra input/output files
cat ToolWL/input.txt
cat ToolWL/output.txt

# Test script verification manually
cd ToolWL
echo "TestAP" > input.txt
echo "password123" >> input.txt
python wireless_edit_ap.py
cat output.txt

# Kiểm tra script dependencies
python -c "import module; print('Module OK')"
```

### Hỗ trợ kỹ thuật

Khi gặp sự cố không thể tự giải quyết:

1. **Thu thập thông tin**:
   - Screenshot lỗi từ ứng dụng (đặc biệt tab Stream và Logs)
   - Log files từ tab Logs (xuất ra file với timestamp)
   - Transaction ID của test bị lỗi
   - Thông tin cấu hình mạng và connection settings
   - Phiên bản ứng dụng và OpenWrt firmware

2. **Thông tin cần cung cấp**:
   - Mô tả chi tiết sự cố và error messages
   - Các bước đã thực hiện để reproduce issue
   - Thời điểm xảy ra lỗi và frequency
   - Loại test gây ra sự cố (LAN/WAN/WIRELESS/NETWORK)
   - Retry attempts và intelligent retry behavior

3. **Tài liệu tham khảo**:
   - File README.md này cho comprehensive guide
   - Log files trong `data/logs/` cho system logs
   - Template files trong `data/templates/` cho test case structure
   - ToolWL folder cho verification script debugging

## Lưu ý quan trọng

**Trước khi kiểm thử:**
- Luôn kiểm tra kết nối trong tab Connection trước khi thực thi test case
- Wireless tests và script verification cần thời gian hoàn thành lâu hơn - hãy kiên nhẫn
- Theo dõi tab Stream để cập nhật tiến trình thời gian thực và transaction ID
- Sao lưu các test case quan trọng và custom templates thường xuyên
- Sử dụng meaningful test names để dễ dàng tracking trong logs

**Nhận hỗ trợ:**
- Kiểm tra phần xử lý sự cố và debug guide trước tiên
- Sử dụng tab Logs với ERROR level để debug chi tiết
- Theo dõi device logs khi cần thiết
- Liên hệ team phát triển với đầy đủ thông tin debug

## Cấu trúc thư mục Release

Sau khi build thành công, thư mục `release/` sẽ chứa:

```
release/
├── TestCaseManager.exe     # File thực thi chính
├── ToolWL/                # Verification scripts folder
│   ├── input.txt          # Script input interface
│   ├── output.txt         # Script output interface
│   ├── wireless_edit_ap.py # WiFi verification script
│   ├── lan_edit_leasetime.py # LAN verification script
│   ├── lan_edit_ip_start.py # LAN IP range verification
│   ├── module.py          # Common verification modules
│   └── wifi_connect/      # WiFi connection utilities
└── data/                  # Dữ liệu ứng dụng
    ├── config/            # File cấu hình connection và settings
    ├── logs/              # File log hệ thống với timestamp
    ├── temp/              # File tạm và test results với transaction ID
    └── templates/         # Template test case (LAN/WAN/WIRELESS/NETWORK)
        ├── lan/           # LAN test templates
        ├── wan/           # WAN test templates
        ├── wireless/      # Wireless test templates
        └── network/       # Network test templates
```

---

**Test Case Manager v1.0** - Công cụ quản lý và thực thi test case chuyên nghiệp cho thiết bị OpenWrt

Copyright © 2025. Tất cả quyền được bảo lưu.
