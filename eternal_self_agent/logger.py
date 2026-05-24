"""
结构化日志系统 — 存续公理推导

设计意图: 存续公理要求系统可观测性，所有行为必须有迹可循。
提供JSON格式日志、文件轮转、级别动态调整、性能指标日志。
零外部依赖，仅使用Python标准库。
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON格式日志输出 — 便于后续查询分析。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # 附加异常信息
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 附加自定义字段
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry, ensure_ascii=False)


class PerformanceLogAdapter(logging.LoggerAdapter):
    """性能指标日志适配器 — 自动附加耗时等性能字段。"""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra", {})
        if not hasattr(self, "extra"):
            self.extra = {}
        merged = {**self.extra, **extra}
        kwargs["extra"] = merged
        return msg, kwargs


class LoggerManager:
    """日志管理器 — 全局日志生命周期管理。"""

    _initialized: bool = False

    @classmethod
    def setup(
        cls,
        level: str = "INFO",
        log_file: str = "",
        json_format: bool = False,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """
        初始化日志系统。

        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
            log_file: 日志文件路径，为空则仅输出到stdout
            json_format: 是否使用JSON格式
            max_bytes: 单个日志文件最大字节数（轮转）
            backup_count: 保留的日志备份文件数
        """
        if cls._initialized:
            return

        root_logger = logging.getLogger("eternal_self_agent")
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # ── 控制台Handler ──
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_fmt = (
            JSONFormatter()
            if json_format
            else logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        console_handler.setFormatter(console_fmt)
        root_logger.addHandler(console_handler)

        # ── 文件Handler（带轮转） ──
        if log_file:
            os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_fmt = (
                JSONFormatter()
                if json_format
                else logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s "
                    "(%(module)s:%(lineno)d): %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            file_handler.setFormatter(file_fmt)
            root_logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def set_level(cls, level: str) -> None:
        """动态调整日志级别。"""
        root_logger = logging.getLogger("eternal_self_agent")
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        # 同步调整所有handler
        for handler in root_logger.handlers:
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取命名logger。"""
        if not cls._initialized:
            cls.setup()
        return logging.getLogger(f"eternal_self_agent.{name}")


def get_logger(name: str) -> logging.Logger:
    """快捷获取logger的公共接口。"""
    return LoggerManager.get_logger(name)


def perf_log(
    logger: logging.Logger, operation: str, elapsed: float, **extra: Any
) -> None:
    """记录性能指标日志。"""
    adapter = PerformanceLogAdapter(
        logger,
        {"operation": operation, "elapsed_ms": round(elapsed * 1000, 2), **extra},
    )
    adapter.info(f"性能指标 | {operation} | {elapsed*1000:.2f}ms")


class Timer:
    """简易计时上下文管理器 — 用于性能日志。"""

    def __init__(self, logger: logging.Logger, operation: str) -> None:
        self._logger = logger
        self._operation = operation
        self._start: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed = time.monotonic() - self._start
        perf_log(self._logger, self._operation, elapsed)
