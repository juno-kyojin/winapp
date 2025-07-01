#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for file-based IPC with file locking

Author: juno-kyojin
Created: 2025-07-05
"""

import os
import json
import time
import pytest
import tempfile
import threading
from pathlib import Path
import sys
import os.path

# Add project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import các module cần test
from src.utils.file_lock_utils import read_file_with_lock, write_file_with_lock

@pytest.fixture
def temp_test_env():
    """Fixture tạo môi trường test tạm"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        config_dir = os.path.join(tmpdirname, "config")
        result_dir = os.path.join(tmpdirname, "result")
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)
        yield {
            "root": tmpdirname,
            "config_dir": config_dir,
            "result_dir": result_dir,
            "config_file": os.path.join(config_dir, "config.json"),
            "result_file": os.path.join(result_dir, "result.json")
        }

def test_file_based_ipc_with_locking(temp_test_env):
    """Test cơ chế IPC dựa trên file với file locking"""
    config_file = temp_test_env["config_file"]
    result_file = temp_test_env["result_file"]
    
    # Mô phỏng server và client
    def server_thread():
        # Server đọc config_file và ghi result_file
        for _ in range(5):
            config = read_file_with_lock(config_file)
            if config:
                # Xử lý config và tạo result
                result = {
                    "status": "success",
                    "input": config,
                    "timestamp": time.time()
                }
                write_file_with_lock(result_file, result)
                break
            time.sleep(0.2)
    
    def client_thread():
        # Client ghi config_file và đọc result_file
        config = {
            "test_id": "test-123",
            "action": "ping",
            "params": {"target": "example.com"}
        }
        write_file_with_lock(config_file, config)
        
        # Đợi và đọc kết quả
        result = None
        for _ in range(10):  # Thử tối đa 10 lần
            result = read_file_with_lock(result_file)
            if result:
                break
            time.sleep(0.5)
        
        assert result is not None
        assert result["status"] == "success"
        assert result["input"] == config
    
    # Chạy các thread
    server = threading.Thread(target=server_thread)
    client = threading.Thread(target=client_thread)
    
    server.start()
    time.sleep(0.1)  # Đảm bảo server đã sẵn sàng
    client.start()
    
    client.join()
    server.join()

def test_multiple_clients_with_locking(temp_test_env):
    """Test nhiều client cùng ghi file với file locking"""
    config_file = temp_test_env["config_file"]
    successful_writes = 0
    
    def client_thread(client_id):
        nonlocal successful_writes
        config = {
            "test_id": f"test-{client_id}",
            "action": "ping",
            "params": {"target": "example.com"}
        }
        success = write_file_with_lock(config_file, config)
        if success:
            successful_writes += 1
    
    # Chạy nhiều client cùng lúc
    clients = []
    for i in range(10):
        client = threading.Thread(target=client_thread, args=(i,))
        clients.append(client)
        client.start()
    
    # Đợi tất cả client hoàn thành
    for client in clients:
        client.join()
    
    # Kiểm tra kết quả
    assert successful_writes > 0  # Ít nhất một client đã ghi thành công
    
    # Đọc file cuối cùng
    final_config = read_file_with_lock(config_file)
    assert final_config is not None
    assert "test_id" in final_config
    assert final_config["action"] == "ping"