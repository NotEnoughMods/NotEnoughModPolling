ID = "say"
permission = 4


async def execute(self, name, params, channel, userdata, rank):
    print("Executing.. ")
    result = " ".join(params)
    print(result)
    await self.send_chat_message(self.send, channel, result)
