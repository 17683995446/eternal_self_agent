"""阶段6测试 — 工具函数库。"""

import os

from eternal_self_agent.utils import (
    atomic_write_json,
    clamp,
    generate_id,
    generate_short_id,
    is_valid_name,
    md5_hash,
    now_iso,
    now_timestamp,
    safe_read_json,
    validate_weight,
)


class TestTimeUtils:
    def test_now_timestamp(self):
        ts = now_timestamp()
        assert ts > 0
        assert isinstance(ts, float)

    def test_now_iso(self):
        iso = now_iso()
        assert "T" in iso
        assert len(iso) == 19


class TestIdUtils:
    def test_generate_id(self):
        id1 = generate_id()
        id2 = generate_id()
        assert len(id1) == 32
        assert id1 != id2

    def test_generate_short_id(self):
        sid = generate_short_id()
        assert len(sid) == 12


class TestHashUtils:
    def test_md5_hash(self):
        h1 = md5_hash("hello")
        h2 = md5_hash("hello")
        h3 = md5_hash("world")
        assert len(h1) == 32
        assert h1 == h2
        assert h1 != h3


class TestFileUtils:
    def test_atomic_write_and_read(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.json")
        data = {"key": "value", "num": 42}
        atomic_write_json(path, data)
        result = safe_read_json(path)
        assert result == data

    def test_safe_read_nonexistent(self):
        result = safe_read_json("/tmp/nonexistent_file_xyz.json", default="DEFAULT")
        assert result == "DEFAULT"

    def test_atomic_write_creates_dir(self, tmp_dir):
        path = os.path.join(tmp_dir, "sub", "deep", "test.json")
        atomic_write_json(path, {"ok": True})
        assert os.path.isfile(path)


class TestValidationUtils:
    def test_clamp(self):
        assert clamp(5, 0, 10) == 5
        assert clamp(-1, 0, 10) == 0
        assert clamp(15, 0, 10) == 10

    def test_validate_weight(self):
        assert validate_weight(0.5) == 0.5
        assert validate_weight(1.5) == 1.0
        assert validate_weight(-0.1) == 0.0
        assert validate_weight(0.0) == 0.0
        assert validate_weight(1.0) == 1.0

    def test_is_valid_name(self):
        assert is_valid_name("test") is True
        assert is_valid_name("测试节点") is True
        assert is_valid_name("") is False
        assert is_valid_name("   ") is False
