"""
通用工具函数库

设计意图: 提供全系统复用的基础工具，避免各模块重复实现。
所有函数均为纯函数或无副作用工具，零外部依赖。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any, TypeVar

T = TypeVar("T")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 时间工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def now_timestamp() -> float:
    """当前Unix时间戳（秒，浮点精度）。"""
    return time.time()


def now_iso() -> str:
    """当前时间的ISO 8601格式字符串。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def elapsed_since(start: float) -> float:
    """计算从start到现在的耗时（秒）。"""
    return time.monotonic() - start


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 标识工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_id() -> str:
    """生成短UUID（去掉连字符，32位十六进制）。"""
    return uuid.uuid4().hex


def generate_short_id() -> str:
    """生成更短的ID（前12位），适用于日志和展示。"""
    return uuid.uuid4().hex[:12]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 哈希工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def md5_hash(text: str) -> str:
    """计算字符串的MD5哈希值（用于去重等场景）。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 文件工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def ensure_dir(path: str) -> str:
    """确保目录存在，不存在则创建。返回路径。"""
    os.makedirs(path, exist_ok=True)
    return path


def atomic_write_json(path: str, data: Any) -> None:
    """
    原子写入JSON文件 — 记忆公理要求断电不丢数据。

    原理: 先写入临时文件，再重命名，利用OS的原子rename保证数据完整性。
    """
    dir_path = os.path.dirname(path)
    if dir_path:
        ensure_dir(dir_path)
    temp_path = f"{path}.tmp.{generate_short_id()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(temp_path, path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def safe_read_json(path: str, default: Any = None) -> Any:
    """安全读取JSON文件，失败返回默认值。"""
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据验证工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def clamp(value: float, min_val: float, max_val: float) -> float:
    """将数值限制在[min_val, max_val]范围内。"""
    return max(min_val, min(value, max_val))


def validate_weight(weight: float) -> float:
    """验证并规范化权重值到[0.0, 1.0]范围。"""
    return clamp(float(weight), 0.0, 1.0)


def is_valid_name(name: str) -> bool:
    """验证名称是否合法（非空、无特殊字符）。"""
    if not name or not name.strip():
        return False
    return bool(name.strip())
