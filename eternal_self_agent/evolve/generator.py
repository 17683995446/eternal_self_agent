"""
自驱任务生成器 — 空闲时自动生成任务

设计意图: 无外部输入时，系统必须自我产生任务。
基于图谱状态智能决定生成什么类型的任务。

公理溯源: 自驱公理 — 无外部输入时自我梳理知识、自我精简迭代
"""

from __future__ import annotations

import logging
import random

from eternal_self_agent.kg.graph import KnowledgeGraph
from eternal_self_agent.task.task import Task, TaskPriority, TaskType

logger = logging.getLogger(__name__)


class SelfDriveGenerator:
    """自驱任务生成器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg
        self._generation_count = 0

    def generate_idle_tasks(self, max_tasks: int = 5) -> list[Task]:
        """
        空闲时生成自驱任务。

        策略:
          1. 如果有孤立节点 → 生成关联探索任务
          2. 如果有低权重边 → 生成权重验证任务
          3. 如果图谱较大 → 生成知识精简任务
          4. 默认 → 生成随机探索任务

        Args:
            max_tasks: 最大生成数量

        Returns:
            Task列表
        """
        tasks: list[Task] = []
        stats = self.kg.get_stats()

        # 策略1: 孤立节点探索
        isolated = self._find_isolated_nodes()
        for node in isolated[:2]:
            tasks.append(
                Task(
                    content=f"探索孤立节点关联: {node.name}",
                    task_type=TaskType.SELF_EVOLVE,
                    priority=TaskPriority.NORMAL,
                )
            )

        # 策略2: 低权重边验证
        low_edges = [e for e in self.kg.edges if e.weight < 0.3]
        if low_edges and len(tasks) < max_tasks:
            edge = random.choice(low_edges)
            src = self.kg.nodes.get(edge.source)
            tgt = self.kg.nodes.get(edge.target)
            if src and tgt:
                tasks.append(
                    Task(
                        content=f"验证关联强度: {src.name} -> {tgt.name}",
                        task_type=TaskType.SELF_EVOLVE,
                        priority=TaskPriority.LOW,
                    )
                )

        # 策略3: 知识精简
        if stats["edge_count"] > 50 and len(tasks) < max_tasks:
            tasks.append(
                Task(
                    content="执行知识精简与优化",
                    task_type=TaskType.SELF_EVOLVE,
                    priority=TaskPriority.LOW,
                )
            )

        # 策略4: 随机探索
        while len(tasks) < max_tasks:
            node = (
                random.choice(list(self.kg.nodes.values())) if self.kg.nodes else None
            )
            if node:
                tasks.append(
                    Task(
                        content=f"深度探索知识: {node.name}",
                        task_type=TaskType.SELF_EVOLVE,
                        priority=TaskPriority.LOW,
                    )
                )
            else:
                break

        self._generation_count += len(tasks)
        if tasks:
            logger.debug("自驱生成%d个任务", len(tasks))

        return tasks[:max_tasks]

    def generate_iteration_task(self, run_counter: int) -> Task:
        """生成系统迭代任务。"""
        return Task(
            content=f"系统迭代任务_{run_counter}",
            task_type=TaskType.ITERATION,
            priority=TaskPriority.NORMAL,
        )

    def _find_isolated_nodes(self) -> list:
        """找出孤立节点。"""
        nodes_with_edges = set()
        for edge in self.kg.edges:
            nodes_with_edges.add(edge.source)
            nodes_with_edges.add(edge.target)

        return [
            node for nid, node in self.kg.nodes.items() if nid not in nodes_with_edges
        ]

    @property
    def total_generated(self) -> int:
        return self._generation_count
