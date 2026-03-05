import asyncio
import logging

ID = "422"

logger = logging.getLogger("irc.err.422")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("Channels to join: %s", self.channels)
    logger.info("No MOTD (422), starting post-connection setup")
    await self.join_channel(send_msg, self.channels)

    results = await asyncio.gather(
        *(
            self.wait_for(
                "366",
                check=lambda p, c, params, ch=chan: ch.lower() in params.lower(),
                timeout=30,
            )
            for chan in self.channels
        ),
        return_exceptions=True,
    )
    for chan, result in zip(self.channels, results):
        if isinstance(result, TimeoutError):
            logger.warning("Timed out waiting for JOIN confirmation on %s", chan)

    await send_msg("MODE " + ",".join(self.channels), 4)
    for chan in self.channels:
        await send_msg("TOPIC " + chan, 4)

    if isinstance(self.auth, str):
        await send_msg(self.auth, 5)

    for _plugin_id, plugin in self.plugins.items():
        if plugin.setup:
            await plugin.setup(self, True)
