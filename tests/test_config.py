"""阶段4测试 — 配置管理模块。"""

import os

from eternal_self_agent.config import Config, load_config


class TestConfig:
    def test_singleton(self):
        c1 = Config()
        c2 = Config()
        assert c1 is c2

    def test_defaults(self):
        cfg = Config()
        assert cfg.get("loop_delay") == 0.3
        assert cfg.get("task_queue_max") == 200

    def test_set_and_get(self):
        cfg = Config()
        cfg.set("loop_delay", 0.8)
        assert cfg.get("loop_delay") == 0.8

    def test_set_unknown_key(self):
        cfg = Config()
        cfg.set("nonexistent_key", 123)
        assert cfg.get("nonexistent_key") is None

    def test_reset(self):
        cfg = Config()
        cfg.set("loop_delay", 99.0)
        cfg.reset()
        assert cfg.get("loop_delay") == 0.3

    def test_to_dict(self):
        cfg = Config()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "loop_delay" in d

    def test_save_and_load_file(self, tmp_dir):
        path = os.path.join(tmp_dir, "config.json")
        cfg = Config()
        cfg.set("loop_delay", 0.7)
        cfg.save_to_file(path)

        # 新实例加载
        Config._instance = None
        cfg2 = Config()
        cfg2.load_from_file(path)
        assert cfg2.get("loop_delay") == 0.7

        # 恢复单例
        Config._instance = cfg

    def test_load_nonexistent_file(self, tmp_dir):
        cfg = Config()
        cfg.reset()
        cfg.load_from_file(os.path.join(tmp_dir, "no_such.json"))
        assert cfg.get("loop_delay") == 0.3

    def test_load_from_env(self, monkeypatch):
        cfg = Config()
        cfg.reset()
        monkeypatch.setenv("ETERNAL_LOOP_DELAY", "0.9")
        cfg.load_from_env()
        assert cfg.get("loop_delay") == 0.9
        monkeypatch.delenv("ETERNAL_LOOP_DELAY")

    def test_load_config_function(self):
        cfg = load_config()
        assert isinstance(cfg, Config)
