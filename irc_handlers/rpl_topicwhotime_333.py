import logging

ID = "333"

logger = logging.getLogger("irc.rpl.333")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("RPL_TOPICWHOTIME: %s %s", prefix, params)
