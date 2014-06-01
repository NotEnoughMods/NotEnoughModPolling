import urllib2
import simplejson
import re
import traceback
import threading
import time
import gzip

from StringIO import StringIO

ID = "nem"
permission = 1

class NotEnoughClasses():
    def getLatestVersion(self):
        try:
            result = self.fetch_page("http://bot.notenoughmods.com/?json")
            return simplejson.loads(result, strict = False)
        except:
            print("Failed to get NEM versions, falling back to hard-coded")
            traceb = str(traceback.format_exc())
            print(traceb)
            return ["1.4.5","1.4.6-1.4.7","1.5.1","1.5.2","1.6.1","1.6.2", "1.6.4"]
    def __init__(self):
        self.useragent = urllib2.build_opener()
        self.useragent.addheaders = [
            ('User-agent', 'NotEnoughMods:Tools/1.X (+http://github.com/SinZ163/NotEnoughMods)'),
            ('Accept-encoding', 'gzip')
        ]

        self.versions = self.getLatestVersion()
        self.version = self.versions[len(self.versions)-1]

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

NEM = NotEnoughClasses()

def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        command(self, name, params, channel, userdata, rank)
    except:
        self.sendChatMessage(self.send, channel, "Invalid sub-command!")
        self.sendChatMessage(self.send, channel, "See \"=nem help\" for help")

def setlist(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["setlist"][1])
    else:
        colourblue = unichr(2)+unichr(3)+"12"
        colour = unichr(3)+unichr(2)

        NEM.version = str(params[1])
        self.sendChatMessage(self.send, channel, "switched list to: "+colourblue+params[1]+colour)
def multilist(self,name,params,channel,userdata,rank):
    if len(params) != 2:
        self.sendChatMessage(self.send, channel, name+ ": Insufficent amount of parameters provided.")
        self.sendChatMessage(self.send, channel, name+ ": "+help["multilist"][1])
    else:
        try:
            jsonres = {}
            results = {}
            for version in NEM.versions:
                result = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(version)+".json")
                jsonres[version] = simplejson.loads(result, strict = False )
                i = -1
                for mod in jsonres[version]:
                    i = i + 1
                    if str(params[1]).lower() == mod["name"].lower():
                        results[version] = i
                        break
                    else:
                        aliases = mod["aliases"].split(" ")
                        for alias in aliases:
                            if params[1].lower() == alias.lower():
                                results[version] = i
                                break
            darkgreen = "03"
            red = "05"
            purple = "06"
            orange = "07"
            blue = "12"
            pink = "13"
            gray = "14"
            lightgray = "15"
            bold = unichr(2)
            colour = unichr(3)
            count = len(results)
            if count == 0:
                self.sendChatMessage(self.send, channel, name+ ": mod not present in NEM.")
                return
            elif count == 1:
                count = str(count)+" MC version"
            else:
                count = str(count)+" MC versions"
            self.sendChatMessage(self.send, channel, "Listing "+count+" for \""+params[1]+"\":")
            for line in sorted(results.iterkeys()):
                alias = colour
                if jsonres[line][results[line]]["aliases"] != "":
                    alias = colour+"("+colour+pink+str(re.sub(" ", colour+', '+colour+pink, jsonres[line][results[line]]["aliases"]))+colour+") "
                comment = colour
                if jsonres[line][results[line]]["comment"] != "":
                    comment = str(colour+"["+colour+gray+jsonres[line][results[line]]["comment"]+colour+"] ")
                dev = colour
                try:
                    if jsonres[line][results[line]]["dev"] != "":
                        dev = str(colour+" ("+colour+gray+"dev"+colour+": "+colour+red+jsonres[line][results[line]]["dev"]+colour+")")
                except Exception as error:
                    print(error)
                    traceback.print_exc()
                    #lol
                self.sendChatMessage(self.send, channel, bold+colour+blue+line+colour+bold+": "+colour+purple+jsonres[line][results[line]]["name"]+" "+alias+colour+darkgreen+jsonres[line][results[line]]["version"]+dev+" "+comment+colour+orange+jsonres[line][results[line]]["shorturl"]+colour)
        except Exception as error:
            self.sendChatMessage(self.send, channel, name+": "+str(error))
            traceback.print_exc()
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
        result = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(version)+".json")
        jsonres = simplejson.loads(result, strict = False )
        results = []
        i = -1
        for mod in jsonres:
            i = i + 1
            if str(params[1]).lower() in mod["name"].lower():
                results.append(i)
                continue
            else:
                aliases = mod["aliases"].split(" ")
                for alias in aliases:
                    if params[1].lower() in alias.lower():
                        results.append(i)
                        break
        darkgreen = "03"
        red = "05"
        purple = "06"
        orange = "7"
        blue = "12"
        pink = "13"
        gray = "14"
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
                alias = colour+"("+colour+pink+str(re.sub(" ", colour+', '+colour+pink, jsonres[line]["aliases"]))+colour+") "
            comment = colour
            if jsonres[line]["comment"] != "":
                comment = str(colour+"("+colour+gray+jsonres[line]["comment"]+colour+") ")
            dev = colour
            try:
                if jsonres[line]["dev"] != "":
                    dev = str(colour+" ("+colour+gray+"dev"+colour+": "+colour+red+str(jsonres[line]["dev"])+colour+")")
            except Exception as error:
                print(error)
                traceback.print_exc()
                #lol
            self.sendChatMessage(self.send, channel, colour+purple+jsonres[line]["name"]+" "+alias+colour+darkgreen+str(jsonres[line]["version"])+dev+" "+comment+colour+orange+jsonres[line]["shorturl"]+colour)
    except Exception as error:
        self.sendChatMessage(self.send, channel, name+": "+str(error))
        traceback.print_exc()
def compare(self, name, params, channel, userdata, rank):
    try:
        data = {
            params[1] : {},
            params[2] : {}
        }
        oldData = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(params[1])+".json")
        oldJson = simplejson.loads(oldData, strict = False )

        for modInfo in oldJson:
            modName = modInfo["name"].lower()
            data[params[1]][modName] = modInfo
        newData = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(params[2])+".json")
        newJson = simplejson.loads(newData, strict = False )

        for modInfo in newJson:
            modName = modInfo["name"].lower()
            data[params[2]][modName] = modInfo
        missingMods = []
        for key in data[params[1]].iterkeys():
            if key not in data[params[2]]:
                missingMods.append(data[params[1]][key]["name"])
        with open("commands/modbot.mca.d3s.co/htdocs/compare/"+params[1]+"..."+params[2]+".json", "w") as f:
            f.write(simplejson.dumps(missingMods, sort_keys=True, indent=4 * ' '))
        self.sendChatMessage(self.send, channel, str(len(missingMods))+" mods died trying to update to "+params[2])
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
    "multilist": multilist,
    "about": about,
    "help" : help,
    "setlist" : setlist,
    "compare" : compare
}
help = {
    "list" : ["=nem list <search> <version>", "Searchs the NotEnoughMods database for <search> and returns all results to IRC"],
    "about": ["=nem about", "Shows some info about this plugin."],
    "help" : ["=nem help [command]", "Shows this help info about [command] or lists all commands for this plugin."],
    "setlist" : ["=nem setlist <version>", "Sets the default version to <version> for the other commands."],
    "multilist" : ["=nem multilist <modName or alias>", "Searchs the NotEnoughMods database for a version per MC version"]
}
