from command_router import Permission

PLUGIN_ID = "topic"


async def _topic(router, name, params, channel, userdata, rank, is_channel):
    chan = (len(params) > 0 and params[0]) or channel
    try:
        await router.send_chat_message(router.send, channel, router.channel_data[chan]["Topic"])
    except KeyError:
        await router.send_chat_message(router.send, channel, "Invalid channel name specified.")


COMMANDS = {
    "topic": {"execute": _topic, "permission": Permission.OP},
}
