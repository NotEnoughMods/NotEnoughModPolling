import traceback
import time
import logging


from commands.NEMP import NEMP_Class
from centralizedThreading import FunctionNameAlreadyExists  # @UnresolvedImport (this makes my IDE happy <_<)

ID = "nemp"
permission = 1
privmsgEnabled = True

nemp_logger = logging.getLogger("NEMPolling")

helpDict = {
    "running" : ["{0}nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll" : ["{0}nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "list" : ["{0}nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["{0}nemp about", "Shows some info about this plugin."],
    "help" : ["{0}nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setversion" : ["{0}nemp setversion <version>", "Sets the version to <version> for polling to assume."],
    "getversion" : ["{0}nemp getversion", "gets the version for polling to assume."],
    "refresh" : ["'{0}nemp refresh' or '{0}nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "reload" : ["'{0}nemp refresh' or '{0}nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "test" : ["{0}nemp test <mod>", "Tests the parser for <mod> and outputs the contents to IRC"],
    "queue" : ["{0}nemp queue [sub-command]", "Shows or modifies the update queue; its main use is for non-voiced users in #NotEnoughMods to more easily help update the list. Type '{0}nemp queue help' for detailed information about this command"],
    "status" : ["{0}nemp status", "Shows whether or not NEMPolling is running and in which channel it is running."],
    "disabledmods" : ["{0}nemp disabledmods", "Shows a list of the currently disabled mods."],
    "failedmods" : ["{0}nemp failedmods", "Shows a list of mods that have failed to be polled at least 5 times in a row and were disabled automatically."],
    "failcount" : ["{0}nemp failcount", "Shows how many times mods have failed to be polled so far. At least two failures in a row required.",
                   "Mods that have failed being polled 5 times are excluded from this list. Check {0}nemp failedmods for those mods."]
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
        self.sendMessage(channel, name+": see \"{0}nemp help\" for a list of commands".format(self.cmdprefix))

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

            timerForPolls = 60*5

            if len(params) == 3:
                timerForPolls = int(params[2])

            self.threading.addThread("NEMP", PollingThread, {"NEM": self.NEM, "PollTime" : timerForPolls})

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
    self.sendMessage(channel, "Additional contributions by Pyker, spacechase & helinus")
    self.sendMessage(channel, "Source code available at: http://github.com/SinZ163/NotEnoughMods")

def nemp_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendMessage(channel, name+ ": Available commands: " + ", ".join(helpDict))
        self.sendMessage(channel, name+ ": For command usage, use \"{0}nemp help <command>\".".format(self.cmdprefix))
    else:
        command = params[1]
        if command in helpDict:
            for line in helpDict[command]:
                self.sendMessage(channel, name+ ": "+line.format(self.cmdprefix))
        else:
            self.sendMessage(channel, name+ ": Invalid command provided")

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
    disabled = []
    for mod in self.NEM.mods:
        if self.NEM.mods[mod]["active"] == False:
            disabled.append(mod)

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
        self.sendNotice(name,   "The following mods have been automatically disabled so far: "
                                "{0}. {1} mod(s) total".format(", ".join(disabled), len(disabled)))

def show_failedcount(self, name, params, channel, userdata, rank):
    print self.NEM_troubledMods
    if len(self.NEM_troubledMods) == 0:
        self.sendNotice(name, "No mods have had trouble polling so far.")
    else:
        sortedMods = sorted(self.NEM_troubledMods, key = lambda x: self.NEM_troubledMods[x])
        newlist = []

        for modName in sortedMods:
            if self.NEM_troubledMods[modName] > 1:
                newlist.append( (modName+" [{0}x]".format(self.NEM_troubledMods[modName])) )

        if len(newlist) == 0:
            self.sendNotice(name,
                            "{0} mod{1} had trouble being polled once. "
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
        #if NEM.newMods:
        #    NEM.mods = NEM.newMods
        #    NEM.InitiateVersions()
        print "I'm still running!"

        tempList = {}
        failed = []
        for mod, info in NEM.mods.iteritems():
            if self.signal:
                return
            if 'name' in info:
                real_name = info['name']
            else:
                real_name = mod
            if NEM.mods[mod]["active"]:
                result, exceptionRaised = NEM.CheckMod(mod)

                # if there is an update
                if any(result):
                    tempList.setdefault(NEM.mods[mod]['mc'], []).append((real_name, result))
                # if there's no update, we must check if there was an exception
                elif exceptionRaised:
                    failed.append(real_name)
        pipe.send((tempList, failed))

        # A more reasonable way of sleeping to quicken up the
        # shutdown of the thread. Sleep in steps of 30 seconds
        for i in xrange(sleepTime//30 + 1):
            #print "Sleeping for 30s, step %s" % i
            if self.signal:
                return
            else:
                time.sleep(30)

"""def MainTimerEvent(self,channels):
    try:
        self.threading.addThread("NEMP", PollingThread)
        self.events["time"].addEvent("NEMP_ThreadClock", 10, MicroTimerEvent, channels)
    except FunctionNameAlreadyExists as e:
        print(e)"""

def NEMP_TimerEvent(self, channels):
    yes = self.threading.poll("NEMP")

    if yes:
        tempList, failedMods = self.threading.recv("NEMP")
        self.NEM_cycle_count += 1
        #self.threading.sigquitThread("NEMP")
        #self.events["time"].removeEvent("NEMP_ThreadClock")

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

                    if self.NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        nemp_logger.debug("Updating DevMod {0}, Flags: {1}".format(mod, flags))
                        #self.sendMessage(channel, "!ldev "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["dev"]))
                        self.sendMessage(channel, "!ldev {0} {1} {2}".format(version, mod, unicode(self.NEM.mods[mod]["dev"])))

                    if self.NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        nemp_logger.debug("Updating Mod {0}, Flags: {1}".format(mod, flags))
                        #self.sendMessage(channel, "!lmod "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["version"]))
                        self.sendMessage(channel, "!lmod {0} {1} {2}".format(version, mod, unicode(self.NEM.mods[mod]["version"])))

                    if self.NEM.mods[mod]["change"] != "NOT_USED" and "changelog" not in self.NEM.mods[mod]:
                        nemp_logger.debug("Sending text for Mod {0}".format(mod))
                        self.sendMessage(channel, " * "+self.NEM.mods[mod]["change"].encode("utf-8"))

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

                    nemp_logger.debug("Mod {0} has failed to be polled at least 5 times, it has been disabled.".format(mod))

        # Reset counter for any mod that is still in the list.
        for mod in current_troubled_mods:
            nemp_logger.debug("Mod {0} is working again. Counter reset (Counter was at {1}) ".format(mod, self.NEM_troubledMods[mod]))
            del self.NEM_troubledMods[mod]

def poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        self.sendMessage(channel, name+ ": Insufficient amount of parameters provided. Required: 2")
        self.sendMessage(channel, name+ ": "+helpDict["poll"][1])

    else:
        setting = False
        if params[2].lower() in ("true","yes","on"):
            setting = True
        elif params[2].lower() in ("false","no","off"):
            setting = False

        if params[1][0:2].lower() == "c:":
            for mod in self.NEM.mods:
                if "category" in self.NEM.mods[mod] and self.NEM.mods[mod]["category"] == params[1][2:]:
                    self.NEM.mods[mod]["active"] = setting
                    self.sendMessage(channel, name+ ": "+mod+"'s poll status is now "+str(setting))

                    # The mod has been manually activated or deactivated, so we remove it from the
                    # autodeactivatedMods dictionary.
                    if mod in self.NEM_autodeactivatedMods:
                        del self.NEM_autodeactivatedMods[mod]
                    if mod in self.NEM_troubledMods:
                        del self.NEM_troubledMods[mod]


        elif params[1] in self.NEM.mods:
            mod = params[1]
            self.NEM.mods[mod]["active"] = setting
            self.sendMessage(channel, name+ ": "+mod+"'s poll status is now "+str(setting))

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

            self.sendMessage(channel, name+ ": All mods are now set to "+str(setting))

def setversion(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendMessage(channel, name+ ": Insufficent amount of parameters provided.")
        self.sendMessage(channel, name+ ": "+helpDict["setversion"][1])
    else:
        colourblue = unichr(2)+unichr(3)+"12"
        colour = unichr(3)+unichr(2)

        self.NEM.nemVersion = str(params[1])
        self.sendMessage(channel, "Default list has been set to: {0}{1}{2}".format(colourblue, params[1], colour))

def getversion(self,name,params,channel,userdata,rank):
    self.sendMessage(channel, self.NEM.nemVersion)

def nemp_list(self,name,params,channel,userdata,rank):
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
            tempList[mcver].append("{0}{1}".format(real_name,relType))

    del mcver
    for mcver in sorted(tempList.iterkeys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        self.sendMessage(dest, "Mods checked for {} ({}): {}".format(color+blue+bold+mcver+color+bold, len(tempList[mcver]), ', '.join(tempList[mcver])))

def nemp_reload(self,name,params,channel,userdata,rank):
    if self.events["time"].doesExist("NotEnoughModPolling"):
        self.events["time"].removeEvent("NotEnoughModPolling")
        self.threading.sigquitThread("NEMP")

        self.sendMessage(channel, "NEMP Polling has been deactivated")


    self.NEM.buildModDict()
    self.NEM.QueryNEM()
    self.NEM.InitiateVersions()

    self.sendMessage(channel, "Reloaded the NEMP Database")

def test_parser(self,name,params,channel,userdata,rank):
    if len(params) > 0:
        if params[1] not in self.NEM.mods:
            self.sendMessage(channel, name+": Mod \""+params[1]+"\" does not exist in the database.")
        else:
            try:
                mod = params[1]
                result = getattr(self.NEM, self.NEM.mods[mod]["function"])(mod)

                print("result of parser: {}".format(result))
                version = self.NEM.mods[params[1]]["mc"]

                if not result:
                    self.sendMessage(channel, "Didn't get a reply from the parser. (got " + repr(result) +")")
                    return

                if "mc" in result:
                    if version != result["mc"]:
                        self.sendMessage(channel, "Expected MC version {}, got {}".format(version,result["mc"]))
                else:
                    self.sendMessage(channel, "Did not receive MC version from parser.")
                if "version" in result:
                    #self.sendMessage(channel, "!mod "+params[1]+" "+unicode(result["version"]))
                    self.sendMessage(channel, "!lmod {0} {1} {2}".format(version, mod, unicode(result["version"])))
                if "dev" in result:
                    #self.sendMessage(channel, "!dev "+params[1]+" "+unicode(result["dev"]))
                    self.sendMessage(channel, "!ldev {0} {1} {2}".format(version, mod, unicode(result["dev"])))
                if "change" in result:
                    self.sendMessage(channel, " * "+result["change"])

            except Exception as error:
                self.sendMessage(channel, name+": "+str(error))
                traceback.print_exc()
                self.sendMessage(channel, params[1]+" failed to be polled")

def nktest(self,name,params,channel,userdata,rank):
    pass

def genHTML(self,name,params,channel,userdata,rank):
    self.NEM.buildHTML()

def nemp_set(self,name,params,channel,userdata,rank):
    #params[1] = mod
    #params[2] = config
    #params[3] = setting if len(params) == 4, else deeper config
    #params[4] = setting
    if len(params) < 4:
        self.sendMessage(channel, "This is not a toy!")
        return
    if len(params) == 4:
        self.NEM.mods[params[1]][params[2]] = params[3]
    else:
        self.NEM.mods[params[1]][params[2]][params[3]] = params[4]
    self.sendMessage(channel, "done.")

# In each entry, the second value in the tuple is the
# rank that is required to be able to use the command.
VOICED = 1
#OP = 2
commands = {
    "running" : (running, VOICED),
    "poll" : (poll, VOICED),
    "list" : (nemp_list, VOICED),
    "about": (about, VOICED),
    "help" : (nemp_help, VOICED),
    "setversion" : (setversion, VOICED),
    "getversion" : (getversion, VOICED),
    "test" : (test_parser, VOICED),
    "reload" : (nemp_reload, VOICED),
    "nktest" : (nktest, VOICED),
    "html" : (genHTML, VOICED),
    "set" : (nemp_set, VOICED),
    "status" : (status, VOICED),
    "disabledmods" : (show_disabledMods, VOICED),
    "failedmods" : (show_autodeactivatedMods, VOICED),
    "failcount" : (show_failedcount, VOICED),

    # -- ALIASES -- #
    "setv" : (setversion, VOICED),
    "getv" : (getversion, VOICED),
    "polling" : (running, VOICED),
    "refresh" : (nemp_reload, VOICED),
    "disabled" : (show_disabledMods, VOICED),
    "failed" : (show_autodeactivatedMods, VOICED)

    # -- END ALIASES -- #
}

