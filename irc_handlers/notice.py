import logging

ID = "NOTICE"

logger = logging.getLogger("irc.notice")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("Notice: %s", params)
