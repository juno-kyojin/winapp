from wifi_connect import wifi_check_connect_to_ap
import time
import sys

if __name__ == "__main__":
    with open("input.txt", "r", encoding="utf-8") as fin, open("output.txt", "w", encoding="utf-8") as fout:
        ssid = fin.readline().strip()
        password = fin.readline().strip()
        ##
        print(f"🔍 Đang kiểm tra SSID “{ssid}”…")
        if wifi_check_connect_to_ap(ssid, password, timeout=20, scan_interval=2, max_retries=10):
            print(f"✅ Kết nối thành công tới “{ssid}”.")
            print(1, file=fout)
        else:
            print(f"❌ Không thể kết nối tới “{ssid}”.")
            print(0, file=fout)
            exit(1)
