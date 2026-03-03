ID = "PING"


async def execute(self, sendMsg, prefix, command, params):
    print("RECEIVED PING: " + params)

    derp = params.strip()
    derp[1:] if derp[0] == ":" else derp

    await sendMsg("PONG " + derp, 0)
