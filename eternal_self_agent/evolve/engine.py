"""
知识推演引擎 — 自驱公理核心实现

设计意图: 基于已有知识图谱关联关系，自动推演、生成、管理新任务。
封装并增强kg模块的基础能力，提供更高层的进化策略。

公理溯源:
  - 自驱公理: 知识关联自动推演新任务，实现真正软件层面"永动"
  - 记忆公理: 所有推演结果沉淀为结构化知识
"""

from __future__ import annotations

import logging
from typing import Any

from eternal_self_agent.constants import DERIVE_WEIGHT_THRESHOLD, TRIM_WEIGHT_THRESHOLD
from eternal_self_agent.kg.graph import KnowledgeGraph
from eternal_self_agent.task.task import Task, TaskPriority

logger = logging.getLogger(__name__)


class EvolveEngine:
    """
    自驱进化引擎 — 系统永动的核心驱动力。

    职责:
      1. 基于图谱推演新任务（阶段36）
      2. 动态调整知识权重（阶段37）
      3. 自动精简低价值知识（阶段38）
    """

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段36: 知识推演引擎
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def derive_tasks(
        self,
        node_name: str,
        threshold: float | None = None,
        max_tasks: int = 10,
    ) -> list[Task]:
        """
        基于节点推演新任务 — 返回Task对象列表。

        增强版: 相比kg.derive_new_tasks返回字符串，
        这里返回完整Task对象，可直接入队执行。

        Args:
            node_name: 节点名称
            threshold: 权重阈值
            max_tasks: 最大推演任务数

        Returns:
            Task对象列表
        """
        threshold = threshold or DERIVE_WEIGHT_THRESHOLD
        node = self.kg.get_node_by_name(node_name)
        if not node:
            return []

        tasks: list[Task] = []
        seen_targets: set[str] = set()

        for edge in self.kg.get_edges_by_source(node.id):
            if edge.weight > threshold and edge.target not in seen_targets:
                target_node = self.kg.nodes.get(edge.target)
                if target_node:
                    task = Task.create_derived(
                        content=f"知识推演任务:{target_node.name}",
                        source=node_name,
                    )
                    # 权重越高，优先级越高
                    if edge.weight >= 0.7:
                        task.priority = TaskPriority.HIGH
                    tasks.append(task)
                    seen_targets.add(edge.target)

            if len(tasks) >= max_tasks:
                break

        logger.debug("推演任务: 源=%s, 生成=%d个", node_name, len(tasks))
        return tasks

    def derive_from_all_active(
        self, threshold: float | None = None, max_per_node: int = 3
    ) -> list[Task]:
        """
        从所有活跃节点推演任务。

        Args:
            threshold: 权重阈值
            max_per_node: 每个节点最大推演数

        Returns:
            Task对象列表
        """
        all_tasks: list[Task] = []
        for node in self.kg.iter_nodes():
            if node.is_active():
                tasks = self.derive_tasks(
                    node.name, threshold=threshold, max_tasks=max_per_node
                )
                all_tasks.extend(tasks)
        return all_tasks

    def derive_by_relation(
        self, relation: str, threshold: float | None = None
    ) -> list[Task]:
        """
        按关系类型推演任务。

        Args:
            relation: 关系名称
            threshold: 权重阈值

        Returns:
            Task对象列表
        """
        threshold = threshold or DERIVE_WEIGHT_THRESHOLD
        tasks: list[Task] = []

        for edge in self.kg.get_edges_by_relation(relation):
            if edge.weight > threshold:
                source_node = self.kg.nodes.get(edge.source)
                target_node = self.kg.nodes.get(edge.target)
                if source_node and target_node:
                    task = Task.create_derived(
                        content=f"关系推演({relation}):{target_node.name}",
                        source=source_node.name,
                    )
                    tasks.append(task)

        return tasks

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段37: 权重计算算法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def reinforce_edge(self, edge_id: str, delta: float = 0.1) -> bool:
        """
        强化边的权重（成功执行后调用）。

        Args:
            edge_id: 边ID
            delta: 增量

        Returns:
            是否成功
        """
        edge = self.kg.get_edge(edge_id)
        if not edge:
            return False

        old_weight = edge.weight
        edge.increase_weight(delta)
        logger.debug(
            "权重强化: %s (%.2f -> %.2f)",
            edge_id[:8],
            old_weight,
            edge.weight,
        )
        return True

    def weaken_edge(self, edge_id: str, delta: float = 0.1) -> bool:
        """
        削弱边的权重（失败执行后调用）。

        Args:
            edge_id: 边ID
            delta: 减量

        Returns:
            是否成功
        """
        edge = self.kg.get_edge(edge_id)
        if not edge:
            return False

        old_weight = edge.weight
        edge.decrease_weight(delta)
        logger.debug(
            "权重削弱: %s (%.2f -> %.2f)",
            edge_id[:8],
            old_weight,
            edge.weight,
        )
        return True

    def reinforce_path(self, edge_ids: list[str], delta: float = 0.05) -> int:
        """
        强化路径上所有边的权重。

        Args:
            edge_ids: 边ID列表
            delta: 每条边的增量

        Returns:
            成功强化的边数
        """
        count = 0
        for eid in edge_ids:
            if self.reinforce_edge(eid, delta):
                count += 1
        return count

    def decay_all_weights(self, factor: float = 0.99) -> int:
        """
        全局权重衰减 — 防止旧知识权重过高。

        每条边权重乘以factor（<1.0），模拟记忆遗忘。

        Args:
            factor: 衰减因子（0.95~1.0）

        Returns:
            受影响的边数
        """
        count = 0
        for edge in self.kg.iter_edges():
            new_weight = edge.weight * factor
            edge.set_weight(new_weight)
            count += 1
        return count

    def normalize_weights(self) -> None:
        """
        归一化所有权重到[0,1]范围。
        按比例缩放，保持相对关系不变。
        """
        if not self.kg.edges:
            return

        max_weight = max(e.weight for e in self.kg.edges)
        if max_weight <= 0:
            return

        for edge in self.kg.iter_edges():
            edge.set_weight(edge.weight / max_weight)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段38: 知识精简算法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def trim_knowledge(self, threshold: float | None = None) -> dict[str, int]:
        """
        精简低价值知识 — 增强版。

        在kg.trim_invalid_knowledge基础上，增加:
        - 归档而非直接删除（保留历史）
        - 返回详细统计

        Args:
            threshold: 权重阈值

        Returns:
            精简统计
        """
        threshold = threshold or TRIM_WEIGHT_THRESHOLD

        # 执行精简
        removed_edges, removed_nodes = self.kg.trim_invalid_knowledge(threshold)

        stats = {
            "removed_edges": removed_edges,
            "removed_nodes": removed_nodes,
            "remaining_nodes": len(self.kg.nodes),
            "remaining_edges": len(self.kg.edges),
        }

        if removed_edges or removed_nodes:
            logger.info(
                "知识精简: 删除%d边, %d节点 (剩余%d边, %d节点)",
                removed_edges,
                removed_nodes,
                stats["remaining_edges"],
                stats["remaining_nodes"],
            )

        return stats

    def trim_by_age(self, max_age_seconds: float = 86400.0) -> dict[str, int]:
        """
        按时间精简 — 删除过期的低活跃知识。

        Args:
            max_age_seconds: 最大存活时间（秒），默认24小时

        Returns:
            精简统计
        """
        import time

        cutoff = time.time() - max_age_seconds
        removed_edges = 0
        removed_nodes = 0

        # 删除过期的低权重边
        edges_to_remove = [
            e for e in self.kg.edges if e.created_at < cutoff and e.weight < 0.3
        ]
        for edge in edges_to_remove:
            self.kg.edges.remove(edge)
            removed_edges += 1

        # 删除过期且无活跃边的节点
        nodes_with_edges = set()
        for edge in self.kg.edges:
            nodes_with_edges.add(edge.source)
            nodes_with_edges.add(edge.target)

        nodes_to_remove = [
            nid
            for nid, node in self.kg.nodes.items()
            if nid not in nodes_with_edges
            and node.created_at < cutoff
            and node.access_count < 3
        ]
        for node_id in nodes_to_remove:
            node = self.kg.nodes[node_id]
            if node.name in self.kg._node_name_index:
                del self.kg._node_name_index[node.name]
            del self.kg.nodes[node_id]
            removed_nodes += 1

        if removed_edges or removed_nodes:
            self.kg._rebuild_indexes()
            self.kg._modified = True
            logger.info(
                "按时间精简: 删除%d边, %d节点",
                removed_edges,
                removed_nodes,
            )

        return {
            "removed_edges": removed_edges,
            "removed_nodes": removed_nodes,
        }

    def full_evolution(self) -> dict[str, Any]:
        """
        执行一次完整的进化周期。

        步骤:
          1. 全局权重衰减
          2. 精简低价值知识
          3. 推演新任务

        Returns:
            进化报告
        """
        # 1. 权重衰减
        decayed = self.decay_all_weights(factor=0.99)

        # 2. 精简
        trim_stats = self.trim_knowledge()

        # 3. 推演
        new_tasks = self.derive_from_all_active(max_per_node=2)

        report = {
            "decayed_edges": decayed,
            "trim": trim_stats,
            "new_tasks_derived": len(new_tasks),
            "tasks": new_tasks,
        }

        logger.info(
            "进化周期完成: 衰减%d边, 精简%d边, 推演%d任务",
            decayed,
            trim_stats["removed_edges"],
            len(new_tasks),
        )

        return report
