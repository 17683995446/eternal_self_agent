"""阶段7测试 — 类型定义模块。"""

from eternal_self_agent.types import (
    Edge,
    GraphState,
    Node,
    NodeStatus,
    SystemState,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class TestNode:
    def test_create_with_defaults(self):
        n = Node(name="测试")
        assert n.name == "测试"
        assert n.id  # 自动生成
        assert len(n.id) == 32
        assert n.created_at > 0
        assert n.status == NodeStatus.ACTIVE
        assert n.attributes == {}

    def test_create_with_custom(self):
        n = Node(
            name="自定义",
            id="fixed_id",
            status=NodeStatus.INACTIVE,
            attributes={"k": "v"},
        )
        assert n.id == "fixed_id"
        assert n.status == NodeStatus.INACTIVE
        assert n.attributes["k"] == "v"

    def test_serialization_roundtrip(self):
        n = Node(name="序列化测试", attributes={"x": 1})
        d = n.to_dict()
        n2 = Node.from_dict(d)
        assert n2.name == n.name
        assert n2.id == n.id
        assert n2.status == n.status
        assert n2.attributes == n.attributes


class TestEdge:
    def test_create_with_defaults(self):
        e = Edge(source="a", target="b", relation="关联")
        assert e.weight == 0.5
        assert e.created_at > 0

    def test_weight_clamp(self):
        e = Edge(source="a", target="b", relation="r", weight=2.0)
        assert e.weight == 1.0
        e2 = Edge(source="a", target="b", relation="r", weight=-0.5)
        assert e2.weight == 0.0

    def test_serialization_roundtrip(self):
        e = Edge(source="x", target="y", relation="测试", weight=0.8)
        d = e.to_dict()
        e2 = Edge.from_dict(d)
        assert e2.source == "x"
        assert e2.weight == 0.8


class TestTask:
    def test_create_with_defaults(self):
        t = Task(content="测试任务")
        assert t.id  # 自动生成
        assert t.status == TaskStatus.PENDING
        assert t.task_type == TaskType.DERIVED
        assert t.priority == TaskPriority.NORMAL
        assert t.retry_count == 0

    def test_create_with_custom(self):
        t = Task(
            content="紧急任务",
            task_type=TaskType.EXTERNAL,
            priority=TaskPriority.CRITICAL,
        )
        assert t.priority == TaskPriority.CRITICAL
        assert t.task_type == TaskType.EXTERNAL

    def test_serialization_roundtrip(self):
        t = Task(
            content="序列化", task_type=TaskType.INITIAL, priority=TaskPriority.HIGH
        )
        d = t.to_dict()
        t2 = Task.from_dict(d)
        assert t2.content == "序列化"
        assert t2.task_type == TaskType.INITIAL
        assert t2.priority == TaskPriority.HIGH


class TestEnums:
    def test_task_priority_ordering(self):
        assert (
            TaskPriority.LOW
            < TaskPriority.NORMAL
            < TaskPriority.HIGH
            < TaskPriority.CRITICAL
        )

    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"

    def test_system_state_values(self):
        assert SystemState.RUNNING.value == "running"
        assert SystemState.REPAIRING.value == "repairing"


class TestGraphState:
    def test_defaults(self):
        gs = GraphState()
        assert gs.node_count == 0
        assert gs.avg_weight == 0.0
