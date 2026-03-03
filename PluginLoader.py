


class PluginModule():
    def __init__(self):
        self.__plugins__ = {}
        
    def LoadPlugins(self, directory):
        pass
    
class Plugin():
    def __init__(self):
        self.__events__ = {}
        self.__commands__ = {}
        self.__threads__ = {}
    
    def addCommand(self, cmdname, rank, function):
        pass
    
    def addEvent(self, eventType, eventFunction, *args):
        pass
    
    def addThread(self, threadName, function):
        pass