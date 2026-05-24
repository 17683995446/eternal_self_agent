"""
知识分析模块 — 关联强度分析、聚类、演化追踪

设计意图: 提供图谱深度分析能力，支持智能决策。
零外部依赖，纯算法实现。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from eternal_self_agent.kg.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class KnowledgeAnalyzer:
    """知识图谱分析器。"""

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段39: 关联强度分析
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_node_centrality(self) -> dict[str, float]:
        """
        计算节点中心性（度中心性）。

        中心性越高，节点在知识网络中越重要。

        Returns:
            {node_id: centrality_score}
        """
        if not self.kg.nodes:
            return {}

        max_possible_degree = len(self.kg.nodes) - 1
        if max_possible_degree <= 0:
            return {nid: 0.0 for nid in self.kg.nodes}

        centrality: dict[str, float] = {}
        for node_id in self.kg.nodes:
            degree = self.kg.get_node_degree(node_id)
            centrality[node_id] = degree / max_possible_degree

        return centrality

    def get_key_nodes(self, top_n: int = 5) -> list[tuple[str, float]]:
        """
        获取关键知识节点（按中心性排序）。

        Returns:
            [(node_id, centrality_score)] 列表
        """
        centrality = self.get_node_centrality()
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:top_n]

    def get_association_strength(self, source_id: str, target_id: str) -> float:
        """
        计算两个节点之间的关联强度。

        综合考虑:
          - 直接边权重
          - 共同邻居数量
          - 路径长度

        Returns:
            关联强度 [0.0, 1.0]
        """
        # 直接边权重
        direct_weight = 0.0
        for edge in self.kg.get_edges_by_source(source_id):
            if edge.target == target_id:
                direct_weight = max(direct_weight, edge.weight)
        for edge in self.kg.get_edges_by_target(source_id):
            if edge.source == target_id:
                direct_weight = max(direct_weight, edge.weight)

        # 共同邻居
        source_neighbors = set()
        for edge in self.kg.get_edges_by_source(source_id):
            source_neighbors.add(edge.target)
        for edge in self.kg.get_edges_by_target(source_id):
            source_neighbors.add(edge.source)

        target_neighbors = set()
        for edge in self.kg.get_edges_by_source(target_id):
            target_neighbors.add(edge.target)
        for edge in self.kg.get_edges_by_target(target_id):
            target_neighbors.add(edge.source)

        common = source_neighbors & target_neighbors
        total = source_neighbors | target_neighbors
        jaccard = len(common) / len(total) if total else 0.0

        # 路径长度
        path = self.kg.find_path(source_id, target_id, max_depth=5)
        path_factor = 1.0 / (len(path) + 1) if path else 0.0

        # 综合评分
        strength = 0.4 * direct_weight + 0.3 * jaccard + 0.3 * path_factor
        return min(max(strength, 0.0), 1.0)

    def get_relation_report(self) -> dict[str, Any]:
        """
        生成关联分析报告。

        Returns:
            分析报告字典
        """
        key_nodes = self.get_key_nodes(5)
        key_details = []
        for node_id, score in key_nodes:
            node = self.kg.nodes.get(node_id)
            name = node.name if node else node_id[:8]
            key_details.append(
                {
                    "node_id": node_id[:8],
                    "name": name,
                    "centrality": round(score, 4),
                    "degree": self.kg.get_node_degree(node_id),
                }
            )

        return {
            "key_nodes": key_details,
            "total_relations": len(self.kg.edges),
            "avg_weight": self.kg.get_stats().get("avg_weight", 0),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段40: 知识聚类算法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def find_communities(self) -> list[set[str]]:
        """
        简单社区发现算法（基于连通分量）。

        Returns:
            社区列表，每个社区是节点ID集合
        """
        visited: set[str] = set()
        communities: list[set[str]] = []

        for node_id in self.kg.nodes:
            if node_id in visited:
                continue

            # BFS遍历连通分量
            community: set[str] = set()
            queue = [node_id]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                community.add(current)

                for neighbor in self.kg.get_neighbors(current):
                    if neighbor.id not in visited:
                        queue.append(neighbor.id)

            if community:
                communities.append(community)

        return communities

    def get_cluster_summary(self) -> list[dict[str, Any]]:
        """
        获取聚类摘要。

        Returns:
            聚类信息列表
        """
        communities = self.find_communities()
        summary = []

        for i, community in enumerate(communities):
            nodes_in_cluster = [
                self.kg.nodes[nid] for nid in community if nid in self.kg.nodes
            ]
            names = [n.name for n in nodes_in_cluster]
            avg_weight = 0.0
            edge_count = 0

            for edge in self.kg.edges:
                if edge.source in community and edge.target in community:
                    avg_weight += edge.weight
                    edge_count += 1

            if edge_count > 0:
                avg_weight /= edge_count

            summary.append(
                {
                    "cluster_id": i,
                    "size": len(community),
                    "nodes": names[:10],  # 最多显示10个
                    "internal_edges": edge_count,
                    "avg_internal_weight": round(avg_weight, 4),
                }
            )

        # 按大小降序排列
        summary.sort(key=lambda x: x["size"], reverse=True)
        return summary

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段41: 知识演化追踪
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_evolution_snapshot(self) -> dict[str, Any]:
        """
        获取当前知识图谱快照（用于演化追踪）。

        Returns:
            快照字典
        """
        stats = self.kg.get_stats()
        metrics = self.kg.get_performance_metrics()

        return {
            "timestamp": time.time(),
            "stats": stats,
            "performance": metrics,
            "key_nodes": self.get_key_nodes(3),
            "cluster_count": len(self.find_communities()),
        }

    def compare_snapshots(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> dict[str, Any]:
        """
        比较两个快照，生成演化差异报告。

        Returns:
            差异报告
        """
        b_stats = before.get("stats", {})
        a_stats = after.get("stats", {})

        return {
            "node_change": a_stats.get("node_count", 0) - b_stats.get("node_count", 0),
            "edge_change": a_stats.get("edge_count", 0) - b_stats.get("edge_count", 0),
            "weight_change": round(
                a_stats.get("avg_weight", 0) - b_stats.get("avg_weight", 0), 4
            ),
            "time_elapsed": round(
                after.get("timestamp", 0) - before.get("timestamp", 0), 2
            ),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段43: 知识复盘机制
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def review_knowledge(self) -> dict[str, Any]:
        """
        知识复盘 — 全面审查图谱健康状态。

        Returns:
            复盘报告
        """
        stats = self.kg.get_stats()
        metrics = self.kg.get_performance_metrics()
        clusters = self.get_cluster_summary()
        key_nodes = self.get_key_nodes(5)
        validation_errors = self.kg.validate()

        # 识别知识缺口
        isolated = metrics.get("connectivity", {}).get("isolated_nodes", 0)
        low_weight_edges = sum(1 for e in self.kg.edges if e.weight < 0.2)

        # 生成建议
        suggestions: list[str] = []
        if isolated > 0:
            suggestions.append(f"发现{isolated}个孤立节点，建议建立关联或删除")
        if low_weight_edges > len(self.kg.edges) * 0.5:
            suggestions.append("超过50%的边权重较低，建议执行知识精简")
        if len(clusters) > 1:
            suggestions.append(
                f"知识图谱分为{len(clusters)}个独立社区，建议增加跨社区关联"
            )
        if validation_errors:
            suggestions.append(f"发现{len(validation_errors)}个数据验证错误，需要修复")

        return {
            "timestamp": time.time(),
            "stats": stats,
            "performance": metrics,
            "clusters": clusters,
            "key_nodes": [
                {
                    "name": (
                        self.kg.nodes[nid].name if nid in self.kg.nodes else nid[:8]
                    ),
                    "centrality": round(score, 4),
                }
                for nid, score in key_nodes
            ],
            "validation_errors": validation_errors,
            "suggestions": suggestions,
            "health_score": self._calculate_health_score(
                stats, metrics, validation_errors
            ),
        }

    def _calculate_health_score(
        self, stats: dict, metrics: dict, errors: list
    ) -> float:
        """计算知识图谱健康评分 [0, 100]。"""
        score = 100.0

        # 扣分: 验证错误
        score -= len(errors) * 10

        # 扣分: 孤立节点
        isolated = metrics.get("connectivity", {}).get("isolated_nodes", 0)
        total = stats.get("node_count", 1)
        if total > 0:
            score -= (isolated / total) * 20

        # 扣分: 低权重边过多
        edge_count = stats.get("edge_count", 0)
        if edge_count > 0:
            low_ratio = stats.get("weight_distribution", {}).get("low", 0) / edge_count
            score -= low_ratio * 15

        return max(0.0, min(100.0, score))
