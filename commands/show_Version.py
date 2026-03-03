ID = "version"
permission = 0

async def execute(self, name, params, channel, userdata, rank):
    await self.sendChatMessage(self.send, channel, "Yoshi2's IRC Bot v0.3")