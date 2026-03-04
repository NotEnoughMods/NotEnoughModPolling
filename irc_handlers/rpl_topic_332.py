import contextlib

ID = "332"


async def execute(self, send_msg, prefix, command, params):
    data = params.split(" ", 2)

    channel = data[1]
    topic = data[2][1:]
    # timestamp = data[3]

    with contextlib.suppress(BaseException):
        self.channel_data[self.get_channel_true_case(channel)]["Topic"] = topic

    # print prefix, params
