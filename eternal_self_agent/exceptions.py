"""
基础异常处理框架 — 存续公理推导

设计意图: 存续公理要求「局部异常永远不能击穿整体系统」。
所有异常按故障域分类，确保全局异常隔离、精准捕获、优雅降级。
"""


class AgentError(Exception):
    """智能体系统基础异常 — 所有自定义异常的根类。"""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 知识图谱异常（记忆公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class KnowledgeGraphError(AgentError):
    """知识图谱操作异常基类。"""


class NodeAlreadyExistsError(KnowledgeGraphError):
    """尝试创建已存在的节点。"""


class NodeNotFoundError(KnowledgeGraphError):
    """引用了不存在的节点。"""


class EdgeValidationError(KnowledgeGraphError):
    """边数据校验失败（如权重越界、端点无效）。"""


class GraphPersistenceError(KnowledgeGraphError):
    """图谱持久化读写失败。"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 任务队列异常（自驱公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TaskError(AgentError):
    """任务系统异常基类。"""


class TaskQueueFullError(TaskError):
    """任务队列已满，无法入队。"""


class TaskExecutionError(TaskError):
    """任务执行过程中发生错误。"""


class TaskTimeoutError(TaskError):
    """任务执行超时。"""


class TaskDuplicateError(TaskError):
    """检测到重复任务。"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 存续保活异常（存续公理域）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AliveError(AgentError):
    """存续保活层异常基类。"""


class SelfRepairError(AliveError):
    """自愈修复过程中发生错误。"""


class ResourceLimitError(AliveError):
    """系统资源达到限制阈值。"""


class CircuitBreakerError(AliveError):
    """熔断器触发，系统进入降级模式。"""
