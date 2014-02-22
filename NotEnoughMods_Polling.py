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
    "running" : ["=nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll" : ["=nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "list" : ["=nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["=nemp about", "Shows some info about this plugin."],
    "help" : ["=nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setversion" : ["=nemp setversion <version>", "Sets the version to <version> for polling to assume."],
    "getversion" : ["=nemp getversion", "gets the version for polling to assume."],
    "refresh" : ["'=nemp refresh' or '=nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "reload" : ["'=nemp refresh' or '=nemp reload'", "Reloads the various data stores (mods list, versions list, etc)"],
    "test" : ["=nemp test <mod>", "Tests the parser for <mod> and outputs the contents to IRC"],
    "queue" : ["=nemp queue [sub-command]", "Shows or modifies the update queue; its main use is for non-voiced users in #NotEnoughMods to more easily help update the list. Type '=nemp queue help' for detailed information about this command"]
}

def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        cmdName = params[0]
        if cmdName in commands:
            command = commands[params[0]]
            command(self, name, params, channel, userdata, rank)
        else:
            self.sendMessage(channel, "invalid command!")
            self.sendMessage(channel, "see {0}nemp help for a list of commands".format(self.cmdprefix))
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

def running(self, name, params, channel, userdata, rank):
    if len(params) >= 2 and (params[1] == "true" or params[1] == "on"):
        if not self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendMessage(channel, "Turning NotEnoughModPolling on.")
            self.NEM.InitiateVersions()
            
            timerForPolls = 60*5
            
            if len(params) == 3:
                timerForPolls = int(params[2])
            
            self.threading.addThread("NEMP", PollingThread, {"NEM": self.NEM, "PollTime" : timerForPolls})
            
            self.events["time"].addEvent("NotEnoughModPolling", timerForPolls, NEMP_TimerEvent, [channel])
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
            except Exception as error:
                print str(error)
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
                self.sendMessage(channel, name+ ": "+line)
        else:
            self.sendMessage(channel, name+ ": Invalid command provided")

def status(self, name, params, channel, userdata, rank):
    if self.events["time"].doesExist("NotEnoughModPolling"):
        self.sendMessage(channel, "NEM Polling is currently running.")
    else:
        self.sendMessage(channel, "NEM Polling is not running.")

def PollingThread(self, pipe):
    NEM = self.base["NEM"]
    sleepTime = self.base["PollTime"]
    
    while self.signal == False:
        #if NEM.newMods:
        #    NEM.mods = NEM.newMods
        #    NEM.InitiateVersions()
        print "I'm still running!"
        
        tempList = {}
        for mod, info in NEM.mods.iteritems():
            if self.signal:
                return
            if 'name' in info:
                real_name = info['name']
            else:
                real_name = mod
            if NEM.mods[mod]["active"]:
                result = NEM.CheckMod(mod)
                if result[0]:
                    if NEM.mods[mod]["mc"] in tempList:
                        tempList[NEM.mods[mod]["mc"]].append((real_name, result[1:]))
                    else:
                        tempVersion = [(real_name, result[1:])]
                        tempList[NEM.mods[mod]["mc"]] = tempVersion
        pipe.send(tempList)
        
        time.sleep(sleepTime)

"""def MainTimerEvent(self,channels):
    try:
        self.threading.addThread("NEMP", PollingThread)
        self.events["time"].addEvent("NEMP_ThreadClock", 10, MicroTimerEvent, channels)
    except FunctionNameAlreadyExists as e:
        print(e)"""

def NEMP_TimerEvent(self, channels):
    yes = self.threading.poll("NEMP")
    
    if yes:
        tempList = self.threading.recv("NEMP")
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
                        self.writeQueue("Updating DevMod {0}, Flags: {1}".format(mod, flags), "NEMP")
                        self.sendMessage(channel, "!ldev "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["dev"]))
                    if self.NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.writeQueue("Updating Mod {0}, Flags: {1}".format(mod, flags), "NEMP")
                        self.sendMessage(channel, "!lmod "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["version"]))
                    if self.NEM.mods[mod]["change"] != "NOT_USED" and "changelog" not in self.NEM.mods[mod]:
                        self.writeQueue("Sending text for Mod {0}".format(mod), "NEMP")
                        self.sendMessage(channel, " * "+self.NEM.mods[mod]["change"].encode("utf-8"))
                
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
                    
        elif params[1] in self.NEM.mods:
            self.NEM.mods[params[1]]["active"] = setting
            self.sendMessage(channel, name+ ": "+params[1]+"'s poll status is now "+str(setting))
            
        elif params[1].lower() == "all":
            for mod in self.NEM.mods:
                self.NEM.mods[mod]["active"] = setting
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
                result = getattr(self.NEM, self.NEM.mods[params[1]]["function"])(params[1])
                print(result)
                if "mc" in result:
                    self.sendMessage(channel, "!setlist "+result["mc"])
                if "version" in result:
                    self.sendMessage(channel, "!mod "+params[1]+" "+unicode(result["version"]))
                if "dev" in result:
                    self.sendMessage(channel, "!dev "+params[1]+" "+unicode(result["dev"]))
                if "change" in result:
                    self.sendMessage(channel, " * "+result["change"])
            except Exception as error:
                self.sendMessage(channel, name+": "+str(error))
                traceback.print_exc()
                self.sendMessage(channel, params[1]+" failed to be polled")
            
#This is a waste of code imo, you can just run normal polling with 10sec delay, and not have it freeze the bot, also doesn't test the polling
def test_polling(self,name,params,channel,userdata,rank):
    try:
        # PollingThread()
        if self.NEM.newMods:
            self.NEM.mods = self.NEM.newMods
            self.NEM.InitiateVersions()
        else:
            self.NEM.InitiateVersions()
        
        tempList = {}
        for mod, info in self.NEM.mods.iteritems():
            if 'name' in info:
                real_name = info['name']
            else:
                real_name = mod
            if self.NEM.mods[mod]["active"]:
                result = self.NEM.CheckMod(mod)
                if result[0]:
                    if self.NEM.mods[mod]["mc"] in tempList:
                        tempList[self.NEM.mods[mod]["mc"]].append((real_name, result[1:]))
                    else:
                        tempVersion = [(real_name, result[1:])]
                        tempList[self.NEM.mods[mod]["mc"]] = tempVersion
        # MicroTimerEvent()
        yes = bool(tempList)
        if yes:
            for version in tempList:
                for item in tempList[version]:
                    # item[0] = name of mod
                    # item[1] = flags for dev/release change
                    # flags[0] = has release version changed?
                    # flags[1] = has dev version changed?
                    mod = item[0]
                    flags = item[1]
                    
                    if self.NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        self.sendMessage(channel, "!ldev "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["dev"]))
                    if self.NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.sendMessage(channel, "!lmod "+version+" "+mod+" "+unicode(self.NEM.mods[mod]["version"]))
                    # if NEM.mods[mod]["change"] != "NOT_USED":
                        # self.sendChatMessage(self.send, channel, " * "+NEM.mods[mod]["change"])
    
    except:
        self.sendMessage(channel, "An exception has occurred, check the console for more information.")
        traceback.print_exc()

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
    
commands = {
    "running" : running,
    "poll" : poll,
    "list" : nemp_list,
    "about": about,
    "help" : nemp_help,
    "setversion" : setversion,
    "getversion" : getversion,
    "test" : test_parser,
    "testpolling" : test_polling,
    "reload" : nemp_reload,
    "nktest" : nktest,
    "html" : genHTML,
    "set" : nemp_set,
    #"queue" : queue, # TODO: move this into its own file
    
    # -- ALIASES -- #
    "setv" : setversion,
    "getv" : getversion,
    "polling" : running,
    "testpoll" : test_polling,
    "refresh" : nemp_reload
    # -- END ALIASES -- #
}

