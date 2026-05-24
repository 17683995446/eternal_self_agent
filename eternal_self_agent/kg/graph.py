"""
轻量化知识图谱 — 记忆公理核心载体

设计意图: 知识图谱作为唯一长期记忆载体，所有行为必须落盘结构化数据。
零外部依赖，全本地文件持久化，支持断电恢复。

公理溯源:
  - 记忆公理: 智能 = 结构化、可沉淀、可关联、可检索的历史经验
  - 自驱公理: 知识关联自动推演新任务
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterator

from eternal_self_agent.constants import (
    DERIVE_WEIGHT_THRESHOLD,
    KG_SAVE_PATH,
    TRIM_WEIGHT_THRESHOLD,
)
from eternal_self_agent.exceptions import (
    GraphPersistenceError,
    NodeAlreadyExistsError,
    NodeNotFoundError,
)
from eternal_self_agent.kg.edge import Edge, EdgeType
from eternal_self_agent.kg.node import Node, NodeStatus
from eternal_self_agent.utils import atomic_write_json, now_timestamp, safe_read_json

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    轻量化第一性原理知识图谱。

    核心设计:
      - nodes: 节点字典 {node_id: Node}
      - edges: 边列表 [Edge]
      - 索引: 加速查询的辅助结构

    公理溯源:
      - 记忆公理: 所有行为必须落盘结构化数据
      - 自驱公理: 知识推演自动生成新任务
    """

    def __init__(self, save_path: str | None = None) -> None:
        """初始化知识图谱。"""
        self.save_path = save_path or KG_SAVE_PATH
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        # ── 索引结构（阶段19优化） ──
        self._node_name_index: dict[str, str] = {}  # name -> node_id
        self._outgoing_index: dict[str, list[Edge]] = {}  # source_id -> edges
        self._incoming_index: dict[str, list[Edge]] = {}  # target_id -> edges
        self._relation_index: dict[str, list[Edge]] = {}  # relation -> edges
        # ── 元数据 ──
        self._last_saved: float = 0.0
        self._modified: bool = False
        # 加载已有数据
        self.load()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段14: 持久化加载
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def load(self) -> bool:
        """
        从本地文件加载图谱数据。

        Returns:
            是否成功加载（文件不存在返回False）
        """
        if not os.path.isfile(self.save_path):
            logger.debug("图谱文件不存在，将创建新图谱: %s", self.save_path)
            return False

        try:
            data = safe_read_json(self.save_path)
            if not data:
                logger.warning("图谱文件为空或损坏: %s", self.save_path)
                return False

            # 加载节点
            self.nodes.clear()
            for node_data in data.get("nodes", []):
                node = Node.from_dict(node_data)
                self.nodes[node.id] = node

            # 加载边
            self.edges.clear()
            for edge_data in data.get("edges", []):
                edge = Edge.from_dict(edge_data)
                self.edges.append(edge)

            # 重建索引
            self._rebuild_indexes()

            self._last_saved = data.get("last_saved", 0.0)
            self._modified = False

            logger.info(
                "图谱加载成功: %d 节点, %d 边",
                len(self.nodes),
                len(self.edges),
            )
            return True

        except Exception as e:
            logger.error("图谱加载失败: %s", e)
            raise GraphPersistenceError(f"图谱加载失败: {e}") from e

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段15: 持久化保存
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def save(self) -> bool:
        """
        将图谱数据持久化到本地文件。

        Returns:
            是否成功保存
        """
        try:
            data = {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "edges": [edge.to_dict() for edge in self.edges],
                "last_saved": now_timestamp(),
                "version": "0.1.0",
            }
            atomic_write_json(self.save_path, data)
            self._last_saved = data["last_saved"]
            self._modified = False
            logger.info("图谱保存成功: %s", self.save_path)
            return True

        except Exception as e:
            logger.error("图谱保存失败: %s", e)
            raise GraphPersistenceError(f"图谱保存失败: {e}") from e

    def _auto_save(self) -> None:
        """自动保存（内部调用）。"""
        if self._modified:
            self.save()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段16: 节点增删改查
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add_node(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        status: NodeStatus = NodeStatus.ACTIVE,
    ) -> Node:
        """
        新增节点。

        Args:
            name: 节点名称
            attributes: 扩展属性
            status: 初始状态

        Returns:
            创建的节点

        Raises:
            NodeAlreadyExistsError: 同名节点已存在
        """
        # 检查同名节点
        if name in self._node_name_index:
            existing_id = self._node_name_index[name]
            logger.debug("节点已存在，返回现有节点: %s", name)
            return self.nodes[existing_id]

        node = Node(name=name, attributes=attributes or {}, status=status)
        self.nodes[node.id] = node
        self._node_name_index[name] = node.id
        self._modified = True
        logger.debug("新增节点: %s (id=%s)", name, node.id[:8])
        return node

    def get_node(self, node_id: str) -> Node | None:
        """根据ID获取节点。"""
        node = self.nodes.get(node_id)
        if node:
            node.touch()
        return node

    def get_node_by_name(self, name: str) -> Node | None:
        """根据名称获取节点。"""
        node_id = self._node_name_index.get(name)
        if node_id:
            return self.get_node(node_id)
        return None

    def update_node(
        self,
        node_id: str,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
        status: NodeStatus | None = None,
    ) -> Node:
        """
        更新节点信息。

        Raises:
            NodeNotFoundError: 节点不存在
        """
        node = self.nodes.get(node_id)
        if not node:
            raise NodeNotFoundError(f"节点不存在: {node_id}")

        # 更新名称（需要更新索引）
        if name and name != node.name:
            if name in self._node_name_index:
                raise NodeAlreadyExistsError(f"节点名称已存在: {name}")
            del self._node_name_index[node.name]
            node.name = name
            self._node_name_index[name] = node_id

        # 更新属性
        if attributes:
            node.attributes.update(attributes)

        # 更新状态
        if status:
            node.status = status

        node.updated_at = now_timestamp()
        self._modified = True
        return node

    def remove_node(self, node_id: str) -> bool:
        """
        删除节点及其关联边。

        Returns:
            是否成功删除
        """
        node = self.nodes.get(node_id)
        if not node:
            return False

        # 删除关联边
        related_edges = self._get_edges_by_node(node_id)
        for edge in related_edges:
            self.edges.remove(edge)

        # 删除节点
        del self.nodes[node_id]
        if node.name in self._node_name_index:
            del self._node_name_index[node.name]

        # 重建索引
        self._rebuild_indexes()
        self._modified = True
        logger.debug("删除节点: %s", node_id[:8])
        return True

    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在。"""
        return node_id in self.nodes

    def has_node_by_name(self, name: str) -> bool:
        """检查节点是否存在（按名称）。"""
        return name in self._node_name_index

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段17: 边增删改查
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 0.5,
        edge_type: EdgeType = EdgeType.DERIVED,
    ) -> Edge:
        """
        新增加权关系边。

        自动保证头尾实体存在（记忆公理要求）。

        Args:
            source: 源节点ID或名称
            target: 目标节点ID或名称
            relation: 关系名称
            weight: 权重值
            edge_type: 边类型

        Returns:
            创建的边
        """
        # 确保节点存在
        source_node = self.get_node_by_name(source) or self.get_node(source)
        if not source_node:
            source_node = self.add_node(source)

        target_node = self.get_node_by_name(target) or self.get_node(target)
        if not target_node:
            target_node = self.add_node(target)

        edge = Edge(
            source=source_node.id,
            target=target_node.id,
            relation=relation,
            weight=weight,
            edge_type=edge_type,
        )
        self.edges.append(edge)

        # 更新索引
        self._add_edge_to_indexes(edge)
        self._modified = True

        logger.debug(
            "新增边: %s -> %s (%s, w=%.2f)",
            source_node.name,
            target_node.name,
            relation,
            weight,
        )
        return edge

    def get_edge(self, edge_id: str) -> Edge | None:
        """根据ID获取边。"""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def get_edges_by_source(self, source_id: str) -> list[Edge]:
        """获取节点的所有出边。"""
        return list(self._outgoing_index.get(source_id, []))

    def get_edges_by_target(self, target_id: str) -> list[Edge]:
        """获取节点的所有入边。"""
        return list(self._incoming_index.get(target_id, []))

    def get_edges_by_relation(self, relation: str) -> list[Edge]:
        """获取指定关系的所有边。"""
        return list(self._relation_index.get(relation, []))

    def update_edge_weight(self, edge_id: str, weight: float) -> Edge | None:
        """更新边的权重。"""
        edge = self.get_edge(edge_id)
        if edge:
            edge.set_weight(weight)
            self._modified = True
        return edge

    def remove_edge(self, edge_id: str) -> bool:
        """删除边。"""
        edge = self.get_edge(edge_id)
        if not edge:
            return False

        self.edges.remove(edge)
        self._rebuild_indexes()
        self._modified = True
        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段18: 节点关系查询
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_neighbors(self, node_id: str) -> list[Node]:
        """获取节点的所有邻居节点。"""
        neighbors = []
        seen = set()

        # 出边邻居
        for edge in self._outgoing_index.get(node_id, []):
            if edge.target not in seen:
                neighbor = self.nodes.get(edge.target)
                if neighbor:
                    neighbors.append(neighbor)
                    seen.add(edge.target)

        # 入边邻居
        for edge in self._incoming_index.get(node_id, []):
            if edge.source not in seen:
                neighbor = self.nodes.get(edge.source)
                if neighbor:
                    neighbors.append(neighbor)
                    seen.add(edge.source)

        return neighbors

    def get_outgoing_neighbors(self, node_id: str) -> list[Node]:
        """获取节点的出边邻居（下游节点）。"""
        neighbors = []
        for edge in self._outgoing_index.get(node_id, []):
            neighbor = self.nodes.get(edge.target)
            if neighbor:
                neighbors.append(neighbor)
        return neighbors

    def get_incoming_neighbors(self, node_id: str) -> list[Node]:
        """获取节点的入边邻居（上游节点）。"""
        neighbors = []
        for edge in self._incoming_index.get(node_id, []):
            neighbor = self.nodes.get(edge.source)
            if neighbor:
                neighbors.append(neighbor)
        return neighbors

    def find_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[Edge] | None:
        """
        查找两个节点之间的路径（BFS）。

        Args:
            source_id: 起点ID
            target_id: 终点ID
            max_depth: 最大搜索深度

        Returns:
            边列表表示的路径，不存在则返回None
        """
        if source_id == target_id:
            return []

        visited = {source_id}
        queue: list[tuple[str, list[Edge]]] = [(source_id, [])]

        while queue:
            current_id, path = queue.pop(0)

            if len(path) >= max_depth:
                continue

            for edge in self._outgoing_index.get(current_id, []):
                next_id = edge.target

                if next_id == target_id:
                    return path + [edge]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [edge]))

        return None

    def get_node_degree(self, node_id: str) -> int:
        """获取节点的度（入边+出边）。"""
        out_degree = len(self._outgoing_index.get(node_id, []))
        in_degree = len(self._incoming_index.get(node_id, []))
        return out_degree + in_degree

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 自驱公理: 知识推演
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def derive_new_tasks(
        self, node_name: str, threshold: float | None = None
    ) -> list[str]:
        """
        基于已有知识推演新生任务 — 永动来源。

        公理溯源: 自驱公理 — 知识关联自动推演新任务

        Args:
            node_name: 节点名称
            threshold: 权重阈值，默认使用DERIVE_WEIGHT_THRESHOLD

        Returns:
            推演出的任务列表
        """
        threshold = threshold or DERIVE_WEIGHT_THRESHOLD
        node = self.get_node_by_name(node_name)
        if not node:
            return []

        tasks = []
        for edge in self._outgoing_index.get(node.id, []):
            if edge.weight > threshold:
                target_node = self.nodes.get(edge.target)
                if target_node:
                    tasks.append(f"知识推演任务:{target_node.name}")

        return list(set(tasks))  # 去重

    def trim_invalid_knowledge(self, threshold: float | None = None) -> tuple[int, int]:
        """
        自动淘汰低价值知识 — 防臃肿老化。

        公理溯源: 自驱公理 — 自动淘汰低价值知识

        Args:
            threshold: 权重阈值，默认使用TRIM_WEIGHT_THRESHOLD

        Returns:
            (删除的边数, 删除的孤立节点数)
        """
        threshold = threshold or TRIM_WEIGHT_THRESHOLD

        # 删除低权重边
        edges_to_remove = [e for e in self.edges if e.weight < threshold]
        for edge in edges_to_remove:
            self.edges.remove(edge)

        # 删除孤立节点
        nodes_with_edges = set()
        for edge in self.edges:
            nodes_with_edges.add(edge.source)
            nodes_with_edges.add(edge.target)

        nodes_to_remove = [nid for nid in self.nodes if nid not in nodes_with_edges]
        for node_id in nodes_to_remove:
            node = self.nodes[node_id]
            if node.name in self._node_name_index:
                del self._node_name_index[node.name]
            del self.nodes[node_id]

        # 重建索引
        self._rebuild_indexes()
        self._modified = True

        removed_edges = len(edges_to_remove)
        removed_nodes = len(nodes_to_remove)

        if removed_edges or removed_nodes:
            logger.info(
                "知识精简完成: 删除 %d 条边, %d 个孤立节点",
                removed_edges,
                removed_nodes,
            )

        return removed_edges, removed_nodes

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 内部方法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_edges_by_node(self, node_id: str) -> list[Edge]:
        """获取与节点相关的所有边。"""
        edges = []
        edges.extend(self._outgoing_index.get(node_id, []))
        edges.extend(self._incoming_index.get(node_id, []))
        return edges

    def _rebuild_indexes(self) -> None:
        """重建所有索引。"""
        # 重建节点名称索引
        self._node_name_index.clear()
        for node in self.nodes.values():
            self._node_name_index[node.name] = node.id

        # 重建边索引
        self._outgoing_index.clear()
        self._incoming_index.clear()
        self._relation_index.clear()

        for edge in self.edges:
            self._add_edge_to_indexes(edge)

    def _add_edge_to_indexes(self, edge: Edge) -> None:
        """将边添加到索引。"""
        # 出边索引
        if edge.source not in self._outgoing_index:
            self._outgoing_index[edge.source] = []
        self._outgoing_index[edge.source].append(edge)

        # 入边索引
        if edge.target not in self._incoming_index:
            self._incoming_index[edge.target] = []
        self._incoming_index[edge.target].append(edge)

        # 关系索引
        if edge.relation not in self._relation_index:
            self._relation_index[edge.relation] = []
        self._relation_index[edge.relation].append(edge)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 迭代器
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def iter_nodes(self) -> Iterator[Node]:
        """迭代所有节点。"""
        return iter(self.nodes.values())

    def iter_edges(self) -> Iterator[Edge]:
        """迭代所有边。"""
        return iter(self.edges)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 统计信息
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_stats(self) -> dict[str, Any]:
        """获取图谱统计信息（阶段23）。"""
        active_nodes = sum(1 for n in self.nodes.values() if n.is_active())
        total_weight = sum(e.weight for e in self.edges)
        avg_weight = total_weight / len(self.edges) if self.edges else 0.0

        # 关系类型分布
        relation_dist: dict[str, int] = {}
        for edge in self.edges:
            relation_dist[edge.relation] = relation_dist.get(edge.relation, 0) + 1

        # 权重分布
        weight_dist = {
            "high": sum(1 for e in self.edges if e.weight >= 0.7),
            "medium": sum(1 for e in self.edges if 0.3 <= e.weight < 0.7),
            "low": sum(1 for e in self.edges if e.weight < 0.3),
        }

        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "active_node_count": active_nodes,
            "avg_weight": round(avg_weight, 4),
            "relation_distribution": relation_dist,
            "weight_distribution": weight_dist,
            "last_saved": self._last_saved,
            "modified": self._modified,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段20: 数据验证
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def validate(self) -> list[str]:
        """
        验证图谱数据完整性。

        Returns:
            错误消息列表，空列表表示验证通过
        """
        errors: list[str] = []

        # 检查节点ID唯一性
        seen_ids: set[str] = set()
        for node in self.nodes.values():
            if node.id in seen_ids:
                errors.append(f"重复的节点ID: {node.id}")
            seen_ids.add(node.id)

        # 检查边端点有效性
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"边的源节点不存在: {edge.source}")
            if edge.target not in self.nodes:
                errors.append(f"边的目标节点不存在: {edge.target}")

        # 检查权重范围
        for edge in self.edges:
            if not (0.0 <= edge.weight <= 1.0):
                errors.append(f"边的权重越界: {edge.id} (weight={edge.weight})")

        # 检查自环
        for edge in self.edges:
            if edge.source == edge.target:
                errors.append(f"检测到自环边: {edge.id}")

        return errors

    def is_valid(self) -> bool:
        """检查图谱是否有效。"""
        return len(self.validate()) == 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段21: 备份恢复
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def backup(self, backup_path: str | None = None) -> str:
        """
        创建图谱备份。

        Args:
            backup_path: 备份文件路径，默认自动生成

        Returns:
            备份文件路径
        """
        if backup_path is None:
            timestamp = now_timestamp()
            backup_path = f"{self.save_path}.backup.{int(timestamp)}"

        data = {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "last_saved": now_timestamp(),
            "version": "0.1.0",
            "backup": True,
        }
        atomic_write_json(backup_path, data)
        logger.info("图谱备份创建: %s", backup_path)
        return backup_path

    def restore(self, backup_path: str) -> bool:
        """
        从备份恢复图谱。

        Args:
            backup_path: 备份文件路径

        Returns:
            是否恢复成功
        """
        if not os.path.isfile(backup_path):
            logger.error("备份文件不存在: %s", backup_path)
            return False

        try:
            # 先备份当前数据
            if self.nodes or self.edges:
                self.backup(f"{self.save_path}.pre_restore")

            # 加载备份数据
            original_path = self.save_path
            self.save_path = backup_path
            success = self.load()
            self.save_path = original_path

            if success:
                logger.info("图谱从备份恢复: %s", backup_path)
            return success

        except Exception as e:
            logger.error("恢复失败: %s", e)
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段22: 压缩优化
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def compress(self) -> dict[str, int]:
        """
        压缩图谱数据，减少存储空间。

        Returns:
            压缩统计信息
        """
        stats = {
            "duplicate_edges_removed": 0,
            "merged_edges": 0,
        }

        # 检测并合并重复边（相同source, target, relation）
        edge_keys: dict[str, Edge] = {}
        edges_to_keep: list[Edge] = []

        for edge in self.edges:
            key = f"{edge.source}|{edge.target}|{edge.relation}"
            if key in edge_keys:
                # 合并：取较高权重，合并证据
                existing = edge_keys[key]
                existing.weight = max(existing.weight, edge.weight)
                existing.evidence.extend(edge.evidence)
                existing.evidence = list(set(existing.evidence))
                stats["merged_edges"] += 1
            else:
                edge_keys[key] = edge
                edges_to_keep.append(edge)

        stats["duplicate_edges_removed"] = len(self.edges) - len(edges_to_keep)
        self.edges = edges_to_keep

        # 重建索引
        self._rebuild_indexes()
        self._modified = True

        if stats["duplicate_edges_removed"] or stats["merged_edges"]:
            logger.info(
                "图谱压缩完成: 删除 %d 重复边, 合并 %d 边",
                stats["duplicate_edges_removed"],
                stats["merged_edges"],
            )

        return stats

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段24: 可视化导出
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def to_dot(self) -> str:
        """
        导出为DOT格式（Graphviz）。

        Returns:
            DOT格式字符串
        """
        lines = ["digraph KnowledgeGraph {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box];")

        # 节点
        for node in self.nodes.values():
            label = node.name.replace('"', '\\"')
            color = "lightblue" if node.is_active() else "lightgray"
            lines.append(
                f'    "{node.id}" [label="{label}", style=filled, fillcolor={color}];'
            )

        # 边
        for edge in self.edges:
            label = f"{edge.relation}\\n{edge.weight:.2f}"
            lines.append(
                f'    "{edge.source}" -> "{edge.target}" '
                f'[label="{label}", penwidth={edge.weight * 3:.1f}];'
            )

        lines.append("}")
        return "\n".join(lines)

    def to_graphml(self) -> str:
        """
        导出为GraphML格式。

        Returns:
            GraphML格式字符串
        """
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('  <graph id="G" edgedefault="directed">')

        # 节点
        for node in self.nodes.values():
            lines.append(f'    <node id="{node.id}">')
            lines.append(f'      <data key="name">{node.name}</data>')
            lines.append(f'      <data key="status">{node.status.value}</data>')
            lines.append("    </node>")

        # 边
        for i, edge in enumerate(self.edges):
            lines.append(
                f'    <edge id="e{i}" source="{edge.source}" target="{edge.target}">'
            )
            lines.append(f'      <data key="relation">{edge.relation}</data>')
            lines.append(f'      <data key="weight">{edge.weight}</data>')
            lines.append("    </edge>")

        lines.append("  </graph>")
        lines.append("</graphml>")
        return "\n".join(lines)

    def to_csv(self) -> tuple[str, str]:
        """
        导出为CSV格式。

        Returns:
            (节点CSV, 边CSV)
        """
        # 节点CSV
        node_lines = ["id,name,status,created_at,access_count"]
        for node in self.nodes.values():
            node_lines.append(
                f"{node.id},{node.name},"
                f"{node.status.value},{node.created_at},{node.access_count}"
            )

        # 边CSV
        edge_lines = ["source,target,relation,weight,edge_type"]
        for edge in self.edges:
            edge_lines.append(
                f"{edge.source},{edge.target},"
                f"{edge.relation},{edge.weight},{edge.edge_type.value}"
            )

        return "\n".join(node_lines), "\n".join(edge_lines)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段25: 性能监控
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        获取性能指标。

        Returns:
            性能指标字典
        """
        import sys

        # 内存估算
        nodes_size = sum(sys.getsizeof(node.to_dict()) for node in self.nodes.values())
        edges_size = sum(sys.getsizeof(edge.to_dict()) for edge in self.edges)
        indexes_size = (
            sys.getsizeof(self._node_name_index)
            + sys.getsizeof(self._outgoing_index)
            + sys.getsizeof(self._incoming_index)
            + sys.getsizeof(self._relation_index)
        )

        # 连通性
        connected_nodes = set()
        for edge in self.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)
        isolated_nodes = len(self.nodes) - len(connected_nodes)

        # 平均度
        avg_degree = (2 * len(self.edges)) / len(self.nodes) if self.nodes else 0.0

        return {
            "memory_estimate": {
                "nodes_bytes": nodes_size,
                "edges_bytes": edges_size,
                "indexes_bytes": indexes_size,
                "total_bytes": nodes_size + edges_size + indexes_size,
            },
            "connectivity": {
                "isolated_nodes": isolated_nodes,
                "connected_nodes": len(connected_nodes),
                "avg_degree": round(avg_degree, 2),
            },
            "indexes": {
                "node_name_index_size": len(self._node_name_index),
                "outgoing_index_size": len(self._outgoing_index),
                "incoming_index_size": len(self._incoming_index),
                "relation_index_size": len(self._relation_index),
            },
        }

    def __len__(self) -> int:
        """返回节点数量。"""
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
