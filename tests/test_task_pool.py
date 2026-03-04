import asyncio
from unittest.mock import MagicMock

import pytest

from task_pool import FunctionNameAlreadyExists, TaskHandle, TaskPool


class TestTaskHandle:
    def test_set_stop_timer(self):
        handle = TaskHandle("test", MagicMock(), asyncio.Queue())
        handle.set_timer()
        handle.stop_timer()
        assert handle.time_delta is not None
        assert handle.time_delta >= 0

    def test_stop_timer_without_start_raises(self):
        handle = TaskHandle("test", MagicMock(), asyncio.Queue())
        with pytest.raises(RuntimeError):
            handle.stop_timer()

    def test_get_time_diff_without_start_raises(self):
        handle = TaskHandle("test", MagicMock(), asyncio.Queue())
        with pytest.raises(RuntimeError):
            handle.get_time_diff()

    def test_time_delta_none_before_stop(self):
        handle = TaskHandle("test", MagicMock(), asyncio.Queue())
        assert handle.time_delta is None


class TestTaskPool:
    async def test_add_task_and_check_status(self):
        pool = TaskPool()

        async def worker(handle, queue):
            await asyncio.sleep(10)

        pool.add_task("test", worker)
        exists, running = pool.check_status("test")
        assert exists is True
        assert running is True
        pool.cancel_all()

    async def test_duplicate_name_raises(self):
        pool = TaskPool()

        async def worker(handle, queue):
            await asyncio.sleep(10)

        pool.add_task("test", worker)
        with pytest.raises(FunctionNameAlreadyExists):
            pool.add_task("test", worker)
        pool.cancel_all()

    async def test_cancel_task(self):
        pool = TaskPool()

        async def worker(handle, queue):
            await asyncio.sleep(10)

        pool.add_task("test", worker)
        pool.cancel_task("test")
        exists, _ = pool.check_status("test")
        assert exists is False

    async def test_cancel_all(self):
        pool = TaskPool()

        async def worker(handle, queue):
            await asyncio.sleep(10)

        pool.add_task("a", worker)
        pool.add_task("b", worker)
        pool.cancel_all()
        assert pool.check_status("a") == (False, None)
        assert pool.check_status("b") == (False, None)

    async def test_send_recv(self):
        pool = TaskPool()
        received = []

        async def worker(handle, queue):
            msg = await queue.get()
            received.append(msg)

        pool.add_task("test", worker)
        await pool.send("test", "hello")
        # Give the task a moment to process
        await asyncio.sleep(0.05)
        assert received == ["hello"]
        pool.cancel_all()

    async def test_poll_empty_vs_nonempty(self):
        pool = TaskPool()

        async def worker(handle, queue):
            await asyncio.sleep(10)

        pool.add_task("test", worker)
        assert pool.poll("test") is False
        await pool.send("test", "data")
        assert pool.poll("test") is True
        pool.cancel_all()

    async def test_exception_in_task_reported_via_queue(self):
        pool = TaskPool()

        async def bad_worker(handle, queue):
            raise ValueError("boom")

        pool.add_task("test", bad_worker)
        # Wait for the task to crash and report
        await asyncio.sleep(0.05)
        msg = await pool.recv("test")
        assert msg["action"] == "exceptionOccured"
        assert isinstance(msg["exception"], ValueError)
        pool.cancel_all()
