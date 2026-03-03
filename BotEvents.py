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
        self.__events__ = {}
        self.operationQueue = []
        self.comes_from_event = False
        self.__event_log__ = logging.getLogger("Event")
        self.eventStats = {}

    def addEvent(self, name, function, channel=None, from_event=False):
        if channel is None:
            channel = []
        if not self.comes_from_event:
            self.__event_log__.debug("Adding event '%s' for channels '%s'", name, channel)
        else:
            self.__event_log__.debug(
                "Adding event '%s' for channels '%s'; Used from inside an event",
                name,
                channel,
            )

        if not callable(function):
            raise TypeError(str(function) + " is not a callable function!")
        elif name in self.__events__:
            raise EventAlreadyExists(name)
        else:
            if not isinstance(channel, list):
                raise TypeError(str(channel) + " is " + str(type(channel)) + " but needs to be list!")

            if not self.comes_from_event:
                self.__events__[name] = {
                    "function": function,
                    "channels": list(channel),
                    "stats": {"average": None, "min": None, "max": None},
                }
            else:
                self.operationQueue.append(("add", name, function, channel))

    async def __execEvent__(self, eventName, commandHandler, *args, **kargs):
        start = default_timer()

        result = self.__events__[eventName]["function"](
            commandHandler, self.__events__[eventName]["channels"], *args, **kargs
        )
        if hasattr(result, "__await__"):
            await result

        timeTaken = default_timer() - start
        stats = self.__events__[eventName]["stats"]

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

    async def tryAllEvents(self, commandHandler, *args, **kargs):
        self.comes_from_event = True
        events_snapshot = list(self.__events__)
        for event in events_snapshot:
            if event in self.__events__:
                await self.__execEvent__(event, commandHandler, *args, **kargs)
        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)
                if oper[0] == "add":
                    name, function, channels = oper[1], oper[2], oper[3]
                    self.__events__[name] = {
                        "function": function,
                        "channels": list(channels),
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    name = oper[1]
                    del self.__events__[name]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    def removeEvent(self, event, from_event=False):
        if not self.comes_from_event:
            self.__event_log__.debug("Removing event '%s'", event)
        else:
            self.__event_log__.debug("Removing event '%s'; Used from inside an event", event)

        if event in self.__events__:
            if not self.comes_from_event:
                del self.__events__[event]
            else:
                self.operationQueue.append(("del", event))
        else:
            raise KeyError("Trying to remove " + event + ", but it doesn't exist!")

    def doesExist(self, event):
        return event in self.__events__

    def addChannel(self, eventName, channel):
        self.__event_log__.debug("Adding channels '%s' to event '%s'", channel, eventName)
        if eventName not in self.__events__:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            if channel not in self.__events__[eventName]["channels"]:
                self.__events__[eventName]["channels"].append(channel)
            else:
                raise ChannelAlreadyExists(channel)

    def removeChannel(self, eventName, channel):
        self.__event_log__.debug("Removing channel '%s' from event '%s'", channel, eventName)
        if eventName not in self.__events__:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            self.__events__[eventName]["channels"].remove(channel)

    def getChannels(self, eventName):
        if eventName not in self.__events__:
            raise KeyError(str(eventName) + " does not exist!")
        else:
            return self.__events__[eventName]["channels"]


class TimerEvent(StandardEvent):
    def addEvent(self, name, interval, function, channel=None, from_event=False):
        if channel is None:
            channel = []
        if not self.comes_from_event:
            self.__event_log__.debug(
                "Adding time event '%s' for channels '%s' with interval = %s second(s)",
                name,
                channel,
                interval,
            )
        else:
            self.__event_log__.debug(
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
        elif name in self.__events__:
            raise EventAlreadyExists(name)
        else:
            if not isinstance(channel, list):
                raise TypeError(str(channel) + " is " + str(type(channel)) + " but needs to be list!")

            if not self.comes_from_event:
                self.__events__[name] = {
                    "timeInterval": interval,
                    "function": function,
                    "lastExecTime": time.time(),
                    "channels": list(channel),
                    "stats": {"average": None, "min": None, "max": None},
                }
            else:
                self.operationQueue.append(("add", name, function, channel, interval, time.time()))

    async def tryAllEvents(self, commandHandler):
        self.comes_from_event = True
        currentTime = time.time()
        events_snapshot = list(self.__events__)
        for event in events_snapshot:
            if event in self.__events__:
                await self.__execEvent__(event, currentTime, commandHandler)
        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)

                if oper[0] == "add":
                    self.__events__[oper[1]] = {
                        "function": oper[2],
                        "channels": list(oper[3]),
                        "timeInterval": oper[4],
                        "lastExecTime": oper[5],
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    del self.__events__[oper[1]]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    async def __execEvent__(self, eventName, ntime, commandHandler):
        last = self.__events__[eventName]["lastExecTime"]
        timeInterval = self.__events__[eventName]["timeInterval"]

        if ntime - last >= timeInterval:
            start = default_timer()

            result = self.__events__[eventName]["function"](commandHandler, self.__events__[eventName]["channels"])
            if hasattr(result, "__await__"):
                await result

            timeTaken = default_timer() - start
            stats = self.__events__[eventName]["stats"]

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

            self.__events__[eventName]["lastExecTime"] = time.time()


class MsgEvent(StandardEvent):
    async def tryAllEvents(self, commandHandler, userdata, message, channel):
        self.comes_from_event = True

        events_snapshot = list(self.__events__)
        for event in events_snapshot:
            if event in self.__events__:
                await self.__execEvent__(event, commandHandler, userdata, message, channel)

        self.comes_from_event = False

        if len(self.operationQueue) > 0:
            for _i in range(len(self.operationQueue)):
                oper = self.operationQueue.pop(0)

                if oper[0] == "add":
                    self.__events__[oper[1]] = {
                        "function": oper[2],
                        "channels": list(oper[3]),
                        "stats": {"average": None, "min": None, "max": None},
                    }
                elif oper[0] == "del":
                    del self.__events__[oper[1]]
                else:
                    raise RuntimeError("Whaaat?!? It is neither add nor del? EXCEPTION")

    async def __execEvent__(self, eventName, commandHandler, userdata, message, channel):
        start = default_timer()

        result = self.__events__[eventName]["function"](
            commandHandler,
            self.__events__[eventName]["channels"],
            userdata,
            message,
            channel,
        )
        if hasattr(result, "__await__"):
            await result

        timeTaken = default_timer() - start
        stats = self.__events__[eventName]["stats"]

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
