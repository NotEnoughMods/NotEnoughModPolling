ID = "shutdown"
permission = 3


class Shutdown(Exception):
    def __init__(self, user, channel):
        self.name = user
        self.channel = channel
    def __str__(self):
        return "Bot is shutting down! The Shutdown was triggered by '{0}' in the channel '{1}'".format(self.name, self.channel) 



def execute(self, name, params, channel, userdata, rank):
    self.send("QUIT :Shutting down", 5)
    raise Shutdown(name, channel)