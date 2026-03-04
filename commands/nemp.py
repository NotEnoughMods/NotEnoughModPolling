import asyncio
import importlib
import logging
import shlex
import textwrap
from collections import namedtuple

from mod_polling import poller

ID = "nemp"
permission = 1
privmsg_enabled = True

nemp_logger = logging.getLogger("NEMPolling")

help_dict = {
    "running": [
        "{0} running <true/false>",
        "Enables or Disables the polling of latest builds.",
    ],
    "poll": [
        "{0} poll <mod> <true/false>",
        "Enables or Disables the polling of <mod>.",
    ],
    "list": ["{0} list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["{0} about", "Shows some info about this plugin."],
    "help": [
        "{0} help [command]",
        "Shows this help info about [command] or lists all commands for this plugin.",
    ],
    "refresh": [
        "'{0} refresh' or '{0} reload'",
        "Reloads the various data stores (mods list, versions list, etc)",
    ],
    "reload": [
        "'{0} refresh' or '{0} reload'",
        "Reloads the various data stores (mods list, versions list, etc)",
    ],
    "test": [
        "{0} test <mod>",
        "Tests the parser for <mod> and outputs the contents to IRC",
    ],
    "status": [
        "{0} status",
        "Shows whether or not NEMPolling is running and in which channel it is running.",
    ],
    "disabledmods": [
        "{0} disabledmods",
        "Shows a list of the currently disabled mods.",
    ],
    "failedmods": [
        "{0} failedmods",
        "Shows a list of mods that have failed to be polled at least 5 times in a row and were disabled automatically.",
    ],
    "failcount": [
        "{0} failcount",
        "Shows how many times mods have failed to be polled so far. At least two failures in a row required.",
        "Mods that have failed being polled 5 times are excluded from this list. Check {0} failedmods for those mods.",
    ],
    "showinfo": [
        "{0} showinfo <mod> [<path> [...]]",
        "Shows polling information for the specified mod.",
    ],
    "url": ["{0} url <mod>", "Spits out the URL of the specified mod."],
    "reloadblocklist": [
        "{0} reloadblocklist",
        "Reloads the blocked versions configuration files (version_blocklist.yml and mc_blocklist.yml).",
    ],
}


async def teardown(self):
    if hasattr(self, "poller") and self.poller and hasattr(self.poller, "session") and self.poller.session:
        await self.poller.session.close()


async def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        cmd_name = params[0].lower()
        if cmd_name in commands:
            user_rank = self.rank_values[rank]

            command, required_rank = commands[cmd_name]
            nemp_logger.debug(f"Needed rank: {required_rank} User rank: {user_rank}")
            if user_rank >= required_rank:
                await command(self, name, params, channel, userdata, rank)
            else:
                await self.send_message(channel, "You're not authorized to use this command.")
        else:
            await self.send_message(
                channel,
                name + f": Invalid command! See {self.cmdprefix + ID} help for a list of commands",
            )
    else:
        await self.send_message(
            channel,
            name + f': see "{self.cmdprefix + ID} help" for a list of commands',
        )


TIME_EVENT_NAME = "NotEnoughModPolling"
TASK_NAME = "NEMP"


def is_running(self):
    return self.events["time"].event_exists(TIME_EVENT_NAME)


async def start_polling(self, timer, channel):
    await self.poller.init_nem_versions()
    self.poll_cycle_count = 0

    self.task_pool.add_task(TASK_NAME, polling_task, {"poller": self.poller, "poll_time": timer})

    self.events["time"].add_event(TIME_EVENT_NAME, 60, nemp_timer_event, [channel])


def stop_polling(self):
    self.events["time"].remove_event(TIME_EVENT_NAME)
    nemp_logger.debug("Removed NEM Polling Event")
    self.task_pool.cancel_task(TASK_NAME)
    nemp_logger.debug("Sigquit to NEMP task sent")

    self.troubled_mods = {}
    # self.auto_disabled_mods = {}


async def setup(self, startup):
    if startup:
        self.poller = await poller.setup()
    else:
        # kill events, tasks
        if is_running(self):
            stop_polling(self)

            nemp_logger.info("NEMP Polling has been disabled.")

        importlib.reload(poller)

        self.poller = await poller.setup()

    self.troubled_mods = {}
    self.auto_disabled_mods = {}
    self.poll_cycle_count = 0

    if startup:
        polling_config = self.poller.config.get("polling", {})
        if polling_config.get("auto_start") and polling_config.get("channel"):
            interval = polling_config.get("interval", 1800)
            channel = polling_config["channel"]
            nemp_logger.info("Auto-starting polling (interval=%ds, channel=%s)", interval, channel)
            await start_polling(self, interval, channel)


async def cmd_enable(self, name, params, channel, userdata, rank):
    if is_running(self):
        await self.send_message(channel, "NotEnoughModPolling is already running.")
        return

    await self.send_message(channel, "Enabling NotEnoughModPolling")

    timer_for_polls = self.poller.config.get("polling", {}).get("interval", 1800)

    if len(params) == 2:
        timer_for_polls = int(params[1])
        await self.send_message(channel, f"Timer is set to {timer_for_polls} seconds")

    await start_polling(self, timer_for_polls, channel)


async def cmd_disable(self, name, params, channel, userdata, rank):
    if not is_running(self):
        await self.send_message(channel, "NotEnoughModPolling isn't running!")
        return

    await self.send_message(channel, "Disabling NotEnoughModPolling")

    try:
        stop_polling(self)
    except Exception:
        nemp_logger.exception("Exception appeared while trying to disable NotEnoughModPolling")
        await self.send_message(channel, "Exception appeared while trying to disable NotEnoughModPolling")


async def cmd_about(self, name, params, channel, userdata, rank):
    await self.send_message(channel, "Not Enough Mods: Polling - Helps keep NEM updated!")
    await self.send_message(
        channel,
        "Source code available at https://github.com/NotEnoughMods/NotEnoughModPolling",
    )
    await self.send_message(
        channel,
        "A list of contributors is available at https://github.com/NotEnoughMods/NotEnoughModPolling/graphs/contributors",
    )


async def cmd_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        await self.send_message(
            channel,
            name + ": Available commands: " + ", ".join(sorted(help_dict.keys())),
        )
        await self.send_message(
            channel,
            name + f': For command usage, use "{self.cmdprefix + ID} help <command>".',
        )
    else:
        command = params[1]
        if command in help_dict:
            for line in help_dict[command]:
                await self.send_message(channel, name + ": " + line.format(self.cmdprefix + ID))
        else:
            await self.send_message(channel, name + ": Invalid command provided")


async def cmd_status(self, name, params, channel, userdata, rank):
    if is_running(self):
        channels = ", ".join(self.events["time"].get_channels(TIME_EVENT_NAME))
        await self.send_message(
            channel,
            "NEM Polling is currently running "
            f"in the following channel(s): {channels}. "
            f"Full cycles completed: {self.poll_cycle_count}",
        )
    else:
        await self.send_message(channel, "NEM Polling is not running.")


async def cmd_disabled_mods(self, name, params, channel, userdata, rank):
    disabled = [mod for mod, info in self.poller.mods.items() if not info["active"]]

    if len(disabled) == 0:
        await self.send_notice(name, "No mods are disabled right now.")
    else:
        await self.send_notice(
            name,
            "The following mods are disabled right now: {}. {} mod(s) total. ".format(
                ", ".join(disabled), len(disabled)
            ),
        )


async def cmd_failed_mods(self, name, params, channel, userdata, rank):
    if len(self.auto_disabled_mods) == 0:
        await self.send_notice(name, "No mods have been automatically disabled so far.")
    else:
        disabled = self.auto_disabled_mods.keys()
        await self.send_notice(
            name,
            "The following mods have been automatically disabled so far: {}. {} mod(s) total".format(
                ", ".join(disabled), len(disabled)
            ),
        )


async def cmd_reset_failed(self, name, params, channel, userdata, rank):
    failed_mods = self.auto_disabled_mods.keys()
    for failed_mod in self.auto_disabled_mods:
        self.poller.mods[failed_mod]["active"] = True
    self.auto_disabled_mods = {}
    await self.send_message(channel, f"Re-enabled {len(failed_mods)} automatically disabled mods.")
    self.poller.build_html()


async def cmd_fail_count(self, name, params, channel, userdata, rank):
    nemp_logger.debug("Troubled mods: %s", self.troubled_mods)
    if len(self.troubled_mods) == 0:
        await self.send_notice(name, "No mods have had trouble polling so far.")
    else:
        sorted_mods = sorted(self.troubled_mods, key=lambda x: self.troubled_mods[x])
        newlist = []

        for mod_name in sorted_mods:
            if self.troubled_mods[mod_name] > 1:
                newlist.append(mod_name + f" [{self.troubled_mods[mod_name]}x]")

        if len(newlist) == 0:
            await self.send_notice(
                name,
                f"{len(sorted_mods)} mod(s) had trouble being polled once. "
                "If the mod(s) fail polling a second time, "
                "they will be shown by this command.",
            )
            return

        await self.send_notice(
            name,
            "The following mods have been having trouble being polled at least twice in a row so far: "
            "{}. {} mod(s) total".format(", ".join(newlist), len(newlist)),
        )

        if len(sorted_mods) - len(newlist) > 0:
            await self.send_notice(
                name,
                f"{len(sorted_mods) - len(newlist)} mod(s) had trouble being polled only a "
                "single time and thus were not shown.",
            )


FailedModEntry = namedtuple("FailedModEntry", "name exception")


async def _poll_single_mod(poller, mod_name):
    """Poll a single mod, returning (poll_results, failed)."""
    statuses, exception = await poller.check_mod(mod_name)
    if exception:
        return ([], [FailedModEntry(name=mod_name, exception=exception)])
    return ([(mod_name, statuses)], [])


async def _poll_document_group(poller, mod_name, document_group):
    """Poll a document group, returning (poll_results, failed)."""
    try:
        mod_results = await poller.check_mods(mod_name)
    except Exception as e:
        document_group_mods = poller.document_groups[document_group]
        return ([], [FailedModEntry(name=m, exception=e) for m in document_group_mods])

    poll_results = []
    failed = []
    for output_mod, output_info in mod_results.items():
        result, exception = output_info
        if exception:
            failed.append(FailedModEntry(name=output_mod, exception=exception))
        else:
            poll_results.append((output_mod, result))
    return (poll_results, failed)


async def polling_task(self, pipe):
    poller = self.base["poller"]
    sleep_time = self.base["poll_time"]

    while True:
        nemp_logger.debug("polling_task: I'm still running!")

        coros = []
        document_groups_done = set()

        for mod_name, mod_info in poller.mods.items():
            if not mod_info["active"]:
                continue

            document_group = mod_info.get("document_group", {}).get("id")

            if document_group:
                if document_group in document_groups_done:
                    continue
                document_groups_done.add(document_group)
                coros.append(_poll_document_group(poller, mod_name, document_group))
            else:
                coros.append(_poll_single_mod(poller, mod_name))

        results = await asyncio.gather(*coros, return_exceptions=True)

        poll_results = []
        failed = []

        for result in results:
            if isinstance(result, BaseException):
                nemp_logger.error("Unexpected exception in polling coroutine", exc_info=result)
                continue
            successes, failures = result
            poll_results.extend(successes)
            failed.extend(failures)

        await pipe.put((poll_results, failed))

        await asyncio.sleep(sleep_time)


# This runs on a timer (once every minute)
async def nemp_timer_event(self, channels):
    # Check if we have any data from polling_task to process
    if not self.task_pool.poll(TASK_NAME):
        return

    nemp_data = await self.task_pool.recv(TASK_NAME)

    self.poll_cycle_count += 1

    staff_channel = self.poller.config.get("irc", {}).get("staff_channel")

    if staff_channel and self.poll_cycle_count % 50 == 0:
        await self.send_message(staff_channel, f"Full cycles completed: {self.poll_cycle_count}")
        if self.auto_disabled_mods:
            await self.send_message(
                staff_channel,
                f"There are {len(self.auto_disabled_mods)} failed mod(s)",
            )

    if isinstance(nemp_data, dict) and "action" in nemp_data and nemp_data["action"] == "exceptionOccured":
        nemp_logger.error(
            "NEMP task {} encountered an unhandled exception: {}".format(
                nemp_data["functionName"], str(nemp_data["exception"])
            )
        )
        nemp_logger.error("Traceback Start")
        nemp_logger.error(nemp_data["traceback"])
        nemp_logger.error("Traceback End")

        nemp_logger.error("Shutting down NEMP Events and Polling")
        stop_polling(self)

        self.troubled_mods = {}
        self.auto_disabled_mods = {}

        return

    poll_results, failed_mods = nemp_data

    for item in poll_results:
        mod_name = item[0]
        new_versions = item[1]

        nem_mod_name = self.poller.mods[mod_name].get("name", mod_name)

        for new_version in new_versions:
            mc_version, dev_version, release_version, changelog = new_version

            last_dev = self.poller.get_nem_dev_version(mod_name, mc_version)
            last_release = self.poller.get_nem_version(mod_name, mc_version)

            if not last_dev and not last_release:
                clone_version = release_version or "dev-only"

                self.poller.set_nem_version(mod_name, clone_version, mc_version)

                nemp_logger.debug(f"Cloning mod {mod_name} to {mc_version}, status: {new_version}")
                for channel in channels:
                    await self.send_message(
                        channel,
                        f"!clone {nem_mod_name} {mc_version} {clone_version}",
                    )
            elif release_version:
                nemp_logger.debug(f"Updating Mod {mod_name}, status: {new_version}")
                self.poller.set_nem_version(mod_name, release_version, mc_version)
                for channel in channels:
                    await self.send_message(
                        channel,
                        f"!lmod {mc_version} {nem_mod_name} {release_version}",
                    )

            if dev_version:
                if release_version and dev_version == release_version:
                    nemp_logger.debug(
                        f"Would update mod {mod_name} to dev {dev_version}, "
                        f"but it matches the new release {release_version}"
                    )
                elif last_release and dev_version == last_release:
                    nemp_logger.debug(
                        f"Would update mod {mod_name} to dev {dev_version}, "
                        f"but it matches the current release {release_version}"
                    )
                else:
                    nemp_logger.debug(f"Updating mod {mod_name} to dev {dev_version}, status: {new_version}")
                    self.poller.set_nem_dev_version(mod_name, dev_version, mc_version)
                    for channel in channels:
                        await self.send_message(
                            channel,
                            f"!ldev {mc_version} {nem_mod_name} {dev_version}",
                        )

            if changelog and "changelog" not in self.poller.mods[mod_name]:
                nemp_logger.debug(f"Sending text for Mod {mod_name}")
                for channel in channels:
                    await self.send_message(channel, " * " + " | ".join(changelog.splitlines())[:300])

    current_troubled_mods = list(self.troubled_mods.keys())

    completely_failed_mods = []

    for item in failed_mods:  # type: FailedModEntry
        nemp_logger.debug(f"Processing failed_mods entry {item!r}")

        assert isinstance(item, FailedModEntry)

        mod_name = item.name
        exception = item.exception

        if isinstance(exception, (poller.NEMPException,)):
            nemp_logger.debug(f"Mod {mod_name} got a {type(exception).__name__}, failing immediately")

            if mod_name in self.troubled_mods:
                del self.troubled_mods[mod_name]
                current_troubled_mods.remove(mod_name)

            self.auto_disabled_mods[mod_name] = True
            self.poller.mods[mod_name]["active"] = False

            if staff_channel:
                await self.send_message(
                    staff_channel,
                    f"Mod {mod_name} \00304failed\003 with a {type(exception).__name__}: {exception}",
                )
        else:
            if mod_name not in self.troubled_mods:
                self.troubled_mods[mod_name] = 1
                nemp_logger.debug(f"Mod {mod_name} had trouble being polled once. Counter set to 1")

            else:
                self.troubled_mods[mod_name] += 1

                current_troubled_mods.remove(mod_name)

                if self.troubled_mods[mod_name] >= 5:
                    self.auto_disabled_mods[mod_name] = True
                    self.poller.mods[mod_name]["active"] = False
                    del self.troubled_mods[mod_name]

                    completely_failed_mods.append(mod_name)

                    nemp_logger.debug(f"Mod {mod_name} has failed to be polled at least 5 times, it has been disabled.")

    self.poller.build_html()

    if staff_channel and completely_failed_mods:
        await self.send_message(
            staff_channel,
            "The following mod(s) \00304failed\003: {}.".format(
                ", ".join(sorted(completely_failed_mods, key=lambda x: x.lower()))
            ),
        )

    for mod_name in current_troubled_mods:
        nemp_logger.debug(
            f"Mod {mod_name} is working again. Counter reset (Counter was at {self.troubled_mods[mod_name]}) "
        )
        del self.troubled_mods[mod_name]


async def cmd_poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        await self.send_message(channel, name + ": Insufficient amount of parameters provided. Required: 2")
        await self.send_message(channel, name + ": " + help_dict["poll"][1])
        return

    if params[2].lower() in ("true", "yes", "on"):
        setting = True
    elif params[2].lower() in ("false", "no", "off"):
        setting = False
    else:
        await self.send_message(channel, "{}: Invalid value. Must be: on/yes/true, off/no/false")
        return

    # "c:" is the category operator
    if params[1][0:2].lower() == "c:":
        category = params[1][2:].lower()
        match_mods = {k: v for k, v in self.poller.mods.items() if v.get("category", "").lower() == category}

        if not match_mods:
            await self.send_message(channel, f"{name}: Could not find any matches.")
        else:
            for mod, info in match_mods.items():
                info["active"] = setting

                if mod in self.auto_disabled_mods:
                    del self.auto_disabled_mods[mod]
                if mod in self.troubled_mods:
                    del self.troubled_mods[mod]
            await self.send_message(
                channel,
                name
                + ": "
                + ", ".join(sorted(match_mods.keys(), key=lambda x: x.lower()))
                + "'s poll status is now "
                + str(setting),
            )

    # "p:" is the parser operator
    elif params[1].lower().startswith("p:"):
        parser = params[1][2:].lower()
        match_mods = {k: v for k, v in self.poller.mods.items() if v["parser"].lower() == parser}

        if not match_mods:
            await self.send_message(channel, f"{name}: Could not find any matches.")
        else:
            for mod, info in match_mods.items():
                info["active"] = setting

                if mod in self.auto_disabled_mods:
                    del self.auto_disabled_mods[mod]
                if mod in self.troubled_mods:
                    del self.troubled_mods[mod]
            await self.send_message(
                channel,
                name
                + ": "
                + ", ".join(sorted(match_mods.keys(), key=lambda x: x.lower()))
                + "'s poll status is now "
                + str(setting),
            )

    # "all" or "*" matches all mods
    elif params[1].lower() == "all" or params[1] == "*":
        for mod in self.poller.mods:
            self.poller.mods[mod]["active"] = setting

            if mod in self.auto_disabled_mods:
                del self.auto_disabled_mods[mod]
            if mod in self.troubled_mods:
                del self.troubled_mods[mod]

        await self.send_message(channel, name + ": All mods are now set to " + str(setting))

    else:
        mod = self.poller.get_proper_name(params[1])

        if not mod:
            await self.send_message(channel, name + ": No such mod in NEMP.")
            return

        self.poller.mods[mod]["active"] = setting
        await self.send_message(channel, name + ": " + mod + "'s poll status is now " + str(setting))

        if mod in self.auto_disabled_mods:
            del self.auto_disabled_mods[mod]
        if mod in self.troubled_mods:
            del self.troubled_mods[mod]
    self.poller.build_html()


async def cmd_list(self, name, params, channel, userdata, rank):
    dest = None
    if len(params) > 1:
        if rank != "@@":
            await self.send_message(channel, f"{name}: Access denied.")
            return

        if params[1] == "pm":
            dest = name
        elif params[1] == "broadcast":
            dest = channel

    if dest is None:
        await self.send_message(channel, "http://polling.notenoughmods.com/")
        return

    darkgreen = "03"
    red = "05"
    blue = "12"
    bold = chr(2)
    color = chr(3)
    temp_list = {}
    for key, info in self.poller.mods.items():
        real_name = info.get("name", key)
        if self.poller.mods[key]["active"]:
            rel_type = ""
            mcver = self.poller.mods[key]["mc"]
            if self.poller.get_nem_version(key, mcver):
                rel_type = rel_type + color + darkgreen + "[R]" + color
            if self.poller.get_nem_dev_version(key, mcver):
                rel_type = rel_type + color + red + "[D]" + color

            if mcver not in temp_list:
                temp_list[mcver] = []
            temp_list[mcver].append(f"{real_name}{rel_type}")

    del mcver
    for mcver in sorted(temp_list.keys()):
        temp_list[mcver] = sorted(temp_list[mcver], key=lambda s: s.lower())
        await self.send_message(
            dest,
            "Mods checked for {} ({}): {}".format(
                color + blue + bold + mcver + color + bold,
                len(temp_list[mcver]),
                ", ".join(temp_list[mcver]),
            ),
        )


async def cmd_reload(self, name, params, channel, userdata, rank):
    if is_running(self):
        stop_polling(self)

        await self.send_message(channel, "NEMP Polling has been deactivated")

    self.troubled_mods = {}
    self.auto_disabled_mods = {}

    self.poller.build_mod_dict()
    await self.poller.query_nem()
    await self.poller.init_nem_versions()
    self.poller.build_html()

    await self.send_message(channel, "Reloaded the NEMP Database")


async def cmd_test(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        await self.send_message(
            channel,
            f"{name}: Wrong number of parameters. This command accepts 1 parameter: the mod's name",
        )
        return

    mod = self.poller.get_proper_name(params[1])

    if not mod:
        await self.send_message(channel, name + ': Mod "' + params[1] + '" does not exist in the database.')
        return

    try:
        if "document_group" in self.poller.mods[mod]:
            document = await getattr(self.poller, "check_" + self.poller.mods[mod]["parser"])(mod, None)
        else:
            document = None
    except Exception as exception:
        await self.send_message(
            channel,
            f"{name}: Failed to obtain document for mod: {type(exception).__name__}: {exception}",
        )
        return

    statuses, exception = await self.poller.check_mod(mod, document=document, simulation=True)

    if exception:
        await self.send_message(
            channel,
            f"Got an exception: {type(exception).__name__}: {exception}",
        )
        return

    if not statuses:
        await self.send_message(channel, name + ": Got no results from the parser")

    real_name = self.poller.mods[mod].get("name", mod)

    nemp_logger.debug("%s %r", mod, statuses)

    commands_list = []

    for status in statuses:
        mc_version, dev_version, release_version, changelog = status

        last_dev = self.poller.get_nem_dev_version(mod, mc_version)
        last_release = self.poller.get_nem_version(mod, mc_version)

        if not last_dev and not last_release:
            clone_version = release_version or "dev-only"

            commands_list.append(f"clone {real_name} {mc_version} {clone_version}")
        elif release_version:
            commands_list.append(f"lmod {mc_version} {real_name} {release_version}")

        if dev_version:
            commands_list.append(f"ldev {mc_version} {real_name} {dev_version}")

        if changelog and "changelog" not in self.poller.mods[mod]:
            commands_list.append(" * " + " | ".join(changelog.splitlines())[:300])

    for line in textwrap.wrap(", ".join(commands_list), width=300):
        await self.send_message(channel, line)


async def cmd_html(self, name, params, channel, userdata, rank):
    self.poller.build_html()
    await self.send_message(channel, name + ": Done.")


async def cmd_set(self, name, params, channel, userdata, rank):
    if len(params) < 4:
        await self.send_message(channel, "This is not a toy!")
        return

    try:
        args = shlex.split(" ".join(params[2:]))
    except Exception:
        await self.send_message(
            channel,
            "That looks like invalid input (are there any unescaped quotes?). Try again.",
        )
        return

    args.insert(0, params[1])

    available_casts = {"int": int, "float": float}

    cast_to = None

    if args and args[0] == "--type":
        if args[1] in available_casts:
            cast_to = available_casts[args[1]]
            args = args[2:]
        else:
            await self.send_message(
                channel,
                "Unknown type. Available types are: " + ", ".join(available_casts.keys()),
            )
            return

    mod = self.poller.get_proper_name(args[0])

    if not mod:
        await self.send_message(channel, name + ": No such mod in NEMP.")
        return

    if args[1] == "active":
        await self.send_message(channel, "You want =nemp poll instead.")
        return

    try:
        new_value = cast_to(args[-1]) if cast_to else args[-1]

        elem = self.poller.mods[mod]

        path = args[1:-2]

        for path_elem in path:
            elem = elem[path_elem]

        elem[args[-2]] = new_value

        self.poller.compile_regex(mod)

        await self.send_message(channel, "done.")
    except KeyError:
        await self.send_message(channel, name + ": No such element in that mod's configuration.")
    except Exception as e:
        await self.send_message(channel, "Error: " + str(e))


async def cmd_show_info(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.send_message(channel, name + ": You have to specify at least the mod's name.")
        return

    mod = self.poller.get_proper_name(params[1])

    if not mod:
        await self.send_message(channel, name + ": No such mod in NEMP.")
        return

    path = params[2:] if len(params) > 1 else []

    try:
        elem = self.poller.mods[mod]
        for path_elem in path:
            if not isinstance(elem, dict):
                raise KeyError()
            elem = elem[path_elem]

        await self.send_message(channel, name + ": " + repr(elem))
    except KeyError:
        await self.send_message(channel, name + ": No such element in that mod's configuration.")


async def cmd_url(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.send_message(channel, name + ": You have to specify at least the mod's name.")
        return

    modname = self.poller.get_proper_name(params[1])

    if not modname:
        await self.send_message(channel, name + ": No such mod in NEMP.")
        return

    mod = self.poller.mods[modname]
    func = mod["parser"]

    if func == "github_release":
        url = "https://github.com/" + mod["github"]["repo"]
    elif func == "cfwidget":
        url = "https://api.cfwidget.com/" + mod["curse"]["id"]
    elif func == "jenkins":
        url = mod["jenkins"]["url"][:-28]
    elif func == "forge_json":
        url = mod["forgejson"]["url"]
    elif func == "html":
        url = mod["html"]["url"]
    else:
        url = None

    if url:
        await self.send_message(channel, name + ": " + url)
    else:
        await self.send_message(channel, name + ": This mod doesn't have a well-defined URL")


async def cmd_reload_blocklist(self, name, params, channel, userdata, rank):
    self.poller.load_version_blocklist()
    await self.poller.load_mc_blocklist()
    self.poller.load_mc_mapping()
    await self.send_message(channel, "Done, blocklists reloaded.")


# In each entry, the second value in the tuple is the
# rank that is required to be able to use the command.
VOICED = 1
OP = 2
commands = {
    "enable": (cmd_enable, OP),
    "disable": (cmd_disable, OP),
    "poll": (cmd_poll, OP),
    "list": (cmd_list, OP),
    "about": (cmd_about, VOICED),
    "help": (cmd_help, OP),
    "test": (cmd_test, OP),
    "reload": (cmd_reload, OP),
    "html": (cmd_html, OP),
    "set": (cmd_set, OP),
    "status": (cmd_status, VOICED),
    "disabledmods": (cmd_disabled_mods, OP),
    "failedmods": (cmd_failed_mods, OP),
    "failcount": (cmd_fail_count, OP),
    "resetfailed": (cmd_reset_failed, OP),
    "showinfo": (cmd_show_info, OP),
    "url": (cmd_url, VOICED),
    "reloadblocklist": (cmd_reload_blocklist, OP),
    # -- ALIASES -- #
    "polling": (cmd_status, OP),
    "refresh": (cmd_reload, OP),
    "disabled": (cmd_disabled_mods, OP),
    "failed": (cmd_failed_mods, OP),
    "cleanfailed": (cmd_reset_failed, OP),
    "show": (cmd_show_info, OP),
    "reloadblocklists": (cmd_reload_blocklist, OP),
    "running": (cmd_status, OP),
    "start": (cmd_enable, OP),
    "stop": (cmd_disable, OP),
    # -- END ALIASES -- #
}
