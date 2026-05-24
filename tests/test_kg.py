"""知识图谱模块测试。"""

import tempfile
import os

import pytest

from eternal_self_agent.kg import Edge, EdgeType, KnowledgeGraph, Node, NodeStatus


class TestNode:
    """节点测试。"""

    def test_create_with_defaults(self):
        n = Node(name="测试节点")
        assert n.name == "测试节点"
        assert n.id and len(n.id) == 32
        assert n.status == NodeStatus.ACTIVE
        assert n.access_count == 0

    def test_state_management(self):
        n = Node(name="状态测试")
        n.deactivate()
        assert n.status == NodeStatus.INACTIVE
        n.activate()
        assert n.is_active()
        n.archive()
        assert n.status == NodeStatus.ARCHIVED

    def test_attributes(self):
        n = Node(name="属性测试")
        n.set_attribute("key1", "value1")
        assert n.get_attribute("key1") == "value1"
        assert n.get_attribute("missing", "default") == "default"
        assert n.remove_attribute("key1")
        assert n.get_attribute("key1") is None

    def test_serialization(self):
        n = Node(name="序列化", attributes={"k": "v"})
        d = n.to_dict()
        n2 = Node.from_dict(d)
        assert n2.name == n.name
        assert n2.id == n.id


class TestEdge:
    """边测试。"""

    def test_create_with_defaults(self):
        e = Edge(source="a", target="b", relation="关联")
        assert e.weight == 0.5
        assert e.edge_type == EdgeType.DERIVED

    def test_weight_management(self):
        e = Edge(source="a", target="b", relation="r")
        e.increase_weight(0.3)
        assert abs(e.weight - 0.8) < 0.001
        e.decrease_weight(0.5)
        assert abs(e.weight - 0.3) < 0.001

    def test_evidence(self):
        e = Edge(source="a", target="b", relation="r")
        e.add_evidence("证据1")
        e.add_evidence("证据2")
        assert e.evidence_count() == 2
        e.remove_evidence("证据1")
        assert e.evidence_count() == 1

    def test_serialization(self):
        e = Edge(source="x", target="y", relation="测试", weight=0.8)
        d = e.to_dict()
        e2 = Edge.from_dict(d)
        assert e2.source == "x"
        assert abs(e2.weight - 0.8) < 0.001


class TestKnowledgeGraph:
    """知识图谱测试。"""

    @pytest.fixture
    def kg(self):
        """创建临时图谱。"""
        tmp_file = tempfile.mktemp(suffix=".json")
        kg = KnowledgeGraph(save_path=tmp_file)
        yield kg
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)

    def test_add_node(self, kg):
        n = kg.add_node("节点A")
        assert kg.has_node(n.id)
        assert kg.has_node_by_name("节点A")

    def test_add_edge(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        e = kg.add_edge("A", "B", "关联", weight=0.8)
        assert kg.get_edge(e.id) is not None
        assert len(kg.get_edges_by_source(kg.get_node_by_name("A").id)) == 1

    def test_persistence(self, kg):
        kg.add_node("节点1")
        kg.add_node("节点2")
        kg.add_edge("节点1", "节点2", "关联")
        kg.save()

        kg2 = KnowledgeGraph(save_path=kg.save_path)
        assert len(kg2) == 2
        assert kg2.has_node_by_name("节点1")

    def test_neighbors(self, kg):
        n1 = kg.add_node("A")
        n2 = kg.add_node("B")
        kg.add_edge("A", "B", "关联")
        neighbors = kg.get_neighbors(n1.id)
        assert len(neighbors) == 1
        assert neighbors[0].name == "B"

    def test_derive_tasks(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联", weight=0.8)
        tasks = kg.derive_new_tasks("A")
        assert len(tasks) == 1
        assert "B" in tasks[0]

    def test_trim_knowledge(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "弱关联", weight=0.05)
        removed_edges, _ = kg.trim_invalid_knowledge(threshold=0.1)
        assert removed_edges == 1

    def test_validate(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联")
        assert kg.is_valid()

    def test_backup_restore(self, kg):
        kg.add_node("测试节点")
        backup_path = kg.backup()
        assert os.path.exists(backup_path)
        os.unlink(backup_path)

    def test_compress(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联", weight=0.5)
        kg.add_edge("A", "B", "关联", weight=0.8)
        stats = kg.compress()
        assert stats["merged_edges"] >= 1

    def test_stats(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联", weight=0.8)
        stats = kg.get_stats()
        assert stats["node_count"] == 2
        assert "relation_distribution" in stats

    def test_export_dot(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联")
        dot = kg.to_dot()
        assert "digraph" in dot

    def test_export_csv(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联")
        nodes_csv, edges_csv = kg.to_csv()
        assert "A" in nodes_csv
        assert "关联" in edges_csv

    def test_performance_metrics(self, kg):
        kg.add_node("A")
        kg.add_node("B")
        kg.add_edge("A", "B", "关联")
        metrics = kg.get_performance_metrics()
        assert "memory_estimate" in metrics
        assert "connectivity" in metrics
