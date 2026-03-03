ID = "chatevent"
permission = 3
privmsgEnabled = False


async def timer(self, channels):
    await self.send_chat_message(self.send, channels[0], "pong")


async def chatEvent(self, channels, userdata, message, currChannel):
    # print channels
    # print currChannel
    if channels and currChannel in channels:
        await self.send_chat_message(self.send, currChannel, str(len(message)))
        if "start" in message:
            await self.send_chat_message(self.send, currChannel, "Starting time event")
            self.events["time"].add_event("TimerTest", 10, timer, [currChannel], from_event=True)

        if "end" in message:
            await self.send_chat_message(self.send, currChannel, "Ending time event")
            self.events["time"].remove_event("TimerTest", from_event=True)


async def execute(self, name, params, channel, userdata, rank):
    # print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["chat"].event_exists("TestFunc"):
            await self.send_chat_message(self.send, channel, "Turning chatevent on.")
            self.timerChannel = channel
            self.events["chat"].add_event("TestFunc", chatEvent)
        else:
            await self.send_chat_message(self.send, channel, "chatevent is already running.")

    elif len(params) == 1 and params[0] == "off":
        if self.events["chat"].event_exists("TestFunc"):
            await self.send_chat_message(self.send, channel, "Turning chatevent off.")
            self.events["chat"].remove_event("TestFunc")
        else:
            await self.send_chat_message(self.send, channel, "chatevent isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "added")
            self.events["chat"].add_channel("TestFunc", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "removed")
            self.events["chat"].remove_channel("TestFunc", channel)
