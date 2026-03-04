import logging

ID = "502"

logger = logging.getLogger("irc.err.502")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("ERR_USERSDONTMATCH: %s %s", prefix, params)
