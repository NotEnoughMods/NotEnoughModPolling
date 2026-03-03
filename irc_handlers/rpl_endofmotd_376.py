import logging

ID = "376"


async def execute(self, sendMsg, prefix, command, params):
    print(self.channels)
    logging.info("End of MotD: 376. If you see 'MotD is missing: 422', please notify the author of the bot.")
    await self.join_channel(sendMsg, self.channels)

    await sendMsg("MODE " + ",".join(self.channels), 4)
    for chan in self.channels:
        await sendMsg("TOPIC " + chan, 4)

    if isinstance(self.auth, str):
        await sendMsg(self.auth, 5)

    for cmd in self.commands:
        if self.commands[cmd][0].setup:
            await self.commands[cmd][0].setup(self, True)
