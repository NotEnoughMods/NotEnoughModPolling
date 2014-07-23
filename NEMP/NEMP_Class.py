import urllib2
import simplejson
import re
import traceback
import gzip

from distutils.version import LooseVersion
from StringIO import StringIO


class NotEnoughClasses():
    nemVersions = []
    nemVersion = ""

    newMods = False
    mods = {}

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
                                self.mods[mod["name"]]["dev"] = str(mod["dev"])
                            else:
                                self.mods[mod["name"]]["dev"] = "NOT_USED"

                            if "version" in mod and mod["version"]:
                                self.mods[mod["name"]]["version"] = str(mod["version"])
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
            pass
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
        result = self.fetch_page("http://www.chickenbones.net/Files/notification/version.php?version="+self.mods[mod]["mc"]+"&file="+mod)
        if result.startswith("Ret: "): #Hacky I know, but this is how ChickenBones does it in his mod
            new_version = result[5:]
            if LooseVersion(new_version) > LooseVersion(self.mods[mod]['version']):
                return {
                    "version" : new_version
                }
            else:
                return {}

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

    def CheckAE2(self,mod):
        result = self.fetch_page("http://ae2.ae-mod.info/builds/builds.json")
        jsonres = simplejson.loads(result, strict = False )
        jsonres = sorted(jsonres['Versions'], key=lambda k: k['Created'], reverse=True)
        relVersion = ""
        MCversion = ""
        devVersion = ""
        if jsonres[0]["Channel"] == "stable":
            relVersion = jsonres[0]["Version"]
            MCversion = jsonres[0]["VersionMC"]
        else:
            devVersion = jsonres[0]["Version"]
            MCversion = jsonres[0]["VersionMC"]
        if relVersion:
            return {
                "version": relVersion,
                "mc": MCversion
            }
        if devVersion:
            return {
                "dev": devVersion,
                "mc": MCversion
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
        result = self.fetch_page("http://spacechase0.com/wp-content/plugins/mc-mod-manager/nem.php?mc="+self.mods[mod]["mc"][2:])
        for line in result.splitlines():
            info = line.split(',')
            #0 = ID, 1=NEM ID, 2=ModID, 3=Author, 4=Link, 5=Version, 6=Comment
            if info[1] == mod:
                return {
                    "version" : info[5]
                }
        return {}

    def CheckLunatrius(self,mod):
        result = self.fetch_page("http://mc.lunatri.us/json?latest&mod="+mod+"&v=2")
        jsonres = simplejson.loads(result, strict = False )
        info = jsonres["mods"][mod]["latest"]
        output = {
            "version" : info["version"],
            "mc" : info["mc"]
        }
        if len(info['changes']) > 0:
            output["change"] = info['changes'][0]
        return output

    def CheckBigReactors(self,mod):
        result = self.fetch_page("http://big-reactors.com/version.json")
        info = simplejson.loads(result, strict = False)
        return {
            "version" : info["version"],
            "mc" : info["version-minecraft"]
        }

    def CheckMod(self, mod):
        try:
            # [dev change, version change]
            status = [False, False]
            output = getattr(self, self.mods[mod]["function"])(mod)
            if "dev" in output:
                # Remove whitespace at the end and start
                self.mods[mod]["dev"] = self.mods[mod]["dev"].strip()
                output["dev"] = output["dev"].strip()
                if self.mods[mod]["dev"] != output["dev"]:
                    self.mods[mod]["dev"] = output["dev"]
                    status[0] = True
            if "version" in output:
                # Remove whitespace at the end and start
                self.mods[mod]["version"] = self.mods[mod]["version"].strip()
                output["version"] = output["version"].strip()
                if self.mods[mod]["version"] != output["version"]:
                    self.mods[mod]["version"] = output["version"]
                    status[1] = True
            if "mc" in output:
                self.mods[mod]["mc"] = output["mc"]
            if "change" in output and "changelog" not in self.mods[mod]:
                self.mods[mod]["change"] = output["change"]
            return status, False # Everything went fine, no exception raised
        except:
            print(mod+" failed to be polled...")
            traceback.print_exc()
            return [False, False], True # an exception was raised, so we return a True
