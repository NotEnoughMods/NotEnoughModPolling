ID = "topic"
permission = 2


async def execute(self, name, params, channel, userdata, rank):
    chan = (len(params) > 0 and params[0]) or channel
    try:
        await self.sendChatMessage(self.send, channel, self.channelData[chan]["Topic"])
    except KeyError:
        await self.sendChatMessage(self.send, channel, "Invalid channel name specified.")
