"""
自驱进化模块 — 自驱公理核心实现

公理溯源: 自驱公理 — 无外部输入时自我产生任务、自我进化
"""

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

__all__ = [
    "EvolveEngine",
    "KnowledgeAnalyzer",
    "SelfDriveGenerator",
    "EvolveStrategy",
    "QualityAssessor",
    "ConflictDetector",
    "KnowledgeFuser",
    "TrendPredictor",
    "EvolveEvaluator",
]
