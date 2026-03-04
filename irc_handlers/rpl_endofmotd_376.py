import logging

ID = "376"

logger = logging.getLogger("irc.rpl.376")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("Channels to join: %s", self.channels)
    logger.info("End of MOTD, starting post-connection setup")
    await self.join_channel(send_msg, self.channels)

    for chan in self.channels:
        try:
            await self.wait_for(
                "366",
                check=lambda p, c, params, ch=chan: ch.lower() in params.lower(),
                timeout=30,
            )
        except TimeoutError:
            logger.warning("Timed out waiting for JOIN confirmation on %s", chan)

    await send_msg("MODE " + ",".join(self.channels), 4)
    for chan in self.channels:
        await send_msg("TOPIC " + chan, 4)

    if isinstance(self.auth, str):
        await send_msg(self.auth, 5)

    for cmd in self.commands:
        if self.commands[cmd][0].setup:
            await self.commands[cmd][0].setup(self, True)
