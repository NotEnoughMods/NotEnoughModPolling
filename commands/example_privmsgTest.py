ID = "ctest"
permission = 3
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    if not chan:
        await self.sendChatMessage(self.send, channel,"You are messaging me privately.")
    elif chan:
        await self.sendChatMessage(self.send, channel,"You are messaging me from a channel.")
    else:
        await self.sendChatMessage(self.send, channel,"waitwhat")