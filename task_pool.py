import asyncio
import logging
import traceback
from timeit import default_timer

_task_logger = logging.getLogger("TaskPoolExceptions")


class FunctionNameAlreadyExists(Exception):
    def __init__(self, event_name):
        self.name = event_name

    def __str__(self):
        return self.name


class TaskHandle:
    def __init__(self, name, task, queue, base=None):
        self.name = name
        self.task = task
        self.queue = queue
        self.base = base
        self.running = True
        self._start_time = None
        self._last_time_running = None

    def set_timer(self):
        self._start_time = default_timer()

    def stop_timer(self):
        if self._start_time is None:
            raise RuntimeError("Can't stop the timer if it hasn't been started yet.")
        self._last_time_running = default_timer() - self._start_time
        self._start_time = None

    def get_time_diff(self):
        if self._start_time is None:
            raise RuntimeError("Can't get time difference if timer hasn't been started yet.")
        return default_timer() - self._start_time

    @property
    def time_delta(self):
        return self._last_time_running


class TaskPool:
    def __init__(self):
        self.pool = {}
        self._logger = logging.getLogger("TaskPool")

    def add_task(self, name, function, base_reference=None):
        if name in self.pool:
            raise FunctionNameAlreadyExists("The name is already used by a different task function!")

        queue = asyncio.Queue()
        handle = None

        async def _wrapper():
            try:
                handle.running = True
                await function(handle, queue)
            except asyncio.QueueShutDown:
                self._logger.debug("Task '%s' stopped via queue shutdown", name)
            except Exception as error:
                exception = traceback.format_exc()
                await queue.put(
                    {
                        "action": "exceptionOccured",
                        "exception": error,
                        "functionName": name,
                        "traceback": exception,
                    }
                )
                _task_logger.warning("Task '%s' crashed! Exception follows.", name)
                _task_logger.exception("Task exception of '%s':", name)
            finally:
                handle.running = False

        task = asyncio.create_task(_wrapper())
        handle = TaskHandle(name, task, queue, base=base_reference)
        self.pool[name] = {"handle": handle, "queue": queue}
        self._logger.debug("New task '%s' started", name)

    def cancel_task(self, name):
        handle = self.pool[name]["handle"]
        handle.queue.shutdown(immediate=True)
        handle.task.cancel()
        del self.pool[name]
        self._logger.debug("Cancelling task '%s'", name)

    async def send(self, name, obj):
        await self.pool[name]["queue"].put(obj)

    async def recv(self, name):
        return await self.pool[name]["queue"].get()

    def poll(self, name):
        return not self.pool[name]["queue"].empty()

    def check_status(self, name):
        if name not in self.pool:
            return False, None
        is_running = self.pool[name]["handle"].running
        return True, is_running

    def cancel_all(self):
        self._logger.debug("Cancelling all running tasks")
        names = list(self.pool.keys())
        for name in names:
            handle = self.pool[name]["handle"]
            handle.queue.shutdown(immediate=True)
            handle.task.cancel()
            del self.pool[name]
        self._logger.debug("All tasks cancelled")
