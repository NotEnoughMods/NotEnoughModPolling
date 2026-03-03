import asyncio
import importlib
import logging
import shlex
import textwrap

from collections import namedtuple
from commands.NEMP import NEMP_Class

ID = "nemp"
permission = 1
privmsgEnabled = True

nemp_logger = logging.getLogger("NEMPolling")

helpDict = {
    "running": ["{0} running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll": ["{0} poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "list": ["{0} list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["{0} about", "Shows some info about this plugin."],
    "help": ["{0} help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "refresh": ["'{0} refresh' or '{0} reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "reload": ["'{0} refresh' or '{0} reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "test": ["{0} test <mod>", "Tests the parser for <mod> and outputs the contents to IRC"],
    "status": ["{0} status", "Shows whether or not NEMPolling is running and in which channel it is running."],
    "disabledmods": ["{0} disabledmods", "Shows a list of the currently disabled mods."],
    "failedmods": ["{0} failedmods", "Shows a list of mods that have failed to be polled at least 5 times in a row and were disabled automatically."],
    "failcount": ["{0} failcount", "Shows how many times mods have failed to be polled so far. At least two failures in a row required.",
                  "Mods that have failed being polled 5 times are excluded from this list. Check {0} failedmods for those mods."],
    "showinfo": ["{0} showinfo <mod> [<path> [...]]", "Shows polling information for the specified mod."],
    "url": ["{0} url <mod>", "Spits out the URL of the specified mod."],
    'reloadblocklist': ['{0} reloadblocklist', 'Reloads the blocked versions configuration files (version_blocklist.yml and mc_blocklist.yml).'],
}


async def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        cmdName = params[0].lower()
        if cmdName in commands:
            userRank = self.rankconvert[rank]

            command, requiredRank = commands[cmdName]
            nemp_logger.debug("Needed rank: {0} User rank: {1}".format(requiredRank, userRank))
            if userRank >= requiredRank:
                await command(self, name, params, channel, userdata, rank)
            else:
                await self.sendMessage(channel, "You're not authorized to use this command.")
        else:
            await self.sendMessage(channel, name + ": Invalid command! See {0} help for a list of commands".format(self.cmdprefix + ID))
    else:
        await self.sendMessage(channel, name + ": see \"{0} help\" for a list of commands".format(self.cmdprefix + ID))

TIME_EVENT_NAME = 'NotEnoughModPolling'
THREAD_NAME = 'NEMP'

def is_running(self):
    return self.events["time"].doesExist(TIME_EVENT_NAME)


def start_polling(self, timer, channel):
    self.NEM.init_nem_versions()
    self.NEM_cycle_count = 0

    self.threading.addThread(THREAD_NAME, PollingThread, {"NEM": self.NEM, "PollTime": timer})

    self.events["time"].addEvent(TIME_EVENT_NAME, 60, NEMP_TimerEvent, [channel])


def stop_polling(self):
    self.events["time"].removeEvent(TIME_EVENT_NAME)
    nemp_logger.debug("Removed NEM Polling Event")
    self.threading.sigquitThread(THREAD_NAME)
    nemp_logger.debug("Sigquit to NEMP Thread sent")

    self.NEM_troubledMods = {}
    #self.NEM_autodeactivatedMods = {}


async def __initialize__(self, Startup):
    if Startup:
        self.NEM = NEMP_Class.NotEnoughClasses()
    else:
        # kill events, threads
        if is_running(self):
            stop_polling(self)

            nemp_logger.info("NEMP Polling has been disabled.")

        importlib.reload(NEMP_Class)

        self.NEM = NEMP_Class.NotEnoughClasses()

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}
    self.NEM_cycle_count = 0


async def cmd_enable(self, name, params, channel, userdata, rank):
    if is_running(self):
        await self.sendMessage(channel, "NotEnoughModPolling is already running.")
        return

    await self.sendMessage(channel, "Enabling NotEnoughModPolling")

    timerForPolls = 60 * 5

    if len(params) == 2:
        timerForPolls = int(params[1])
        await self.sendMessage(channel, "Timer is set to {} seconds".format(timerForPolls))

    start_polling(self, timerForPolls, channel)


async def cmd_disable(self, name, params, channel, userdata, rank):
    if not is_running(self):
        await self.sendMessage(channel, "NotEnoughModPolling isn't running!")
        return

    await self.sendMessage(channel, "Disabling NotEnoughModPolling")

    try:
        stop_polling(self)
    except Exception as error:
        nemp_logger.exception("Exception appeared while trying to disable NotEnoughModPolling")
        await self.sendMessage(channel, "Exception appeared while trying to disable NotEnoughModPolling")


async def cmd_about(self, name, params, channel, userdata, rank):
    await self.sendMessage(channel, "Not Enough Mods: Polling - Helps keep NEM updated!")
    await self.sendMessage(channel, "Source code available at https://github.com/NotEnoughMods/NotEnoughModPolling")
    await self.sendMessage(channel, "A list of contributors is available at https://github.com/NotEnoughMods/NotEnoughModPolling/graphs/contributors")


async def cmd_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        await self.sendMessage(channel, name + ": Available commands: " + ", ".join(sorted(helpDict.keys())))
        await self.sendMessage(channel, name + ": For command usage, use \"{0} help <command>\".".format(self.cmdprefix + ID))
    else:
        command = params[1]
        if command in helpDict:
            for line in helpDict[command]:
                await self.sendMessage(channel, name + ": " + line.format(self.cmdprefix + ID))
        else:
            await self.sendMessage(channel, name + ": Invalid command provided")


async def cmd_status(self, name, params, channel, userdata, rank):
    if is_running(self):
        channels = ", ".join(self.events["time"].getChannels(TIME_EVENT_NAME))
        await self.sendMessage(channel,
                         "NEM Polling is currently running "
                         "in the following channel(s): {0}. "
                         "Full cycles completed: {1}".format(channels, self.NEM_cycle_count)
                         )
    else:
        await self.sendMessage(channel, "NEM Polling is not running.")


async def cmd_disabled_mods(self, name, params, channel, userdata, rank):
    disabled = [mod for mod, info in self.NEM.mods.items() if not info['active']]

    if len(disabled) == 0:
        await self.sendNotice(name, "No mods are disabled right now.")
    else:
        await self.sendNotice(name,
                        "The following mods are disabled right now: {0}. "
                        "{1} mod(s) total. ".format(", ".join(disabled), len(disabled))
                        )


async def cmd_failed_mods(self, name, params, channel, userdata, rank):
    if len(self.NEM_autodeactivatedMods) == 0:
        await self.sendNotice(name, "No mods have been automatically disabled so far.")
    else:
        disabled = self.NEM_autodeactivatedMods.keys()
        await self.sendNotice(name, "The following mods have been automatically disabled so far: "
                        "{0}. {1} mod(s) total".format(", ".join(disabled), len(disabled)))


async def cmd_reset_failed(self, name, params, channel, userdata, rank):
    failed_mods = self.NEM_autodeactivatedMods.keys()
    for failed_mod in self.NEM_autodeactivatedMods:
        self.NEM.mods[failed_mod]['active'] = True
    self.NEM_autodeactivatedMods = {}
    await self.sendMessage(channel, "Re-enabled {0} automatically disabled mods.".format(len(failed_mods)))
    self.NEM.buildHTML()


async def cmd_fail_count(self, name, params, channel, userdata, rank):
    print(self.NEM_troubledMods)
    if len(self.NEM_troubledMods) == 0:
        await self.sendNotice(name, "No mods have had trouble polling so far.")
    else:
        sortedMods = sorted(self.NEM_troubledMods, key=lambda x: self.NEM_troubledMods[x])
        newlist = []

        for modName in sortedMods:
            if self.NEM_troubledMods[modName] > 1:
                newlist.append((modName + " [{0}x]".format(self.NEM_troubledMods[modName])))

        if len(newlist) == 0:
            await self.sendNotice(name,
                            "{0} mod(s) had trouble being polled once. "
                            "If the mod(s) fail polling a second time, "
                            "they will be shown by this command.".format(len(sortedMods))
                            )
            return

        await self.sendNotice(name,
                        "The following mods have been having trouble being polled at least twice in a row so far: "
                        "{0}. {1} mod(s) total".format(", ".join(newlist), len(newlist))
                        )

        if len(sortedMods) - len(newlist) > 0:
            await self.sendNotice(name,
                            "{0} mod(s) had trouble being polled only a "
                            "single time and thus were not shown.".format(len(sortedMods) - len(newlist))
                            )


FailedModEntry = namedtuple('FailedModEntry', 'name exception')


async def PollingThread(self, pipe):
    NEM = self.base["NEM"]
    sleepTime = self.base["PollTime"]

    while not self.signal:
        nemp_logger.debug("PollingThread: I'm still running!")

        poll_results = []
        document_groups_done = []
        failed = []  # type: List[FailedModEntry]

        # Run the blocking polling work in a thread to avoid blocking the event loop
        def _poll_all():
            results = []
            doc_groups_done = []
            fail_list = []

            for mod_name, mod_info in NEM.mods.items():
                if self.signal:
                    return results, doc_groups_done, fail_list

                if not mod_info["active"]:
                    continue

                document_group = mod_info.get('document_group', {}).get('id')

                if document_group:
                    if document_group in doc_groups_done:
                        continue
                    doc_groups_done.append(document_group)

                    try:
                        mod_results = NEM.CheckMods(mod_name)
                    except Exception as e:
                        document_group_mods = NEM.document_groups[document_group]
                        for document_group_mod in document_group_mods:
                            fail_list.append(FailedModEntry(name=document_group_mod, exception=e))
                        continue

                    for outputMod, outputInfo in mod_results.items():
                        result, exception = outputInfo
                        if exception:
                            fail_list.append(FailedModEntry(name=outputMod, exception=exception))
                        else:
                            results.append((outputMod, result))
                else:
                    statuses, exception = NEM.CheckMod(mod_name)
                    if exception:
                        fail_list.append(FailedModEntry(name=mod_name, exception=exception))
                    else:
                        results.append((mod_name, statuses))

            return results, doc_groups_done, fail_list

        poll_results, document_groups_done, failed = await asyncio.to_thread(_poll_all)

        await pipe.put((poll_results, failed))

        # Sleep in steps of 30 seconds to allow quick shutdown
        for i in range(sleepTime // 30 + 1):
            if self.signal:
                return
            await asyncio.sleep(30)


# This runs on a timer (once every minute)
async def NEMP_TimerEvent(self, channels):
    # Check if we have any data from PollingThread to process
    if not self.threading.poll(THREAD_NAME):
        return

    nemp_data = await self.threading.recv(THREAD_NAME)

    self.NEM_cycle_count += 1

    staff_channel = self.NEM.config.get('irc', {}).get('staff_channel')

    if staff_channel and self.NEM_cycle_count % 50 == 0:
        await self.sendMessage(staff_channel, 'Full cycles completed: {}'.format(self.NEM_cycle_count))
        if self.NEM_autodeactivatedMods:
            await self.sendMessage(staff_channel, 'There are {} failed mod(s)'.format(len(self.NEM_autodeactivatedMods)))

    if isinstance(nemp_data, dict) and "action" in nemp_data and nemp_data["action"] == "exceptionOccured":
        nemp_logger.error("NEMP Thread {0} encountered an unhandled exception: {1}".format(nemp_data["functionName"],
                                                                                           str(nemp_data["exception"])))
        nemp_logger.error("Traceback Start")
        nemp_logger.error(nemp_data["traceback"])
        nemp_logger.error("Traceback End")

        nemp_logger.error("Shutting down NEMP Events and Polling")
        stop_polling(self)

        self.NEM_troubledMods = {}
        self.NEM_autodeactivatedMods = {}

        return

    poll_results, failedMods = nemp_data

    for item in poll_results:
        mod_name = item[0]
        new_versions = item[1]

        nem_mod_name = self.NEM.mods[mod_name].get('name', mod_name)

        for new_version in new_versions:
            mc_version, dev_version, release_version, changelog = new_version

            last_dev = self.NEM.get_nem_dev_version(mod_name, mc_version)
            last_release = self.NEM.get_nem_version(mod_name, mc_version)

            if not last_dev and not last_release:
                if release_version:
                    clone_version = release_version
                else:
                    clone_version = 'dev-only'

                self.NEM.set_nem_version(mod_name, clone_version, mc_version)

                nemp_logger.debug('Cloning mod {} to {}, status: {}'.format(mod_name, mc_version, new_version))
                for channel in channels:
                    await self.sendMessage(channel, '!clone {} {} {}'.format(nem_mod_name, mc_version, clone_version))
            elif release_version:
                nemp_logger.debug("Updating Mod {0}, status: {1}".format(mod_name, new_version))
                self.NEM.set_nem_version(mod_name, release_version, mc_version)
                for channel in channels:
                    await self.sendMessage(channel, "!lmod {} {} {}".format(mc_version, nem_mod_name, release_version))

            if dev_version:
                if release_version and dev_version == release_version:
                    nemp_logger.debug("Would update mod {} to dev {}, but it matches the new release {}".format(
                        mod_name, dev_version, release_version
                    ))
                elif last_release and dev_version == last_release:
                    nemp_logger.debug("Would update mod {} to dev {}, but it matches the current release {}".format(
                        mod_name, dev_version, release_version
                    ))
                else:
                    nemp_logger.debug("Updating mod {} to dev {}, status: {}".format(mod_name, dev_version, new_version))
                    self.NEM.set_nem_dev_version(mod_name, dev_version, mc_version)
                    for channel in channels:
                        await self.sendMessage(channel, "!ldev {} {} {}".format(mc_version, nem_mod_name, dev_version))

            if changelog and "changelog" not in self.NEM.mods[mod_name]:
                nemp_logger.debug("Sending text for Mod {0}".format(mod_name))
                for channel in channels:
                    await self.sendMessage(channel, " * " + ' | '.join(changelog.splitlines())[:300])

    current_troubled_mods = list(self.NEM_troubledMods.keys())

    completely_failed_mods = []

    for item in failedMods:  # type: FailedModEntry
        nemp_logger.debug('Processing failedMods entry {!r}'.format(item))

        assert(isinstance(item, FailedModEntry))

        mod_name = item.name
        exception = item.exception

        if isinstance(exception, (NEMP_Class.NEMPException, )):
            nemp_logger.debug('Mod {} got a {}, failing immediately'.format(mod_name, type(exception).__name__))

            if mod_name in self.NEM_troubledMods:
                del self.NEM_troubledMods[mod_name]
                current_troubled_mods.remove(mod_name)

            self.NEM_autodeactivatedMods[mod_name] = True
            self.NEM.mods[mod_name]['active'] = False

            if staff_channel:
                await self.sendMessage(staff_channel, 'Mod {} \00304failed\003 with a {}: {}'.format(mod_name, type(exception).__name__, exception))
        else:
            if mod_name not in self.NEM_troubledMods:
                self.NEM_troubledMods[mod_name] = 1
                nemp_logger.debug("Mod {0} had trouble being polled once. Counter set to 1".format(mod_name))

            else:
                self.NEM_troubledMods[mod_name] += 1

                current_troubled_mods.remove(mod_name)

                if self.NEM_troubledMods[mod_name] >= 5:
                    self.NEM_autodeactivatedMods[mod_name] = True
                    self.NEM.mods[mod_name]["active"] = False
                    del self.NEM_troubledMods[mod_name]

                    completely_failed_mods.append(mod_name)

                    nemp_logger.debug("Mod {0} has failed to be polled at least 5 times, it has been disabled.".format(mod_name))

    self.NEM.buildHTML()

    if staff_channel and completely_failed_mods:
        await self.sendMessage(staff_channel, 'The following mod(s) \00304failed\003: {0}.'.format(', '.join(sorted(completely_failed_mods, key=lambda x: x.lower()))))

    for mod_name in current_troubled_mods:
        nemp_logger.debug("Mod {0} is working again. Counter reset (Counter was at {1}) ".format(mod_name, self.NEM_troubledMods[mod_name]))
        del self.NEM_troubledMods[mod_name]


async def cmd_poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        await self.sendMessage(channel, name + ": Insufficient amount of parameters provided. Required: 2")
        await self.sendMessage(channel, name + ": " + helpDict["poll"][1])
        return

    if params[2].lower() in ("true", "yes", "on"):
        setting = True
    elif params[2].lower() in ("false", "no", "off"):
        setting = False
    else:
        await self.sendMessage(channel, '{}: Invalid value. Must be: on/yes/true, off/no/false')
        return

    # "c:" is the category operator
    if params[1][0:2].lower() == "c:":
        category = params[1][2:].lower()
        match_mods = {k: v for k, v in self.NEM.mods.items() if v.get('category', '').lower() == category}

        if not match_mods:
            await self.sendMessage(channel, '{}: Could not find any matches.'.format(name))
        else:
            for mod, info in match_mods.items():
                info["active"] = setting

                if mod in self.NEM_autodeactivatedMods:
                    del self.NEM_autodeactivatedMods[mod]
                if mod in self.NEM_troubledMods:
                    del self.NEM_troubledMods[mod]
            await self.sendMessage(channel, name + ": " + ', '.join(sorted(match_mods.keys(), key=lambda x: x.lower())) + "'s poll status is now " + str(setting))

    # "p:" is the parser operator
    elif params[1].lower().startswith('p:'):
        parser = params[1][2:].lower()
        match_mods = {k: v for k, v in self.NEM.mods.items() if v['function'][5:].lower() == parser}

        if not match_mods:
            await self.sendMessage(channel, '{}: Could not find any matches.'.format(name))
        else:
            for mod, info in match_mods.items():
                info['active'] = setting

                if mod in self.NEM_autodeactivatedMods:
                    del self.NEM_autodeactivatedMods[mod]
                if mod in self.NEM_troubledMods:
                    del self.NEM_troubledMods[mod]
            await self.sendMessage(channel, name + ": " + ', '.join(sorted(match_mods.keys(), key=lambda x: x.lower())) + "'s poll status is now " + str(setting))

    # "all" or "*" matches all mods
    elif params[1].lower() == "all" or params[1] == '*':
        for mod in self.NEM.mods:
            self.NEM.mods[mod]["active"] = setting

            if mod in self.NEM_autodeactivatedMods:
                del self.NEM_autodeactivatedMods[mod]
            if mod in self.NEM_troubledMods:
                del self.NEM_troubledMods[mod]

        await self.sendMessage(channel, name + ": All mods are now set to " + str(setting))

    else:
        mod = self.NEM.get_proper_name(params[1])

        if not mod:
            await self.sendMessage(channel, name + ': No such mod in NEMP.')
            return

        self.NEM.mods[mod]["active"] = setting
        await self.sendMessage(channel, name + ": " + mod + "'s poll status is now " + str(setting))

        if mod in self.NEM_autodeactivatedMods:
            del self.NEM_autodeactivatedMods[mod]
        if mod in self.NEM_troubledMods:
            del self.NEM_troubledMods[mod]
    self.NEM.buildHTML()


async def cmd_list(self, name, params, channel, userdata, rank):
    dest = None
    if len(params) > 1:
        if rank != '@@':
            await self.sendMessage(channel, '{}: Access denied.'.format(name))
            return

        if params[1] == "pm":
            dest = name
        elif params[1] == "broadcast":
            dest = channel

    if dest is None:
        await self.sendMessage(channel, "http://polling.notenoughmods.com/")
        return

    darkgreen = "03"
    red = "05"
    blue = "12"
    bold = chr(2)
    color = chr(3)
    tempList = {}
    for key, info in self.NEM.mods.items():
        real_name = info.get('name', key)
        if self.NEM.mods[key]["active"]:
            relType = ""
            mcver = self.NEM.mods[key]["mc"]
            if self.NEM.get_nem_version(key, mcver):
                relType = relType + color + darkgreen + "[R]" + color
            if self.NEM.get_nem_dev_version(key, mcver):
                relType = relType + color + red + "[D]" + color

            if mcver not in tempList:
                tempList[mcver] = []
            tempList[mcver].append("{0}{1}".format(real_name, relType))

    del mcver
    for mcver in sorted(tempList.keys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        await self.sendMessage(dest, "Mods checked for {} ({}): {}".format(color + blue + bold + mcver + color + bold, len(tempList[mcver]), ', '.join(tempList[mcver])))


async def cmd_reload(self, name, params, channel, userdata, rank):
    if is_running(self):
        stop_polling(self)

        await self.sendMessage(channel, "NEMP Polling has been deactivated")

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}

    self.NEM.buildModDict()
    self.NEM.QueryNEM()
    self.NEM.init_nem_versions()
    self.NEM.buildHTML()

    await self.sendMessage(channel, "Reloaded the NEMP Database")


async def cmd_test(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        await self.sendMessage(channel, "{name}: Wrong number of parameters. This command accepts 1 parameter: the mod's name".format(name=name))
        return

    mod = self.NEM.get_proper_name(params[1])

    if not mod:
        await self.sendMessage(channel, name + ": Mod \"" + params[1] + "\" does not exist in the database.")
        return

    try:
        if 'document_group' in self.NEM.mods[mod]:
            document = getattr(self.NEM, self.NEM.mods[mod]["function"])(mod, None)
        else:
            document = None
    except Exception as exception:
        await self.sendMessage(channel, '{}: Failed to obtain document for mod: {}: {}'.format(
            name, type(exception).__name__, exception
        ))
        return

    statuses, exception = self.NEM.CheckMod(mod, document=document, simulation=True)

    if exception:
        await self.sendMessage(channel, 'Got an exception: {}: {}'.format(type(exception).__name__, exception))
        return

    if not statuses:
        await self.sendMessage(channel, name + ": Got no results from the parser")

    real_name = self.NEM.mods[mod].get('name', mod)

    print('{} {!r}'.format(mod, statuses))

    commands_list = []

    for status in statuses:
        mc_version, dev_version, release_version, changelog = status

        last_dev = self.NEM.get_nem_dev_version(mod, mc_version)
        last_release = self.NEM.get_nem_version(mod, mc_version)

        if not last_dev and not last_release:
            if release_version:
                clone_version = release_version
            else:
                clone_version = 'dev-only'

            commands_list.append('clone {} {} {}'.format(real_name, mc_version, clone_version))
        elif release_version:
            commands_list.append('lmod {} {} {}'.format(mc_version, real_name, release_version))

        if dev_version:
            commands_list.append('ldev {} {} {}'.format(mc_version, real_name, dev_version))

        if changelog and 'changelog' not in self.NEM.mods[mod]:
            commands_list.append(' * ' + ' | '.join(changelog.splitlines())[:300])

    for line in textwrap.wrap(', '.join(commands_list), width=300):
        await self.sendMessage(channel, line)


async def cmd_html(self, name, params, channel, userdata, rank):
    self.NEM.buildHTML()
    await self.sendMessage(channel, name + ': Done.')


async def cmd_set(self, name, params, channel, userdata, rank):
    if len(params) < 4:
        await self.sendMessage(channel, "This is not a toy!")
        return

    try:
        args = shlex.split(' '.join(params[2:]))
    except:
        await self.sendMessage(channel, "That looks like invalid input (are there any unescaped quotes?). Try again.")
        return

    args.insert(0, params[1])

    available_casts = {
        'int': int,
        'float': float
    }

    cast_to = None

    if args and args[0] == '--type':
        if args[1] in available_casts:
            cast_to = available_casts[args[1]]
            args = args[2:]
        else:
            await self.sendMessage(channel, "Unknown type. Available types are: " + ', '.join(available_casts.keys()))
            return

    mod = self.NEM.get_proper_name(args[0])

    if not mod:
        await self.sendMessage(channel, name + ': No such mod in NEMP.')
        return

    if args[1] == 'active':
        await self.sendMessage(channel, "You want =nemp poll instead.")
        return

    try:
        if cast_to:
            new_value = cast_to(args[-1])
        else:
            new_value = args[-1]

        elem = self.NEM.mods[mod]

        path = args[1:-2]

        for path_elem in path:
            elem = elem[path_elem]

        elem[args[-2]] = new_value

        self.NEM.compile_regex(mod)

        await self.sendMessage(channel, "done.")
    except KeyError:
        await self.sendMessage(channel, name + ": No such element in that mod's configuration.")
    except Exception as e:
        await self.sendMessage(channel, "Error: " + str(e))


async def cmd_show_info(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.sendMessage(channel, name + ": You have to specify at least the mod's name.")
        return

    mod = self.NEM.get_proper_name(params[1])

    if not mod:
        await self.sendMessage(channel, name + ": No such mod in NEMP.")
        return

    if len(params) > 1:
        path = params[2:]
    else:
        path = []

    try:
        elem = self.NEM.mods[mod]
        for path_elem in path:
            if not isinstance(elem, dict):
                raise KeyError()
            elem = elem[path_elem]

        await self.sendMessage(channel, name + ": " + repr(elem))
    except KeyError:
        await self.sendMessage(channel, name + ": No such element in that mod's configuration.")


async def cmd_url(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.sendMessage(channel, name + ": You have to specify at least the mod's name.")
        return

    modname = self.NEM.get_proper_name(params[1])

    if not modname:
        await self.sendMessage(channel, name + ": No such mod in NEMP.")
        return

    mod = self.NEM.mods[modname]
    func = mod["function"]

    if func == "CheckGitHubRelease":
        url = "https://github.com/" + mod["github"]["repo"]
    elif func == "CheckCurse":
        url = 'https://api.cfwidget.com/' + mod['curse']['id']
    elif func == "CheckJenkins":
        url = mod["jenkins"]["url"][:-28]
    elif func == "CheckChickenBones":
        url = "http://www.chickenbones.net/Files/notification/version.php?version=" + mod['mc'] + "&file=" + modname
    elif func == 'CheckForgeJson':
        url = mod['forgejson']['url']
    elif func == 'CheckHTML':
        url = mod['html']['url']
    else:
        url = None

    if url:
        await self.sendMessage(channel, name + ": " + url)
    else:
        await self.sendMessage(channel, name + ": This mod doesn't have a well-defined URL")


async def cmd_reload_blocklist(self, name, params, channel, userdata, rank):
    self.NEM.load_version_blocklist()
    self.NEM.load_mc_blocklist()
    self.NEM.load_mc_mapping()
    await self.sendMessage(channel, 'Done, blocklists reloaded.')


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
    'reloadblocklist': (cmd_reload_blocklist, OP),

    # -- ALIASES -- #
    "polling": (cmd_status, OP),
    "refresh": (cmd_reload, OP),
    "disabled": (cmd_disabled_mods, OP),
    "failed": (cmd_failed_mods, OP),
    "cleanfailed": (cmd_reset_failed, OP),
    "show": (cmd_show_info, OP),
    'reloadblocklists': (cmd_reload_blocklist, OP),
    "running": (cmd_status, OP),
    "start": (cmd_enable, OP),
    "stop": (cmd_disable, OP),
    # -- END ALIASES -- #
}
