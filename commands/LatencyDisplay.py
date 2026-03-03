ID = "latency"
permission = 2
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    if self.latency != None:
        latency = round(self.latency, 2)
        await self.sendChatMessage(self.send, channel, "My current latency is {0} seconds.".format(latency))
    else:
        await self.send("NOTICE {0} :Please wait a bit so I can measure the latency.".format(name))