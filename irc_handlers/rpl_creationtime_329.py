import logging

ID = "329"

logger = logging.getLogger("irc.rpl.329")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("RPL_CREATIONTIME: %s %s", prefix, params)
