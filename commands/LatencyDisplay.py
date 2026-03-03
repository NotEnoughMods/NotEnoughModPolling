ID = "latency"
permission = 2
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    if self.latency is not None:
        latency = round(self.latency, 2)
        await self.sendChatMessage(self.send, channel, f"My current latency is {latency} seconds.")
    else:
        await self.send(f"NOTICE {name} :Please wait a bit so I can measure the latency.")
