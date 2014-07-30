import urllib2
import simplejson
import traceback
import gzip
import logging
import os

from StringIO import StringIO
from string import ascii_letters, digits
from time import time

ID = "nem"
permission = 1

nem_logger = logging.getLogger("NEM_Tools")

## Colour Constants for List and Multilist command
COLOURPREFIX = unichr(3)
COLOUREND = COLOURPREFIX
BOLD = unichr(2)

DARKGREEN = COLOURPREFIX+"03"
RED = COLOURPREFIX+"05"
PURPLE = COLOURPREFIX+"06"
ORANGE = COLOURPREFIX+"07"
BLUE = COLOURPREFIX+"12"
PINK = COLOURPREFIX+"13"
GRAY = COLOURPREFIX+"14"
LIGHTGRAY = COLOURPREFIX+"15"

ALLOWED_IN_FILENAME = "-_.() %s%s" % (ascii_letters, digits)

            
## Colour Constants End

class NotEnoughClasses():
    def getLatestVersion(self):
        try:
            result = self.fetch_page("http://bot.notenoughmods.com/?json")
            return simplejson.loads(result, strict = False)
        except:
            print("Failed to get NEM versions, falling back to hard-coded")
            nem_logger.exception("Failed to get NEM versions, falling back to hard-coded.")
            #traceb = str(traceback.format_exc())
            #print(traceb)
            return ["1.4.5","1.4.6-1.4.7","1.5.1","1.5.2","1.6.1","1.6.2", "1.6.4", 
                    "1.7.2", "1.7.4", "1.7.5", "1.7.7", "1.7.9", "1.7.10"]

    def __init__(self):
        self.useragent = urllib2.build_opener()
        self.useragent.addheaders = [
            ('User-agent', 'NotEnoughMods:Tools/1.X (+http://github.com/SinZ163/NotEnoughMods)'),
            ('Accept-encoding', 'gzip')
        ]
        
        self.cacheDir = os.path.join("commands", "NEM", "cache")
        self.cache_FileLastUpdated = {}
        self.cache_period = 24 * 60 * 60 # once per day
        

        self.versions = self.getLatestVersion()
        self.version = self.versions[len(self.versions)-1]
    
    def normalize_filename(self, name):
        return ''.join(c for c in name if c in ALLOWED_IN_FILENAME)
        
    def fetch_page(self, url, decompress=True, timeout=10, cache = False):
        
        try:
            fname = self.normalize_filename(url)
            filepath = os.path.join(self.cacheDir, fname)
            
            if cache == True:
                if fname in self.cache_FileLastUpdated:
                    lastUpdated = self.cache_FileLastUpdated[fname]
                    
                    if time() - lastUpdated > self.cache_period:
                        pass
                    else:
                        #print "Loading from cache,",filepath
                        with open(filepath, "r") as f:
                            return f.read()
                else:
                    if os.path.exists(filepath):
                        #print "Loading from cache,",filepath
                        self.cache_FileLastUpdated[fname] = time()
                        
                        with open(filepath, "r") as f:
                            return f.read()
            
            response = self.useragent.open(url, timeout=timeout)
            if response.info().get('Content-Encoding') == 'gzip' and decompress:
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf, mode='rb')
                data = f.read()
            else:
                data = response.read()
            
            if cache == True:
                #print "Writing to cache,",filepath
                with open(filepath, "w") as f:
                    f.write(data)
                self.cache_FileLastUpdated[fname] = time()
            
            return data
        except:
            traceback.print_exc()
            pass
            #most likely a timeout

NEM = NotEnoughClasses()

def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        command(self, name, params, channel, userdata, rank)
    except:
        self.sendMessage(channel, "Invalid sub-command!")
        self.sendMessage(channel, "See \"=nem help\" for help")

def setlist(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        self.sendMessage(channel, 
                         "{name}: Insufficient amount of parameters provided.".format(name = name)
                         )
        self.sendMessage(channel, 
                         "{name}: {setlistHelp}".format(name = name,
                                                        setlistHelp = help["setlist"][0])
                         )
    else:
        NEM.version = str(params[1])
        self.sendMessage(channel, 
                         "switched list to: "
                         "{bold}{blue}{version}{colourEnd}".format(bold = BOLD,
                                                                   blue = BLUE,
                                                                   version = params[1],
                                                                   colourEnd = COLOUREND)
                         )

def multilist(self,name,params,channel,userdata,rank):
    if len(params) != 2:
        self.sendMessage(channel, 
                         "{name}: Insufficient amount of parameters provided.".format(name = name))
        self.sendMessage(channel, 
                         "{name}: {multilistHelp}".format(name = name,
                                                          multilistHelp = help["multilist"][0])
                         )
    else:
        try:
            jsonres = {}
            results = {}
            
            modName = params[1]
            
            for version in NEM.versions:
                result = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(version)+".json", cache = True)
                jsonres[version] = simplejson.loads(result, strict = False )
                
                for i, mod in enumerate(jsonres[version]):
                    if modName.lower() == mod["name"].lower():
                        results[version] = i
                        break
                    else:
                        aliases = [mod_alias.lower() for mod_alias in mod["aliases"] ]
                        if modName.lower() in aliases:
                            results[version] = i
            
            count = len(results)
            
            if count == 0:
                self.sendMessage(channel, name+ ": mod not present in NEM.")
                return
            elif count == 1:
                count = str(count)+" MC version"
            else:
                count = str(count)+" MC versions"
                
            self.sendMessage(channel, "Listing "+count+" for \""+params[1]+"\":")
            
            for version in sorted(results.iterkeys()):
                alias = ""
                modData = jsonres[version][results[version]]
                
                if modData["aliases"]:
                    alias_joinText= "{colourEnd}, {colour}".format(colourEnd = COLOUREND,
                                                               colour = PINK)
                    alias_text = alias_joinText.join(modData["aliases"])
                    
                    alias = "({colour}{text}{colourEnd}) ".format(colourEnd = COLOUREND, 
                                                                  colour = PINK,
                                                                  text = alias_text)
                
                comment = ""
                if modData["comment"] != "":
                    comment = "({colour}{text}{colourEnd}) ".format(colourEnd = COLOUREND, 
                                                                colour = GRAY,
                                                                text = modData["comment"])
                
                dev = ""
                try:
                    if modData["dev"] != "":
                        dev = ("({colour}dev{colourEnd}): "
                               "{colour2}{version}{colourEnd})".format(colourEnd = COLOUREND, 
                                                                   colour = GRAY,
                                                                   colour2 = RED,
                                                                   version = modData["dev"])
                                )
                                
                except Exception as error:
                    print(error)
                    traceback.print_exc()
                    
                self.sendMessage(channel, 
                                 "{bold}{blue}{mcversion}{colourEnd}{bold}: "
                                 "{purple}{name}{colourEnd} {aliasString}"
                                 "{darkgreen}{version}{colourEnd} {devString}"
                                 "{comment}{orange}{shorturl}{colourEnd}".format(name = modData["name"],
                                                                             aliasString = alias,
                                                                             devString = dev,
                                                                             comment = comment,
                                                                             version = modData["version"],
                                                                             shorturl = modData["shorturl"],
                                                                             mcversion = version,
                                                                             
                                                                             bold = BOLD,
                                                                             blue = BLUE,
                                                                             purple = PURPLE,
                                                                             darkgreen = DARKGREEN,
                                                                             orange = ORANGE,
                                                                             colourEnd = COLOUREND)
                             )
                
        except Exception as error:
            self.sendMessage(channel, name+": "+str(error))
            traceback.print_exc()

def list(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        self.sendMessage(channel, 
                         "{name}: Insufficient amount of parameters provided.".format(name = name))
        self.sendMessage(channel, 
                         "{name}: {helpEntry}".format(name = name,
                                                      helpEntry = help["list"][0])
                         )
        return
    if len(params) >= 3:
        version = params[2]
    else:
        version = NEM.version
    try:
        result = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(version)+".json", cache = True)
        if not result:
            self.sendMessage(channel, 
                             "{0}: Could not fetch the list. Are you sure it exists?".format(name)
                             )
            return
        jsonres = simplejson.loads(result, strict = False )
        results = []
        i = -1
        for mod in jsonres:
            i = i + 1
            if str(params[1]).lower() in mod["name"].lower():
                results.append(i)
                continue
            else:
                aliases = mod["aliases"]
                for alias in aliases:
                    if params[1].lower() in alias.lower():
                        results.append(i)
                        break
        
        count = len(results)
        
        if count == 0:
            self.sendMessage(channel, name+ ": no results found.")
            return
        elif count == 1:
            count = str(count)+" result"
        else:
            count = str(count)+" results"
            
        self.sendMessage(channel, 
                        "Listing {count} for \"{term}\" in "
                        "{bold}{colour}{version}"
                        "{colourEnd}{bold}".format(count = count,
                                                   term = params[1],
                                                   version = version,
                                                   bold = BOLD,
                                                   colourEnd = COLOUREND,
                                                   colour = BLUE)
                         )
        
        for line in results:
            alias = COLOURPREFIX
            if jsonres[line]["aliases"]:
                alias_joinText= "{colourEnd}, {colour}".format(colourEnd = COLOUREND,
                                                               colour = PINK)
                alias_text = alias_joinText.join(jsonres[line]["aliases"])
                
                alias = "({colour}{text}{colourEnd}) ".format(colourEnd = COLOUREND, 
                                                              colour = PINK,
                                                              text = alias_text)
            comment = ""
            if jsonres[line]["comment"] != "":
                comment = "({colour}{text}{colourEnd}) ".format(colourEnd = COLOUREND, 
                                                                colour = GRAY,
                                                                text = jsonres[line]["comment"])
            dev = ""
            try:
                if jsonres[line]["dev"] != "":
                    dev = ("({colour}dev{colourEnd}): "
                           "{colour2}{version}{colourEnd})".format(colourEnd = COLOUREND, 
                                                                   colour = GRAY,
                                                                   colour2 = RED,
                                                                   version = jsonres[line]["dev"])
                           )
            except Exception as error:
                print(error)
                traceback.print_exc()
                
            self.sendMessage(channel, 
                             "{purple}{name}{colourEnd} {aliasString}"
                             "{darkgreen}{version}{colourEnd} {devString}"
                             "{comment}{orange}{shorturl}{colourEnd}".format(name = jsonres[line]["name"],
                                                                             aliasString = alias,
                                                                             devString = dev,
                                                                             comment = comment,
                                                                             version = jsonres[line]["version"],
                                                                             shorturl = jsonres[line]["shorturl"],
                                                                             
                                                                             purple = PURPLE,
                                                                             darkgreen = DARKGREEN,
                                                                             orange = ORANGE,
                                                                             colourEnd = COLOUREND)
                             )
    except Exception as error:
        self.sendMessage(channel, "{0}: {1}".format(name, error) )
        traceback.print_exc()

def compare(self, name, params, channel, userdata, rank):
    try:
        oldVersion, newVersion = params[1], params[2]

        oldData = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(oldVersion)+".json", cache = True)
        oldJson = simplejson.loads(oldData, strict = False )
        
        newData = NEM.fetch_page("http://bot.notenoughmods.com/"+urllib2.quote(newVersion)+".json", cache = True)
        newJson = simplejson.loads(newData, strict = False )
        
        newMods = {modInfo["name"].lower(): True for modInfo in newJson}
        
        missingMods = []
        
        for modInfo in oldJson:
            old_modName = modInfo["name"].lower()
            if old_modName not in newMods:
                missingMods.append(modInfo["name"])
                
        path = "commands/modbot.mca.d3s.co/htdocs/compare/{0}...{1}.json".format(oldVersion, newVersion)
        with open(path, "w") as f:
            f.write(simplejson.dumps(missingMods, sort_keys=True, indent=4 * ' '))
        
        self.sendMessage(channel, 
                         "{0} mods died trying to update to {1}".format(len(missingMods), newVersion)
                         )
        
    except Exception as error:
        self.sendMessage(channel, "{0}: {1}".format(name, error) )
        traceback.print_exc()

def about(self, name, params, channel, userdata, rank):
    self.sendMessage(channel, "Not Enough Mods toolkit for IRC by SinZ & Yoshi2 v4.0")

def help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        self.sendMessage(channel, 
                         "{0}: Available commands: {1}".format(name, 
                                                               ", ".join(help))
                         )
    else:
        command = params[1]
        if command in help:
            for line in help[command]:
                self.sendMessage(channel, name+ ": "+line)
        else:
            self.sendMessage(channel, name+ ": Invalid command provided")

def force_cacheRedownload(self, name, params, channel, userdata, rank):
    if self.rankconvert[rank] >= 3:
        for version in NEM.versions:
            url = "http://bot.notenoughmods.com/"+urllib2.quote(version)+".json"
            normalized = NEM.normalize_filename(url)
            filepath = os.path.join(NEM.cacheDir, normalized)
            if os.path.exists(filepath):
                NEM.cache_FileLastUpdated[normalized] = 0
                
        self.sendMessage(channel, "Cache Timestamps have been reset. Cache will be redownloaded on the next fetching.")

commands = {
    "list" : list,
    "multilist": multilist,
    "about": about,
    "help" : help,
    "setlist" : setlist,
    "compare" : compare,
    "forceredownload" : force_cacheRedownload
}

help = {
    "list" : ["=nem list <search> <version>", 
              "Searches the NotEnoughMods database for <search> and returns all results to IRC."],
    "about": ["=nem about", 
              "Shows some info about the NEM plugin."],
    "help" : ["=nem help [command]", 
              "Shows the help info about [command] or lists all commands for this plugin."],
    "setlist" : ["=nem setlist <version>", 
                 "Sets the default version to be used by other commands to <version>."],
    "multilist" : ["=nem multilist <modName or alias>", 
                   "Searches the NotEnoughMods database for modName or alias in all MC versions."],
    "compare" : ["=nem compare <oldVersion> <newVersion>", 
                 "Compares the NEMP entries for two different MC versions and says how many mods haven't been updated to the new version."]
        }
