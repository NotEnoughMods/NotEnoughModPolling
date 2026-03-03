ID = "shutdown"
permission = 3


class Shutdown(Exception):
    def __init__(self, user, channel):
        self.name = user
        self.channel = channel

    def __str__(self):
        return f"Bot is shutting down! The Shutdown was triggered by '{self.name}' in the channel '{self.channel}'"


async def execute(self, name, params, channel, userdata, rank):
    await self.send("QUIT :Shutting down", 5)
    raise Shutdown(name, channel)
