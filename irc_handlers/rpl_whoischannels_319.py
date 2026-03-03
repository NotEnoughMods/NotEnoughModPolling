import logging

ID = "319"

logger = logging.getLogger("irc.rpl.319")


async def execute(self, sendMsg, prefix, command, params):
    logger.debug("RPL_WHOISCHANNELS: %s", params)

    fields = params.split(":")

    userinfo = fields[0].split(" ")
    channelinfo = fields[1].split(" ")

    userinfo[1]

    logger.debug("WHOIS channels: user=%s channels=%s", userinfo, channelinfo)
