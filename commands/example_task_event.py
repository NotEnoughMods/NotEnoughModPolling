import asyncio
import logging
import random

ID = "taskevent"
permission = 3
privmsgEnabled = False

logger = logging.getLogger("cmd.taskevent")


async def example_task(self, pipe):
    # print channels
    # print currChannel
    while not self.signal:
        rand = random.randint(10, 20)

        await pipe.put(f"I will wait {rand} seconds!")
        await asyncio.sleep(rand)
        logger.debug("Received from pipe: %s", await pipe.get())
        logger.debug("success")


async def task_checker(self, channels):
    yes = self.task_pool.poll("taskTest")

    # print yes
    if yes:
        msg = await self.task_pool.recv("taskTest")
        if isinstance(msg, dict) and "action" in msg and msg["action"] == "exceptionOccured":
            logger.debug("EXCEPTION: %s", msg["traceback"])
        else:
            await self.send_chat_message(self.send, channels[0], "Message from task: " + msg)
            await self.task_pool.send("taskTest", random.choice(["0", "1", "2", "3"]))
        # print "sent message"


async def execute(self, name, params, channel, userdata, rank):
    # print "running"
    if len(params) == 1 and params[0] == "on":
        if not self.events["time"].event_exists("taskChecker"):
            await self.send_chat_message(self.send, channel, "Turning task event on.")
            self.timerChannel = channel
            self.events["time"].add_event("taskChecker", 1, task_checker, [channel])

            self.task_pool.add_task("taskTest", example_task)
        else:
            await self.send_chat_message(self.send, channel, "Task event is already running.")

    elif len(params) == 1 and params[0] == "off":
        if self.events["time"].event_exists("taskChecker"):
            await self.send_chat_message(self.send, channel, "Turning task event off.")
            self.events["time"].remove_event("taskChecker")

            self.task_pool.cancel_task("taskTest")
        else:
            await self.send_chat_message(self.send, channel, "Task event isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "added")
            self.events["time"].add_channel("taskChecker", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = self.get_channel_true_case(params[1])

        if channel:
            await self.send_chat_message(self.send, channel, "removed")
            self.events["time"].remove_channel("taskChecker", channel)
