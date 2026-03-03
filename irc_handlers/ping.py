import logging

ID = "PING"

logger = logging.getLogger("irc.ping")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("Received PING: %s", params)

    derp = params.strip()
    derp[1:] if derp[0] == ":" else derp

    await sendMsg("PONG " + derp, 0)
