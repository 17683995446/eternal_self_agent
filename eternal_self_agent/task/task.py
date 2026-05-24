"""
任务数据结构 — 自驱公理核心载体

设计意图: 任务是系统唯一驱动源，代表一次待执行的工作单元。
支持完整生命周期管理、优先级调度、超时控制。

公理溯源: 自驱公理 — 无外部输入时自我产生任务
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eternal_self_agent.utils import generate_id, md5_hash, now_timestamp


class TaskStatus(str, Enum):
    """任务生命周期状态。"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 执行失败
    TIMEOUT = "timeout"  # 执行超时
    CANCELLED = "cancelled"  # 已取消


class TaskPriority(int, Enum):
    """任务优先级（数值越大优先级越高）。"""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class TaskType(str, Enum):
    """任务类型。"""

    INITIAL = "initial"  # 系统初始认知
    DERIVED = "derived"  # 知识推演生成
    SELF_EVOLVE = "self_evolve"  # 空闲自驱进化
    ITERATION = "iteration"  # 系统迭代任务
    EXTERNAL = "external"  # 外部注入任务
    REPAIR = "repair"  # 自愈修复任务


@dataclass
class Task:
    """
    任务单元 — 系统唯一驱动源。

    公理溯源:
      - 自驱公理: 知识关联自动生成任务
      - 存续公理: 任务执行异常不能击穿系统

    属性:
        content: 任务内容描述
        task_type: 任务类型
        priority: 优先级
        status: 当前状态
        id: 唯一标识
        created_at: 创建时间
        started_at: 开始执行时间
        completed_at: 完成时间
        result: 执行结果
        error: 错误信息
        retry_count: 已重试次数
        max_retries: 最大重试次数
        timeout: 超时时间(秒)，0表示不超时
        deadline: 截止时间戳
        tags: 任务标签列表
        metadata: 元数据字典
        _content_hash: 内容哈希（用于去重）
    """

    content: str
    task_type: TaskType = TaskType.DERIVED
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    id: str = ""
    created_at: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 0.0
    deadline: float = 0.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    _content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id()
        if not self.created_at:
            self.created_at = now_timestamp()
        if not self._content_hash:
            self._update_content_hash()

    def _update_content_hash(self) -> None:
        """更新内容哈希（用于去重）。"""
        content_str = f"{self.task_type.value}:{self.content}"
        self._content_hash = md5_hash(content_str)

    # ── 状态转换 ──

    def start(self) -> None:
        """标记任务开始执行。"""
        self.status = TaskStatus.RUNNING
        self.started_at = now_timestamp()
        self.error = None

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """标记任务完成。"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = now_timestamp()
        if result:
            self.result.update(result)

    def fail(self, error: str) -> None:
        """标记任务失败。"""
        self.status = TaskStatus.FAILED
        self.completed_at = now_timestamp()
        self.error = error

    def mark_timeout(self) -> None:
        """标记任务超时。"""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = now_timestamp()

    def cancel(self) -> None:
        """取消任务。"""
        if self.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            self.status = TaskStatus.CANCELLED
            self.completed_at = now_timestamp()

    def can_retry(self) -> bool:
        """检查是否可以重试。"""
        return self.retry_count < self.max_retries and self.status in (
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
        )

    def retry(self) -> bool:
        """
        重置任务状态以便重试。

        Returns:
            是否成功重置
        """
        if not self.can_retry():
            return False

        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error = None
        return True

    # ── 状态查询 ──

    def is_pending(self) -> bool:
        return self.status == TaskStatus.PENDING

    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING

    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        return self.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT)

    def is_terminal(self) -> bool:
        """检查是否处于终止状态。"""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        )

    def is_expired(self) -> bool:
        """检查是否已过期（超过deadline）。"""
        if self.deadline <= 0:
            return False
        return now_timestamp() > self.deadline

    def is_timed_out(self) -> bool:
        """检查是否执行超时。"""
        if self.timeout <= 0 or not self.is_running() or not self.started_at:
            return False
        return (now_timestamp() - self.started_at) > self.timeout

    # ── 执行时间统计 ──

    def get_wait_time(self) -> float:
        """获取等待时间（从创建到开始）。"""
        if not self.started_at:
            return now_timestamp() - self.created_at
        return self.started_at - self.created_at

    def get_execution_time(self) -> float | None:
        """获取执行时间（从开始到完成）。"""
        if not self.started_at:
            return None
        end_time = self.completed_at or now_timestamp()
        return end_time - self.started_at

    def get_total_time(self) -> float:
        """获取总耗时（从创建到现在/完成）。"""
        end_time = self.completed_at or now_timestamp()
        return end_time - self.created_at

    # ── 标签管理 ──

    def add_tag(self, tag: str) -> None:
        """添加标签。"""
        if tag and tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """移除标签。"""
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """检查是否有指定标签。"""
        return tag in self.tags

    # ── 元数据管理 ──

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据。"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据。"""
        return self.metadata.get(key, default)

    # ── 内容哈希（去重用） ──

    def get_content_hash(self) -> str:
        """获取内容哈希。"""
        return self._content_hash

    def is_duplicate_of(self, other: Task) -> bool:
        """检查是否与另一个任务重复。"""
        return self._content_hash == other._content_hash

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "id": self.id,
            "content": self.content,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "deadline": self.deadline,
            "tags": self.tags,
            "metadata": self.metadata,
            "_content_hash": self._content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """从字典反序列化。"""
        return cls(
            id=data.get("id", ""),
            content=data["content"],
            task_type=TaskType(data.get("task_type", "derived")),
            priority=TaskPriority(data.get("priority", 5)),
            status=TaskStatus(data.get("status", "pending")),
            created_at=data.get("created_at", 0.0),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            result=data.get("result", {}),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout=data.get("timeout", 0.0),
            deadline=data.get("deadline", 0.0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            _content_hash=data.get("_content_hash", ""),
        )

    def copy(self) -> Task:
        """创建任务副本（新ID）。"""
        data = self.to_dict()
        data["id"] = ""
        data["created_at"] = 0.0
        data["started_at"] = None
        data["completed_at"] = None
        data["status"] = TaskStatus.PENDING.value
        data["retry_count"] = 0
        data["result"] = {}
        data["error"] = None
        return Task.from_dict(data)

    # ── 比较 ──

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __lt__(self, other: Task) -> bool:
        """用于优先级比较（数值大的优先级高）。"""
        if not isinstance(other, Task):
            return NotImplemented
        # 先比较优先级，再比较创建时间（FIFO）
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at

    def __repr__(self) -> str:
        return (
            f"Task({self.id[:8]}..., type={self.task_type.value}, "
            f"priority={self.priority.value}, status={self.status.value})"
        )

    # ── 工厂方法 ──

    @classmethod
    def create_initial(cls, content: str = "系统初始认知迭代") -> Task:
        """创建初始任务。"""
        return cls(
            content=content,
            task_type=TaskType.INITIAL,
            priority=TaskPriority.HIGH,
        )

    @classmethod
    def create_derived(cls, content: str, source: str = "") -> Task:
        """创建知识推演任务。"""
        task = cls(
            content=content,
            task_type=TaskType.DERIVED,
            priority=TaskPriority.NORMAL,
        )
        if source:
            task.set_metadata("source", source)
        return task

    @classmethod
    def create_self_evolve(cls, content: str) -> Task:
        """创建自驱进化任务。"""
        return cls(
            content=content,
            task_type=TaskType.SELF_EVOLVE,
            priority=TaskPriority.LOW,
        )
