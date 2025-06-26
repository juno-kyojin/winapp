#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LAN Checker for Test Case Manager
Provides basic functions to verify LAN configuration

Author: juno-kyojin
Created: 2025-06-25
"""

import re
import subprocess
import time
import logging
from datetime import datetime

# Core IP and lease time verification functions
def ip_to_int(ip: str) -> int:
    parts = [int(x) for x in ip.strip().split('.')]
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

def check_ip(ip: str, start: str, limit: int) -> bool:
    try:
        ip_int = ip_to_int(ip)
        start_int = ip_to_int(start)
        limit = int(limit)
    except Exception:
        return False
    return start_int <= ip_int <= start_int + limit

def parse_leasetime(leasetime: str):
    formats = [
        "%A, %B %d, %Y %I:%M:%S %p",   # Thursday, June 26, 2025 8:06:09 AM
        "%d %B %Y %H:%M:%S",           # 25 June 2025 12:01:27
        "%d/%m/%Y %H:%M:%S",           # 25/06/2025 12:01:27
        "%Y-%m-%d %H:%M:%S",           # 2025-06-25 12:01:27
    ]
    for fmt in formats:
        try:
            return datetime.strptime(leasetime, fmt)
        except Exception:
            continue
    return None

def check_leasetime(leasetime: str, leasetime_config: int) -> bool:
    dt = parse_leasetime(leasetime)
    if not dt:
        return False
    lease_ts = int(dt.timestamp())
    now_ts = int(datetime.now().timestamp())
    diff = lease_ts - now_ts
    return diff < leasetime_config

def get_ip_start(ipconfig_output: str):
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section:
            continue
        if "VMware" in section or "vEthernet" in section:
            continue
        ip_match = re.search(r"IPv4 Address[^\:]*:\s*([\d\.]+)", section)
        if not ip_match:
            ip_match = re.search(r"IPv4[\s\.]*:\s*([\d\.]+)", section)
        if ip_match:
            return ip_match.group(1)
    return None

def get_leasetime(ipconfig_output: str):
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section:
            continue
        if "VMware" in section or "vEthernet" in section:
            continue
        lease_match = re.search(r"Lease Expires[^\:]*:\s*(.+)", section)
        if lease_match:
            return lease_match.group(1).strip()
    return None

# Simple helpers for test case manager integration
def get_current_network_info():
    """Get current network information without any changes"""
    try:
        result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        return {
            "output": output,
            "ip": get_ip_start(output),
            "leasetime": get_leasetime(output)
        }
    except Exception:
        return {"output": "", "ip": None, "leasetime": None}

def refresh_network_config():
    """Simple network refresh using only ipconfig /renew"""
    logger = logging.getLogger(__name__)
    logger.info("Refreshing network configuration (ipconfig /renew)")
    try:
        subprocess.run(["ipconfig", "/renew"], capture_output=True, text=True, timeout=60)
        logger.info("IP renewal request completed")
    except subprocess.TimeoutExpired:
        # Bỏ cảnh báo này đi, chỉ tiếp tục không log gì cả
        pass
    except Exception as e:
        logger.warning(f"DHCP renew error: {e}")

def verify_lan_test(test_data, result_data, logger=None):
    """Simple verification of LAN test results focusing on network connectivity only"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    # Đảm bảo result_data là dict
    if result_data is None:
        result_data = {}
    
    # Kiểm tra kết quả từ router thành công
    if result_data and "summary" in result_data and result_data["summary"].get("passed", 0) > 0:
        # Refresh network để lấy thông tin mới nhất
        refresh_network_config()
        network_info = get_current_network_info()
        
        # Kiểm tra đơn giản: có kết nối mạng không
        if network_info["ip"]:
            logger.info(f"Network connection verified: IP={network_info['ip']}")
            result_data["client_verification"] = {
                "status": True,
                "message": f"Network connection verified with IP {network_info['ip']}"
            }
            
            # Nếu có thông tin test case, log thêm thông tin phụ trợ
            if test_data and "test_cases" in test_data and test_data["test_cases"]:
                test_case = test_data["test_cases"][0]
                action = test_case.get("action", "").lower()
                
                # Log thông tin lease time nếu liên quan
                if action == "edit_leasetime" and network_info["leasetime"]:
                    logger.info(f"Current lease time: {network_info['leasetime']}")
                    
                # In IP hiện tại cho test liên quan đến IP
                if "ip" in action and network_info["ip"]:
                    logger.info(f"Current IP: {network_info['ip']}")
            
            # Báo cáo thành công cho client verification
            if "client_verification" in result_data:
                logger.info(f"Client verification passed: {result_data['client_verification']['message']}")
        else:
            logger.error("Failed to verify network connection")
            result_data["client_verification"] = {
                "status": False,
                "message": "Failed to verify network connection"
            }
    
    return result_data