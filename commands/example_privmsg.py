ID = "ctest"
permission = 3
privmsgEnabled = True


async def execute(self, name, params, channel, userdata, rank, chan):
    if not chan:
        await self.send_chat_message(self.send, channel, "You are messaging me privately.")
    elif chan:
        await self.send_chat_message(self.send, channel, "You are messaging me from a channel.")
    else:
        await self.send_chat_message(self.send, channel, "waitwhat")
