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
                        #print("a")
                        if self.mods[mod["name"]]["dev"] == True:
                            self.mods[mod["name"]]["version"] = mod["dev"]
                            #print("b")
                        else:
                            self.mods[mod["name"]]["version"] = mod["version"]
                        #print("c")
                        templist.remove(mod["name"])
                        #print("d")
        
    def QueryJenkins(self, url, start, end):
        jenkinFeed = urllib2.urlopen(url, timeout = 10)
        result = jenkinFeed.read()
        jenkinFeed.close()
        lines = result.split()
        result = ""
        for line in lines:
            if end in line.lower():
                result = line
                break
        result = result[6:]
        i = result.find('"')
        j = result.find(start)
        result = result[j+1:i-4]
        return result
        
    def CheckMPSA(self,mod):
        result = self.QueryJenkins("http://build.technicpack.net/job/ModularPowersuitsAddons/lastSuccessfulBuild/artifact/build/dist/","-",".jar") # TODO: FIX!
        k = result.find("_")
        return {
            "version" : result[0:k]
        } 
    def CheckInvTweaks(self,mod):
        result = self.QueryJenkins("http://build.technicpack.net/job/Inventory-Tweaks/lastSuccessfulBuild/artifact/build/out/", "-", ".jar")
        i = result.find("-")
        result = result[i+1:]
        j = result.find("-")
        version = result[2:j]
        result = result[j+1:]
        return {
            "version" : result,
            "mc" : version
        }
    def CheckJenkinsNew(self, mod):
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
    def CheckJenkins(self, mod): # foo-x.x.x
        return {
            "version" : self.QueryJenkins(self.mods[mod]["jenkins"]["url"],self.mods[mod]["jenkins"]["start"],self.mods[mod]["jenkins"]["extention"])
        }
    def CheckJenkinsMC(self,mod): # foo-1.6.1-x.x.x
        output = self.QueryJenkins(self.mods[mod]["jenkins"]["url"],self.mods[mod]["jenkins"]["start"],self.mods[mod]["jenkins"]["extention"])
        i = output.find("-")
        version = output[i+1:]
        mcver = output[0:i]
        return {
            "version" : version,
            "mc" : mcver
        }
    def CheckJenkinsMC2(self,mod): #foo-bar-1.6.2-x.x.x
        result = self.QueryJenkins(self.mods[mod]["jenkins"]["url"],self.mods[mod]["jenkins"]["start"],self.mods[mod]["jenkins"]["extention"])
        i = result.rfind("-")
        j = result.find("-")
        return {
            "version" : result[i+1:],
            "mc" : result[j+1+len(self.mods[mod]["prefix"]):i]
        }
    def CheckMCForge(self,mod):
        forgeFeed = urllib2.urlopen("http://files.minecraftforge.net/"+self.mods[mod]["mcforge"]["name"]+"/json", timeout = 10)
        result = forgeFeed.read()
        forgeFeed.close()
        jsonres = simplejson.loads(result, strict = False )
        promotionArray = jsonres["promotions"]
        for promotion in promotionArray:
            if promotion["name"] == self.mods[mod]["mcforge"]["promotion"]:
                info = promotion["files"][0]["url"]
                match = re.search(self.mods[mod]["mcforge"]["regex"],info)
                if match:   
                    return {
                        "version" : match.group(2),
                        "mc" : match.group(1)
                    } 
    def CheckChickenBones(self,mod):
        chickenFeed = urllib2.urlopen("http://www.chickenbones.craftsaddle.org/Files/New_Versions/version.php?file="+mod+"&version="+self.mods[mod]["mc"], timeout = 10)
        result = chickenFeed.read()
        chickenFeed.close()
        if result.startswith("Ret: "): #Hacky I know, but this is how ChickenBones does it in his mod
            print(mod+": "+result[5:]) #This is also hacky, but ^
            return {
                "version" : result[5:]
            }
    def CheckMod(self, mod):
        try:
            output = self.mods[mod]["function"](self,mod)
            if self.mods[mod]["version"] != output["version"]:
                self.mods[mod]["version"] = output["version"]
                if "mc" in output:
                    self.mods[mod]["mc"] = output["mc"]
                if "change" in output:
                    self.mods[mod]["change"] = output["change"]
                return True
        except:
            print mod+" failed to be polled..."
    #def CheckOpenMod(self,mod):
        
    mods = {
        "MinecraftForge" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "mcforge" : {
                "name" : "minecraftforge",
                "promotion" : "latest",
                "regex" : "minecraftforge-src-(.+?)-(.+?).zip$"
            }
        },
        "IronChests" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "mcforge" : {
                "name" : "IronChests2",
                "promotion" : "latest",
                "regex" : "ironchest-universal-(.+?)-(.+?).zip$"
            }
        },
        "ForgeMultipart" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "mcforge" : {
                "name" : "ForgeMultipart",
                "promotion" : "latest",
                "regex" : "ForgeMultipart-universal-(.+?)-(.+?).jar$"
            }
        },
        "CompactSolars" : {
            "function" : CheckMCForge,
            "version" : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "dev" : True,
            "mcforge" : {
                "name" : "CompactSolars",
                "promotion" : "latest",
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
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/view/PowerCrystals/job/MineFactoryReloaded/lastSuccessfulBuild/api/json",
                "regex": "MineFactoryReloaded-(?P<version>.+?).jar$",
                "item": 1
            }
        },
        "IndustrialCraft2" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://ic2api.player.to:8080/job/IC2_lf/lastSuccessfulBuild/api/json",
                "regex" : "industrialcraft-2_(?P<version>.+?)-lf.jar$",
                "item" : 2
            }
        },
        "ModularPowersuits" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/Machine-Muse-Power-Suits/lastSuccessfulBuild/api/json",
                "regex" : "ModularPowersuits-(?P<mc>.+?)-(?P<version>.+?).jar$",
                "item" : 0
            }
        },
        "ModularPowersuits-Addons" : {
            "function" : CheckMPSA,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True
        },
        "MFFSv2Classic" : {
            "function" : CheckJenkins,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://minalien.com:8080/job/Modular%20Forcefield%20System/lastSuccessfulBuild/artifact/bin/",
                "start" : "-",
                "extention" : ".jar"
            }
        },
        "InventoryTweaks" : {
            "function" : CheckInvTweaks,
            "version" : "",
            "mc" : "",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True
        },
        "DimensionalDoors" : {
            "function" : CheckJenkins,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/DimDoors/lastSuccessfulBuild/artifact/build/dist/",
                "start" : "R",
                "extention" : ".zip"
            }
        },
        "PowerCrystalsCore" : {
            "function" : CheckJenkins,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/PowerCrystalsCore/lastSuccessfulBuild/artifact/build/dist/",
                "start" : "-",
                "extention" : ".jar"
            }
        },
        "PowerConverters" : {
            "function" : CheckJenkins,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/PowerConverters/lastSuccessfulBuild/artifact/build/dist/",
                "start" : "-",
                "extention" : ".jar"
            }
        },
        "AdditionalBuildcraftObjects" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "https://jenkins.ra-doersch.de/job/AdditionalBuildcraftObjects/lastSuccessfulBuild/api/json",
                "regex" : "buildcraft-Z-additional-buildcraft-objects-(?P<version>.+?).jar$",
                "item" : 1
            }
        },
        "Galacticraft" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://2.iongaming.org:8080/job/Galacticraft/lastSuccessfulBuild/api/json",
                "regex" : "Galacticraft-(?P<mc>.+?)-(?P<version>.+?).jar$",
                "item" : 0
            }
        },
        "NEM-VersionChecker" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "dev"    : False,
            "jenkins" : {
                "url" : "http://ci.thezorro266.com/job/NEM-VersionChecker/lastSuccessfulBuild/api/json",
                "regex" : "NEM-VersionChecker-MC(?P<mc>.+?)-(?P<version>.+?).jar$",
                "item" : 0
            }
        },
        "Buildcraft" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "dev" : True,
            "jenkins" : {
                "url" : "http://nallar.me/buildservice/job/Buildcraft/lastSuccessfulBuild/api/json",
                "regex" : "buildcraft-universal-(?P<mc>.+?)-(?P<version>.+?).jar$",
                "item" : 0
            }
        },
        "MCPC-PLUS" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "active" : True,
            "dev" : True,
            "jenkins" : {
                "url" : "http://ci.md-5.net/job/MCPC-Plus/lastSuccessfulBuild/api/json",
                #mcpc-plus-1.6.2-R0.2-forge819-B53.jar
                "regex": "mcpc-plus-(?P<mc>.+?)-(.+?)-(.+?)-(?P<version>.+?).jar$",
                "item": 0
            }
        },
        "Artifice" : {
            "function" : CheckJenkinsNew,
            "version" : "",
            "mc" : "",
            "change" : "",
            "active" : True,
            "dev"    : True,
            "jenkins" : {
                "url" : "http://build.technicpack.net/job/Artifice/lastSuccessfulBuild/api/json",
                "regex": "Artifice-(?P<version>.+?).jar$",
                "item": 0
            }
        },
        "CodeChickenCore" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
        },
        "ChickenChunks" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
        },
        "NotEnoughItems" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
        },
        "EnderStorage" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
        },
        "Translocator" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
        },
        "WR-CBE" : {
            "function" : CheckChickenBones,
            "version" : "",
            "mc" : "NOT_USED",
            "change" : "NOT_USED",
            "active" : True,
            "dev"    : False
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
            self.events["time"].addEvent("NotEnoughModPolling", 60*5, TimerEvent, [channel])
            
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
def TimerEvent(self,channels):
    for channel in channels:
        tempList = {}
        setList = "null"
        for mod in NEM.mods:
            if NEM.mods[mod]["active"]:
                if NEM.CheckMod(mod):
                    if NEM.mods[mod]["mc"] in tempList:
                        tempList[NEM.mods[mod]["mc"]].append(mod)
                    else:
                        tempVersion = [mod]
                        tempList[NEM.mods[mod]["mc"]] = tempVersion
        for version in tempList:
            if setList == "null":
                if version != NEM.nemVersion:
                    self.sendChatMessage(self.send, channel, "!setlist "+version)
            elif version != setList:
                self.sendChatMessage(self.send, channel, "!setlist "+version)
                    
            for mod in tempList[version]:
                if NEM.mods[mod]["dev"] == True:
                    self.sendChatMessage(self.send, channel, "!dev "+mod+" "+NEM.mods[mod]["version"])
                else:
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
    self.sendChatMessage(self.send, channel, "Not Enough Mods: Polling for IRC by SinZ v1.2")
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
    tempList = {}
    for key in NEM.mods:
        dev = ""
        mcver = NEM.mods[key]["mc"]
        if NEM.mods[key]["dev"] == True:
            dev = "(dev)"
        if not mcver in tempList:
            tempList[mcver] = []
        tempList[mcver].append("{0}{1}".format(key,dev))
    
    del mcver
    for mcver in tempList:
        self.sendChatMessage(self.send,channel, "Mods checked for MC{0}: {1}".format(mcver, ', '.join(tempList[mcver])))

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
    "refresh" : refresh
}

help = {
    "list" : ["=nemp list", "Lists the mods that NotEnoughModPolling checks"],
    "about": ["=nemp about", "Shows some info about this plugin."],
    "help" : ["=nemp help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setversion" : ["=nemp setversion <version>", "Sets the version to <version> for polling to assume."],
    "running" : ["=nemp running <true/false>", "Enables or Disables the polling of latest builds."],
    "poll" : ["=nemp poll <mod> <true/false>", "Enables or Disables the polling of <mod>."],
    "refresh" : ["=nemp refresh", "Queries NEM to get the \"latest\" versions"]
}
