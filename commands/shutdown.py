from command_router import Permission

PLUGIN_ID = "shutdown"


class Shutdown(Exception):
    def __init__(self, user, channel):
        self.name = user
        self.channel = channel

    def __str__(self):
        return f"Bot is shutting down! The Shutdown was triggered by '{self.name}' in the channel '{self.channel}'"


async def _shutdown(router, name, params, channel, userdata, rank, is_channel):
    await router.send("QUIT :Shutting down", 5)
    raise Shutdown(name, channel)


COMMANDS = {
    "shutdown": {"execute": _shutdown, "permission": Permission.ADMIN},
}
