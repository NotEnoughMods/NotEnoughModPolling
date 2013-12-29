import urllib2
import simplejson
import re
import traceback
from StringIO import StringIO
import gzip

from centralizedThreading import FunctionNameAlreadyExists  # @UnresolvedImport (this makes my IDE happy <_<)

ID = "nemp"
permission = 1
privmsgEnabled = True

class NotEnoughClasses():
    nemVersions = []
    nemVersion = ""
    
    newMods = False
    mods = {}
    
    updatequeue = []
    
    def __init__(self):
        self.useragent = urllib2.build_opener()
        self.useragent.addheaders = [
            ('User-agent', 'NotEnoughMods:Polling/1.X (+http://github.com/SinZ163/NotEnoughMods)'),
            ('Accept-encoding', 'gzip')
        ]
        
        self.buildModDict()
        self.buildHTML()
        self.QueryNEM()
        self.InitiateVersions()

    def fetch_page(self, url, decompress=True, timeout=10):
        try:
            response = self.useragent.open(url, timeout=timeout)
            if response.info().get('Content-Encoding') == 'gzip' and decompress:
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf, mode='rb')
                data = f.read()
            else:
                data = response.read()
            return data
        except:
            pass
            #most likely a timeout

    def buildModDict(self):
        modList = open("commands/NEMP/mods.json", "r")
        fileInfo = modList.read()
        self.mods = simplejson.loads(fileInfo, strict = False)
        for mod in self.mods:
            if "change" not in self.mods[mod]:
                self.mods[mod]["change"] = "NOT_USED"
    def buildHTML(self):
        headerText = ""
        with open("commands/NEMP/header.txt", "r") as f:
            headerText = f.read()
        footerText = ""
        with open("commands/NEMP/footer.txt", "r") as f:
            footerText = f.read()
        with open("commands/NEMP/htdocs/index.html", "w") as f:
            f.write(re.sub("~MOD_COUNT~", str(len(self.mods)), headerText))
            for modName, info in sorted(self.mods.iteritems()): # TODO: make this not terrible
                if info["active"]:
                    isDisabled = "active"
                else:
                    isDisabled = "disabled"
                f.write("""
        <tr class='{}'>
            <td class='name'>{}</td>""".format(isDisabled,modName))
                f.write("""
            <td class='function'>{}</td>
""".format(info["function"]))
                try:
                    f.write("            <td class='category'>{}</td>\r\n".format(info["category"]))
                except:
                    pass
                f.write("        </tr>\r\n")
            f.write(footerText)
            
    def QueryNEM(self):
        try:
            result = self.fetch_page("http://bot.notenoughmods.com/?json")
            self.nemVersions = reversed(simplejson.loads(result, strict = False))
        except:
            print("Failed to get NEM versions, falling back to hard-coded")
            traceb = str(traceback.format_exc())
            print(traceb)
            self.nemVersions = reversed(["1.4.5","1.4.6-1.4.7","1.5.1","1.5.2","1.6.1","1.6.2","1.6.4","1.7.2"])
            
    def InitiateVersions(self):
        templist = self.mods.keys()
        try:
            for version in self.nemVersions:
                if "-dev" not in version: #is this still needed?
                    rawJson = self.fetch_page("http://bot.notenoughmods.com/"+version+".json")
                    
                    jsonres = simplejson.loads(rawJson, strict = False)
                    
                    for mod in jsonres:
                        if mod["name"] in templist:
                            self.mods[mod["name"]]["mc"] = version
                            
                            if "dev" in mod and mod["dev"]:
                                self.mods[mod["name"]]["dev"] = str(mod["dev"])         #Inconsistant JSON is bad, and Pyker should feel bad.
                            else:
                                self.mods[mod["name"]]["dev"] = "NOT_USED"
                            
                            if "version" in mod and mod["version"]:
                                self.mods[mod["name"]]["version"] = str(mod["version"]) #Inconsistant JSON is bad, and Pyker should feel bad.
                            else:
                                self.mods[mod["name"]]["version"] = "NOT_USED"
                            
                            templist.remove(mod["name"])
        except:
            pass
            #most likely a timeout
        
    def CheckJenkins(self, mod):
        result = self.fetch_page(self.mods[mod]["jenkins"]["url"])
        jsonres = simplejson.loads(result, strict = False )
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = re.search(self.mods[mod]["jenkins"]["regex"],filename)
        output = match.groupdict()
        try:
            output["change"] = jsonres["changeSet"]["items"][0]["comment"]
        except:
            output["change"] = "NOT_USED"
        return output
    def CheckMCForge2(self,mod):
        result = self.fetch_page(self.mods[mod]["mcforge"]["url"])
        jsonres = simplejson.loads(result, strict=False)
        
        for promo in jsonres["promos"]:
            if promo == self.mods[mod]["mcforge"]["promo"]:
                return {
                    self.mods[mod]["mcforge"]["promoType"] : jsonres["promos"][promo]["version"],
                    "mc" : jsonres["promos"][promo]["mcversion"]
                }
        return {}

    def CheckMCForge(self,mod):
        result = self.fetch_page("http://files.minecraftforge.net/"+self.mods[mod]["mcforge"]["name"]+"/json")
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
        result = self.fetch_page("http://www.chickenbones.craftsaddle.org/Files/New_Versions/version.php?file="+mod+"&version="+self.mods[mod]["mc"])
        if result.startswith("Ret: "): #Hacky I know, but this is how ChickenBones does it in his mod
            return {
                "version" : result[5:]
            }
            
    def CheckmDiyo(self,mod):
        result = self.fetch_page("http://tanis.sunstrike.io/"+self.mods[mod]["mDiyo"]["location"])
        lines = result.split()
        result = ""
        for line in lines:
            if ".jar" in line.lower():
                result = line
        match = re.search(self.mods[mod]["mDiyo"]["regex"],result)
        output = match.groupdict()
        return output
        
    def CheckAE(self,mod):
        result = self.fetch_page("http://ae-mod.info/releases")
        jsonres = simplejson.loads(result, strict = False )
        jsonres = sorted(jsonres, key=lambda k: k['Released'])
        relVersion = ""
        #relMC = ""
        devVersion = ""
        devMC = ""
        for version in jsonres:
            if version["Channel"] == "Stable":
                relVersion = version["Version"]
                #relMC = version["Minecraft"]
            else:
                devVersion = version["Version"]
                devMC = version["Minecraft"]
        return {
            "version" : relVersion,
            "dev" : devVersion,
            "mc" : devMC #TODO: this doesn't seem reliable...
        }
        
    def CheckDropBox(self,mod):
        result = self.fetch_page(self.mods[mod]["html"]["url"])
        match = None
        for match in re.finditer(self.mods[mod]["html"]["regex"], result):
            pass
        # "match" is still in this scope
        if match:
            match = match.groupdict()

            if 'mc' not in match:
                match['mc'] = self.mods[mod]['mc']

            # we already have the 'version', 'dev' and 'mc' fields from the regex
            return match
        else:
            return {}
        
    def CheckHTML(self,mod):
        result = self.fetch_page(self.mods[mod]["html"]["url"])
        output = {}
        for line in result.splitlines():
            match = re.search(self.mods[mod]["html"]["regex"], line)
            if match:
                output = match.groupdict()
        return output
        
    def CheckSpacechase(self,mod):
        result = self.fetch_page("http://spacechase0.com/wp-content/plugins/mc-mod-manager/nem.php?mc=6")
        for line in result.splitlines():
            info = line.split(',')
            #0 = ID, 1=NEM ID, 2=ModID, 3=Author, 4=Link, 5=Version, 6=Comment
            if info[1] == mod:
                return {
                    "version" : info[5]
                }
        return {}
    def CheckLunatrius(self,mod):
        result = self.fetch_page("http://mc.lunatri.us/json?latest&mod="+mod)
        jsonres = simplejson.loads(result, strict = False )
        info = jsonres["mods"][mod]["latest"]
        return {
            "version" : info["version"],
            "mc" : info["mc"]
        }
    def CheckBigReactors(self,mod):
        result = self.fetch_page("http://big-reactors.com/version.json")
        info = simplejson.loads(result, strict = False)
        return {
            "version" : info["version"],
            "mc" : info["version-minecraft"]
        }
    def CheckMod(self, mod):
        try:
            # First False is for if there was an update.
            # Next two Falses are for if there was an dev or version change
            status = [False, 
                      False, False]
            output = getattr(self, self.mods[mod]["function"])(mod)
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
            traceback.print_exc()
            return [False, False, False]
    
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
            try:
                self.events["time"].removeEvent("NotEnoughModPolling")
                self.events["time"].removeEvent("NEMP_ThreadClock")
                self.threading.sigquitThread("NEMP")
            except:
                pass
        else:
            self.sendChatMessage(self.send, channel, "NotEnoughModPolling isn't running!")

def PollingThread(self, pipe):
    if NEM.newMods:
        NEM.mods = NEM.newMods
        NEM.InitiateVersions()
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
            for version in tempList:
                for item in tempList[version]:
                    # item[0] = name of mod
                    # item[1] = flags for dev/release change
                    # flags[0] = has release version changed?
                    # flags[1] = has dev version changed?
                    mod = item[0]
                    flags = item[1]
                    
                    
                    if NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        self.writeQueue("Updating DevMod {0}, Flags: {1}".format(mod, flags), "NEMP")
                        self.sendChatMessage(self.send, channel, "!ldev "+version+" "+mod+" "+unicode(NEM.mods[mod]["dev"]))
                    if NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.writeQueue("Updating Mod {0}, Flags: {1}".format(mod, flags), "NEMP")
                        self.sendChatMessage(self.send, channel, "!lmod "+version+" "+mod+" "+unicode(NEM.mods[mod]["version"]))
                    if NEM.mods[mod]["change"] != "NOT_USED":
                        self.writeQueue("Sending text for Mod {0}".format(mod), "NEMP")
                        self.sendChatMessage(self.send, channel, " * "+NEM.mods[mod]["change"].encode("utf-8"))
                
def poll(self, name, params, channel, userdata, rank):
    if len(params) < 3:
        self.sendChatMessage(self.send, channel, name+ ": Insufficient amount of parameters provided. Required: 2")
        self.sendChatMessage(self.send, channel, name+ ": "+help["poll"][1])
        
    else:
        setting = False
        if params[2].lower() in ("true","yes","on"):
                setting = True
        elif params[2].lower() in ("false","no","off"):
            setting = False
        
        if params[1][0:2].lower() == "c:":
            for mod in NEM.mods:
                if "category" in NEM.mods[mod] and NEM.mods[mod]["category"] == params[1][2:]:
                    NEM.mods[mod]["active"] = setting
                    self.sendChatMessage(self.send, channel, name+ ": "+mod+"'s poll status is now "+str(setting))
        elif params[1] in NEM.mods:
            NEM.mods[params[1]]["active"] = setting
            self.sendChatMessage(self.send, channel, name+ ": "+params[1]+"'s poll status is now "+str(setting))
        elif params[1].lower() == "all":
            for mod in NEM.mods:
                NEM.mods[mod]["active"] = setting
            self.sendChatMessage(self.send, channel, name+ ": All mods are now set to "+str(setting))
     
def execute(self, name, params, channel, userdata, rank, chan):
    if len(params) > 0:
        try:
            command = commands[params[0]]
            command(self, name, params, channel, userdata, rank)
        except KeyError:
            self.sendChatMessage(self.send, channel, "invalid command!")
            self.sendChatMessage(self.send, channel, "see =nemp help for a list of commands")
    else:
        self.sendChatMessage(self.send, channel, name+": see \"=nemp help\" for a list of commands")

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
    self.sendChatMessage(self.send, channel, "Not Enough Mods: Polling for IRC by SinZ, with help from NightKev - v1.3")
    self.sendChatMessage(self.send, channel, "Source code available at: http://github.com/SinZ163/NotEnoughMods")
    
def nemp_help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendChatMessage(self.send, channel, name+ ": Available commands: " + ", ".join(helpDict))
        self.sendChatMessage(self.send, channel, name+ ": For command usage, use \"=nemp help <command>\".")
    else:
        command = params[1]
        if command in helpDict:
            for line in helpDict[command]:
                self.sendChatMessage(self.send, channel, name+ ": "+line)
        else:
            self.sendChatMessage(self.send, channel, name+ ": Invalid command provided")

def nemp_list(self,name,params,channel,userdata,rank):
    dest = ""
    if len(params) > 1:
        if params[1] == "pm":
            dest = userdata[0]
        elif params[1] == "broadcast":
            dest = channel
    if dest == "":
        self.sendChatMessage(self.send, channel, "http://nemp.mca.d3s.co/")
        return
    darkgreen = "03"
    red = "05"
    blue = "12"
    bold = unichr(2)
    color = unichr(3)
    tempList = {}
    for key, info in NEM.mods.iteritems():
        real_name = info.get('name', key)
        if NEM.mods[key]["active"]:
            relType = ""
            mcver = NEM.mods[key]["mc"]
            if NEM.mods[key]["version"] != "NOT_USED":
                relType = relType + color + darkgreen + "[R]" + color
            if NEM.mods[key]["dev"] != "NOT_USED":
                relType = relType + color + red + "[D]" + color
            
            if not mcver in tempList:
                tempList[mcver] = []
            tempList[mcver].append("{0}{1}".format(real_name,relType))
    
    del mcver
    for mcver in sorted(tempList.iterkeys()):
        tempList[mcver] = sorted(tempList[mcver], key=lambda s: s.lower())
        self.sendChatMessage(self.send, dest, "Mods checked for {} ({}): {}".format(color+blue+bold+mcver+color+bold, len(tempList[mcver]), ', '.join(tempList[mcver])))
    
def nemp_reload(self,name,params,channel,userdata,rank):
    NEM.buildModDict()
    NEM.QueryNEM()
    NEM.InitiateVersions()
    
    self.sendChatMessage(self.send,channel, "Reloaded the NEMP Database")
    
def test_parser(self,name,params,channel,userdata,rank):
    if len(params) > 0:
        if params[1] not in NEM.mods:
            self.sendChatMessage(self.send, channel, name+": No polling info for \""+params[1]+"\"")
            return
        try:
            result = getattr(NEM,NEM.mods[params[1]]["function"])(params[1])
            print(result)
            if "mc" in result:
                self.sendChatMessage(self.send,channel, "!setlist "+result["mc"])
            if "version" in result:
                self.sendChatMessage(self.send,channel, "!mod "+params[1]+" "+unicode(result["version"]))
            if "dev" in result:
                self.sendChatMessage(self.send,channel, "!dev "+params[1]+" "+unicode(result["dev"]))
            if "change" in result:
                self.sendChatMessage(self.send,channel, " * "+result["change"])
        except Exception as error:
            self.sendChatMessage(self.send, channel, name+": "+str(error))
            traceback.print_exc()
            self.sendChatMessage(self.send,channel, params[1]+" failed to be polled")

def test_polling(self,name,params,channel,userdata,rank):
    try:
        # PollingThread()
        if NEM.newMods:
            NEM.mods = NEM.newMods
            NEM.InitiateVersions()
        else:
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
                    
                    
                    
                    if NEM.mods[mod]["dev"] != "NOT_USED" and flags[0]:
                        self.sendChatMessage(self.send, channel, "!ldev "+version+" "+mod+" "+unicode(NEM.mods[mod]["dev"]))
                    if NEM.mods[mod]["version"]  != "NOT_USED" and flags[1]:
                        self.sendChatMessage(self.send, channel, "!lmod "+version+" "+mod+" "+unicode(NEM.mods[mod]["version"]))
                    if NEM.mods[mod]["change"] != "NOT_USED":
                        self.sendChatMessage(self.send, channel, " * "+NEM.mods[mod]["change"])
    
    except:
        self.sendChatMessage(self.send, channel, "An exception has occurred, check the console for more information.")
        traceback.print_exc()

def nktest(self,name,params,channel,userdata,rank):
    pass

def genHTML(self,name,params,channel,userdata,rank):
    NEM.buildHTML()

def queue(self,name,params,channel,userdata,rank): #Why is this still here
    if len(params) < 2:
        self.sendChatMessage(self.send, channel, "{} item(s) in the queue.".format(len(NEM.updatequeue)))
        
    elif params[1] in ("show","list","display"):
        i = 0
        if len(NEM.updatequeue) == 0:
            self.sendChatMessage(self.send, channel, "There are no items currently in the queue.")
            return
        for item in NEM.updatequeue:
            self.sendChatMessage(self.send, name, "{}: {}".format(i, item))
            i += 1
            
    elif params[1] in ("add","new") and len(params) > 2:
        NEM.updatequeue.append(" ".join(params[2:]))
        self.sendChatMessage(self.send, channel, "Success!")
    
    elif params[1] in ("del","delete","rem","remove","rm") and len(params) > 2:
        if rank > 0:
            if params[2].isdigit():
                del NEM.updatequeue[int(params[2])]
                self.sendChatMessage(self.send, channel, "Success!")
            else:
                self.sendChatMessage(self.send, channel, "'{}' is not a number.".format(params[2]))
                
    elif params[1] in ("execute","update") and len(params) > 2:
        if params[2].isdigit():
            index = int(params[2])
        else:
            self.sendChatMessage(self.send, channel, "'{}' is not a number.".format(params[2]))
            return
        
        if len(NEM.updatequeue) >= index and rank > 0:
            self.sendChatMessage(self.send, channel, NEM.updatequeue[index])
            del NEM.updatequeue[index]
            self.sendChatMessage(self.send, channel, "Success!")
            
    elif params[1] in ("help","?","info"):
        if len(params) == 2:
            self.sendChatMessage(self.send, channel, "Possible sub-commands include: show/list/display, add/new, del/delete/rem/remove/rm, execute/update, help/?/info. You can also type '=nemp queue' by itself to get the number of items in the queue.")
            self.sendChatMessage(self.send, channel, "Type =nemp queue help <sub-command> for more information about that specific sub-command.")
            
        else:
            if params[2] in ("show","list","display"):
                self.sendChatMessage(self.send, channel, "This will query you with the contents of the queue.")
                
            elif params[2] in ("add","new"):
                self.sendChatMessage(self.send, channel, "This will add a new item to the queue. Usage: '=nemp queue add [modinfo]'")
            
            elif params[2] in ("del","delete","rem","remove","rm"):
                self.sendChatMessage(self.send, channel, "This will remove an item from the queue. Usage: '=nemp queue del [index]'. Requires voiced or higher rank.")
            
            elif params[2] in ("execute","update"):
                self.sendChatMessage(self.send, channel, "This will send the queue item as a message to the channel and then remove it from the queue, it can be used if the queue item is a properly formatted ModBot command. Usage: '=nemp queue update [index]'")
                self.sendChatMessage(self.send, channel, "Example: If the second queue item is the string '!lmod 1.6.4 RedLogic 58.1.2', then you would type '=nemp queue update 1' (the queue starts at 0) and the bot would output that exact string to the channel.")
            
            elif params[2] in ("help","?","info"):
                self.sendChatMessage(self.send, channel, "Yes, that's the name of the help command, congrats.")

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
    "queue" : queue,
    
    # -- ALIASES -- #
    "setv" : setversion,
    "getv" : getversion,
    "polling" : running,
    "testpoll" : test_polling,
    "refresh" : nemp_reload
    # -- END ALIASES -- #
}

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
