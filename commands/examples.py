import asyncio
import logging
import random

from command_router import Permission

PLUGIN_ID = "examples"

logger = logging.getLogger("cmd.examples")


# -- ctest: example private message detection --


async def _ctest(router, name, params, channel, userdata, rank, is_channel):
    if not is_channel:
        await router.send_chat_message(router.send, channel, "You are messaging me privately.")
    elif is_channel:
        await router.send_chat_message(router.send, channel, "You are messaging me from a channel.")
    else:
        await router.send_chat_message(router.send, channel, "waitwhat")


# -- event: example timer event --


async def _event_timer(router, channels):
    logger.debug("executing timer event")
    if channels and len(channels) > 0:
        await router.send_chat_message(router.send, channels[0], "Time has passed.")


async def _event(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 1 and params[0] == "on":
        if not router.events["time"].event_exists("TestFunc"):
            await router.send_chat_message(router.send, channel, "Turning timerevent on.")
            router.timer_channel = channel
            router.events["time"].add_event("TestFunc", 60, _event_timer)
        else:
            await router.send_chat_message(router.send, channel, "Timerevent is already running.")
    if len(params) == 1 and params[0] == "off":
        if router.events["time"].event_exists("TestFunc"):
            await router.send_chat_message(router.send, channel, "Turning timerevent off.")
            router.events["time"].remove_event("TestFunc")
        else:
            await router.send_chat_message(router.send, channel, "Timerevent isn't running!")

    if len(params) == 2 and params[0] == "add":
        channel = params[1]
        router.events["time"].add_channel("TestFunc", channel)

    if len(params) == 2 and params[0] == "rem":
        channel = params[1]
        router.events["time"].remove_channel("TestFunc", channel)


# -- chatevent: example chat event --


async def _chatevent_timer(router, channels):
    await router.send_chat_message(router.send, channels[0], "pong")


async def _chatevent_chat(router, channels, userdata, message, curr_channel):
    if channels and curr_channel in channels:
        await router.send_chat_message(router.send, curr_channel, str(len(message)))
        if "start" in message:
            await router.send_chat_message(router.send, curr_channel, "Starting time event")
            router.events["time"].add_event("TimerTest", 10, _chatevent_timer, [curr_channel], from_event=True)

        if "end" in message:
            await router.send_chat_message(router.send, curr_channel, "Ending time event")
            router.events["time"].remove_event("TimerTest", from_event=True)


async def _chatevent(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 1 and params[0] == "on":
        if not router.events["chat"].event_exists("TestFunc"):
            await router.send_chat_message(router.send, channel, "Turning chatevent on.")
            router.timer_channel = channel
            router.events["chat"].add_event("TestFunc", _chatevent_chat)
        else:
            await router.send_chat_message(router.send, channel, "chatevent is already running.")

    elif len(params) == 1 and params[0] == "off":
        if router.events["chat"].event_exists("TestFunc"):
            await router.send_chat_message(router.send, channel, "Turning chatevent off.")
            router.events["chat"].remove_event("TestFunc")
        else:
            await router.send_chat_message(router.send, channel, "chatevent isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = router.get_channel_true_case(params[1])

        if channel:
            await router.send_chat_message(router.send, channel, "added")
            router.events["chat"].add_channel("TestFunc", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = router.get_channel_true_case(params[1])

        if channel:
            await router.send_chat_message(router.send, channel, "removed")
            router.events["chat"].remove_channel("TestFunc", channel)


# -- taskevent: example task event --


async def _example_task(self, pipe):
    while True:
        rand = random.randint(10, 20)

        await pipe.put(f"I will wait {rand} seconds!")
        await asyncio.sleep(rand)
        logger.debug("Received from pipe: %s", await pipe.get())
        logger.debug("success")


async def _task_checker(router, channels):
    yes = router.task_pool.poll("taskTest")

    if yes:
        msg = await router.task_pool.recv("taskTest")
        if isinstance(msg, dict) and "action" in msg and msg["action"] == "exceptionOccured":
            logger.debug("EXCEPTION: %s", msg["traceback"])
        else:
            await router.send_chat_message(router.send, channels[0], "Message from task: " + msg)
            await router.task_pool.send("taskTest", random.choice(["0", "1", "2", "3"]))


async def _taskevent(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 1 and params[0] == "on":
        if not router.events["time"].event_exists("taskChecker"):
            await router.send_chat_message(router.send, channel, "Turning task event on.")
            router.timer_channel = channel
            router.events["time"].add_event("taskChecker", 1, _task_checker, [channel])

            router.task_pool.add_task("taskTest", _example_task)
        else:
            await router.send_chat_message(router.send, channel, "Task event is already running.")

    elif len(params) == 1 and params[0] == "off":
        if router.events["time"].event_exists("taskChecker"):
            await router.send_chat_message(router.send, channel, "Turning task event off.")
            router.events["time"].remove_event("taskChecker")

            router.task_pool.cancel_task("taskTest")
        else:
            await router.send_chat_message(router.send, channel, "Task event isn't running!")

    elif len(params) == 2 and params[0] == "add":
        channel = router.get_channel_true_case(params[1])

        if channel:
            await router.send_chat_message(router.send, channel, "added")
            router.events["time"].add_channel("taskChecker", channel)

    elif len(params) == 2 and params[0] == "rem":
        channel = router.get_channel_true_case(params[1])

        if channel:
            await router.send_chat_message(router.send, channel, "removed")
            router.events["time"].remove_channel("taskChecker", channel)


COMMANDS = {
    "ctest": {"execute": _ctest, "permission": Permission.ADMIN, "allow_private": True},
    "event": {"execute": _event, "permission": Permission.ADMIN},
    "chatevent": {"execute": _chatevent, "permission": Permission.ADMIN},
    "taskevent": {"execute": _taskevent, "permission": Permission.ADMIN},
}
