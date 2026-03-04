import logging

ID = "403"

logger = logging.getLogger("irc.err.403")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("ERR_NOSUCHCHANNEL: %s %s", prefix, params)
