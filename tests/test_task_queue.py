"""任务队列模块测试 — 阶段35压力测试。"""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from eternal_self_agent.task import Task, TaskPriority, TaskQueue, TaskStatus


class TestTask:
    """任务单元测试。"""

    def test_create_with_defaults(self):
        t = Task(content="测试任务")
        assert t.status == TaskStatus.PENDING
        assert t.priority == TaskPriority.NORMAL
        assert t._content_hash

    def test_state_transitions(self):
        t = Task(content="状态测试")
        t.start()
        assert t.status == TaskStatus.RUNNING
        t.complete({"result": "ok"})
        assert t.status == TaskStatus.COMPLETED

    def test_retry(self):
        t = Task(content="重试测试", max_retries=2)
        t.fail("error")
        assert t.can_retry()
        assert t.retry()
        assert t.retry_count == 1
        assert t.status == TaskStatus.PENDING

    def test_duplicate_detection(self):
        t1 = Task(content="相同内容", task_type=TaskStatus.PENDING)
        t2 = Task(content="相同内容", task_type=TaskStatus.PENDING)
        assert t1.is_duplicate_of(t2)

    def test_priority_comparison(self):
        th = Task(content="high", priority=TaskPriority.HIGH)
        tl = Task(content="low", priority=TaskPriority.LOW)
        assert th < tl  # 高优先级 < 低优先级（用于排序）


class TestTaskQueue:
    """任务队列测试。"""

    @pytest.fixture
    def queue(self):
        tmp_file = tempfile.mktemp(suffix=".json")
        q = TaskQueue(max_size=100, save_path=tmp_file)
        yield q
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)

    def test_add_and_get(self, queue):
        t = Task(content="测试任务")
        assert queue.add(t)
        assert queue.size() == 1
        got = queue.get()
        assert got is not None
        assert got.content == "测试任务"

    def test_priority_ordering(self, queue):
        t1 = Task(content="low", priority=TaskPriority.LOW)
        t2 = Task(content="high", priority=TaskPriority.HIGH)
        t3 = Task(content="normal", priority=TaskPriority.NORMAL)
        queue.add(t1)
        queue.add(t2)
        queue.add(t3)

        # 高优先级先出
        assert queue.get().content == "high"
        assert queue.get().content == "normal"
        assert queue.get().content == "low"

    def test_duplicate_rejection(self, queue):
        t1 = Task(content="重复任务")
        t2 = Task(content="重复任务")
        queue.add(t1)
        with pytest.raises(Exception):
            queue.add(t2)

    def test_capacity_limit(self, queue):
        small_queue = TaskQueue(max_size=3)
        for i in range(5):
            t = Task(content=f"任务{i}", priority=TaskPriority.LOW)
            small_queue.add(t)
        assert len(small_queue) <= 3

    def test_persistence(self, queue):
        t = Task(content="持久化测试")
        queue.add(t)
        queue.save()

        # 新队列加载
        queue2 = TaskQueue(max_size=100, save_path=queue.save_path)
        assert queue2.size() == 1

    def test_batch_operations(self, queue):
        tasks = [Task(content=f"批处理{i}") for i in range(10)]
        success, failed = queue.batch_add(tasks)
        assert success == 10
        assert queue.size() == 10

        batch = queue.batch_get(5)
        assert len(batch) == 5

    def test_dead_letter(self, queue):
        t = Task(content="死信测试", max_retries=0)
        queue.add(t)
        t = queue.get()
        queue.fail_task(t.id, "error")
        assert len(queue.get_dead_letter_tasks()) == 1

    def test_stats(self, queue):
        t = Task(content="统计测试")
        queue.add(t)
        stats = queue.get_stats()
        assert "pending_count" in stats
        assert "fill_ratio" in stats


class TestTaskQueueStress:
    """阶段35: 队列压力测试。"""

    @pytest.fixture
    def queue(self):
        tmp_file = tempfile.mktemp(suffix=".json")
        q = TaskQueue(max_size=1000, save_path=tmp_file)
        yield q
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)

    def test_high_throughput(self, queue):
        """高吞吐量测试: 1000任务入队出队。"""
        start = time.time()

        # 批量入队
        for i in range(1000):
            t = Task(content=f"高吞吐任务{i}", priority=TaskPriority.NORMAL)
            queue.add(t)

        # 批量出队
        count = 0
        while queue.get():
            count += 1

        elapsed = time.time() - start
        print(f"\n高吞吐测试: {count}任务, {elapsed:.2f}秒, {count/elapsed:.0f}任务/秒")
        assert count == 1000
        assert elapsed < 5  # 5秒内完成

    def test_memory_stability(self, queue):
        """内存稳定性测试: 大量任务不会导致内存泄漏。"""
        initial_pending = queue.size()

        # 添加并处理大量任务
        for round_num in range(10):
            batch = [Task(content=f"内存测试{round_num}_{i}") for i in range(100)]
            queue.batch_add(batch)
            tasks = queue.batch_get(100)
            # 完成任务以清理
            for t in tasks:
                queue.complete_task(t.id)

        # 检查待处理队列大小回到初始状态
        assert queue.size() == initial_pending

    def test_concurrent_access(self, queue):
        """并发访问测试。"""
        from eternal_self_agent.exceptions import TaskDuplicateError

        results = {"added": 0, "got": 0}

        def producer(thread_id):
            for i in range(50):
                t = Task(content=f"并发任务{thread_id}_{i}")
                try:
                    if queue.add(t):
                        results["added"] += 1
                except TaskDuplicateError:
                    pass  # 重复任务忽略

        def consumer():
            for _ in range(50):
                if queue.get():
                    results["got"] += 1

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(2):
                futures.append(executor.submit(producer, i))
                futures.append(executor.submit(consumer))
            for f in futures:
                f.result()

        print(f"\n并发测试: 添加{results['added']}, 获取{results['got']}")
        assert results["added"] > 0

    def test_priority_stress(self, queue):
        """优先级压力测试: 混合优先级任务。"""
        priorities = [
            TaskPriority.LOW,
            TaskPriority.NORMAL,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL,
        ]

        # 添加200个任务，随机优先级
        for i in range(200):
            p = priorities[i % len(priorities)]
            t = Task(content=f"优先级任务{i}", priority=p)
            queue.add(t)

        # 验证优先级顺序
        prev_priority = float("inf")
        while True:
            t = queue.get()
            if t is None:
                break
            assert t.priority.value <= prev_priority
            prev_priority = t.priority.value

    def test_boundary_conditions(self, queue):
        """边界条件测试。"""
        # 空队列出队
        assert queue.get() is None

        # 单个任务
        t = Task(content="边界测试")
        queue.add(t)
        assert queue.size() == 1
        got = queue.get()
        assert got is not None
        assert queue.get() is None  # 再次出队为空

        # 队列满时丢弃低优先级
        small_queue = TaskQueue(max_size=2)
        small_queue.add(Task(content="low1", priority=TaskPriority.LOW))
        small_queue.add(Task(content="low2", priority=TaskPriority.LOW))
        # 添加高优先级应该成功（丢弃一个低优先级）
        assert small_queue.add(Task(content="high", priority=TaskPriority.HIGH))
