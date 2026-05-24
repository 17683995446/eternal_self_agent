"""
类型定义模块 — 全系统类型注解

设计意图: 为知识图谱、任务队列、智能体等核心结构提供统一类型定义。
使用Python dataclass实现轻量化数据结构，零外部依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 知识图谱类型（记忆公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class NodeStatus(str, Enum):
    """节点有效状态。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


@dataclass
class Node:
    """
    知识图谱节点 — 代表一次任务、一次认知、一个实体经验。

    属性:
        id: 唯一标识符
        name: 节点名称/内容
        created_at: 创建时间戳
        status: 有效状态
        attributes: 扩展属性字典
    """

    name: str
    id: str = ""
    created_at: float = 0.0
    status: NodeStatus = NodeStatus.ACTIVE
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            from eternal_self_agent.utils import generate_id

            self.id = generate_id()
        if not self.created_at:
            from eternal_self_agent.utils import now_timestamp

            self.created_at = now_timestamp()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "status": self.status.value,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data.get("created_at", 0.0),
            status=NodeStatus(data.get("status", "active")),
            attributes=data.get("attributes", {}),
        )


@dataclass
class Edge:
    """
    知识图谱边 — 代表实体之间的关联逻辑，附带权重值。

    属性:
        source: 源节点ID
        target: 目标节点ID
        relation: 关系名称
        weight: 权重值（0.0~1.0），智能经验积累的唯一量化标准
        created_at: 创建时间戳
    """

    source: str
    target: str
    relation: str
    weight: float = 0.5
    created_at: float = 0.0

    def __post_init__(self) -> None:
        from eternal_self_agent.utils import validate_weight

        self.weight = validate_weight(self.weight)
        if not self.created_at:
            from eternal_self_agent.utils import now_timestamp

            self.created_at = now_timestamp()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        return cls(
            source=data["source"],
            target=data["target"],
            relation=data["relation"],
            weight=data.get("weight", 0.5),
            created_at=data.get("created_at", 0.0),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务队列类型（自驱公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TaskStatus(str, Enum):
    """任务生命周期状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


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


@dataclass
class Task:
    """
    任务单元 — 系统唯一驱动源。

    属性:
        content: 任务内容描述
        task_type: 任务类型
        priority: 优先级
        status: 当前状态
        id: 唯一标识
        created_at: 创建时间
        result: 执行结果
        retry_count: 已重试次数
    """

    content: str
    task_type: TaskType = TaskType.DERIVED
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    id: str = ""
    created_at: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            from eternal_self_agent.utils import generate_id

            self.id = generate_id()
        if not self.created_at:
            from eternal_self_agent.utils import now_timestamp

            self.created_at = now_timestamp()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "result": self.result,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            content=data["content"],
            task_type=TaskType(data.get("task_type", "derived")),
            priority=TaskPriority(data.get("priority", 5)),
            status=TaskStatus(data.get("status", "pending")),
            created_at=data.get("created_at", 0.0),
            result=data.get("result", {}),
            retry_count=data.get("retry_count", 0),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 系统状态类型（存续公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SystemState(str, Enum):
    """系统运行状态。"""

    INITIALIZING = "initializing"
    RUNNING = "running"
    IDLE = "idle"
    EVOLVING = "evolving"
    REPAIRING = "repairing"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class GraphState:
    """知识图谱全局状态快照。"""

    node_count: int = 0
    edge_count: int = 0
    active_node_count: int = 0
    avg_weight: float = 0.0
    last_saved: float = 0.0
