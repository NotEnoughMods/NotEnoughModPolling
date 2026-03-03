ID = "topic"
permission = 2

def execute(self, name, params, channel, userdata, rank):
    chan = len(params) > 0 and params[0] or channel
    try:
        self.sendChatMessage(self.send, channel, self.channelData[chan]["Topic"])
    except KeyError:
        self.sendChatMessage(self.send, channel, "Invalid channel name specified.")
    