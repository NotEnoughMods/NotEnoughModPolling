ID = "hardreload"
permission = 3


async def execute(self, name, params, channel, userdata, rank):
    await self.sendChatMessage(self.send, channel, "Reloading..")
    self.protocol_handlers = self.__LoadModules__("irc_handlers")
    await self.sendChatMessage(self.send, channel, "Done!")
