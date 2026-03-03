ID = "channels"
permission = 3
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    channels = ", ".join(self.channelData.keys())
    await self.sendNotice(name, f"I'm currently connected to the following channels: {channels}")
