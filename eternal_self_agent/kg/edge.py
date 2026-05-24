"""
知识图谱边 — 记忆公理核心数据结构

设计意图: 边代表实体之间的关联逻辑，附带权重值。
权重 = 智能经验积累的唯一量化标准。
权重越高，关联越可靠，越容易衍生新任务。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eternal_self_agent.utils import generate_id, now_timestamp, validate_weight


class EdgeType(str, Enum):
    """边类型枚举。"""

    DERIVED = "derived"  # 知识推演
    CAUSAL = "causal"  # 因果关系
    TEMPORAL = "temporal"  # 时序关系
    SEMANTIC = "semantic"  # 语义关联
    HIERARCHICAL = "hierarchical"  # 层级关系


@dataclass
class Edge:
    """
    知识图谱边 — 代表实体之间的关联逻辑，附带权重值。

    公理溯源:
      - 记忆公理: 智能 = 结构化、可关联的历史经验
      - 自驱公理: 权重越高，越容易衍生新任务

    属性:
        id: 唯一标识符
        source: 源节点ID
        target: 目标节点ID
        relation: 关系名称
        weight: 权重值（0.0~1.0），智能经验积累的唯一量化标准
        edge_type: 边类型
        created_at: 创建时间戳
        updated_at: 最后更新时间戳
        evidence: 支持该关系的证据列表
        metadata: 元数据字典
    """

    source: str
    target: str
    relation: str
    id: str = ""
    weight: float = 0.5
    edge_type: EdgeType = EdgeType.DERIVED
    created_at: float = 0.0
    updated_at: float = 0.0
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id()
        self.weight = validate_weight(self.weight)
        if not self.created_at:
            self.created_at = now_timestamp()
        if not self.updated_at:
            self.updated_at = self.created_at

    # ── 权重管理 ──

    def increase_weight(self, delta: float = 0.1) -> float:
        """增加权重（成功执行后调用）。"""
        self.weight = validate_weight(self.weight + delta)
        self.updated_at = now_timestamp()
        return self.weight

    def decrease_weight(self, delta: float = 0.1) -> float:
        """减少权重（失败执行后调用）。"""
        self.weight = validate_weight(self.weight - delta)
        self.updated_at = now_timestamp()
        return self.weight

    def set_weight(self, value: float) -> None:
        """直接设置权重。"""
        self.weight = validate_weight(value)
        self.updated_at = now_timestamp()

    def is_high_value(self, threshold: float = 0.2) -> bool:
        """检查是否为高价值关联。"""
        return self.weight >= threshold

    def is_low_value(self, threshold: float = 0.1) -> bool:
        """检查是否为低价值关联（可被精简）。"""
        return self.weight < threshold

    # ── 证据管理 ──

    def add_evidence(self, evidence: str) -> None:
        """添加支持证据。"""
        if evidence and evidence not in self.evidence:
            self.evidence.append(evidence)
            self.updated_at = now_timestamp()

    def remove_evidence(self, evidence: str) -> bool:
        """移除证据，返回是否成功。"""
        if evidence in self.evidence:
            self.evidence.remove(evidence)
            self.updated_at = now_timestamp()
            return True
        return False

    def evidence_count(self) -> int:
        """获取证据数量。"""
        return len(self.evidence)

    # ── 元数据管理 ──

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据。"""
        self.metadata[key] = value
        self.updated_at = now_timestamp()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据。"""
        return self.metadata.get(key, default)

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "edge_type": self.edge_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        """从字典反序列化。"""
        return cls(
            id=data.get("id", ""),
            source=data["source"],
            target=data["target"],
            relation=data["relation"],
            weight=data.get("weight", 0.5),
            edge_type=EdgeType(data.get("edge_type", "derived")),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            evidence=data.get("evidence", []),
            metadata=data.get("metadata", {}),
        )

    def copy(self) -> Edge:
        """创建边副本。"""
        return Edge.from_dict(self.to_dict())

    # ── 比较 ──

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"Edge({self.source[:8]}... -> {self.target[:8]}..., "
            f"relation={self.relation!r}, weight={self.weight:.2f})"
        )

    # ── 工厂方法 ──

    @classmethod
    def create_link(
        cls, source: str, target: str, relation: str, weight: float = 0.5
    ) -> Edge:
        """创建简单关联边。"""
        return cls(source=source, target=target, relation=relation, weight=weight)

    @classmethod
    def create_derived(
        cls, source: str, target: str, relation: str, weight: float = 0.8
    ) -> Edge:
        """创建知识推演边（默认高权重）。"""
        return cls(
            source=source,
            target=target,
            relation=relation,
            weight=weight,
            edge_type=EdgeType.DERIVED,
        )
