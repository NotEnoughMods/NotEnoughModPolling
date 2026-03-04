import logging
import time

ID = "ERROR"

logger = logging.getLogger("irc.error")


class ForceShutdown(Exception):
    def __init__(self, prefix, command, params):
        self.time = time.asctime()
        self.pref = prefix
        self.cmd = command
        self.params = params

    def __str__(self):
        return f"Server is forcefully killing connection to bot: \n \
        Received command '{self.cmd}' with prefix '{self.pref}' and params '{self.params}'.\n \
        Time: {self.time}"


async def execute(self, send_msg, prefix, command, params):
    logger.warning("Server sent an ERROR packet: %s %s", prefix, params)
    raise ForceShutdown(prefix, command, params)
