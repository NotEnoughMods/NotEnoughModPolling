ID = "say"
permission = 4

async def execute(self, name, params, channel, userdata, rank):
    print("Executing.. ")
    result = " ".join(params)
    print(result)
    await self.sendChatMessage(self.send, channel, result)
    