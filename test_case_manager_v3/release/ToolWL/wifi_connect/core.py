# wifi_connect/core.py
import time
import sys
import platform
import pywifi
from pywifi import const

def get_iface():
    wifi = pywifi.PyWiFi()
    ifaces = wifi.interfaces()
    if not ifaces:
        raise RuntimeError("No Wi-Fi card found.")
    return ifaces[0]

def scan_networks():
    iface = get_iface()
    iface.scan()
    time.sleep(2)
    return sorted({cell.ssid for cell in iface.scan_results() if cell.ssid})

def get_current_ssid():
    iface = get_iface()
    status = iface.status()
    if status in (const.IFACE_CONNECTED, const.IFACE_INACTIVE):
        import subprocess, re
        if platform.system().lower().startswith('win'):
            out = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'], encoding='oem', errors='ignore')
            m = re.search(r'\s*SSID\s*:\s*(.+)', out)
            return m.group(1).strip() if m else None
        else:
            return subprocess.check_output(['iwgetid', '-r'], encoding='utf-8', errors='ignore').strip()
    return None

def disconnect():
    iface = get_iface()
    iface.disconnect()
    time.sleep(1)

def connect(ssid, password=None, timeout=20):
    iface = get_iface()
    # iface.remove_all_network_profiles()
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    if password:
        profile.key = password
    prof = iface.add_network_profile(profile)
    iface.connect(prof)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if iface.status() == const.IFACE_CONNECTED:
            return True
        time.sleep(1)
    return False

def wifi_check_connect_to_ap(ssid, password=None, timeout=20, scan_interval=2, max_retries=10):
    retries = 0
    while retries < max_retries:
        networks = scan_networks()
        if ssid in networks:
            return connect(ssid, password, timeout)
        time.sleep(scan_interval)
        retries += 1
    return False