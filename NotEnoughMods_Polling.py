import urllib
import urllib2
import simplejson
import re
import traceback
import threading
import time

ID = "nemp"
permission = 1

class NotEnoughClasses():
    nemVersions = []
    nemVersion = ""
    def __init__(self):
        self.QueryNEM()
    def QueryNEM(self):
        try:
            NEMfeed = urllib2.urlopen("http://bot.notenoughmods.com/?json", timeout = 10)
            result = NEMfeed.read()
            NEMfeed.close() 
            self.nemVersions = reversed(simplejson.loads(result, strict = False))
        except:
            print("Failed to get NEM versions, falling back to hard-coded")
            traceb = str(traceback.format_exc())
            print(traceb)
            self.nemVersions = reversed(["1.4.5","1.4.6-1.4.7","1.5.1","1.5.2","1.6.1","1.6.2"])
            
    def InitiateVersions(self):
        templist = self.mods.keys()
        
        for version in self.nemVersions:
            if "-dev" not in version:
                versionFeed = urllib2.urlopen("http://bot.notenoughmods.com/"+version+".json", timeout = 10)
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
        jenkinFeed = urllib2.urlopen(self.mods[mod]["jenkins"]["url"], timeout = 10)
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
        forgeFeed = urllib2.urlopen("http://files.minecraftforge.net/"+self.mods[mod]["mcforge"]["name"]+"/json", timeout = 10)
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
        chickenFeed = urllib2.urlopen("http://www.chickenbones.craftsaddle.org/Files/New_Versions/version.php?file="+mod+"&version="+self.mods[mod]["mc"], timeout = 10)
        result = chickenFeed.read()
        chickenFeed.close()
        if result.startswith("Ret: "): #Hacky I know, but this is how ChickenBones does it in his mod
            return {
                "version" : result[5:]
            }
    def CheckmDiyo(self,mod):
        mDiyoFeed = urllib2.urlopen("http://tanis.sunstrike.io/"+self.mods[mod]["mDiyo"]["location"],timeout = 10)
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
    def CheckMod(self, mod):
        try:
            # First False is for if there was an update.
            # Next two Falses are for if there was an dev or version change
            status = [False, 
                      False, False]
            output = self.mods[mod]["function"](self,mod)
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
        
    mods = {
        "MinecraftForge" : {
            "function" : CheckMCForge,
            "version" : "",
            "dev"    : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "mcforge" : {
                "name" : "minecraftforge",
                "dev" : "latest",
                "rec" : "recommended",
                "regex" : "minecraftforge-universal-(.+?)-(.+?).jar$"
            }
        },
        "IronChests" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "dev"    : "",
            "change" : "NOT_USED",
            "active" : True,
            "mcforge" : {
                "name" : "IronChests2",
                "dev" : "latest",
                "rec" : "recommended",
                "regex" : "ironchest-universal-(.+?)-(.+?).zip$"
            }
        },
        "ForgeMultipart" : {
            "function" : CheckMCForge,
            "version" : "",
            "dev"    : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "mcforge" : {
                "name" : "ForgeMultipart",
                "dev" : "latest",
                "rec" : "recommended",
                "regex" : "ForgeMultipart-universal-(.+?)-(.+?).jar$"
            }
        },
        "CompactSolars" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "dev"    : "",
            "change" : "NOT_USED",
            "active" : True,
            "mcforge" : {
                "name" : "CompactSolars",
                "dev" : "latest",
                "rec" : "recommended",
                "regex" : "compactsolars-universal-(.+?)-(.+?).zip$"
            }
        },
        #"OpenCCSensors" : { #Will rewrite when Mikee gives me a mod flag for http://openperipheral.info/releases
        #    "function" : CheckOCS,
        #    "version" : "",
        #    "mc" : "",
        #    "change" : "NOT_USED",
        #    "active" : False
        #},
        #"OpenPeripheral" : {
        #    "function" : CheckOP,
        #    "version" : "",
        #    "mc" : "",
        #    "change" : "NOT_USED",
        #    "active" : False
        #},
        "MineFactoryReloaded" : {
            "function" : CheckJenkins,
            "version" : "",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/view/PowerCrystals/job/MineFactoryReloaded/lastSuccessfulBuild/api/json",
                "regex": "MineFactoryReloaded-(?P<dev>.+?).jar$",
                "item": 1
            }
        },
        "IndustrialCraft2" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://ic2api.player.to:8080/job/IC2_lf/lastSuccessfulBuild/api/json",
                "regex" : "industrialcraft-2_(?P<dev>.+?)-lf.jar$",
                "item" : 2
            }
        },
        "ModularPowersuits" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/ModularPowersuits/lastSuccessfulBuild/api/json",
                "regex" : "ModularPowersuits-(?P<mc>.+?)-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "ModularPowersuits-Addons" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/ModularPowersuitsAddons/lastSuccessfulBuild/api/json",
                "regex" : "MPSA-(?P<dev>.+?)_(.+?).jar$",
                "item" : 0
            }
        },
        "MFFSv2Classic" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://minalien.com:8080/job/Modular%20Forcefield%20System/lastSuccessfulBuild/api/json",
                "regex" : "ModularForcefieldSystem-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "InventoryTweaks" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/Inventory-Tweaks/lastSuccessfulBuild/api/json",
                "regex" : "InventoryTweaks-MC(?P<mc>.+?)-(?P<dev>.+?).jar",
                "item" : 1
            }
        },
        "DimensionalDoors" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/DimDoors/lastSuccessfulBuild/api/json",
                "regex" : "DimensionalDoors-(?P<mc>.+?)R(?P<dev>.+?).zip$",
                "item" : 0
            }
        },
        "PowerCrystalsCore" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/PowerCrystalsCore/lastSuccessfulBuild/api/json",
                "regex" : "PowerCrystalsCore-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "PowerConverters" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/PowerConverters/lastSuccessfulBuild/api/json",
                "regex" : "PowerConverters-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "AdditionalBuildcraftObjects" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "https://jenkins.ra-doersch.de/job/AdditionalBuildcraftObjects/lastSuccessfulBuild/api/json",
                "regex" : "buildcraft-Z-additional-buildcraft-objects-(?P<dev>.+?).jar$",
                "item" : 1
            }
        },
        "Galacticraft" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://2.iongaming.org:8080/job/Galacticraft/lastSuccessfulBuild/api/json",
                "regex" : "Galacticraft-(?P<mc>.+?)-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "NEM-VersionChecker" : {
            "function" : CheckJenkins,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://ci.thezorro266.com/job/NEM-VersionChecker/lastSuccessfulBuild/api/json",
                "regex" : "NEM-VersionChecker-MC(?P<mc>.+?)-(?P<version>.+?).jar$",
                "item" : 0
            }
        },
        "Buildcraft" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://nallar.me/buildservice/job/Buildcraft/lastSuccessfulBuild/api/json",
                "regex" : "buildcraft-universal-(?P<mc>.+?)-(?P<dev>.+?).jar$",
                "item" : 0
            }
        },
        "MCPC-PLUS" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://ci.md-5.net/job/MCPC-Plus/lastSuccessfulBuild/api/json",
                #mcpc-plus-1.6.2-R0.2-forge819-B53.jar
                "regex": "mcpc-plus-(?P<mc>.+?)-(.+?)-(.+?)-(?P<dev>.+?).jar$",
                "item": 0
            }
        },
        "Artifice" : {
            "function" : CheckJenkins,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/Artifice/lastSuccessfulBuild/api/json",
                "regex": "Artifice-(?P<dev>.+?).jar$",
                "item": 0
            }
        },
        "CodeChickenCore" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "ChickenChunks" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "NotEnoughItems" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "EnderStorage" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "Translocator" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "WR-CBE" : {
            "function" : CheckChickenBones,
            "version" : "",
            "dev"    : "NOT_USED",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True
        },
        "TinkersConstruct" : {
            "function" : CheckmDiyo,
            "version" : "NOT_USED",
            "dev"    : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "mDiyo" : {
                "location" : "TConstruct/development/",
                "regex" : "TConstruct_(?P<mc>.+?)_(?P<dev>.+?).jar"
            }
        }
    }
NEM = NotEnoughClasses()
def ChatEvent(self, channels, userdata, message, currChannel):
    #detect initial list
    match = re.match("^Current list: (.+?)$",message)
    if match:
        NEM.nemVersion = match.group(1).split(" ")[0]
        #self.sendChatMessage(self.send, currChannel, "Confirming latest version is: "+match.group(1))
    else:
        #detect list change
        match = re.match("^switched list to: \002\00312(.+?)\003\002$",message)
        if match:
            NEM.nemVersion = match.group(1)
            #self.sendChatMessage(self.send, currChannel, "Confirming list change to: "+match.group(1))

def running(self, name, params, channel, userdata, rank):
    if len(params) == 2 and (params[1] == "true" or params[1] == "on"):
        if not self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendChatMessage(self.send, channel, "Turning NotEnoughModPolling on.")
            NEM.InitiateVersions()
            self.events["time"].addEvent("NotEnoughModPolling", 60*5, MainTimerEvent, [channel])
            
            #Detect current list (and future changes)
            if self.events["chat"].doesExist("NEMP"):
                self.events["chat"].removeEvent("NEMP")
            self.events["chat"].addEvent("NEMP", ChatEvent, [channel])
            self.sendChatMessage(self.send, channel, "!current")
        else:
            self.sendChatMessage(self.send, channel, "NotEnoughMods-Polling is already running.")
    if len(params) == 2 and (params[1] == "false" or params[1] == "off"):
        if self.events["time"].doesExist("NotEnoughModPolling"):
            self.sendChatMessage(self.send, channel, "Turning NotEnoughPolling off.") 
            self.events["time"].removeEvent("NotEnoughModPolling")
        else:
            self.sendChatMessage(self.send, channel, "NotEnoughModPolling isn't running!")
def PollingThread(self, pipe):
    tempList = {}
    for mod in NEM.mods:
        if NEM.mods[mod]["active"]:
            result = NEM.CheckMod(mod)
            if result[0]:
                if NEM.mods[mod]["mc"] in tempList:
                    tempList[NEM.mods[mod]["mc"]].append((mod, result[1:]))
                else:
                    tempVersion = [(mod, result[1:])]
                    tempList[NEM.mods[mod]["mc"]] = tempVersion
    pipe.send(tempList)
def MainTimerEvent(self,channels):
    self.threading.addThread("NEMP", PollingThread)
    self.events["time"].addEvent("NEMP_ThreadClock", 10, MicroTimerEvent, channels, from_event = True)
def MicroTimerEvent(self,channels):
    yes = self.threading.poll("NEMP")
    if yes:
        tempList = self.threading.recv("NEMP")
        self.threading.sigquitThread("NEMP")
        self.events["time"].removeEvent("NEMP_ThreadClock", from_event = True)
        for channel in channels:
            setList = "null"
            for version in tempList:
                if setList == "null":
                    if version != NEM.nemVersion:
                        self.sendChatMessage(self.send, channel, "!setlist "+version)
                elif version != setList:
                    self.sendChatMessage(self.send, channel, "!setlist "+version)
                        
                for item in tempList[version]:
                    # item[0] = name of mod
                    # item[1] = flags for dev/release change
                    # flags[0] = has release version changed?
                    # flags[1] = has dev version changed?
                    mod = item[0]
                    flags = item[1]
                    if NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        self.sendChatMessage(self.send, channel, "!dev "+mod+" "+NEM.mods[mod]["dev"])
                    if NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.sendChatMessage(self.send, channel, "!mod "+mod+" "+NEM.mods[mod]["version"])
                    if NEM.mods[mod]["change"] != "NOT_USED":
                        self.sendChatMessage(self.send, channel, " * "+NEM.mods[mod]["change"])
                setList = version
            if (setList != NEM.nemVersion):
                if setList != "null":
                    self.sendChatMessage(self.send,channel, "!setlist "+NEM.nemVersion)
                
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
        print(e)

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
    darkgreen = "3"
    red = "4"
    blue = "12"
    bold = unichr(2)
    color = unichr(3)
    tempList = {}
    for key in NEM.mods:
        type = ""
        mcver = NEM.mods[key]["mc"]
        if NEM.mods[key]["version"] != "NOT_USED":
            type = type + bold + color + darkgreen + "[R]" + color + bold
        if NEM.mods[key]["dev"] != "NOT_USED":
            type = type + bold + color + red + "[D]" + color + bold
        
        if not mcver in tempList:
            tempList[mcver] = []
        tempList[mcver].append("{0}{1}".format(key,type))
    
    del mcver
    for mcver in tempList:
        tempList[mcver].sort()
        self.sendChatMessage(self.send,channel, "Mods checked for {0}: {1}".format(color+blue+bold+mcver+color+bold, ', '.join(tempList[mcver])))

def refresh(self,name,params,channel,userdata,rank):
    NEM.QueryNEM()
    NEM.InitiateVersions()
    self.sendChatMessage(self.send,channel, "Queried NEM for \"latest\" versions")

commands = {
    "running" : running,
    "poll" : poll,
    "list" : list,
    "about": about,
    "help" : help,
    "setversion" : setversion,
    "getversion" : getversion,
    "refresh" : refresh,
}

help = {
    "list" : ["=nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["=nemp about", "Shows some info about this plugin."],
    "help" : ["=nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setversion" : ["=nemp setversion <version>", "Sets the version to <version> for polling to assume."],
    "running" : ["=nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll" : ["=nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "refresh" : ["=nemp refresh", "Queries NEM to get the \"latest\" versions"],
}
