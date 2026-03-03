import contextlib

ID = "332"


async def execute(self, sendMsg, prefix, command, params):
    data = params.split(" ", 2)

    channel = data[1]
    topic = data[2][1:]
    # timestamp = data[3]

    with contextlib.suppress(BaseException):
        self.channelData[self.retrieveTrueCase(channel)]["Topic"] = topic

    # print prefix, params
