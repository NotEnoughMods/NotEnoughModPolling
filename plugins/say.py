import logging

from command_router import Permission

PLUGIN_ID = "say"

logger = logging.getLogger("cmd.say")


async def _say(router, name, params, channel, userdata, rank, is_channel):
    logger.debug("Executing say command")
    result = " ".join(params)
    logger.debug("Say result: %s", result)
    await router.send_chat_message(router.send, channel, result)


COMMANDS = {
    "say": {"execute": _say, "permission": Permission.HIDDEN},
}
