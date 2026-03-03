ID = "hardreload"
permission = 3


async def execute(self, name, params, channel, userdata, rank):
    await self.send_chat_message(self.send, channel, "Reloading..")
    self.protocol_handlers = self._load_modules("irc_handlers")
    await self.send_chat_message(self.send, channel, "Done!")
