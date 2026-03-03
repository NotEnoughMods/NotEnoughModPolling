import time

ID = "ERROR"

class ForceShutdown(Exception):
    def __init__(self, prefix, command, params):
        self.time = time.asctime()
        self.pref = prefix
        self.cmd = command
        self.params = params
    def __str__(self):
        return "Server is forcefully killing connection to bot: \n \
        Received command '{0}' with prefix '{1}' and params '{2}'.\n \
        Time: {3}".format(self.cmd, self.pref, self.params, self.time) 

def execute(self, sendMsg, prefix, command, params):
    print("~Server sent an ERROR packet~")
    print(prefix)
    print(params)
    raise ForceShutdown(prefix, command, params)


