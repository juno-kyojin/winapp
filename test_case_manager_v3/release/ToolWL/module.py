# module.py
import subprocess
import time
import re
from datetime import datetime

def renew_ip_and_get_output() -> str | None:
    """Thực hiện renew IP và trả về output của 'ipconfig /all'."""
    try:
        # Chạy lệnh không hiển thị cửa sổ console
        creationflags = subprocess.CREATE_NO_WINDOW
        
        print("-> Đang renew IP...")
        subprocess.run(["ipconfig", "/renew"], check=True, capture_output=True, text=True, creationflags=creationflags)
        time.sleep(5)
        
        print("-> Đang lấy thông tin mạng...")
        result = subprocess.run(["ipconfig", "/all"], check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[Lỗi] Không thể chạy lệnh ipconfig: {e}")
        return None

def get_active_ip(ipconfig_output: str) -> str | None:
    """Trích xuất địa chỉ IP từ card mạng active."""
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section or "VMware" in section:
            continue
        ip_match = re.search(r"IPv4 Address[^\:]*:\s*([\d\.]+)", section)
        if ip_match:
            return ip_match.group(1).strip()
    return None

def check_ip_in_range(ip: str, start: str, limit: int) -> bool:
    """Kiểm tra IP có nằm trong dải cho trước không."""
    try:
        ip_int = int.from_bytes(bytes(map(int, ip.split('.'))), 'big')
        start_int = int.from_bytes(bytes(map(int, start.split('.'))), 'big')
        return start_int <= ip_int < start_int + limit
    except Exception:
        return False
# Thêm các hàm này vào cuối file module.py

def get_active_leasetime_str(ipconfig_output: str) -> str | None:
    """Trích xuất chuỗi 'Lease Expires' từ card mạng active."""
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section or "VMware" in section:
            continue
        lease_match = re.search(r"Lease Expires[^\:]*:\s*(.+)", section)
        if lease_match:
            return lease_match.group(1).strip()
    return None

def parse_leasetime_str(leasetime_str: str) -> datetime | None:
    """Phân tích chuỗi thời gian từ ipconfig."""
    formats = ["%A, %B %d, %Y %I:%M:%S %p", "%d %B %Y %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(leasetime_str, fmt)
        except ValueError:
            continue
    return None
def parse_leasetime(leasetime_str: str) -> datetime | None:
    """
    Phân tích chuỗi thời gian từ ipconfig, thử nhiều định dạng khác nhau.
    """
    formats = [
        "%A, %B %d, %Y %I:%M:%S %p",  # Thursday, June 26, 2025 8:06:09 AM
        "%d %B %Y %H:%M:%S",          # 25 June 2025 12:01:27
        "%d/%m/%Y %H:%M:%S",          # 25/06/2025 12:01:27
        "%Y-%m-%d %H:%M:%S",          # 2025-06-25 12:01:27
    ]
    for fmt in formats:
        try:
            return datetime.strptime(leasetime_str, fmt)
        except ValueError:
            continue
    return None