### BotEvents.py contains various kinds of Event Handlers
### For the moment, only Timer and Message events are used
import logging
import time
from timeit import default_timer


class EventAlreadyExists(Exception):
    def __init__(self, eventName):
        self.name = eventName

    def __str__(self):
        return self.name


class ChannelAlreadyExists(Exception):
    def __init__(self, chanName):
        self.name = chanName

    def __str__(self):
        return self.name


class StandardEvent:
    def __init__(self):
        self._events = {}
        self.operationQueue = []
        self.comes_from_event = False
        self._logger = logging.getLogger("Event")
        self.eventStats = {}

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
                self.operationQueue.append(("add", name, function, channel))

    async def _execute_event(self, eventName, commandHandler, *args, **kargs):
        start = default_timer()

        result = self._events[eventName]["function"](
            commandHandler, self._events[eventName]["channels"], *args, **kargs
        )
        if hasattr(result, "__await__"):
            await result

        timeTaken = default_timer() - start
        stats = self._events[eventName]["stats"]

        if stats["average"] is None:
            stats["average"] = timeTaken
            stats["min"] = timeTaken
            stats["max"] = timeTaken
        else:
            stats["average"] = (stats["average"] + timeTaken) / 2.0
            if timeTaken < stats["min"]:
                stats["min"] = timeTaken
            if timeTaken > stats["max"]:
                stats["max"] = timeTaken

    async def run_all_events(self, commandHandler, *args, **kargs):
        self.comes_from_event = True
        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, commandHandler, *args, **kargs)
        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)
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
                self.operationQueue.append(("del", event))
        else:
            raise KeyError("Trying to remove " + event + ", but it doesn't exist!")

    def event_exists(self, event):
        return event in self._events

    def add_channel(self, eventName, channel):
        self._logger.debug("Adding channels '%s' to event '%s'", channel, eventName)
        if eventName not in self._events:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            if channel not in self._events[eventName]["channels"]:
                self._events[eventName]["channels"].append(channel)
            else:
                raise ChannelAlreadyExists(channel)

    def remove_channel(self, eventName, channel):
        self._logger.debug("Removing channel '%s' from event '%s'", channel, eventName)
        if eventName not in self._events:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            self._events[eventName]["channels"].remove(channel)

    def get_channels(self, eventName):
        if eventName not in self._events:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            return self._events[eventName]["channels"]


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
                    "timeInterval": interval,
                    "function": function,
                    "lastExecTime": time.time(),
                    "channels": list(channel),
                    "stats": {"average": None, "min": None, "max": None},
                }
            else:
                self.operationQueue.append(("add", name, function, channel, interval, time.time()))

    async def run_all_events(self, commandHandler):
        self.comes_from_event = True
        currentTime = time.time()
        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, currentTime, commandHandler)
        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)

                if oper[0] == "add":
                    self._events[oper[1]] = {
                        "function": oper[2],
                        "channels": list(oper[3]),
                        "timeInterval": oper[4],
                        "lastExecTime": oper[5],
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    del self._events[oper[1]]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    async def _execute_event(self, eventName, ntime, commandHandler):
        last = self._events[eventName]["lastExecTime"]
        timeInterval = self._events[eventName]["timeInterval"]

        if ntime - last >= timeInterval:
            start = default_timer()

            result = self._events[eventName]["function"](commandHandler, self._events[eventName]["channels"])
            if hasattr(result, "__await__"):
                await result

            timeTaken = default_timer() - start
            stats = self._events[eventName]["stats"]

            if stats["average"] is None:
                stats["average"] = timeTaken
                stats["min"] = timeTaken
                stats["max"] = timeTaken
            else:
                stats["average"] = (stats["average"] + timeTaken) / 2.0
                if timeTaken < stats["min"]:
                    stats["min"] = timeTaken
                if timeTaken > stats["max"]:
                    stats["max"] = timeTaken

            self._events[eventName]["lastExecTime"] = time.time()


class MsgEvent(StandardEvent):
    async def run_all_events(self, commandHandler, userdata, message, channel):
        self.comes_from_event = True

        events_snapshot = list(self._events)
        for event in events_snapshot:
            if event in self._events:
                await self._execute_event(event, commandHandler, userdata, message, channel)

        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)

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

    async def _execute_event(self, eventName, commandHandler, userdata, message, channel):
        start = default_timer()

        result = self._events[eventName]["function"](
            commandHandler,
            self._events[eventName]["channels"],
            userdata,
            message,
            channel,
        )
        if hasattr(result, "__await__"):
            await result

        timeTaken = default_timer() - start
        stats = self._events[eventName]["stats"]

        if stats["average"] is None:
            stats["average"] = timeTaken
            stats["min"] = timeTaken
            stats["max"] = timeTaken
        else:
            stats["average"] = (stats["average"] + timeTaken) / 2.0
            if timeTaken < stats["min"]:
                stats["min"] = timeTaken
            if timeTaken > stats["max"]:
                stats["max"] = timeTaken
