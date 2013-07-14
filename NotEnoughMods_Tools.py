import urllib
import urllib2
import simplejson
import re
import traceback
import threading
import time

ID = "nem"
permission = 1

class NotEnoughClasses(): 
    def getLatestVersion(self):
        try:
            NEMfeed = urllib2.urlopen("http://bot.notenoughmods.com/?json", timeout = 10)
            result = NEMfeed.read()
            NEMfeed.close()
            jsonres = simplejson.loads(result, strict = False )
            keys = jsonres.keys() #is different in Python 3.x
            return keys[0]
        except:
            print "dafuq, getting version failed, falling back to hard-coded"
            return "1.5.2"
    def __init__(self):
        self.version = self.getLatestVersion()
        
NEM = NotEnoughClasses()
     
def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        command(self, name, params, channel, userdata, rank)
    except KeyError:
        self.sendChatMessage(self.send, channel, "Invalid arguments!")

def setlist(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["setlist"][1])
    else:        
        colourblue = unichr(2)+unichr(3)+"12"
        colour = unichr(3)+unichr(2)
        
        NEM.version = str(params[1])
        self.sendChatMessage(self.send, channel, "switched list to: "+colourblue+params[1]+colour)
        
def list(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["list"][1])
        return
    if len(params) >= 3:
        version = params[2]
    else:
        version = NEM.version
    try:
        NEMfeed = urllib.urlopen("http://bot.notenoughmods.com/"+urllib.quote(version)+".json")
        result = NEMfeed.read()
        NEMfeed.close()
        jsonres = simplejson.loads(result, strict = False )
        results = []
        i = -1
        for mod in jsonres:
            i = i + 1
            if str(params[1]).lower() in str(mod["name"]).lower():
                results.append(i)
                continue
            else:
                aliases = mod["aliases"].split(" ")
                for alias in aliases:
                    if params[1].lower() in alias.lower():
                        results.append(i)
                        break
        orange = "7"
        blue = "12"
        gray = "14"
        lightgray = "15"
        bold = unichr(2)
        colour = unichr(3)
        count = len(results)
        if count == 0:
            self.sendChatMessage(self.send, channel, name+ ": no results found.")
            return
        elif count == 1:
            count = str(count)+" result"
        else:
            count = str(count)+" results"
        self.sendChatMessage(self.send, channel, "Listing "+count+" for \""+params[1]+"\" in "+bold+colour+blue+version+colour+bold+":")
        for line in results:
            alias = colour
            if jsonres[line]["aliases"] != "":
                alias = colour+"("+colour+gray+str(re.sub(" ", ', ', jsonres[line]["aliases"]))+colour+") "
            comment = colour
            if jsonres[line]["comment"] != "":
                comment = str(colour+"["+colour+gray+jsonres[line]["comment"]+colour+"] ")
            self.sendChatMessage(self.send, channel, colour+gray+jsonres[line]["name"]+" "+alias+colour+lightgray+jsonres[line]["version"]+" "+comment+colour+orange+jsonres[line]["shorturl"]+colour)
    except Exception as error:
        self.sendChatMessage(self.send, channel, name+": "+str(error))
        traceback.print_exc()
        
def about(self, name, params, channel, userdata, rank):
    self.sendChatMessage(self.send, channel, "Not Enough Mods toolkit for IRC by SinZ v3.0")
    
def help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendChatMessage(self.send, channel, name+ ": Available commands: " + ", ".join(help))
    else:
        command = params[1]
        if command in help:
            for line in help[command]:
                self.sendChatMessage(self.send, channel, name+ ": "+line)
        else:
            self.sendChatMessage(self.send, channel, name+ ": Invalid command provided")
commands = {
    "list" : list,
    "about": about,
    "help" : help,
    "setlist" : setlist
}
help = {
    "list" : ["=nem list <search> <version>", "Searchs the NotEnoughMods database for <search> and returns all results to IRC"],
    "about": ["=nem about", "Shows some info about this plugin."],
    "help" : ["=nem help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setlist" : ["=nem setlist <version>", "Sets the default version to <version> for the other commands."]
}