from command_router import Permission

PLUGIN_ID = "version"


async def _version(router, name, params, channel, userdata, rank, is_channel):
    await router.send_chat_message(router.send, channel, "Yoshi2's IRC Bot v0.3")


COMMANDS = {
    "version": {"execute": _version, "permission": Permission.GUEST},
}
