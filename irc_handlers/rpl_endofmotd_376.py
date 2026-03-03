import logging

ID = "376"

logger = logging.getLogger("irc.rpl.376")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("Channels to join: %s", self.channels)
    logger.info("End of MOTD, starting post-connection setup")
    await self.join_channel(sendMsg, self.channels)

    await sendMsg("MODE " + ",".join(self.channels), 4)
    for chan in self.channels:
        await sendMsg("TOPIC " + chan, 4)

    if isinstance(self.auth, str):
        await sendMsg(self.auth, 5)

    for cmd in self.commands:
        if self.commands[cmd][0].setup:
            await self.commands[cmd][0].setup(self, True)
