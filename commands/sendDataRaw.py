ID = "raw"
permission = 3

async def execute(self, name, params, channel, userdata, rank):
    await self.send(" ".join(params), 4)