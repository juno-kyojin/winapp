from wifi_connect import wifi_check_connect_to_ap
import time
import sys

if __name__ == "__main__":
    with open("input.txt", "r", encoding="utf-8") as fin, open("output.txt", "w", encoding="utf-8") as fout:
        ssid = fin.readline().strip()
        password = fin.readline().strip()
        ##
        print(f"Checking SSID: {ssid}")
        if wifi_check_connect_to_ap(ssid, password, timeout=20, scan_interval=2, max_retries=10):
            print(f"Successfully connected to: {ssid}")
            print(1, file=fout)
        else:
            print(f"Failed to connect to: {ssid}")
            print(0, file=fout)
            exit(1)
