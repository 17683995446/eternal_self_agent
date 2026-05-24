"""
知识图谱模块 — 记忆公理核心载体

公理溯源: 记忆公理 — 智能 = 结构化、可沉淀、可关联的历史经验
"""

from eternal_self_agent.kg.edge import Edge, EdgeType
from eternal_self_agent.kg.graph import KnowledgeGraph
from eternal_self_agent.kg.node import Node, NodeStatus

__all__ = [
    "Node",
    "NodeStatus",
    "Edge",
    "EdgeType",
    "KnowledgeGraph",
]
