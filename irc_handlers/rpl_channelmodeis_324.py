ID = "324"


async def execute(self, send_msg, prefix, command, params):
    data = params.split(" ")

    channel = data[1]
    mode = data[2]

    self.channel_data[self.get_channel_true_case(channel)]["Mode"] = mode
