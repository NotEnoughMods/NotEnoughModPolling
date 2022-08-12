import logging
import shlex
import time
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


def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        cmdName = params[0].lower()
        if cmdName in commands:
            userRank = self.rankconvert[rank]

            command, requiredRank = commands[cmdName]
            nemp_logger.debug("Needed rank: {0} User rank: {1}".format(requiredRank, userRank))
            if userRank >= requiredRank:
                command(self, name, params, channel, userdata, rank)
            else:
                self.sendMessage(channel, "You're not authorized to use this command.")
        else:
            self.sendMessage(channel, name + ": Invalid command! See {0} help for a list of commands".format(self.cmdprefix + ID))
    else:
        self.sendMessage(channel, name + ": see \"{0} help\" for a list of commands".format(self.cmdprefix + ID))

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


def __initialize__(self, Startup):
    if Startup:
        self.NEM = NEMP_Class.NotEnoughClasses()
    else:
        # kill events, threads
        if is_running(self):
            stop_polling(self)

            nemp_logger.info("NEMP Polling has been disabled.")

        reload(NEMP_Class)

        self.NEM = NEMP_Class.NotEnoughClasses()

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}
    self.NEM_cycle_count = 0


def cmd_enable(self, name, params, channel, userdata, rank):
    if is_running(self):
        self.sendMessage(channel, "NotEnoughModPolling is already running.")
        return

    self.sendMessage(channel, "Enabling NotEnoughModPolling")

    timerForPolls = 60 * 5

    if len(params) == 2:
        timerForPolls = int(params[1])
        self.sendMessage(channel, "Timer is set to {} seconds".format(timerForPolls))

    start_polling(self, timerForPolls, channel)


def cmd_disable(self, name, params, channel, userdata, rank):
    if not is_running(self):
        self.sendMessage(channel, "NotEnoughModPolling isn't running!")
        return

    self.sendMessage(channel, "Disabling NotEnoughModPolling")

    try:
        stop_polling(self)
    except Exception as error:
        nemp_logger.exception("Exception appeared while trying to disable NotEnoughModPolling")
        self.sendMessage(channel, "Exception appeared while trying to disable NotEnoughModPolling")


def cmd_about(self, name, params, channel, userdata, rank):
    self.sendMessage(channel, "Not Enough Mods: Polling - Helps keep NEM updated!")
    self.sendMessage(channel, "Source code available at https://github.com/NotEnoughMods/NotEnoughModPolling")
    self.sendMessage(channel, "A list of contributors is available at https://github.com/NotEnoughMods/NotEnoughModPolling/graphs/contributors")


def cmd_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendMessage(channel, name + ": Available commands: " + ", ".join(sorted(helpDict.keys())))
        self.sendMessage(channel, name + ": For command usage, use \"{0} help <command>\".".format(self.cmdprefix + ID))
    else:
        command = params[1]
        if command in helpDict:
            for line in helpDict[command]:
                self.sendMessage(channel, name + ": " + line.format(self.cmdprefix + ID))
        else:
            self.sendMessage(channel, name + ": Invalid command provided")


def cmd_status(self, name, params, channel, userdata, rank):
    if is_running(self):
        channels = ", ".join(self.events["time"].getChannels(TIME_EVENT_NAME))
        self.sendMessage(channel,
                         "NEM Polling is currently running "
                         "in the following channel(s): {0}. "
                         "Full cycles completed: {1}".format(channels, self.NEM_cycle_count)
                         )
    else:
        self.sendMessage(channel, "NEM Polling is not running.")


def cmd_disabled_mods(self, name, params, channel, userdata, rank):
    disabled = [mod for mod, info in self.NEM.mods.iteritems() if not info['active']]

    if len(disabled) == 0:
        self.sendNotice(name, "No mods are disabled right now.")
    else:
        self.sendNotice(name,
                        "The following mods are disabled right now: {0}. "
                        "{1} mod(s) total. ".format(", ".join(disabled), len(disabled))
                        )


def cmd_failed_mods(self, name, params, channel, userdata, rank):
    if len(self.NEM_autodeactivatedMods) == 0:
        self.sendNotice(name, "No mods have been automatically disabled so far.")
    else:
        disabled = self.NEM_autodeactivatedMods.keys()
        self.sendNotice(name, "The following mods have been automatically disabled so far: "
                        "{0}. {1} mod(s) total".format(", ".join(disabled), len(disabled)))


def cmd_reset_failed(self, name, params, channel, userdata, rank):
    failed_mods = self.NEM_autodeactivatedMods.keys()
    for failed_mod in self.NEM_autodeactivatedMods:
        self.NEM.mods[failed_mod]['active'] = True
    self.NEM_autodeactivatedMods = {}
    self.sendMessage(channel, "Re-enabled {0} automatically disabled mods.".format(len(failed_mods)))
    self.NEM.buildHTML()


def cmd_fail_count(self, name, params, channel, userdata, rank):
    print self.NEM_troubledMods
    if len(self.NEM_troubledMods) == 0:
        self.sendNotice(name, "No mods have had trouble polling so far.")
    else:
        sortedMods = sorted(self.NEM_troubledMods, key=lambda x: self.NEM_troubledMods[x])
        newlist = []

        for modName in sortedMods:
            if self.NEM_troubledMods[modName] > 1:
                newlist.append((modName + " [{0}x]".format(self.NEM_troubledMods[modName])))

        if len(newlist) == 0:
            self.sendNotice(name,
                            "{0} mod(s) had trouble being polled once. "
                            "If the mod(s) fail polling a second time, "
                            "they will be shown by this command.".format(len(sortedMods))
                            )
            return

        self.sendNotice(name,
                        "The following mods have been having trouble being polled at least twice in a row so far: "
                        "{0}. {1} mod(s) total".format(", ".join(newlist), len(newlist))
                        )

        if len(sortedMods) - len(newlist) > 0:
            self.sendNotice(name,
                            "{0} mod(s) had trouble being polled only a "
                            "single time and thus were not shown.".format(len(sortedMods) - len(newlist))
                            )


FailedModEntry = namedtuple('FailedModEntry', 'name exception')


def PollingThread(self, pipe):
    NEM = self.base["NEM"]
    sleepTime = self.base["PollTime"]

    while self.signal == False:
        nemp_logger.debug("PollingThread: I'm still running!")

        poll_results = []
        document_groups_done = []
        failed = []  # type: List[FailedModEntry]

        for mod_name, mod_info in NEM.mods.iteritems():
            # Check if the thread was requested to terminate
            if self.signal:
                return

            if not mod_info["active"]:
                continue

            document_group = mod_info.get('document_group', {}).get('id')

            if document_group:
                # Have we processed this document group before? If we have, skip mods from this group.
                if document_group in document_groups_done:
                    # nemp_logger.debug("Already polled document group {} before".format(document_group))
                    # continue to next mod
                    continue

                # Remember this poll cycle that we have processed this document group
                document_groups_done.append(document_group)

                try:
                    results = NEM.CheckMods(mod_name)
                except Exception as e:
                    # We got an exception when getting the document, so we mark every mod in this group as failed
                    document_group_mods = NEM.document_groups[document_group]
                    for document_group_mod in document_group_mods:
                        failed.append(FailedModEntry(name=document_group_mod, exception=e))
                    # drop out (to the next mod)
                    continue

                for outputMod, outputInfo in results.iteritems():
                    result, exception = outputInfo

                    if exception:
                        failed.append(FailedModEntry(name=outputMod, exception=exception))
                    else:
                        poll_results.append((outputMod, result))
            else:
                statuses, exception = NEM.CheckMod(mod_name)

                if exception:
                    failed.append(FailedModEntry(name=mod_name, exception=exception))
                else:
                    poll_results.append((mod_name, statuses))

        pipe.send((poll_results, failed))

        # A more reasonable way of sleeping to quicken up the
        # shutdown of the thread. Sleep in steps of 30 seconds
        for i in xrange(sleepTime // 30 + 1):
            # print "Sleeping for 30s, step %s" % i
            if self.signal:
                return
            else:
                time.sleep(30)


# This runs on a timer (once every minute)
def NEMP_TimerEvent(self, channels):
    # Check if we have any data from PollingThread to process
    if not self.threading.poll(THREAD_NAME):
        return

    # nemp_data is either:
    # - (poll_results, failed_mods)
    # - { 'action': 'exceptionOccured', 'functionName': 'NEMP_TimerEvent', 'exception': exception, 'traceback': traceback }
    # The latter comes from Renol thread handling
    nemp_data = self.threading.recv(THREAD_NAME)

    self.NEM_cycle_count += 1

    staff_channel = self.NEM.config.get('irc', {}).get('staff_channel')

    if staff_channel and self.NEM_cycle_count % 50 == 0:
        self.sendMessage(staff_channel, 'Full cycles completed: {}'.format(self.NEM_cycle_count))
        if self.NEM_autodeactivatedMods:
            self.sendMessage(staff_channel, 'There are {} failed mod(s)'.format(len(self.NEM_autodeactivatedMods)))

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
        # item[0] = name of mod
        # item[1] = list of versions
        # assume status = item[1][x]:
        # status[0] = mc version
        # status[1] = dev version
        # status[2] = release version
        # status[3] = changelog
        mod_name = item[0]
        new_versions = item[1]

        # Get the mod's NEM name, defaults to NEMP name
        nem_mod_name = self.NEM.mods[mod_name].get('name', mod_name)

        for new_version in new_versions:
            mc_version, dev_version, release_version, changelog = new_version

            last_dev = self.NEM.get_nem_dev_version(mod_name, mc_version)
            last_release = self.NEM.get_nem_version(mod_name, mc_version)

            if not last_dev and not last_release:
                # There's no previously known dev or release version in NEM, so it's new to this NEM list/MC version.
                # This means we need to run the !clone command

                # Check if we have a release version to use in the clone command
                # Setting the dev version is handled later
                if release_version:
                    clone_version = release_version
                else:
                    clone_version = 'dev-only'

                self.NEM.set_nem_version(mod_name, clone_version, mc_version)

                nemp_logger.debug('Cloning mod {} to {}, status: {}'.format(mod_name, mc_version, new_version))
                for channel in channels:
                    self.sendMessage(channel, '!clone {} {} {}'.format(nem_mod_name, mc_version, clone_version))
            elif release_version:
                # The mod has a previous release/stable version in NEM, so we simply update that
                nemp_logger.debug("Updating Mod {0}, status: {1}".format(mod_name, new_version))
                self.NEM.set_nem_version(mod_name, release_version, mc_version)
                for channel in channels:
                    self.sendMessage(channel, "!lmod {} {} {}".format(mc_version, nem_mod_name, release_version))

            if dev_version:
                # If this version update has a release version, and the dev version is the same, we ignore it
                if release_version and dev_version == release_version:
                    nemp_logger.debug("Would update mod {} to dev {}, but it matches the new release {}".format(
                        mod_name, dev_version, release_version
                    ))
                # If the dev version in this version update matches the current NEM release/stable version, we ignore it
                elif last_release and dev_version == last_release:
                    nemp_logger.debug("Would update mod {} to dev {}, but it matches the current release {}".format(
                        mod_name, dev_version, release_version
                    ))
                # This mod is new to this NEM list/MC version (no last release version) and we have a dev version, so
                # we set it here
                else:
                    nemp_logger.debug("Updating mod {} to dev {}, status: {}".format(mod_name, dev_version, new_version))
                    self.NEM.set_nem_dev_version(mod_name, dev_version, mc_version)
                    for channel in channels:
                        self.sendMessage(channel, "!ldev {} {} {}".format(mc_version, nem_mod_name, dev_version))

            # If we have a changelog, and it's not explicitly disabled in the mod's configuration (via an existing
            # "changelog" key), then we send it to the channel. The value of the "changelog" key is ignored entirely.
            if changelog and "changelog" not in self.NEM.mods[mod_name]:
                nemp_logger.debug("Sending text for Mod {0}".format(mod_name))
                for channel in channels:
                    self.sendMessage(channel, " * " + ' | '.join(changelog.splitlines())[:300])

    # A temporary list containing the mods that have failed to be polled so far.
    # We use it to check if the same mods had trouble in the newest polling attempt.
    # If not, the counter for each mod that succeeded to be polled will be reset.
    current_troubled_mods = self.NEM_troubledMods.keys()

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
                self.sendMessage(staff_channel, 'Mod {} \00304failed\003 with a {}: {}'.format(mod_name, type(exception).__name__, exception))
        else:
            if mod_name not in self.NEM_troubledMods:
                self.NEM_troubledMods[mod_name] = 1
                nemp_logger.debug("Mod {0} had trouble being polled once. Counter set to 1".format(mod_name))

            else:
                self.NEM_troubledMods[mod_name] += 1

                # We have checked the mod, so we remove it from our temporary list
                current_troubled_mods.remove(mod_name)

                if self.NEM_troubledMods[mod_name] >= 5:
                    self.NEM_autodeactivatedMods[mod_name] = True
                    self.NEM.mods[mod_name]["active"] = False
                    del self.NEM_troubledMods[mod_name]

                    completely_failed_mods.append(mod_name)

                    nemp_logger.debug("Mod {0} has failed to be polled at least 5 times, it has been disabled.".format(mod_name))

    self.NEM.buildHTML()

    if staff_channel and completely_failed_mods:
        self.sendMessage(staff_channel, 'The following mod(s) \00304failed\003: {0}.'.format(', '.join(sorted(completely_failed_mods, key=lambda x: x.lower()))))

    # Reset counter for any mod that is still in the list.
    for mod_name in current_troubled_mods:
        nemp_logger.debug("Mod {0} is working again. Counter reset (Counter was at {1}) ".format(mod_name, self.NEM_troubledMods[mod_name]))
        del self.NEM_troubledMods[mod_name]


def cmd_poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        self.sendMessage(channel, name + ": Insufficient amount of parameters provided. Required: 2")
        self.sendMessage(channel, name + ": " + helpDict["poll"][1])
        return

    if params[2].lower() in ("true", "yes", "on"):
        setting = True
    elif params[2].lower() in ("false", "no", "off"):
        setting = False
    else:
        self.sendMessage(channel, '{}: Invalid value. Must be: on/yes/true, off/no/false')
        return

    # "c:" is the category operator
    if params[1][0:2].lower() == "c:":
        category = params[1][2:].lower()
        match_mods = {k: v for k, v in self.NEM.mods.iteritems() if v.get('category', '').lower() == category}

        if not match_mods:
            self.sendMessage(channel, '{}: Could not find any matches.'.format(name))
        else:
            for mod, info in match_mods.iteritems():
                info["active"] = setting

                # The mod has been manually activated or deactivated, so we remove it from the
                # autodeactivatedMods dictionary.
                if mod in self.NEM_autodeactivatedMods:
                    del self.NEM_autodeactivatedMods[mod]
                if mod in self.NEM_troubledMods:
                    del self.NEM_troubledMods[mod]
            self.sendMessage(channel, name + ": " + ', '.join(sorted(match_mods.keys(), key=lambda x: x.lower())) + "'s poll status is now " + str(setting))

    # "p:" is the parser operator
    elif params[1].lower().startswith('p:'):
        parser = params[1][2:].lower()
        match_mods = {k: v for k, v in self.NEM.mods.iteritems() if v['function'][5:].lower() == parser}

        if not match_mods:
            self.sendMessage(channel, '{}: Could not find any matches.'.format(name))
        else:
            for mod, info in match_mods.iteritems():
                info['active'] = setting

                if mod in self.NEM_autodeactivatedMods:
                    del self.NEM_autodeactivatedMods[mod]
                if mod in self.NEM_troubledMods:
                    del self.NEM_troubledMods[mod]
            self.sendMessage(channel, name + ": " + ', '.join(sorted(match_mods.keys(), key=lambda x: x.lower())) + "'s poll status is now " + str(setting))

    # "all" or "*" matches all mods
    elif params[1].lower() == "all" or params[1] == '*':
        for mod in self.NEM.mods:
            self.NEM.mods[mod]["active"] = setting

            if mod in self.NEM_autodeactivatedMods:
                del self.NEM_autodeactivatedMods[mod]
            if mod in self.NEM_troubledMods:
                del self.NEM_troubledMods[mod]

        self.sendMessage(channel, name + ": All mods are now set to " + str(setting))

    else:
        mod = self.NEM.get_proper_name(params[1])

        if not mod:
            self.sendMessage(channel, name + ': No such mod in NEMP.')
            return

        self.NEM.mods[mod]["active"] = setting
        self.sendMessage(channel, name + ": " + mod + "'s poll status is now " + str(setting))

        if mod in self.NEM_autodeactivatedMods:
            del self.NEM_autodeactivatedMods[mod]
        if mod in self.NEM_troubledMods:
            del self.NEM_troubledMods[mod]
    self.NEM.buildHTML()


def cmd_list(self, name, params, channel, userdata, rank):
    dest = None
    if len(params) > 1:
        if rank != '@@':
            self.sendMessage(channel, '{}: Access denied.'.format(name))
            return

        if params[1] == "pm":
            dest = name
        elif params[1] == "broadcast":
            dest = channel

    if dest is None:
        self.sendMessage(channel, "http://polling.notenoughmods.com/")
        return

    darkgreen = "03"
    red = "05"
    blue = "12"
    bold = unichr(2)
    color = unichr(3)
    tempList = {}
    for key, info in self.NEM.mods.iteritems():
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
    for mcver in sorted(tempList.iterkeys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        self.sendMessage(dest, "Mods checked for {} ({}): {}".format(color + blue + bold + mcver + color + bold, len(tempList[mcver]), ', '.join(tempList[mcver])))


def cmd_reload(self, name, params, channel, userdata, rank):
    if is_running(self):
        stop_polling(self)

        self.sendMessage(channel, "NEMP Polling has been deactivated")

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}

    self.NEM.buildModDict()
    self.NEM.QueryNEM()
    self.NEM.init_nem_versions()
    self.NEM.buildHTML()

    self.sendMessage(channel, "Reloaded the NEMP Database")


def cmd_test(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendMessage(channel, "{name}: Wrong number of parameters. This command accepts 1 parameter: the mod's name".format(name=name))
        return

    mod = self.NEM.get_proper_name(params[1])

    if not mod:
        self.sendMessage(channel, name + ": Mod \"" + params[1] + "\" does not exist in the database.")
        return

    try:
        if 'document_group' in self.NEM.mods[mod]:
            document = getattr(self.NEM, self.NEM.mods[mod]["function"])(mod, None)
        else:
            document = None
    except Exception as exception:
        self.sendMessage(channel, '{}: Failed to obtain document for mod: {}: {}'.format(
            name, type(exception).__name__, exception
        ))
        return

    statuses, exception = self.NEM.CheckMod(mod, document=document, simulation=True)

    if exception:
        self.sendMessage(channel, 'Got an exception: {}: {}'.format(type(exception).__name__, exception))
        return

    if not statuses:
        self.sendMessage(channel, name + ": Got no results from the parser")

    real_name = self.NEM.mods[mod].get('name', mod)

    print '{} {!r}'.format(mod, statuses)

    commands = []

    for status in statuses:
        mc_version, dev_version, release_version, changelog = status

        last_dev = self.NEM.get_nem_dev_version(mod, mc_version)
        last_release = self.NEM.get_nem_version(mod, mc_version)

        if not last_dev and not last_release:
            if release_version:
                clone_version = release_version
            else:
                clone_version = 'dev-only'

            commands.append('clone {} {} {}'.format(real_name, mc_version, clone_version))
        elif release_version:
            commands.append('lmod {} {} {}'.format(mc_version, real_name, release_version))

        if dev_version:
            commands.append('ldev {} {} {}'.format(mc_version, real_name, dev_version))

        if changelog and 'changelog' not in self.NEM.mods[mod]:
            commands.append(' * ' + ' | '.join(changelog.splitlines())[:300])

    for line in textwrap.wrap(', '.join(commands), width=300):
        self.sendMessage(channel, line)


def cmd_html(self, name, params, channel, userdata, rank):
    self.NEM.buildHTML()
    self.sendMessage(channel, name + ': Done.')


def cmd_set(self, name, params, channel, userdata, rank):
    if len(params) < 4:
        self.sendMessage(channel, "This is not a toy!")
        return

    # Split the arguments in a shell-like fashion
    try:
        args = shlex.split(' '.join(params[2:]))
    except:
        self.sendMessage(channel, "That looks like invalid input (are there any unescaped quotes?). Try again.")
        return

    # insert the mod's name as the first argument
    args.insert(0, params[1])

    available_casts = {
        'int': int,
        'float': float
    }

    cast_to = None

    if args and args[0] == '--type':
        if args[1] in available_casts:
            cast_to = available_casts[args[1]]
            # Trim out these 2 args so the rest will work just fine
            args = args[2:]
        else:
            self.sendMessage(channel, "Unknown type. Available types are: " + ', '.join(available_casts.iterkeys()))
            return

    mod = self.NEM.get_proper_name(args[0])

    if not mod:
        self.sendMessage(channel, name + ': No such mod in NEMP.')
        return

    if args[1] == 'active':
        self.sendMessage(channel, "You want =nemp poll instead.")
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

        # recompile the regex just in case it was changed manually
        self.NEM.compile_regex(mod)

        self.sendMessage(channel, "done.")
    except KeyError:
        self.sendMessage(channel, name + ": No such element in that mod's configuration.")
    except Exception as e:
        self.sendMessage(channel, "Error: " + str(e))


def cmd_show_info(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        self.sendMessage(channel, name + ": You have to specify at least the mod's name.")
        return

    mod = self.NEM.get_proper_name(params[1])

    if not mod:
        self.sendMessage(channel, name + ": No such mod in NEMP.")
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

        self.sendMessage(channel, name + ": " + repr(elem))
    except KeyError:
        self.sendMessage(channel, name + ": No such element in that mod's configuration.")


def cmd_url(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        self.sendMessage(channel, name + ": You have to specify at least the mod's name.")
        return

    modname = self.NEM.get_proper_name(params[1])

    if not modname:
        self.sendMessage(channel, name + ": No such mod in NEMP.")
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
        self.sendMessage(channel, name + ": " + url)
    else:
        self.sendMessage(channel, name + ": This mod doesn't have a well-defined URL")


def cmd_reload_blocklist(self, name, params, channel, userdata, rank):
    self.NEM.load_version_blocklist()
    self.NEM.load_mc_blocklist()
    self.NEM.load_mc_mapping()
    self.sendMessage(channel, 'Done, blocklists reloaded.')


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
