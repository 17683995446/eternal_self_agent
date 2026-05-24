"""
知识图谱节点 — 记忆公理核心数据结构

设计意图: 节点代表一次任务、一次认知、一个实体经验。
支持完整生命周期管理、序列化、状态转换。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eternal_self_agent.utils import generate_id, now_timestamp


class NodeStatus(str, Enum):
    """节点有效状态。"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


@dataclass
class Node:
    """
    知识图谱节点 — 代表一次任务、一次认知、一个实体经验。

    公理溯源: 记忆公理 — 智能 = 结构化、可沉淀的历史经验

    属性:
        id: 唯一标识符（32位hex）
        name: 节点名称/内容
        created_at: 创建时间戳
        updated_at: 最后更新时间戳
        status: 有效状态
        attributes: 扩展属性字典
        access_count: 访问次数（用于热度计算）
    """

    name: str
    id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    status: NodeStatus = NodeStatus.ACTIVE
    attributes: dict[str, Any] = field(default_factory=dict)
    access_count: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id()
        if not self.created_at:
            self.created_at = now_timestamp()
        if not self.updated_at:
            self.updated_at = self.created_at

    # ── 状态管理 ──

    def activate(self) -> None:
        """激活节点。"""
        self.status = NodeStatus.ACTIVE
        self.updated_at = now_timestamp()

    def deactivate(self) -> None:
        """停用节点。"""
        self.status = NodeStatus.INACTIVE
        self.updated_at = now_timestamp()

    def archive(self) -> None:
        """归档节点。"""
        self.status = NodeStatus.ARCHIVED
        self.updated_at = now_timestamp()

    def is_active(self) -> bool:
        """检查节点是否活跃。"""
        return self.status == NodeStatus.ACTIVE

    # ── 访问统计 ──

    def touch(self) -> None:
        """记录一次访问。"""
        self.access_count += 1
        self.updated_at = now_timestamp()

    # ── 属性管理 ──

    def set_attribute(self, key: str, value: Any) -> None:
        """设置扩展属性。"""
        self.attributes[key] = value
        self.updated_at = now_timestamp()

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """获取扩展属性。"""
        return self.attributes.get(key, default)

    def remove_attribute(self, key: str) -> bool:
        """删除扩展属性，返回是否成功。"""
        if key in self.attributes:
            del self.attributes[key]
            self.updated_at = now_timestamp()
            return True
        return False

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "attributes": self.attributes,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        """从字典反序列化。"""
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            status=NodeStatus(data.get("status", "active")),
            attributes=data.get("attributes", {}),
            access_count=data.get("access_count", 0),
        )

    def copy(self) -> Node:
        """创建节点副本。"""
        return Node.from_dict(self.to_dict())

    # ── 比较 ──

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Node(id={self.id[:8]}..., name={self.name!r}, status={self.status.value})"
        )
