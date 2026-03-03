import logging

ID = "366"

logger = logging.getLogger("irc.rpl.366")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("RPL_ENDOFNAMES: %s %s", prefix, params)
