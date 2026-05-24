"""
任务队列系统 — 自驱公理核心载体

设计意图: 有限容量、优先级调度、去重机制、持久化支持。
零外部依赖，全本地文件持久化。

公理溯源:
  - 自驱公理: 知识推演自动生成任务入队
  - 存续公理: 队列满时丢弃低优先级任务，防止内存无限膨胀
  - 资源守恒公理: TASK_QUEUE_MAX限制任务池上限
"""

from __future__ import annotations

import heapq
import logging
import os
from collections import deque
from typing import Any, Iterator

from eternal_self_agent.constants import TASK_QUEUE_MAX, TASK_QUEUE_SAVE_PATH
from eternal_self_agent.exceptions import TaskDuplicateError
from eternal_self_agent.task.task import Task, TaskStatus
from eternal_self_agent.utils import atomic_write_json, now_timestamp, safe_read_json

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    有限容量优先级任务队列。

    核心设计:
      - _queue: 优先队列（堆），按优先级排序
      - _tasks: 任务字典 {task_id: Task}
      - _content_hashes: 内容哈希集合（去重用）
      - _dead_letter: 死信队列（失败任务）

    公理溯源:
      - 自驱公理: 知识推演任务自动入队
      - 资源守恒: 容量限制，满时丢弃低优先级
    """

    def __init__(
        self, max_size: int = TASK_QUEUE_MAX, save_path: str | None = None
    ) -> None:
        """
        初始化任务队列。

        Args:
            max_size: 队列最大容量
            save_path: 持久化文件路径
        """
        self.max_size = max_size
        self.save_path = save_path or TASK_QUEUE_SAVE_PATH

        # 核心数据结构
        self._queue: list[tuple[int, float, str]] = (
            []
        )  # (priority_neg, created_at, task_id)
        self._tasks: dict[str, Task] = {}  # task_id -> Task
        self._content_hashes: set[str] = set()  # 去重用
        self._dead_letter: deque[Task] = deque(maxlen=100)  # 死信队列

        # 统计
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._total_dropped = 0

        # 加载已有数据
        self.load()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段27: 基础入队出队
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add(self, task: Task, *, skip_duplicate_check: bool = False) -> bool:
        """
        添加任务到队列。

        Args:
            task: 要添加的任务
            skip_duplicate_check: 是否跳过重复检查

        Returns:
            是否成功添加

        Raises:
            TaskDuplicateError: 检测到重复任务
        """
        # 阶段31: 去重检查
        if not skip_duplicate_check and task._content_hash in self._content_hashes:
            logger.debug("任务重复，跳过: %s", task.content[:30])
            raise TaskDuplicateError(f"任务已存在: {task.content[:30]}")

        # 检查容量
        if len(self._tasks) >= self.max_size:
            # 尝试丢弃最低优先级任务
            if not self._drop_lowest_priority(task.priority.value):
                logger.warning("队列已满，无法添加任务: %s", task.content[:30])
                self._total_dropped += 1
                return False

        # 添加到队列
        task_id = task.id
        self._tasks[task_id] = task
        self._content_hashes.add(task._content_hash)

        # 堆插入（优先级取负，实现大顶堆）
        heapq.heappush(self._queue, (-task.priority.value, task.created_at, task_id))

        self._total_submitted += 1
        logger.debug(
            "任务入队: %s (priority=%d)", task.content[:30], task.priority.value
        )
        return True

    def get(self) -> Task | None:
        """
        获取并移除最高优先级任务。

        Returns:
            任务对象，队列为空返回None
        """
        while self._queue:
            _, _, task_id = heapq.heappop(self._queue)
            task = self._tasks.get(task_id)

            if task is None:
                # 任务已被删除
                continue

            if task.status != TaskStatus.PENDING:
                # 任务状态已改变
                continue

            # 检查是否过期
            if task.is_expired():
                task.cancel()
                self._remove_task(task_id)
                continue

            # 标记为执行中
            task.start()
            return task

        return None

    def peek(self) -> Task | None:
        """查看最高优先级任务（不移除）。"""
        for priority_neg, created_at, task_id in self._queue:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING and not task.is_expired():
                return task
        return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段28: 优先级队列
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _drop_lowest_priority(self, new_priority: int) -> bool:
        """
        丢弃最低优先级任务以腾出空间。

        Args:
            new_priority: 新任务的优先级

        Returns:
            是否成功腾出空间
        """
        if not self._queue:
            return False

        # 找到最低优先级任务（堆中最大负值的最小值）
        lowest_priority = float("inf")
        lowest_task_id = None

        for priority_neg, _, task_id in self._queue:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                priority = -priority_neg
                if priority < lowest_priority:
                    lowest_priority = priority
                    lowest_task_id = task_id

        # 如果新任务优先级更高，丢弃最低优先级任务
        if lowest_task_id and new_priority > lowest_priority:
            self._remove_task(lowest_task_id)
            logger.debug("丢弃低优先级任务 (priority=%d)", lowest_priority)
            self._total_dropped += 1
            return True

        return False

    def reprioritize(self, task_id: str, new_priority: int) -> bool:
        """
        动态调整任务优先级。

        Args:
            task_id: 任务ID
            new_priority: 新优先级

        Returns:
            是否成功调整
        """
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        # 移除旧条目
        self._remove_from_heap(task_id)

        # 更新优先级
        task.priority = new_priority  # type: ignore

        # 重新入队
        heapq.heappush(self._queue, (-task.priority.value, task.created_at, task_id))

        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段29: 状态管理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def complete_task(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        """标记任务完成。"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.complete(result)
        self._total_completed += 1
        self._remove_task(task_id, keep_in_memory=True)
        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败，尝试重试。"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.fail(error)

        # 尝试重入队重试
        if task.can_retry():
            task.retry()
            self._requeue_task(task_id)
            logger.debug("任务重试: %s (retry=%d)", task.content[:30], task.retry_count)
        else:
            self._total_failed += 1
            self._move_to_dead_letter(task)
            self._remove_task(task_id)

        return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务。"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.cancel()
        self._remove_task(task_id)
        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段30: 持久化
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def save(self) -> bool:
        """保存队列状态到文件。"""
        try:
            data = {
                "tasks": [task.to_dict() for task in self._tasks.values()],
                "dead_letter": [task.to_dict() for task in self._dead_letter],
                "stats": {
                    "total_submitted": self._total_submitted,
                    "total_completed": self._total_completed,
                    "total_failed": self._total_failed,
                    "total_dropped": self._total_dropped,
                },
                "saved_at": now_timestamp(),
            }
            atomic_write_json(self.save_path, data)
            logger.debug("队列保存成功: %s", self.save_path)
            return True
        except Exception as e:
            logger.error("队列保存失败: %s", e)
            return False

    def load(self) -> bool:
        """从文件加载队列状态。"""
        if not os.path.isfile(self.save_path):
            return False

        try:
            data = safe_read_json(self.save_path)
            if not data:
                return False

            # 加载任务
            for task_data in data.get("tasks", []):
                task = Task.from_dict(task_data)
                if task.status == TaskStatus.PENDING:
                    self._tasks[task.id] = task
                    self._content_hashes.add(task._content_hash)
                    heapq.heappush(
                        self._queue, (-task.priority.value, task.created_at, task.id)
                    )

            # 加载死信队列
            for task_data in data.get("dead_letter", []):
                task = Task.from_dict(task_data)
                self._dead_letter.append(task)

            # 加载统计
            stats = data.get("stats", {})
            self._total_submitted = stats.get("total_submitted", 0)
            self._total_completed = stats.get("total_completed", 0)
            self._total_failed = stats.get("total_failed", 0)
            self._total_dropped = stats.get("total_dropped", 0)

            logger.info("队列加载成功: %d 任务", len(self._tasks))
            return True

        except Exception as e:
            logger.error("队列加载失败: %s", e)
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段31: 去重机制
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def is_duplicate(self, task: Task) -> bool:
        """检查任务是否重复。"""
        return task._content_hash in self._content_hashes

    def get_duplicate_count(self) -> int:
        """获取重复任务数量（用于统计）。"""
        # 实际重复任务不会被加入队列，这里返回0
        # 如需统计，需要在add方法中计数
        return 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段32: 超时处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_timeouts(self) -> list[str]:
        """
        检查并处理超时任务。

        Returns:
            超时任务ID列表
        """
        timed_out = []

        for task in self._tasks.values():
            if task.is_running() and task.is_timed_out():
                task.mark_timeout()
                timed_out.append(task.id)

                # 尝试重试
                if task.can_retry():
                    task.retry()
                    self._requeue_task(task.id)
                else:
                    self._total_failed += 1
                    self._move_to_dead_letter(task)
                    self._remove_task(task.id)

        if timed_out:
            logger.debug("检测到 %d 个超时任务", len(timed_out))

        return timed_out

    def get_dead_letter_tasks(self) -> list[Task]:
        """获取死信队列中的任务。"""
        return list(self._dead_letter)

    def clear_dead_letter(self) -> int:
        """清空死信队列，返回清除数量。"""
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段33: 批处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def batch_add(self, tasks: list[Task]) -> tuple[int, int]:
        """
        批量添加任务。

        Args:
            tasks: 任务列表

        Returns:
            (成功数量, 失败/重复数量)
        """
        success = 0
        failed = 0

        for task in tasks:
            try:
                if self.add(task):
                    success += 1
                else:
                    failed += 1
            except TaskDuplicateError:
                failed += 1

        return success, failed

    def batch_get(self, max_count: int = 10) -> list[Task]:
        """
        批量获取任务。

        Args:
            max_count: 最大获取数量

        Returns:
            任务列表
        """
        tasks = []
        for _ in range(max_count):
            task = self.get()
            if task is None:
                break
            tasks.append(task)
        return tasks

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 阶段34: 队列监控
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def size(self) -> int:
        """获取队列中待处理任务数量。"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)

    def __len__(self) -> int:
        """返回队列中所有任务数量。"""
        return len(self._tasks)

    def is_empty(self) -> bool:
        """检查队列是否为空。"""
        return self.size() == 0

    def is_full(self) -> float:
        """返回队列填充比例。"""
        return len(self._tasks) / self.max_size

    def get_stats(self) -> dict[str, Any]:
        """获取队列统计信息。"""
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

        # 平均等待时间
        wait_times = [
            t.get_wait_time()
            for t in self._tasks.values()
            if t.status == TaskStatus.PENDING
        ]
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0

        return {
            "pending_count": pending,
            "running_count": running,
            "total_count": len(self._tasks),
            "dead_letter_count": len(self._dead_letter),
            "max_size": self.max_size,
            "fill_ratio": round(self.is_full(), 4),
            "avg_wait_time": round(avg_wait_time, 2),
            "total_submitted": self._total_submitted,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "total_dropped": self._total_dropped,
        }

    def get_pending_tasks(self) -> list[Task]:
        """获取所有待处理任务。"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_running_tasks(self) -> list[Task]:
        """获取所有执行中任务。"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 内部方法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _remove_task(self, task_id: str, keep_in_memory: bool = False) -> None:
        """移除任务。"""
        task = self._tasks.get(task_id)
        if task:
            self._content_hashes.discard(task._content_hash)
            if not keep_in_memory:
                del self._tasks[task_id]

    def _remove_from_heap(self, task_id: str) -> None:
        """从堆中移除任务（标记删除）。"""
        # 堆不支持直接删除，采用惰性删除策略
        # 实际删除在get()时处理
        pass

    def _requeue_task(self, task_id: str) -> None:
        """重新入队任务。"""
        task = self._tasks.get(task_id)
        if task:
            heapq.heappush(
                self._queue, (-task.priority.value, task.created_at, task_id)
            )

    def _move_to_dead_letter(self, task: Task) -> None:
        """移动任务到死信队列。"""
        self._dead_letter.append(task)
        logger.debug("任务移入死信队列: %s", task.content[:30])

    def __iter__(self) -> Iterator[Task]:
        """迭代所有任务。"""
        return iter(self._tasks.values())

    def __repr__(self) -> str:
        return f"TaskQueue(pending={self.size()}, max={self.max_size})"
