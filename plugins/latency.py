from command_router import Permission

PLUGIN_ID = "latency"


async def _latency(router, name, params, channel, userdata, rank, is_channel):
    if router.latency is not None:
        latency = round(router.latency, 2)
        await router.send_chat_message(router.send, channel, f"My current latency is {latency} seconds.")
    else:
        await router.send(f"NOTICE {name} :Please wait a bit so I can measure the latency.")


COMMANDS = {
    "latency": {"execute": _latency, "permission": Permission.OP, "allow_private": True},
}
