import logging

ID = "say"
permission = 4

logger = logging.getLogger("cmd.say")


async def execute(self, name, params, channel, userdata, rank):
    logger.debug("Executing say command")
    result = " ".join(params)
    logger.debug("Say result: %s", result)
    await self.send_chat_message(self.send, channel, result)
