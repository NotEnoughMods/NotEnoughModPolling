ID = "topic"
permission = 2


async def execute(self, name, params, channel, userdata, rank):
    chan = (len(params) > 0 and params[0]) or channel
    try:
        await self.send_chat_message(self.send, channel, self.channel_data[chan]["Topic"])
    except KeyError:
        await self.send_chat_message(self.send, channel, "Invalid channel name specified.")
