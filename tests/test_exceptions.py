"""阶段3测试 — 异常处理框架。"""

import pytest

from eternal_self_agent.exceptions import (
    AgentError,
    AliveError,
    CircuitBreakerError,
    EdgeValidationError,
    GraphPersistenceError,
    KnowledgeGraphError,
    NodeAlreadyExistsError,
    NodeNotFoundError,
    ResourceLimitError,
    SelfRepairError,
    TaskDuplicateError,
    TaskError,
    TaskExecutionError,
    TaskQueueFullError,
    TaskTimeoutError,
)


class TestExceptionHierarchy:
    def test_agent_error_is_base(self):
        assert issubclass(KnowledgeGraphError, AgentError)
        assert issubclass(TaskError, AgentError)
        assert issubclass(AliveError, AgentError)

    def test_kg_exceptions(self):
        assert issubclass(NodeAlreadyExistsError, KnowledgeGraphError)
        assert issubclass(NodeNotFoundError, KnowledgeGraphError)
        assert issubclass(EdgeValidationError, KnowledgeGraphError)
        assert issubclass(GraphPersistenceError, KnowledgeGraphError)

    def test_task_exceptions(self):
        assert issubclass(TaskQueueFullError, TaskError)
        assert issubclass(TaskExecutionError, TaskError)
        assert issubclass(TaskTimeoutError, TaskError)
        assert issubclass(TaskDuplicateError, TaskError)

    def test_alive_exceptions(self):
        assert issubclass(SelfRepairError, AliveError)
        assert issubclass(ResourceLimitError, AliveError)
        assert issubclass(CircuitBreakerError, AliveError)


class TestExceptionInstance:
    def test_basic_message(self):
        e = NodeNotFoundError("节点xyz不存在")
        assert str(e) == "节点xyz不存在"
        assert e.cause is None

    def test_with_cause(self):
        cause = ValueError("原始错误")
        e = TaskExecutionError("任务失败", cause=cause)
        assert e.cause is cause
        assert str(e) == "任务失败"

    def test_catch_hierarchy(self):
        with pytest.raises(AgentError):
            raise TaskQueueFullError("满")
        with pytest.raises(TaskError):
            raise TaskTimeoutError("超时")
