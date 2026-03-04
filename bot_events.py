### BotEvents.py contains various kinds of Event Handlers
### For the moment, only Timer and Message events are used
import logging
import time
from timeit import default_timer


class EventAlreadyExists(Exception):
    def __init__(self, event_name):
        self.name = event_name

    def __str__(self):
        return self.name


class ChannelAlreadyExists(Exception):
    def __init__(self, chan_name):
        self.name = chan_name

    def __str__(self):
        return self.name


class StandardEvent:
    def __init__(self):
        self._events = {}
        self.operation_queue = []
        self.comes_from_event = False
        self._logger = logging.getLogger("Event")
        self.event_stats = {}

    def add_event(self, name, function, channel=None, from_event=False):
        if channel is None:
            channel = []
        if not self.comes_from_event:
            self._logger.debug("Adding event '%s' for channels '%s'", name, channel)
        else:
            self._logger.debug(
                "Adding event '%s' for channels '%s'; Used from inside an event",
                name,
                channel,
            )

        if not callable(function):
            raise TypeError(str(function) + " is not a callable function!")
        elif name in self._events:
            raise EventAlreadyExists(name)
        else:
            if not isinstance(channel, list):
                raise TypeError(str(channel) + " is " + str(type(channel)) + " but needs to be list!")

            if not self.comes_from_event:
                self._events[name] = {
                    "function": function,
                    "channels": list(channel),
                    "stats": {"average": None, "min": None, "max": None},
                }
            else:
                self.operation_queue.append(("add", name, function, channel))

    async def _execute_event(self, event_name, command_handler, *args, **kargs):
        start = default_timer()

        result = self._events[event_name]["function"](
            command_handler, self._events[event_name]["channels"], *args, **kargs
        )
        if hasattr(result, "__await__"):
            await result

        time_taken = default_timer() - start
        stats = self._events[event_name]["stats"]

        if stats["average"] is None:
            stats["average"] = time_taken
            stats["min"] = time_taken
            stats["max"] = time_taken
        else:
            stats["average"] = (stats["average"] + time_taken) / 2.0
            if time_taken < stats["min"]:
                stats["min"] = time_taken
            if time_taken > stats["max"]:
                stats["max"] = time_taken

    async def run_all_events(self, command_handler, *args, **kargs):
        self.comes_from_event = True
        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, command_handler, *args, **kargs)
        self.comes_from_event = False

        if len(self.operation_queue) > 0:
            for _i in range(len(self.operation_queue)):
                oper = self.operation_queue.pop(0)
                if oper[0] == "add":
                    name, function, channels = oper[1], oper[2], oper[3]
                    self._events[name] = {
                        "function": function,
                        "channels": list(channels),
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    name = oper[1]
                    del self._events[name]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    def remove_event(self, event, from_event=False):
        if not self.comes_from_event:
            self._logger.debug("Removing event '%s'", event)
        else:
            self._logger.debug("Removing event '%s'; Used from inside an event", event)

        if event in self._events:
            if not self.comes_from_event:
                del self._events[event]
            else:
                self.operation_queue.append(("del", event))
        else:
            raise KeyError("Trying to remove " + event + ", but it doesn't exist!")

    def event_exists(self, event):
        return event in self._events

    def add_channel(self, event_name, channel):
        self._logger.debug("Adding channels '%s' to event '%s'", channel, event_name)
        if event_name not in self._events:
            raise KeyError(str(event_name) + " does not exist!")
        else:
            if channel not in self._events[event_name]["channels"]:
                self._events[event_name]["channels"].append(channel)
            else:
                raise ChannelAlreadyExists(channel)

    def remove_channel(self, event_name, channel):
        self._logger.debug("Removing channel '%s' from event '%s'", channel, event_name)
        if event_name not in self._events:
            raise KeyError(str(event_name) + " does not exist!")
        else:
            self._events[event_name]["channels"].remove(channel)

    def get_channels(self, event_name):
        if event_name not in self._events:
            raise KeyError(str(event_name) + " does not exist!")
        else:
            return self._events[event_name]["channels"]


class TimerEvent(StandardEvent):
    def add_event(self, name, interval, function, channel=None, from_event=False):
        if channel is None:
            channel = []
        if not self.comes_from_event:
            self._logger.debug(
                "Adding time event '%s' for channels '%s' with interval = %s second(s)",
                name,
                channel,
                interval,
            )
        else:
            self._logger.debug(
                "Adding time event '%s' for channels '%s' with interval = %s second(s); Used from inside an event",
                name,
                channel,
                interval,
            )

        if not isinstance(interval, (int, float)):
            raise TypeError(str(interval) + " is not an integer/float!")
        elif interval < 0:
            raise ValueError(str(interval) + " is smaller than 0!")
        elif not callable(function):
            raise TypeError(str(function) + " is not a callable function!")
        elif name in self._events:
            raise EventAlreadyExists(name)
        else:
            if not isinstance(channel, list):
                raise TypeError(str(channel) + " is " + str(type(channel)) + " but needs to be list!")

            if not self.comes_from_event:
                self._events[name] = {
                    "time_interval": interval,
                    "function": function,
                    "last_exec_time": time.time(),
                    "channels": list(channel),
                    "stats": {"average": None, "min": None, "max": None},
                }
            else:
                self.operation_queue.append(("add", name, function, channel, interval, time.time()))

    async def run_all_events(self, command_handler):
        self.comes_from_event = True
        current_time = time.time()
        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, current_time, command_handler)
        self.comes_from_event = False

        if len(self.operation_queue) > 0:
            for _i in range(len(self.operation_queue)):
                oper = self.operation_queue.pop(0)

                if oper[0] == "add":
                    self._events[oper[1]] = {
                        "function": oper[2],
                        "channels": list(oper[3]),
                        "time_interval": oper[4],
                        "last_exec_time": oper[5],
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    del self._events[oper[1]]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    async def _execute_event(self, event_name, ntime, command_handler):
        last = self._events[event_name]["last_exec_time"]
        time_interval = self._events[event_name]["time_interval"]

        if ntime - last >= time_interval:
            start = default_timer()

            result = self._events[event_name]["function"](command_handler, self._events[event_name]["channels"])
            if hasattr(result, "__await__"):
                await result

            time_taken = default_timer() - start
            stats = self._events[event_name]["stats"]

            if stats["average"] is None:
                stats["average"] = time_taken
                stats["min"] = time_taken
                stats["max"] = time_taken
            else:
                stats["average"] = (stats["average"] + time_taken) / 2.0
                if time_taken < stats["min"]:
                    stats["min"] = time_taken
                if time_taken > stats["max"]:
                    stats["max"] = time_taken

            self._events[event_name]["last_exec_time"] = time.time()


class MsgEvent(StandardEvent):
    async def run_all_events(self, command_handler, userdata, message, channel):
        self.comes_from_event = True

        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, command_handler, userdata, message, channel)

        self.comes_from_event = False

        if len(self.operation_queue) > 0:
            for _i in range(len(self.operation_queue)):
                oper = self.operation_queue.pop(0)

                if oper[0] == "add":
                    self._events[oper[1]] = {
                        "function": oper[2],
                        "channels": list(oper[3]),
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    del self._events[oper[1]]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    async def _execute_event(self, event_name, command_handler, userdata, message, channel):
        start = default_timer()

        result = self._events[event_name]["function"](
            command_handler,
            self._events[event_name]["channels"],
            userdata,
            message,
            channel,
        )
        if hasattr(result, "__await__"):
            await result

        time_taken = default_timer() - start
        stats = self._events[event_name]["stats"]

        if stats["average"] is None:
            stats["average"] = time_taken
            stats["min"] = time_taken
            stats["max"] = time_taken
        else:
            stats["average"] = (stats["average"] + time_taken) / 2.0
            if time_taken < stats["min"]:
                stats["min"] = time_taken
            if time_taken > stats["max"]:
                stats["max"] = time_taken
