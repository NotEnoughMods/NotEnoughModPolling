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
    yes = self.task_pool.poll("threadTest")

    # print yes
    if yes:
        msg = await self.task_pool.recv("threadTest")
        if isinstance(msg, dict) and "action" in msg and msg["action"] == "exceptionOccured":
            print("EXCEPTION")
            print(msg["traceback"])
        else:
            await self.send_chat_message(self.send, channels[0], "Message from Thread: " + msg)
            await self.task_pool.send("threadTest", random.choice(["0", "1", "2", "3"]))
        # print "sent message"


async def execute(self, name, params, channel, userdata, rank):
    # print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].event_exists("threadChecker"):
            await self.send_chat_message(self.send, channel, "Turning threadevent on.")
            self.timerChannel = channel
            self.events["time"].add_event("threadChecker", 1, threadChecker, [channel])

            self.task_pool.add_task("threadTest", thread)
        else:
            await self.send_chat_message(self.send, channel, "threadevent is already running.")

    elif len(params) == 1 and params[0] == "off":
        if self.events["time"].event_exists("threadChecker"):
            await self.send_chat_message(self.send, channel, "Turning threadevent off.")
            self.events["time"].remove_event("threadChecker")

            self.task_pool.cancel_task("threadTest")
        else:
            await self.send_chat_message(self.send, channel, "threadevent isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "added")
            self.events["time"].add_channel("threadChecker", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "removed")
            self.events["time"].remove_channel("threadChecker", channel)
