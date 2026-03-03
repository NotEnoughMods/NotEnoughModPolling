import asyncio
import logging
import traceback
from timeit import default_timer

_task_logger = logging.getLogger("TaskPoolExceptions")


class FunctionNameAlreadyExists(Exception):
    def __init__(self, eventName):
        self.name = eventName

    def __str__(self):
        return self.name


class TaskHandle:
    def __init__(self, name, task, queue):
        self.name = name
        self.task = task
        self.queue = queue
        self.signal = False
        self.running = True
        self._startTime = None
        self._lastTimeRunning = None
        self._metadata = {}

    def setTimer(self):
        self._startTime = default_timer()

    def stopTimer(self):
        if self._startTime is None:
            raise RuntimeError("Can't stop the timer if it hasn't been started yet.")
        self._lastTimeRunning = default_timer() - self._startTime
        self._startTime = None

    def getTimeDiff(self):
        if self._startTime is None:
            raise RuntimeError("Can't get time difference if timer hasn't been started yet.")
        return default_timer() - self._startTime

    @property
    def timeDelta(self):
        return self._lastTimeRunning


class TaskPool:
    def __init__(self):
        self.pool = {}
        self._logger = logging.getLogger("TaskPool")

    def add_task(self, name, function, baseReference=None):
        if name in self.pool:
            raise FunctionNameAlreadyExists("The name is already used by a different task function!")

        queue = asyncio.Queue()
        handle = None

        async def _wrapper():
            try:
                handle.running = True
                await function(handle, queue)
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
        handle = TaskHandle(name, task, queue)
        self.pool[name] = {"handle": handle, "queue": queue}
        self._logger.debug("New task '%s' started", name)

    def cancel_task(self, name):
        handle = self.pool[name]["handle"]
        handle.signal = True
        handle.task.cancel()
        del self.pool[name]
        self._logger.debug("Cancelling task '%s'", name)

    async def send(self, name, obj):
        await self.pool[name]["queue"].put(obj)

    async def recv(self, name):
        return await self.pool[name]["queue"].get()

    def poll(self, name, timeout=0.0):
        return not self.pool[name]["queue"].empty()

    def check_status(self, name):
        if name not in self.pool:
            return False, None
        isRunning = self.pool[name]["handle"].running
        return True, isRunning

    def cancel_all(self):
        self._logger.debug("Cancelling all running tasks")
        names = list(self.pool.keys())
        for name in names:
            handle = self.pool[name]["handle"]
            handle.signal = True
            handle.task.cancel()
            del self.pool[name]
        self._logger.debug("All tasks cancelled")
