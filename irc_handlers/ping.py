import logging

ID = "PING"

logger = logging.getLogger("irc.ping")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("Received PING: %s", params)

    derp = params.strip()
    derp[1:] if derp[0] == ":" else derp

    await send_msg("PONG " + derp, 0)
