ID = "ctest"
permission = 3
privmsgEnabled = True


def execute(self, name, params, channel, userdata, rank, chan):
    if chan == False:
        self.sendChatMessage(self.send, channel,"You are messaging me privately.")
    elif chan == True:
        self.sendChatMessage(self.send, channel,"You are messaging me from a channel.")
    else:
        self.sendChatMessage(self.send, channel,"waitwhat")