ID = "hardreload"
permission = 3

def execute(self, name, params, channel, userdata, rank):
    self.sendChatMessage(self.send, channel, "Reloading..")
    self.Plugin = self.__LoadModules__("IRCpackets")
    self.sendChatMessage(self.send, channel, "Done!")