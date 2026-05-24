"""
进化策略与评估 — 阶段44-49

设计意图: 提供可配置的进化策略、质量评估、冲突检测、
知识融合、趋势预测、效果评估等高级能力。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from eternal_self_agent.kg.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段44: 进化策略配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EvolveStrategy:
    """进化策略配置 — 所有进化参数的唯一来源。"""

    def __init__(
        self,
        derive_threshold: float = 0.2,
        trim_threshold: float = 0.1,
        decay_factor: float = 0.99,
        reinforce_delta: float = 0.1,
        weaken_delta: float = 0.1,
        max_derive_per_node: int = 3,
        evolve_interval: int = 50,
    ) -> None:
        self.derive_threshold = derive_threshold
        self.trim_threshold = trim_threshold
        self.decay_factor = decay_factor
        self.reinforce_delta = reinforce_delta
        self.weaken_delta = weaken_delta
        self.max_derive_per_node = max_derive_per_node
        self.evolve_interval = evolve_interval

    def to_dict(self) -> dict[str, Any]:
        return {
            "derive_threshold": self.derive_threshold,
            "trim_threshold": self.trim_threshold,
            "decay_factor": self.decay_factor,
            "reinforce_delta": self.reinforce_delta,
            "weaken_delta": self.weaken_delta,
            "max_derive_per_node": self.max_derive_per_node,
            "evolve_interval": self.evolve_interval,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段45: 知识质量评估
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class QualityAssessor:
    """知识图谱质量评估器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    def assess(self) -> dict[str, Any]:
        """
        全面评估知识图谱质量。

        Returns:
            质量报告
        """
        stats = self.kg.get_stats()
        metrics = self.kg.get_performance_metrics()
        validation = self.kg.validate()

        # 连通性评分
        connectivity = metrics.get("connectivity", {})
        total_nodes = stats["node_count"]
        connected = connectivity.get("connected_nodes", 0)
        connectivity_score = connected / total_nodes if total_nodes > 0 else 0.0

        # 覆盖率评分（活跃节点占比）
        coverage_score = (
            stats["active_node_count"] / total_nodes if total_nodes > 0 else 0.0
        )

        # 权重健康度
        weight_dist = stats.get("weight_distribution", {})
        total_edges = stats["edge_count"]
        high_ratio = weight_dist.get("high", 0) / total_edges if total_edges > 0 else 0

        # 综合评分
        overall = (
            connectivity_score * 30
            + coverage_score * 30
            + high_ratio * 20
            + (1.0 if not validation else 0.0) * 20
        )

        return {
            "overall_score": round(overall, 2),
            "connectivity_score": round(connectivity_score, 4),
            "coverage_score": round(coverage_score, 4),
            "weight_health": round(high_ratio, 4),
            "validation_errors": len(validation),
            "details": stats,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段46: 知识冲突检测
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ConflictDetector:
    """知识冲突检测器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    def detect(self) -> list[dict[str, Any]]:
        """
        检测知识冲突。

        Returns:
            冲突列表
        """
        conflicts: list[dict[str, Any]] = []

        # 1. 循环依赖检测
        cycles = self._detect_cycles()
        for cycle in cycles:
            conflicts.append(
                {
                    "type": "circular_dependency",
                    "severity": "medium",
                    "details": cycle,
                }
            )

        # 2. 矛盾关系检测（A->B权重高，B->A权重也高）
        for edge in self.kg.edges:
            for other in self.kg.edges:
                if (
                    edge.source == other.target
                    and edge.target == other.source
                    and edge.id != other.id
                ):
                    if edge.weight > 0.5 and other.weight > 0.5:
                        conflicts.append(
                            {
                                "type": "contradictory_relation",
                                "severity": "low",
                                "source": edge.source[:8],
                                "target": edge.target[:8],
                                "weight_a": edge.weight,
                                "weight_b": other.weight,
                            }
                        )

        return conflicts

    def _detect_cycles(self, max_depth: int = 5) -> list[list[str]]:
        """检测循环依赖（DFS）。"""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        path: list[str] = []
        path_set: set[str] = set()

        def dfs(node_id: str, depth: int) -> None:
            if depth > max_depth:
                return
            if node_id in path_set:
                idx = path.index(node_id)
                cycles.append(path[idx:] + [node_id])
                return
            if node_id in visited:
                return

            visited.add(node_id)
            path.append(node_id)
            path_set.add(node_id)

            for edge in self.kg.get_edges_by_source(node_id):
                dfs(edge.target, depth + 1)

            path.pop()
            path_set.discard(node_id)

        for node_id in self.kg.nodes:
            dfs(node_id, 0)

        return cycles[:10]  # 最多返回10个


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段47: 知识融合算法
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class KnowledgeFuser:
    """知识融合器 — 合并相似知识。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    def merge_similar_nodes(
        self, name_a: str, name_b: str, keep_name: str | None = None
    ) -> bool:
        """
        合并两个同名或相似节点。

        Args:
            name_a: 节点A名称
            name_b: 节点B名称
            keep_name: 保留的名称，默认为name_a

        Returns:
            是否成功
        """
        node_a = self.kg.get_node_by_name(name_a)
        node_b = self.kg.get_node_by_name(name_b)
        if not node_a or not node_b:
            return False

        keep = keep_name or name_a
        remove_id = node_b.id

        # 将B的所有出边重定向到A
        edges_to_redirect = list(self.kg.get_edges_by_source(remove_id))
        for edge in edges_to_redirect:
            self.kg.add_edge(keep, edge.target, edge.relation, edge.weight)

        # 将B的所有入边重定向到A
        edges_to_redirect = list(self.kg.get_edges_by_target(remove_id))
        for edge in edges_to_redirect:
            self.kg.add_edge(edge.source, keep, edge.relation, edge.weight)

        # 删除B
        self.kg.remove_node(remove_id)
        logger.info("知识融合: %s + %s -> %s", name_a, name_b, keep)
        return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段48: 知识预测模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TrendPredictor:
    """知识趋势预测器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg
        self._history: list[dict[str, Any]] = []

    def record_snapshot(self) -> None:
        """记录当前快照。"""
        self._history.append(self.kg.get_stats())
        # 最多保留100个快照
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def predict_growth(self, steps: int = 5) -> dict[str, Any]:
        """
        预测知识图谱增长趋势。

        Args:
            steps: 预测步数

        Returns:
            预测结果
        """
        if len(self._history) < 2:
            return {"error": "数据不足，至少需要2个快照"}

        # 简单线性回归
        node_counts = [h["node_count"] for h in self._history]
        edge_counts = [h["edge_count"] for h in self._history]

        node_trend = (
            (node_counts[-1] - node_counts[0]) / len(node_counts) if node_counts else 0
        )
        edge_trend = (
            (edge_counts[-1] - edge_counts[0]) / len(edge_counts) if edge_counts else 0
        )

        predicted_nodes = node_counts[-1] + node_trend * steps
        predicted_edges = edge_counts[-1] + edge_trend * steps

        return {
            "current_nodes": node_counts[-1],
            "current_edges": edge_counts[-1],
            "node_trend_per_step": round(node_trend, 2),
            "edge_trend_per_step": round(edge_trend, 2),
            "predicted_nodes_in_%d_steps" % steps: round(predicted_nodes, 1),
            "predicted_edges_in_%d_steps" % steps: round(predicted_edges, 1),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 阶段49: 进化效果评估
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EvolveEvaluator:
    """进化效果评估器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg
        self._before_snapshot: dict[str, Any] | None = None
        self._evolution_log: list[dict[str, Any]] = []

    def mark_before(self) -> None:
        """标记进化前的快照。"""
        self._before_snapshot = self.kg.get_stats()

    def evaluate(self, evolution_result: dict[str, Any]) -> dict[str, Any]:
        """
        评估一次进化的效果。

        Args:
            evolution_result: 进化操作的结果

        Returns:
            评估报告
        """
        after = self.kg.get_stats()
        before = self._before_snapshot or after

        report = {
            "before": before,
            "after": after,
            "node_delta": after["node_count"] - before["node_count"],
            "edge_delta": after["edge_count"] - before["edge_count"],
            "weight_delta": round(after["avg_weight"] - before["avg_weight"], 4),
            "tasks_derived": evolution_result.get("new_tasks_derived", 0),
            "edges_trimmed": evolution_result.get("trim", {}).get("removed_edges", 0),
            "timestamp": time.time(),
        }

        self._evolution_log.append(report)
        return report

    def get_history(self) -> list[dict[str, Any]]:
        """获取评估历史。"""
        return list(self._evolution_log)

    def get_summary(self) -> dict[str, Any]:
        """获取进化效果摘要。"""
        if not self._evolution_log:
            return {"total_evolutions": 0}

        total = len(self._evolution_log)
        avg_tasks = sum(e["tasks_derived"] for e in self._evolution_log) / total
        avg_trimmed = sum(e["edges_trimmed"] for e in self._evolution_log) / total

        return {
            "total_evolutions": total,
            "avg_tasks_per_evolution": round(avg_tasks, 2),
            "avg_edges_trimmed": round(avg_trimmed, 2),
        }
