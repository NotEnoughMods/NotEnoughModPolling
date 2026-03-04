from command_router import Permission

PLUGIN_ID = "raw"


async def _raw(router, name, params, channel, userdata, rank, is_channel):
    await router.send(" ".join(params), 4)


COMMANDS = {
    "raw": {"execute": _raw, "permission": Permission.ADMIN},
}
