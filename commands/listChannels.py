ID = "channels"
permission = 3
privmsgEnabled = True

def execute(self, name, params, channel, userdata, rank, chan):
    channels = ", ".join(self.channelData.keys())
    self.sendNotice(name, "I'm currently connected to the following channels: {0}".format(channels))