import time

ID = "event"
permission = 3

async def timer(self, channels):
    print("executing")
    if channels != False and len(channels) > 0:
        await self.sendChatMessage(self.send, channels[0], "Time has passed.")

    #self.sendChatMessage(self.send, self.timerChannel, "Test: "+str(channels))

async def execute(self, name, params, channel, userdata, rank):
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].doesExist("TestFunc"):
            await self.sendChatMessage(self.send, channel, "Turning timerevent on.")
            self.timerChannel = channel
            self.events["time"].addEvent("TestFunc", 60, timer)
        else:
            await self.sendChatMessage(self.send, channel, "Timerevent is already running.")
    if len(params) == 1 and params[0] == "off":
        if self.events["time"].doesExist("TestFunc"):
            await self.sendChatMessage(self.send, channel, "Turning timerevent off.")
            self.events["time"].removeEvent("TestFunc")
        else:
            await self.sendChatMessage(self.send, channel, "Timerevent isn't running!")


    if len(params) == 2 and params[0] == "add":
        channel = params[1]
        self.events["time"].addChannel("TestFunc", channel)

    if len(params) == 2 and params[0] == "rem":
        channel = params[1]
        self.events["time"].removeChannel("TestFunc", channel)
        
        
            


