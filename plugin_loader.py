class PluginModule:
    def __init__(self):
        self._plugins = {}

    def LoadPlugins(self, directory):
        pass


class Plugin:
    def __init__(self):
        self._events = {}
        self._commands = {}
        self._tasks = {}

    def add_command(self, cmdname, rank, function):
        pass

    def add_event(self, eventType, eventFunction, *args):
        pass

    def add_task(self, task_name, function):
        pass
