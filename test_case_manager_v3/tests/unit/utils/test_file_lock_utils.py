#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for file_lock_utils module

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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import module cần test
from src.utils.file_lock_utils import read_file_with_lock, write_file_with_lock

@pytest.fixture
def temp_dir():
    """Fixture tạo thư mục tạm cho test"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

def test_write_and_read_with_lock(temp_dir):
    """Test cơ bản: ghi và đọc file với lock"""
    file_path = os.path.join(temp_dir, "test.json")
    test_data = {"test": "data", "number": 123}
    
    # Ghi file
    success = write_file_with_lock(file_path, test_data)
    assert success is True
    assert os.path.exists(file_path)
    
    # Đọc file
    read_data = read_file_with_lock(file_path)
    assert read_data is not None
    assert read_data == test_data
    
    # Kiểm tra file lock đã được xóa
    assert not os.path.exists(file_path + ".lock")

def test_concurrent_access(temp_dir):
    """Test truy cập đồng thời: nhiều thread cùng đọc/ghi một file"""
    file_path = os.path.join(temp_dir, "concurrent.json")
    results = []
    
    def writer_thread(data):
        success = write_file_with_lock(file_path, data)
        results.append(("write", data, success))
    
    def reader_thread():
        data = read_file_with_lock(file_path)
        results.append(("read", data))
    
    # Tạo và chạy các thread
    threads = []
    for i in range(5):
        # Xen kẽ thread đọc và ghi
        if i % 2 == 0:
            t = threading.Thread(target=writer_thread, args=({"id": i},))
        else:
            t = threading.Thread(target=reader_thread)
        threads.append(t)
        t.start()
    
    # Đợi tất cả thread hoàn thành
    for t in threads:
        t.join()
    
    # Kiểm tra kết quả
    write_successes = sum(1 for r in results if r[0] == "write" and r[2] is True)
    assert write_successes > 0
    
    # Kiểm tra file lock đã được xóa
    assert not os.path.exists(file_path + ".lock")

def test_empty_file_retry(temp_dir):
    """Test retry khi gặp file trống"""
    file_path = os.path.join(temp_dir, "empty.json")
    
    # Tạo file trống
    with open(file_path, 'w') as f:
        pass
    
    # Đọc file trống (sẽ retry và trả về None)
    data = read_file_with_lock(file_path, max_retries=2)
    assert data is None

def test_lock_contention(temp_dir):
    """Test khi file bị lock bởi process khác"""
    file_path = os.path.join(temp_dir, "locked.json")
    lock_path = file_path + ".lock"
    
    # Tạo file lock giả
    with open(lock_path, 'w') as f:
        f.write("fake_pid")
    
    # Thử đọc file (sẽ retry và trả về None do file bị lock)
    start_time = time.time()
    data = read_file_with_lock(file_path, max_retries=2, initial_backoff=0.1)
    end_time = time.time()
    
    # Kiểm tra thời gian thực hiện (phải lớn hơn tổng thời gian backoff)
    # 0.1s + 0.2s = 0.3s
    assert end_time - start_time >= 0.3
    assert data is None 