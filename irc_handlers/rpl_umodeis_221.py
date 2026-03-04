import logging

ID = "221"

logger = logging.getLogger("irc.rpl.221")


async def execute(self, send_msg, prefix, command, params):
    logger.debug("RPL_UMODEIS: %s %s", prefix, params)
