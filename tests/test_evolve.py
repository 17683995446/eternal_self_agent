"""自驱进化模块测试 — 阶段50压力测试。"""

import os
import tempfile
import time

import pytest

from eternal_self_agent.evolve.analyzer import KnowledgeAnalyzer
from eternal_self_agent.evolve.engine import EvolveEngine
from eternal_self_agent.evolve.generator import SelfDriveGenerator
from eternal_self_agent.evolve.strategy import (
    ConflictDetector,
    EvolveEvaluator,
    EvolveStrategy,
    KnowledgeFuser,
    QualityAssessor,
    TrendPredictor,
)
from eternal_self_agent.kg import KnowledgeGraph


@pytest.fixture
def kg():
    tmp_file = tempfile.mktemp(suffix=".json")
    k = KnowledgeGraph(save_path=tmp_file)
    # 构建测试图谱
    for i in range(10):
        k.add_node(f"节点{i}")
    for i in range(9):
        k.add_edge(f"节点{i}", f"节点{i+1}", "链式关联", weight=0.5 + i * 0.05)
    k.add_edge("节点0", "节点5", "跨链关联", weight=0.8)
    k.add_edge("节点2", "节点7", "跨链关联", weight=0.3)
    yield k
    if os.path.exists(tmp_file):
        os.unlink(tmp_file)


class TestEvolveEngine:
    def test_derive_tasks(self, kg):
        engine = EvolveEngine(kg)
        tasks = engine.derive_tasks("节点0")
        assert len(tasks) >= 1

    def test_derive_from_all(self, kg):
        engine = EvolveEngine(kg)
        tasks = engine.derive_from_all_active(max_per_node=2)
        assert len(tasks) >= 1

    def test_reinforce_and_weaken(self, kg):
        engine = EvolveEngine(kg)
        edge = kg.get_edges_by_source(kg.get_node_by_name("节点0").id)[0]
        old_w = edge.weight
        engine.reinforce_edge(edge.id, 0.1)
        assert kg.get_edge(edge.id).weight > old_w
        engine.weaken_edge(edge.id, 0.05)

    def test_decay(self, kg):
        engine = EvolveEngine(kg)
        count = engine.decay_all_weights(0.9)
        assert count == len(kg.edges)

    def test_trim(self, kg):
        kg.add_edge("节点0", "节点9", "弱关联", weight=0.01)
        engine = EvolveEngine(kg)
        stats = engine.trim_knowledge(threshold=0.05)
        assert stats["removed_edges"] >= 1

    def test_full_evolution(self, kg):
        engine = EvolveEngine(kg)
        report = engine.full_evolution()
        assert "decayed_edges" in report
        assert "new_tasks_derived" in report


class TestKnowledgeAnalyzer:
    def test_centrality(self, kg):
        analyzer = KnowledgeAnalyzer(kg)
        centrality = analyzer.get_node_centrality()
        assert len(centrality) == 10

    def test_key_nodes(self, kg):
        analyzer = KnowledgeAnalyzer(kg)
        key = analyzer.get_key_nodes(3)
        assert len(key) == 3

    def test_association_strength(self, kg):
        analyzer = KnowledgeAnalyzer(kg)
        n0 = kg.get_node_by_name("节点0").id
        n1 = kg.get_node_by_name("节点1").id
        strength = analyzer.get_association_strength(n0, n1)
        assert 0.0 <= strength <= 1.0

    def test_communities(self, kg):
        analyzer = KnowledgeAnalyzer(kg)
        communities = analyzer.find_communities()
        assert len(communities) >= 1

    def test_review(self, kg):
        analyzer = KnowledgeAnalyzer(kg)
        review = analyzer.review_knowledge()
        assert "health_score" in review


class TestSelfDriveGenerator:
    def test_generate_idle(self, kg):
        gen = SelfDriveGenerator(kg)
        tasks = gen.generate_idle_tasks(3)
        assert len(tasks) > 0
        assert gen.total_generated > 0


class TestStrategy:
    def test_config(self):
        s = EvolveStrategy(derive_threshold=0.3)
        d = s.to_dict()
        assert d["derive_threshold"] == 0.3


class TestQualityAssessor:
    def test_assess(self, kg):
        qa = QualityAssessor(kg)
        report = qa.assess()
        assert "overall_score" in report


class TestConflictDetector:
    def test_detect(self, kg):
        cd = ConflictDetector(kg)
        conflicts = cd.detect()
        assert isinstance(conflicts, list)


class TestKnowledgeFuser:
    def test_merge(self, kg):
        kg.add_node("副本")
        kg.add_edge("副本", "节点1", "关联", 0.4)
        fuser = KnowledgeFuser(kg)
        assert fuser.merge_similar_nodes("节点0", "副本")


class TestTrendPredictor:
    def test_predict(self, kg):
        pred = TrendPredictor(kg)
        pred.record_snapshot()
        kg.add_node("新节点")
        pred.record_snapshot()
        forecast = pred.predict_growth(3)
        assert "node_trend_per_step" in forecast


class TestEvolveEvaluator:
    def test_evaluate(self, kg):
        ev = EvolveEvaluator(kg)
        ev.mark_before()
        engine = EvolveEngine(kg)
        result = engine.full_evolution()
        report = ev.evaluate(result)
        assert "node_delta" in report
        assert ev.get_summary()["total_evolutions"] == 1


class TestEvolveStress:
    """阶段50: 进化系统压力测试。"""

    def test_large_graph_evolution(self):
        """大规模图谱进化测试。"""
        tmp_file = tempfile.mktemp(suffix=".json")
        kg = KnowledgeGraph(save_path=tmp_file)

        # 创建200个节点的图谱
        for i in range(200):
            kg.add_node(f"N{i}")
        for i in range(199):
            kg.add_edge(f"N{i}", f"N{i+1}", "链式", weight=0.5)
        # 添加一些跨链关联
        for i in range(0, 200, 10):
            kg.add_edge(f"N{i}", f"N{i+5}", "跨链", weight=0.7)

        engine = EvolveEngine(kg)
        start = time.time()

        # 执行10轮进化
        for _ in range(10):
            engine.full_evolution()

        elapsed = time.time() - start
        print(f"\n大规模进化: 200节点, 10轮, {elapsed:.2f}秒")
        assert elapsed < 5

        if os.path.exists(tmp_file):
            os.unlink(tmp_file)

    def test_rapid_derive(self):
        """高频推演测试。"""
        tmp_file = tempfile.mktemp(suffix=".json")
        kg = KnowledgeGraph(save_path=tmp_file)

        for i in range(50):
            kg.add_node(f"T{i}")
        for i in range(49):
            kg.add_edge(f"T{i}", f"T{i+1}", "关联", weight=0.6)

        engine = EvolveEngine(kg)
        start = time.time()

        total_tasks = 0
        for i in range(50):
            kg.add_node(f"新{i}")
            name = f"新{i}"
            kg.add_edge("T0", name, "推演", weight=0.8)
            tasks = engine.derive_from_all_active(max_per_node=1)
            total_tasks += len(tasks)

        elapsed = time.time() - start
        print(f"\n高频推演: {total_tasks}任务, {elapsed:.2f}秒")
        assert total_tasks > 0

        if os.path.exists(tmp_file):
            os.unlink(tmp_file)

    def test_repeated_trim(self):
        """反复精简稳定性测试。"""
        tmp_file = tempfile.mktemp(suffix=".json")
        kg = KnowledgeGraph(save_path=tmp_file)

        for i in range(100):
            kg.add_node(f"R{i}")
        for i in range(99):
            w = 0.01 + (i % 5) * 0.2  # 混合权重
            kg.add_edge(f"R{i}", f"R{i+1}", "关联", weight=w)

        engine = EvolveEngine(kg)

        for _ in range(20):
            engine.trim_knowledge(threshold=0.1)
            # 添加新知识
            kg.add_node("新节点")
            kg.add_edge("R0", "新节点", "新关联", weight=0.8)

        assert len(kg.nodes) > 0
        assert len(kg.edges) > 0

        if os.path.exists(tmp_file):
            os.unlink(tmp_file)
