ID = "324"


async def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ")

    channel = data[1]
    mode = data[2]

    self.channel_data[self.retrieveTrueCase(channel)]["Mode"] = mode
