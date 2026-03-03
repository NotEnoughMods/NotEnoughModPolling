ID = "version"
permission = 0


async def execute(self, name, params, channel, userdata, rank):
    await self.send_chat_message(self.send, channel, "Yoshi2's IRC Bot v0.3")
