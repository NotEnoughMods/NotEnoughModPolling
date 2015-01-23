import traceback
import time
import logging
import shlex
import re


from commands.NEMP import NEMP_Class

ID = "nemp"
permission = 1
privmsgEnabled = True

nemp_logger = logging.getLogger("NEMPolling")

helpDict = {
    "running": ["{0}nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll": ["{0}nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "list": ["{0}nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["{0}nemp about", "Shows some info about this plugin."],
    "help": ["{0}nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "refresh": ["'{0}nemp refresh' or '{0}nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "reload": ["'{0}nemp refresh' or '{0}nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "test": ["{0}nemp test <mod>", "Tests the parser for <mod> and outputs the contents to IRC"],
    "queue": ["{0}nemp queue [sub-command]", "Shows or modifies the update queue; its main use is for non-voiced users in #NotEnoughMods to more easily help update the list. Type '{0}nemp queue help' for detailed information about this command"],
    "status": ["{0}nemp status", "Shows whether or not NEMPolling is running and in which channel it is running."],
    "disabledmods": ["{0}nemp disabledmods", "Shows a list of the currently disabled mods."],
    "failedmods": ["{0}nemp failedmods", "Shows a list of mods that have failed to be polled at least 5 times in a row and were disabled automatically."],
    "failcount": ["{0}nemp failcount", "Shows how many times mods have failed to be polled so far. At least two failures in a row required.",
                  "Mods that have failed being polled 5 times are excluded from this list. Check {0}nemp failedmods for those mods."],
    "showinfo": ["{0}nemp showinfo <mod> [<path> [...]]", "Shows polling information for the specified mod."]
}

def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        cmdName = params[0]
        if cmdName in commands:
            userRank = self.rankconvert[rank]

            command, requiredRank = commands[params[0]]
            print "Needed rank: {0} User rank: {1}".format(requiredRank, userRank)
            if userRank >= requiredRank:
                command(self, name, params, channel, userdata, rank)
            else:
                self.sendMessage(channel, "You're not authorized to use this command.")
        else:
            self.sendMessage(channel, "Invalid command!")
            self.sendMessage(channel, "See {0}nemp help for a list of commands".format(self.cmdprefix))
    else:
        self.sendMessage(channel, name + ": see \"{0}nemp help\" for a list of commands".format(self.cmdprefix))

def __initialize__(self, Startup):
    if Startup:
        self.NEM = NEMP_Class.NotEnoughClasses()
    else:
        # kill events, threads
        if self.events["time"].doesExist("NotEnoughModPolling"):
            self.events["time"].removeEvent("NotEnoughModPolling")
            self.threading.sigquitThread("NEMP")

            nemp_logger.info("NEMP Polling has been disabled.")

        reload(NEMP_Class)

        self.NEM = NEMP_Class.NotEnoughClasses()

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}
    self.NEM_cycle_count = 0

def running(self, name, params, channel, userdata, rank):
    if len(params) >= 2 and (params[1] == "true" or params[1] == "on"):
        if not self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendMessage(channel, "Turning NotEnoughModPolling on.")
            self.NEM.InitiateVersions()
            self.NEM_cycle_count = 0

            timerForPolls = 60 * 5

            if len(params) == 3:
                timerForPolls = int(params[2])

            self.threading.addThread("NEMP", PollingThread, {"NEM": self.NEM, "PollTime": timerForPolls})

            self.events["time"].addEvent("NotEnoughModPolling", 60, NEMP_TimerEvent, [channel])
        else:
            self.sendMessage(channel, "NotEnoughMods-Polling is already running.")

    if len(params) == 2 and (params[1] == "false" or params[1] == "off"):
        if self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendMessage(channel, "Turning NotEnoughPolling off.")

            try:
                self.events["time"].removeEvent("NotEnoughModPolling")
                print "Removed NEM Polling Event"
                self.threading.sigquitThread("NEMP")
                print "Sigquit to NEMP Thread sent"

                self.NEM_troubledMods = {}
                #self.NEM_autodeactivatedMods = {}

            except Exception as error:
                print str(error)
                self.sendMessage(channel, "Exception appeared while trying to turn NotEnoughPolling off.")
        else:
            self.sendMessage(channel, "NotEnoughModPolling isn't running!")

def about(self, name, params, channel, userdata, rank):
    self.sendMessage(channel, "Not Enough Mods: Polling for IRC by SinZ, with help from NightKev & Yoshi2 - v1.4")
    self.sendMessage(channel, "Additional contributions by Pyker, spacechase, helinus & sMi")
    self.sendMessage(channel, "Source code available at: http://github.com/SinZ163/NotEnoughMods")

def nemp_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendMessage(channel, name + ": Available commands: " + ", ".join(helpDict))
        self.sendMessage(channel, name + ": For command usage, use \"{0}nemp help <command>\".".format(self.cmdprefix))
    else:
        command = params[1]
        if command in helpDict:
            for line in helpDict[command]:
                self.sendMessage(channel, name + ": " + line.format(self.cmdprefix))
        else:
            self.sendMessage(channel, name + ": Invalid command provided")

def status(self, name, params, channel, userdata, rank):
    if self.events["time"].doesExist("NotEnoughModPolling"):
        channels = ", ".join(self.events["time"].getChannels("NotEnoughModPolling"))
        self.sendMessage(channel,
                         "NEM Polling is currently running "
                         "in the following channel(s): {0}. "
                         "Full cycles completed: {1}".format(channels, self.NEM_cycle_count)
                         )
    else:
        self.sendMessage(channel, "NEM Polling is not running.")

def show_disabledMods(self, name, params, channel, userdata, rank):
    disabled = [mod for mod, info in self.NEM.mods.iteritems() if not info['active']]

    if len(disabled) == 0:
        self.sendNotice(name, "No mods are disabled right now.")
    else:
        self.sendNotice(name,
                        "The following mods are disabled right now: {0}. "
                        "{1} mod(s) total. ".format(", ".join(disabled), len(disabled))
                        )

def show_autodeactivatedMods(self, name, params, channel, userdata, rank):
    if len(self.NEM_autodeactivatedMods) == 0:
        self.sendNotice(name, "No mods have been automatically disabled so far.")
    else:
        disabled = self.NEM_autodeactivatedMods.keys()
        self.sendNotice(name, "The following mods have been automatically disabled so far: "
                        "{0}. {1} mod(s) total".format(", ".join(disabled), len(disabled)))

def clean_failed_mods(self, name, params, channel, userdata, rank):
    failed_mods = self.NEM_autodeactivatedMods.keys()
    for failed_mod in self.NEM_autodeactivatedMods:
        self.NEM.mods[failed_mod]['active'] = True
    self.NEM_autodeactivatedMods = {}
    self.sendMessage(channel, "Re-enabled {0} automatically disabled mods.".format(len(failed_mods)))
    self.NEM.buildHTML()

def show_failedcount(self, name, params, channel, userdata, rank):
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

def PollingThread(self, pipe):
    NEM = self.base["NEM"]
    sleepTime = self.base["PollTime"]

    while self.signal == False:
        # if NEM.newMods:
        #    NEM.mods = NEM.newMods
        #    NEM.InitiateVersions()
        print "I'm still running!"

        tempList = {}
        SinZationalHax = []
        failed = []
        for mod, info in NEM.mods.iteritems():
            if self.signal:
                return

            if NEM.mods[mod]["active"]:
                if "SinZationalHax" in NEM.mods[mod]:
                    if NEM.mods[mod]["SinZationalHax"]["id"] not in SinZationalHax: #have we polled this set of mods before
                        results = NEM.CheckMods(mod)
                        for outputMod, outputInfo in results.iteritems():
                            result, exceptionRaised = results[outputMod]
                            if any(result):
                                tempList.setdefault(NEM.mods[outputMod]['mc'], []).append((outputMod, result))
                            elif exceptionRaised:
                                failed.append(outputMod)
                        SinZationalHax.append(NEM.mods[mod]["SinZationalHax"]["id"]) #Remember this poll that we have done this set of mods
                    else:
                        nemp_logger.debug("Already polled {} before".format(NEM.mods[mod]["SinZationalHax"]["id"]))
                else:
                    result, exceptionRaised = NEM.CheckMod(mod)

                    # if there is an update
                    if any(result):
                        tempList.setdefault(NEM.mods[mod]['mc'], []).append((mod, result))
                    # if there's no update, we must check if there was an exception
                    elif exceptionRaised:
                        failed.append(mod)
        pipe.send((tempList, failed))

        # A more reasonable way of sleeping to quicken up the
        # shutdown of the thread. Sleep in steps of 30 seconds
        for i in xrange(sleepTime // 30 + 1):
            # print "Sleeping for 30s, step %s" % i
            if self.signal:
                return
            else:
                time.sleep(30)

# Returns the version string with some replacements, like:
# - whitespace (space/tab/etc) replaced by hyphen
def clean_version(version):
    return re.sub(r'\s+', '-', version)

def NEMP_TimerEvent(self, channels):
    yes = self.threading.poll("NEMP")

    if yes:
        tempList, failedMods = self.threading.recv("NEMP")
        self.NEM_cycle_count += 1
        # self.threading.sigquitThread("NEMP")
        # self.events["time"].removeEvent("NEMP_ThreadClock")

        if isinstance(tempList, dict) and "action" in tempList and tempList["action"] == "exceptionOccured":
            nemp_logger.error("NEMP Thread {0} encountered an unhandled exception: {1}".format(tempList["functionName"],
                                                                                               str(tempList["exception"])))
            nemp_logger.error("Traceback Start")
            nemp_logger.error(tempList["traceback"])
            nemp_logger.error("Traceback End")

            nemp_logger.error("Shutting down NEMP Events and Polling")
            self.threading.sigquitThread("NEMP")
            self.events["time"].removeEvent("NotEnoughModPolling")

            self.NEM_troubledMods = {}
            self.NEM_autodeactivatedMods = {}

            return

        for channel in channels:
            for version in tempList:
                for item in tempList[version]:
                    # item[0] = name of mod
                    # item[1] = flags for dev/release change
                    # flags[0] = has release version changed?
                    # flags[1] = has dev version changed?
                    mod = item[0]
                    flags = item[1]
                    real_name = ""
                    if 'name' in self.NEM.mods[mod]:
                        real_name = self.NEM.mods[mod]['name']
                    else:
                        real_name = mod

                    if self.NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        nemp_logger.debug("Updating DevMod {0}, Flags: {1}".format(mod, flags))
                        self.sendMessage(channel, "!ldev {0} {1} {2}".format(version, real_name, unicode(clean_version(self.NEM.mods[mod]["dev"]))))

                    if self.NEM.mods[mod]["version"] != "NOT_USED" and flags[1]:
                        nemp_logger.debug("Updating Mod {0}, Flags: {1}".format(mod, flags))
                        self.sendMessage(channel, "!lmod {0} {1} {2}".format(version, real_name, unicode(clean_version(self.NEM.mods[mod]["version"]))))

                    if self.NEM.mods[mod]["change"] != "NOT_USED" and "changelog" not in self.NEM.mods[mod]:
                        nemp_logger.debug("Sending text for Mod {0}".format(mod))
                        self.sendMessage(channel, " * " + self.NEM.mods[mod]["change"])

        # A temporary list containing the mods that have failed to be polled so far.
        # We use it to check if the same mods had trouble in the newest polling attempt.
        # If not, the counter for each mod that succeeded to be polled will be reset.
        current_troubled_mods = self.NEM_troubledMods.keys()

        for mod in failedMods:
            if mod not in self.NEM_troubledMods:
                self.NEM_troubledMods[mod] = 1
                nemp_logger.debug("Mod {0} had trouble being polled once. Counter set to 1".format(mod))

            else:
                self.NEM_troubledMods[mod] += 1

                # We have checked the mod, so we remove it from our temporary list
                current_troubled_mods.remove(mod)

                if self.NEM_troubledMods[mod] >= 5:
                    self.NEM_autodeactivatedMods[mod] = True
                    self.NEM.mods[mod]["active"] = False
                    del self.NEM_troubledMods[mod]

                    # TODO: Not hardcode the channel
                    self.sendMessage('#test', 'Mod {0} failed.'.format(mod))

                    nemp_logger.debug("Mod {0} has failed to be polled at least 5 times, it has been disabled.".format(mod))
                    self.NEM.buildHTML()

        # Reset counter for any mod that is still in the list.
        for mod in current_troubled_mods:
            nemp_logger.debug("Mod {0} is working again. Counter reset (Counter was at {1}) ".format(mod, self.NEM_troubledMods[mod]))
            del self.NEM_troubledMods[mod]

def poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        self.sendMessage(channel, name + ": Insufficient amount of parameters provided. Required: 2")
        self.sendMessage(channel, name + ": " + helpDict["poll"][1])

    else:
        setting = False
        if params[2].lower() in ("true", "yes", "on"):
            setting = True
        elif params[2].lower() in ("false", "no", "off"):
            setting = False

        if params[1][0:2].lower() == "c:":
            for mod in self.NEM.mods:
                if "category" in self.NEM.mods[mod] and self.NEM.mods[mod]["category"] == params[1][2:]:
                    self.NEM.mods[mod]["active"] = setting
                    self.sendMessage(channel, name + ": " + mod + "'s poll status is now " + str(setting))

                    # The mod has been manually activated or deactivated, so we remove it from the
                    # autodeactivatedMods dictionary.
                    if mod in self.NEM_autodeactivatedMods:
                        del self.NEM_autodeactivatedMods[mod]
                    if mod in self.NEM_troubledMods:
                        del self.NEM_troubledMods[mod]

        if params[1].lower().startswith('p:'):
            parser = params[1][2:].lower()
            match_mods = {k: v for k, v in self.NEM.mods.iteritems() if v['function'][5:].lower() == parser}
            for mod, info in match_mods.iteritems():
                if info['function'][5:].lower() == parser:
                    info['active'] = setting
                    #self.sendMessage(channel, name + ": " + mod + "'s poll status is now " + str(setting))

                    if mod in self.NEM_autodeactivatedMods:
                        del self.NEM_autodeactivatedMods[mod]
                    if mod in self.NEM_troubledMods:
                        del self.NEM_troubledMods[mod]
            self.sendMessage(channel, name + ": " + ', '.join(sorted(match_mods.keys(), key=lambda x: x.lower())) + "'s poll status is now " + str(setting))

        elif params[1] in self.NEM.mods:
            mod = params[1]
            self.NEM.mods[mod]["active"] = setting
            self.sendMessage(channel, name + ": " + mod + "'s poll status is now " + str(setting))

            if mod in self.NEM_autodeactivatedMods:
                del self.NEM_autodeactivatedMods[mod]
            if mod in self.NEM_troubledMods:
                del self.NEM_troubledMods[mod]

        elif params[1].lower() == "all":
            for mod in self.NEM.mods:
                self.NEM.mods[mod]["active"] = setting

                if mod in self.NEM_autodeactivatedMods:
                    del self.NEM_autodeactivatedMods[mod]
                if mod in self.NEM_troubledMods:
                    del self.NEM_troubledMods[mod]

            self.sendMessage(channel, name + ": All mods are now set to " + str(setting))
        self.NEM.buildHTML()

def nemp_list(self, name, params, channel, userdata, rank):
    dest = None
    if len(params) > 1:
        if params[1] == "pm":
            dest = name
        elif params[1] == "broadcast":
            dest = channel

    if dest == None:
        self.sendMessage(channel, "http://nemp.mca.d3s.co/")
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
            if self.NEM.mods[key]["version"] != "NOT_USED":
                relType = relType + color + darkgreen + "[R]" + color
            if self.NEM.mods[key]["dev"] != "NOT_USED":
                relType = relType + color + red + "[D]" + color

            if not mcver in tempList:
                tempList[mcver] = []
            tempList[mcver].append("{0}{1}".format(real_name, relType))

    del mcver
    for mcver in sorted(tempList.iterkeys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        self.sendMessage(dest, "Mods checked for {} ({}): {}".format(color + blue + bold + mcver + color + bold, len(tempList[mcver]), ', '.join(tempList[mcver])))

def nemp_reload(self, name, params, channel, userdata, rank):
    if self.events["time"].doesExist("NotEnoughModPolling"):
        self.events["time"].removeEvent("NotEnoughModPolling")
        self.threading.sigquitThread("NEMP")

        self.sendMessage(channel, "NEMP Polling has been deactivated")

    self.NEM_troubledMods = {}
    self.NEM_autodeactivatedMods = {}

    self.NEM.buildModDict()
    self.NEM.QueryNEM()
    self.NEM.InitiateVersions()
    self.NEM.buildHTML()

    self.sendMessage(channel, "Reloaded the NEMP Database")

def test_parser(self, name, params, channel, userdata, rank):
    if len(params) > 0:
        if params[1] not in self.NEM.mods:
            self.sendMessage(channel, name + ": Mod \"" + params[1] + "\" does not exist in the database.")
        else:
            try:
                mod = params[1]
                result = getattr(self.NEM, self.NEM.mods[mod]["function"])(mod)
                real_name = self.NEM.mods[mod].get('name', mod)

                print("result of parser: {}".format(result))
                if 'mc' in result:
                    version = result['mc']
                else:
                    version = self.NEM.mods[params[1]]["mc"]

                if not result:
                    self.sendMessage(channel, "Didn't get a reply from the parser. (got " + repr(result) + ")")
                    return

                if "mc" in result:
                    if version != result["mc"]:
                        self.sendMessage(channel, "Expected MC version {}, got {}".format(version, result["mc"]))
                else:
                    self.sendMessage(channel, "Did not receive MC version from parser.")
                if "version" in result:
                    self.sendMessage(channel, "!lmod {0} {1} {2}".format(version, real_name, unicode(clean_version(result["version"]))))
                if "dev" in result:
                    self.sendMessage(channel, "!ldev {0} {1} {2}".format(version, real_name, unicode(clean_version(result["dev"]))))
                if "change" in result:
                    self.sendMessage(channel, " * " + result["change"])

            except Exception as error:
                self.sendMessage(channel, name + ": " + str(error))
                traceback.print_exc()
                self.sendMessage(channel, params[1] + " failed to be polled")

def genHTML(self, name, params, channel, userdata, rank):
    self.NEM.buildHTML()

def nemp_set(self, name, params, channel, userdata, rank):
    #params[1] = mod
    #params[2] = config
    # params[3] = setting if len(params) == 4, else deeper config
    #params[4] = setting

    # Split the arguments in a shell-like fashion
    try:
        args = shlex.split(' '.join(params[1:]))
    except:
        self.sendMessage(channel, "That looks like invalid input (are there any unescaped quotes?). Try again.")
        return

    if len(args) < 3:
        self.sendMessage(channel, "This is not a toy!")
        return

    if args[1] == 'active':
        self.sendMessage(channel, "You want =nemp poll instead.")
        return

    if len(args) == 3:
        self.NEM.mods[args[0]][args[1]] = args[2]
    else:
        self.NEM.mods[args[0]][args[1]][args[2]] = args[3]
    self.sendMessage(channel, "done.")

def nemp_showinfo(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        self.sendMessage(channel, name + ": You have to specify at least the mod's name.")
        return

    mod = params[1]

    if mod not in self.NEM.mods:
        self.sendMessage(channel, name + ": No such mod in NEMP.")
        return

    if len(params) > 1:
        path = params[2:]
    else:
        path = []

    try:
        elem = self.NEM.mods[mod]
        for path_elem in path:
            elem = elem[path_elem]

        self.sendMessage(channel, name + ": " + repr(elem))
    except KeyError:
        self.sendMessage(channel, name + ": No such element in that mod's configuration.")

# In each entry, the second value in the tuple is the
# rank that is required to be able to use the command.
VOICED = 1
#OP = 2
commands = {
    "running": (running, VOICED),
    "poll": (poll, VOICED),
    "list": (nemp_list, VOICED),
    "about": (about, VOICED),
    "help": (nemp_help, VOICED),
    "test": (test_parser, VOICED),
    "reload": (nemp_reload, VOICED),
    "html": (genHTML, VOICED),
    "set": (nemp_set, VOICED),
    "status": (status, VOICED),
    "disabledmods": (show_disabledMods, VOICED),
    "failedmods": (show_autodeactivatedMods, VOICED),
    "failcount": (show_failedcount, VOICED),
    "resetfailed": (clean_failed_mods, VOICED),
    "showinfo": (nemp_showinfo, VOICED),

    # -- ALIASES -- #
    "polling": (running, VOICED),
    "refresh": (nemp_reload, VOICED),
    "disabled": (show_disabledMods, VOICED),
    "failed": (show_autodeactivatedMods, VOICED),
    "cleanfailed": (clean_failed_mods, VOICED),
    "show": (nemp_showinfo, VOICED)

    # -- END ALIASES -- #
}
