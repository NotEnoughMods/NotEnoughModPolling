import logging

ID = "433"

logger = logging.getLogger("irc.err.433")


async def execute(self, sendMsg, msgprefix, command, params):
    logger.debug("ERR_NICKNAMEINUSE: %s %s", msgprefix, params)
