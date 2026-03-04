import logging

ID = "461"

logger = logging.getLogger("irc.err.461")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("ERR_NEEDMOREPARAMS: %s %s", prefix, params)
