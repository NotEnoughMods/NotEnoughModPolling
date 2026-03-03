ID = "oplist"
permission = 2


async def execute(self, name, params, channel, userdata, rank):
    if len(self.operators) > 0:
        await self.send_chat_message(
            self.send,
            channel,
            "The following users are Operators of this bot: " + ", ".join(self.operators),
        )
    if len(self.operators) == 0:
        await self.send_chat_message(self.send, channel, "Nobody is Operator of this bot!")
