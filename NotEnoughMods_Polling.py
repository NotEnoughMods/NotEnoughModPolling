import urllib2
import simplejson
import re
import traceback
import threading
import time

from centralizedThreading import FunctionNameAlreadyExists

ID = "nemp"
permission = 1

class NotEnoughClasses():
    nemVersions = []
    nemVersion = ""
    
    newMods = False
    mods = {}
    
    def __init__(self):
        self.useragent = urllib2.build_opener()
        self.useragent.addheaders = [('User-agent', 'NotEnoughMods:Polling/1.X (+http://github.com/SinZ163/NotEnoughMods)')]
        
        file = open("commands/NEMP/mods.json", "r")
        fileInfo = file.read()
        self.mods = simplejson.loads(fileInfo, strict = False)
        
        self.QueryNEM()
        
    def QueryNEM(self):
        try:
            NEMfeed = self.useragent.open("http://bot.notenoughmods.com/?json", timeout = 10)
            result = NEMfeed.read()
            NEMfeed.close() 
            self.nemVersions = reversed(simplejson.loads(result, strict = False))
        except:
            print("Failed to get NEM versions, falling back to hard-coded")
            traceb = str(traceback.format_exc())
            print(traceb)
            self.nemVersions = reversed(["1.4.5","1.4.6-1.4.7","1.5.1","1.5.2","1.6.1","1.6.2","1.6.4"])
            
    def InitiateVersions(self):
        templist = self.mods.keys()
        
        for version in self.nemVersions:
            if "-dev" not in version:
                versionFeed = self.useragent.open("http://bot.notenoughmods.com/"+version+".json", timeout = 10)
                rawJson = versionFeed.read()
                versionFeed.close()
                
                jsonres = simplejson.loads(rawJson, strict = False)
                
                for mod in jsonres:
                    if mod["name"] in templist:
                        print(mod["name"]+" has versions for "+version)
                        self.mods[mod["name"]]["mc"] = version
                        if self.mods[mod["name"]]["dev"] != "NOT_USED":
                            self.mods[mod["name"]]["dev"] = mod["dev"]
                        if self.mods[mod["name"]]["version"] != "NOT_USED":
                            self.mods[mod["name"]]["version"] = mod["version"]
                        templist.remove(mod["name"])
        
    def CheckJenkins(self, mod):
        jenkinFeed = self.useragent.open(self.mods[mod]["jenkins"]["url"], timeout = 10)
        result = jenkinFeed.read()
        jenkinFeed.close()
        jsonres = simplejson.loads(result, strict = False )
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = re.search(self.mods[mod]["jenkins"]["regex"],filename)
        output = match.groupdict()
        try:
            output["change"] = jsonres["changeSet"]["items"][0]["comment"]
        except:
            print("Aww, no changelog for "+mod)
            output["change"] = "NOT_USED"
        return output

    def CheckMCForge(self,mod):
        forgeFeed = self.useragent.open("http://files.minecraftforge.net/"+self.mods[mod]["mcforge"]["name"]+"/json", timeout = 10)
        result = forgeFeed.read()
        forgeFeed.close()
        jsonres = simplejson.loads(result, strict = False )
        promotionArray = jsonres["promotions"]
        devMatch = ""
        recMatch = ""
        for promotion in promotionArray:
            if promotion["name"] == self.mods[mod]["mcforge"]["dev"]:
                for entry in promotion["files"]:
                    if entry["type"] == "universal":
                        info = entry["url"]
                        devMatch = re.search(self.mods[mod]["mcforge"]["regex"],info)
            elif promotion["name"] == self.mods[mod]["mcforge"]["rec"]:
                for entry in promotion["files"]:
                    if entry["type"] == "universal":
                        info = entry["url"]
                        recMatch = re.search(self.mods[mod]["mcforge"]["regex"],info)
        if devMatch:
            output = {}
            tmpMC = "null"
            if recMatch:
                output["version"] = recMatch.group(2)
                tmpMC = recMatch.group(1)
            if devMatch.group(1) != tmpMC:
                output["version"] = "NOT_USED"
                output["mc"] = devMatch.group(1)
            else:
                output["mc"] = tmpMC
            output["dev"] = devMatch.group(2)
            return output
            
    def CheckChickenBones(self,mod):
        chickenFeed = self.useragent.open("http://www.chickenbones.craftsaddle.org/Files/New_Versions/version.php?file="+mod+"&version="+self.mods[mod]["mc"], timeout = 10)
        result = chickenFeed.read()
        chickenFeed.close()
        if result.startswith("Ret: "): #Hacky I know, but this is how ChickenBones does it in his mod
            return {
                "version" : result[5:]
            }
            
    def CheckmDiyo(self,mod):
        mDiyoFeed = self.useragent.open("http://tanis.sunstrike.io/"+self.mods[mod]["mDiyo"]["location"],timeout = 10)
        result = mDiyoFeed.read()
        mDiyoFeed.close()
        lines = result.split()
        result = ""
        for line in lines:
            if ".jar" in line.lower(): #TODO: Dynamic this thing if changes
                result = line
        match = re.search(self.mods[mod]["mDiyo"]["regex"],result)
        output = match.groupdict()
        return output
        
    def CheckAE(self,mod):
        aeFeed = self.useragent.open("http://ae-mod.info/releases", timeout=10)
        result = aeFeed.read()
        aeFeed.close()
        jsonres = simplejson.loads(result, strict = False )
        jsonres = sorted(jsonres, key=lambda k: k['Released'])
        relVersion = ""
        relMC = ""
        devVersion = ""
        devMC = ""
        for version in jsonres:
            #print(version)
            if version["Channel"] == "Stable":
                relVersion = version["Version"]
                relMC = version["Minecraft"]
            else:
                devVersion = version["Version"]
                devMC = version["Minecraft"]
            #print(" |"+relVersion+" || "+relMC)
            #print("~|"+devVersion+"~||~"+devMC)
        return {
            "version" : relVersion,
            "dev" : devVersion,
            "mc" : devMC
        }
        
    def CheckHTML(self,mod):
        bmFeed = self.useragent.open(self.mods[mod]["html"]["url"], timeout=10)
        result = bmFeed.read()
        bmFeed.close()
        output = {}
        for line in result.splitlines():
            match = re.search(self.mods[mod]["html"]["regex"], line)
            if match:
                output = match.groupdict()
        return output
        
    def CheckSpacechase(self,mod):
        spaceFeed = self.useragent.open("http://spacechase0.com/wp-content/plugins/mc-mod-manager/nem.php?mc=6", timeout=10)
        result = spaceFeed.read()
        spaceFeed.close()
        for line in result.splitlines():
            info = line.split(',')
            #0 = ID, 1=NEM ID, 2=ModID, 3=Author, 4=Link, 5=Version, 6=Comment
            if info[1] == mod:
                return {
                    "version" : info[5]
                }
                
    def CheckMod(self, mod):
        try:
            # First False is for if there was an update.
            # Next two Falses are for if there was an dev or version change
            status = [False, 
                      False, False]
            output = self.parsers[self.mods[mod]["function"]](self,mod)
            if "dev" in output:
                if self.mods[mod]["dev"] != output["dev"]:
                    self.mods[mod]["dev"] = output["dev"]
                    status[0] = True
                    status[1] = True
            if "version" in output:
                if self.mods[mod]["version"] != output["version"]:
                    self.mods[mod]["version"] = output["version"]
                    status[0] = True
                    status[2] = True
            if "mc" in output:
                self.mods[mod]["mc"] = output["mc"]
            if "change" in output:
                self.mods[mod]["change"] = output["change"]
            return status
        except:
            print(mod+" failed to be polled...")
            return [False, False, False]
            
    #def CheckOpenMod(self,mod):
    
    parsers = {
        "CheckMCForge" : CheckMCForge,
        "CheckJenkins" : CheckJenkins,
        "CheckChickenBones" : CheckChickenBones,
        "CheckmDiyo" : CheckmDiyo,
        "CheckAE" : CheckAE,
        "CheckHTML" : CheckHTML,
        "CheckSpacechase" : CheckSpacechase,
    }
    
NEM = NotEnoughClasses()
def running(self, name, params, channel, userdata, rank):
    if len(params) >= 2 and (params[1] == "true" or params[1] == "on"):
        if not self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendChatMessage(self.send, channel, "Turning NotEnoughModPolling on.")
            NEM.InitiateVersions()
            timerForPolls = 60*5
            if len(params) == 3:
                timerForPolls = int(params[2])
            self.events["time"].addEvent("NotEnoughModPolling", timerForPolls, MainTimerEvent, [channel])
        else:
            self.sendChatMessage(self.send, channel, "NotEnoughMods-Polling is already running.")
    if len(params) == 2 and (params[1] == "false" or params[1] == "off"):
        if self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendChatMessage(self.send, channel, "Turning NotEnoughPolling off.") 
            self.events["time"].removeEvent("NotEnoughModPolling")
        else:
            self.sendChatMessage(self.send, channel, "NotEnoughModPolling isn't running!")
def PollingThread(self, pipe):
    if NEM.newMods:
        NEM.mods = NEM.newMods
        NEM.InitiateVersions()
    tempList = {}
    for mod, info in NEM.mods.iteritems():
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
def MainTimerEvent(self,channels):
    try:
        self.threading.addThread("NEMP", PollingThread)
        self.events["time"].addEvent("NEMP_ThreadClock", 10, MicroTimerEvent, channels)
    except FunctionNameAlreadyExists as e:
        print(e)
def MicroTimerEvent(self,channels):
    yes = self.threading.poll("NEMP")
    if yes:
        tempList = self.threading.recv("NEMP")
        self.threading.sigquitThread("NEMP")
        self.events["time"].removeEvent("NEMP_ThreadClock")
        for channel in channels:
            setList = "null"
            for version in tempList:
                for item in tempList[version]:
                    # item[0] = name of mod
                    # item[1] = flags for dev/release change
                    # flags[0] = has release version changed?
                    # flags[1] = has dev version changed?
                    mod = item[0]
                    flags = item[1]
                    if NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        self.sendChatMessage(self.send, channel, "!ldev "+version+" "+mod+" "+NEM.mods[mod]["dev"])
                    if NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.sendChatMessage(self.send, channel, "!lmod "+version+" "+mod+" "+NEM.mods[mod]["version"])
                    if NEM.mods[mod]["change"] != "NOT_USED":
                        self.sendChatMessage(self.send, channel, " * "+NEM.mods[mod]["change"])
                
def poll(self, name, params, channel, userdata, rank):
    if len(params) != 3:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["poll"][1])
        
    else:
        setting = False
        if params[1] in NEM.mods:
            if params[2].lower() == "true" or params[2].lower() == "yes" or params[2].lower() == "on":
                setting = True
            elif params[2].lower() == "false" or params[2].lower() == "no" or params[2].lower() == "off":
                setting = False
            NEM.mods[params[1]]["active"] = setting
            self.sendChatMessage(self.send, channel, name+ ": "+params[1]+"'s poll status is now "+str(setting))
        elif params[1].lower() == "all":
            if params[2].lower() == "true" or params[2].lower() == "yes":
                setting = True
            elif params[2].lower() == "false" or params[2].lower() == "no":
                setting = False
            for mod in NEM.mods:
                NEM.mods[mod]["active"] = setting
            self.sendChatMessage(self.send, channel, name+ ": All mods are now set to "+str(setting))
     
def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        command(self, name, params, channel, userdata, rank)
    except Exception as e:
        self.sendChatMessage(self.send, channel, "invalid command!")
        self.sendChatMessage(self.send, channel, "see =nemp help for a list of commands")
        traceback.print_exc()

def setversion(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["setlist"][1])
    else:        
        colourblue = unichr(2)+unichr(3)+"12"
        colour = unichr(3)+unichr(2)
        
        NEM.nemVersion = str(params[1])
        self.sendChatMessage(self.send, channel, "set default list to: "+colourblue+params[1]+colour)
        
def getversion(self,name,params,channel,userdata,rank):
    self.sendChatMessage(self.send, channel, NEM.nemVersion)
        
def about(self, name, params, channel, userdata, rank):
    self.sendChatMessage(self.send, channel, "Not Enough Mods: Polling for IRC by SinZ, with help from NightKev - v1.2")
    self.sendChatMessage(self.send, channel, "Source code available at: http://github.com/SinZ163/NotEnoughMods")
    
def help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendChatMessage(self.send, channel, name+ ": Available commands: " + ", ".join(help))
        self.sendChatMessage(self.send, channel, name+ ": For command usage, use \"=nemp help <command>\".")
    else:
        command = params[1]
        if command in help:
            for line in help[command]:
                self.sendChatMessage(self.send, channel, name+ ": "+line)
        else:
            self.sendChatMessage(self.send, channel, name+ ": Invalid command provided")

def list(self,name,params,channel,userdata,rank):
    dest = userdata[0]
    if len(params) > 1 and params[1] == "broadcast":
        dest = channel
    darkgreen = "03"
    red = "05"
    blue = "12"
    bold = unichr(2)
    color = unichr(3)
    tempList = {}
    for key in NEM.mods:
        if NEM.mods[key]["active"]:
            type = ""
            mcver = NEM.mods[key]["mc"]
            if NEM.mods[key]["version"] != "NOT_USED":
                type = type + color + darkgreen + "[R]" + color
            if NEM.mods[key]["dev"] != "NOT_USED":
                type = type + color + red + "[D]" + color
            
            if not mcver in tempList:
                tempList[mcver] = []
            tempList[mcver].append("{0}{1}".format(key,type))
    
    del mcver
    for mcver in sorted(tempList.iterkeys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        self.sendChatMessage(self.send, dest, "Mods checked for {0}: {1}".format(color+blue+bold+mcver+color+bold, ', '.join(tempList[mcver])))

def refresh(self,name,params,channel,userdata,rank):
    NEM.QueryNEM()
    NEM.InitiateVersions()
    self.sendChatMessage(self.send,channel, "Queried NEM for \"latest\" versions")
def reload(self,name,params,channel,userdata,rank):
    file = open("commands/NEMP/mods.json", "r")
    fileInfo = file.read()
    
    if "NEMP" not in self.threading.pool:
        NEM.mods = simplejson.loads(fileInfo, strict = False)
        NEM.InitiateVersions()
    else:
        NEM.newMods = simplejson.loads(fileInfo, strict = False)
    
    self.sendChatMessage(self.send,channel, "Reloaded the NEMP Database")
    
def test(self,name,params,channel,userdata,rank):
    if len(params) > 0:
        try:
            result = NEM.parsers[NEM.mods[params[1]]["function"]](NEM,params[1])
            print(result)
            if "mc" in result:
                self.sendChatMessage(self.send,channel, "!setlist "+result["mc"])
            if "version" in result:
                self.sendChatMessage(self.send,channel, "!mod "+params[1]+" "+result["version"])
            if "dev" in result:
                self.sendChatMessage(self.send,channel, "!dev "+params[1]+" "+result["dev"])
            if "change" in result:
                self.sendChatMessage(self.send,channel, " * "+result["change"])
        except Exception as error:
            self.sendChatMessage(self.send, channel, name+": "+str(error))
            traceback.print_exc()
            self.sendChatMessage(self.send,channel, params[1]+" failed to be polled")

def nktest(self,name,params,channel,userdata,rank):
    pass

commands = {
    "running" : running,
    "poll" : poll,
    "list" : list,
    "about": about,
    "help" : help,
    "setversion" : setversion,
    "getversion" : getversion,
    "refresh" : refresh,
    "test" : test,
    "reload" : reload,
    "nktest" : nktest,
    
    ###  ALIASES ###
    "setv" : setversion,
    "getv" : getversion,
    "polling" : running
    ### END ALIASES ###
}

help = {
    "running" : ["=nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll" : ["=nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "list" : ["=nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["=nemp about", "Shows some info about this plugin."],
    "help" : ["=nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setversion" : ["=nemp setversion <version>", "Sets the version to <version> for polling to assume."],
    "getversion" : ["=nemp getversion", "gets the version for polling to assume."],
    "refresh" : ["=nemp refresh", "Queries NEM to get the \"latest\" versions"],
    "test" : ["=nemp test <mod>", "Runs CheckMod for <mod> and outputs the contents to IRC"]
}
