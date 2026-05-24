"""阶段2测试 — 全局常量定义模块。"""

from eternal_self_agent import constants


class TestConstants:
    def test_loop_delay(self):
        assert constants.LOOP_DELAY == 0.3
        assert isinstance(constants.LOOP_DELAY, float)

    def test_evolve_step(self):
        assert constants.EVOLVE_STEP == 50
        assert isinstance(constants.EVOLVE_STEP, int)

    def test_kg_save_path(self):
        assert constants.KG_SAVE_PATH.endswith("knowledge_graph.json")
        assert "data" in constants.KG_SAVE_PATH

    def test_task_queue_max(self):
        assert constants.TASK_QUEUE_MAX == 200

    def test_derive_weight_threshold(self):
        assert 0.0 < constants.DERIVE_WEIGHT_THRESHOLD <= 1.0

    def test_trim_weight_threshold(self):
        assert (
            0.0 <= constants.TRIM_WEIGHT_THRESHOLD < constants.DERIVE_WEIGHT_THRESHOLD
        )

    def test_system_name(self):
        assert constants.SYSTEM_NAME == "eternal_self_agent"

    def test_version(self):
        assert constants.VERSION == "0.1.0"
