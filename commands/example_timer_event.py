ID = "event"
permission = 3


async def timer(self, channels):
    print("executing")
    if channels and len(channels) > 0:
        await self.send_chat_message(self.send, channels[0], "Time has passed.")

    # self.send_chat_message(self.send, self.timerChannel, "Test: "+str(channels))


async def execute(self, name, params, channel, userdata, rank):
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].event_exists("TestFunc"):
            await self.send_chat_message(self.send, channel, "Turning timerevent on.")
            self.timerChannel = channel
            self.events["time"].add_event("TestFunc", 60, timer)
        else:
            await self.send_chat_message(self.send, channel, "Timerevent is already running.")
    if len(params) == 1 and params[0] == "off":
        if self.events["time"].event_exists("TestFunc"):
            await self.send_chat_message(self.send, channel, "Turning timerevent off.")
            self.events["time"].remove_event("TestFunc")
        else:
            await self.send_chat_message(self.send, channel, "Timerevent isn't running!")

    if len(params) == 2 and params[0] == "add":
        channel = params[1]
        self.events["time"].add_channel("TestFunc", channel)

    if len(params) == 2 and params[0] == "rem":
        channel = params[1]
        self.events["time"].remove_channel("TestFunc", channel)
