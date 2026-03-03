ID = "hardreload"
permission = 3

async def execute(self, name, params, channel, userdata, rank):
    await self.sendChatMessage(self.send, channel, "Reloading..")
    self.Plugin = self.__LoadModules__("IRCpackets")
    await self.sendChatMessage(self.send, channel, "Done!")