import logging

ID = "421"

logger = logging.getLogger("irc.err.421")


async def execute(self, sendMsg, msgprefix, command, params):
    logger.debug("ERR_UNKNOWNCOMMAND: %s %s", msgprefix, params)
