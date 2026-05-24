"""测试公共配置 — fixtures、工具函数、数据工厂。"""

import os
import sys
import tempfile

import pytest

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_dir():
    """提供临时目录，测试结束后自动清理。"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def tmp_json_file(tmp_dir):
    """提供临时JSON文件路径。"""
    return os.path.join(tmp_dir, "test.json")
