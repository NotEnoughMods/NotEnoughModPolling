class PluginModule:
    def __init__(self):
        self._plugins = {}

    def LoadPlugins(self, directory):
        pass


class Plugin:
    def __init__(self):
        self._events = {}
        self._commands = {}
        self._threads = {}

    def addCommand(self, cmdname, rank, function):
        pass

    def addEvent(self, eventType, eventFunction, *args):
        pass

    def addThread(self, threadName, function):
        pass
