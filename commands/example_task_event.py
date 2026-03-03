import asyncio
import random

ID = "threadevent"
permission = 3
privmsgEnabled = False


async def thread(self, pipe):
    # print channels
    # print currChannel
    while not self.signal:
        rand = random.randint(10, 20)

        await pipe.put(f"I will wait {rand} seconds!")
        await asyncio.sleep(rand)
        print(await pipe.get())
        print("success")


async def threadChecker(self, channels):
    yes = self.threading.poll("threadTest")

    # print yes
    if yes:
        msg = await self.threading.recv("threadTest")
        if isinstance(msg, dict) and "action" in msg and msg["action"] == "exceptionOccured":
            print("EXCEPTION")
            print(msg["traceback"])
        else:
            await self.sendChatMessage(self.send, channels[0], "Message from Thread: " + msg)
            await self.threading.send("threadTest", random.choice(["0", "1", "2", "3"]))
        # print "sent message"


async def execute(self, name, params, channel, userdata, rank):
    # print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].doesExist("threadChecker"):
            await self.sendChatMessage(self.send, channel, "Turning threadevent on.")
            self.timerChannel = channel
            self.events["time"].addEvent("threadChecker", 1, threadChecker, [channel])

            self.threading.addThread("threadTest", thread)
        else:
            await self.sendChatMessage(self.send, channel, "threadevent is already running.")

    elif len(params) == 1 and params[0] == "off":
        if self.events["time"].doesExist("threadChecker"):
            await self.sendChatMessage(self.send, channel, "Turning threadevent off.")
            self.events["time"].removeEvent("threadChecker")

            self.threading.sigquitThread("threadTest")
        else:
            await self.sendChatMessage(self.send, channel, "threadevent isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = self.retrieveTrueCase(params[1])

        if channel:
            await self.sendChatMessage(self.send, channel, "added")
            self.events["time"].addChannel("threadChecker", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = self.retrieveTrueCase(params[1])

        if channel:
            await self.sendChatMessage(self.send, channel, "removed")
            self.events["time"].removeChannel("threadChecker", channel)
