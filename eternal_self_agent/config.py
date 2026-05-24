"""
配置管理模块 — 系统参数统一管理

设计意图: 零外部依赖约束下，提供轻量化配置管理。
支持环境变量覆盖、JSON文件持久化、运行时热更新。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from eternal_self_agent.constants import DATA_DIR

logger = logging.getLogger(__name__)

# 默认配置 — 所有可调参数的唯一初始来源
_DEFAULTS: dict[str, Any] = {
    # 存续公理
    "loop_delay": 0.3,
    "evolve_step": 50,
    "self_repair_delay": 1.0,
    # 自驱公理
    "derive_weight_threshold": 0.2,
    "trim_weight_threshold": 0.1,
    # 资源守恒
    "task_queue_max": 200,
    # 日志
    "log_level": "INFO",
    "log_file": "",
}


class Config:
    """轻量化配置管理器 — 单例模式，全局唯一配置源。"""

    _instance: Config | None = None
    _data: dict[str, Any]

    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = dict(_DEFAULTS)
        return cls._instance

    # ── 加载 ──

    def load_from_file(self, path: str | None = None) -> None:
        """从JSON文件加载配置，覆盖默认值。"""
        if path is None:
            path = os.path.join(DATA_DIR, "config.json")
        if not os.path.isfile(path):
            logger.debug("配置文件不存在，使用默认配置: %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data: dict[str, Any] = json.load(f)
            self._data.update(file_data)
            logger.info("配置已从文件加载: %s", path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("配置文件加载失败，使用默认配置: %s", e)

    def load_from_env(self) -> None:
        """从环境变量加载配置，优先级最高。格式: ETERNAL_KEY=value"""
        prefix = "ETERNAL_"
        for key, default_value in _DEFAULTS.items():
            env_key = f"{prefix}{key.upper()}"
            env_value = os.environ.get(env_key)
            if env_value is not None:
                self._data[key] = self._cast(env_value, type(default_value))
                logger.debug("环境变量覆盖配置: %s=%s", env_key, env_value)

    # ── 保存 ──

    def save_to_file(self, path: str | None = None) -> None:
        """将当前配置持久化到JSON文件。"""
        if path is None:
            path = os.path.join(DATA_DIR, "config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.info("配置已保存: %s", path)
        except OSError as e:
            logger.error("配置保存失败: %s", e)

    # ── 读写 ──

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """运行时修改配置（热更新）。"""
        if key in _DEFAULTS:
            self._data[key] = value
            logger.debug("配置热更新: %s=%s", key, value)
        else:
            logger.warning("未知配置项: %s", key)

    def to_dict(self) -> dict[str, Any]:
        """返回配置快照。"""
        return dict(self._data)

    def reset(self) -> None:
        """重置为默认配置。"""
        self._data = dict(_DEFAULTS)
        logger.info("配置已重置为默认值")

    # ── 内部工具 ──

    @staticmethod
    def _cast(value: str, target_type: type) -> Any:
        """将环境变量字符串转为目标类型。"""
        if target_type is bool:
            return value.lower() in ("true", "1", "yes")
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return value


def load_config() -> Config:
    """初始化并返回全局配置（文件 → 环境变量，后者覆盖前者）。"""
    cfg = Config()
    cfg.load_from_file()
    cfg.load_from_env()
    return cfg
