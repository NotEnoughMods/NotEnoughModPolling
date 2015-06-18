import logging
import re
import requests
import simplejson
import traceback
import yaml

from distutils.version import LooseVersion

logging.getLogger('requests').setLevel(logging.WARNING)


class InvalidVersion(Exception):

    def __init__(self, version):
        self.version = version

    def __str__(self):
        return 'Invalid version: {!r}'.format(self.version)


class NotEnoughClasses():
    nemVersions = []

    newMods = False
    mods = {}
    SinZationalHax = {}

    invalid_versions = []

    def __init__(self):
        self.requests_session = requests.Session()
        self.requests_session.headers = {
            'User-agent': 'NotEnoughMods:Polling/1.X (+http://github.com/SinZ163/NotEnoughMods)'
        }
        self.requests_session.max_redirects = 5

        self.load_config()
        self.load_version_bans()
        self.buildModDict()
        self.QueryNEM()
        self.InitiateVersions()
        self.buildHTML()

    def fetch_page(self, url, timeout=10, decode_json=False):
        request = self.requests_session.get(url, timeout=timeout)
        if decode_json:
            return request.json()
        else:
            return request.text

    def fetch_json(self, *args, **kwargs):
        return self.fetch_page(*args, decode_json=True, **kwargs)

    def load_config(self):
        try:
            with open('commands/NEMP/config.yml', 'r') as f:
                self.config = yaml.load(f)
        except:
            print('You need to setup the NEMP/config.yml file')
            raise

    def load_version_bans(self):
        try:
            with open('commands/NEMP/bans.yml', 'r') as f:
                self.invalid_versions = yaml.load(f)
        except:
            print('You need to setup the NEMP/bans.yml file')
            raise

        # compile regexes for performance
        for i, regex in enumerate(self.invalid_versions[:]):
            self.invalid_versions[i] = re.compile(regex, re.I)

    def buildModDict(self):
        with open("commands/NEMP/mods.json", "rb") as modList:
            self.mods = simplejson.load(modList)

        for mod in self.mods:
            if "change" not in self.mods[mod]:
                self.mods[mod]["change"] = "NOT_USED"
            if "SinZationalHax" in self.mods[mod]:
                if self.mods[mod]["SinZationalHax"]["id"] in self.SinZationalHax:
                    self.SinZationalHax[self.mods[mod]["SinZationalHax"]["id"]].append(mod)
                else:
                    self.SinZationalHax[self.mods[mod]["SinZationalHax"]["id"]] = [mod]

    def buildHTML(self):
        headerText = ""
        with open("commands/NEMP/header.txt", "r") as f:
            headerText = f.read()
        footerText = ""
        with open("commands/NEMP/footer.txt", "r") as f:
            footerText = f.read()
        with open("commands/NEMP/htdocs/index.html", "w") as f:
            f.write(re.sub("~MOD_COUNT~", str(len(self.mods)), headerText))
            for modName, info in sorted(self.mods.iteritems()):  # TODO: make this not terrible
                if info["active"]:
                    isDisabled = "active"
                else:
                    isDisabled = "disabled"
                f.write("""
        <tr class='{}'>
            <td class='name'>{}</td>""".format(isDisabled, modName))
                f.write("""
            <td class='function'>{}</td>
            <td class='mc_version'>{}</td>
""".format(info["function"], info["mc"]))
                try:
                    f.write("            <td class='category'>{}</td>\r\n".format(info["category"]))
                except:
                    pass
                f.write("        </tr>\r\n")
            f.write(footerText)

    def QueryNEM(self):
        self.nemVersions = reversed(self.fetch_json("http://bot.notenoughmods.com/?json"))

    def InitiateVersions(self):
        # Store a list of mods so we dont override our version
        templist = self.mods.keys()
        try:
            # for MC version in NEM's list
            for version in self.nemVersions:
                # Get the NEM List for this MC Version
                jsonres = self.fetch_json("http://bot.notenoughmods.com/" + version + ".json")

                # For each NEM Mod...
                for mod in jsonres:
                    # Is it in our list?
                    if mod["name"] in templist:
                        # Its in our list, lets store this info
                        self.mods[mod["name"]]["mc"] = version

                        # Does this NEM Mod have a dev version
                        if "dev" in mod and mod["dev"]:
                            # It does
                            self.mods[mod["name"]]["dev"] = str(mod["dev"])
                        else:
                            # It doesn't
                            self.mods[mod["name"]]["dev"] = "NOT_USED"

                        # Does this NEM Mod have a version (not required, but yay redundancy)
                        if "version" in mod and mod["version"]:
                            # What a suprise, it did...
                            self.mods[mod["name"]]["version"] = str(mod["version"])
                        else:
                            # What the actual fuck, how did this happen
                            self.mods[mod["name"]]["version"] = "NOT_USED"

                        # We have had our way with this mod, throw it away
                        templist.remove(mod["name"])

                # ok, so it wasn't directly on the list, is it indirectly on the list though.
                for lonelyMod in templist[:]:
                    # Is this mod a PykerHack(tm)
                    if "name" in self.mods[lonelyMod]:
                        # ok, this is a PykerHack(tm) mod, lets loop through NEM again to find it
                        for lonelyTestMod in jsonres:
                            # Is it here?
                            if self.mods[lonelyMod]["name"] == lonelyTestMod["name"]:
                                 # ok, does it exist for this MC version.
                                self.mods[lonelyMod]["mc"] = version

                                # Does it have a dev version
                                if "dev" in lonelyTestMod and lonelyTestMod["dev"]:
                                    # It did
                                    self.mods[lonelyMod]["dev"] = str(lonelyTestMod["dev"])
                                else:
                                    # It didn't
                                    self.mods[lonelyMod]["dev"] = "NOT_USED"
                                # #Redundancy
                                if "version" in lonelyTestMod and lonelyTestMod["version"]:
                                    # yay
                                    self.mods[lonelyMod]["version"] = str(lonelyTestMod["version"])
                                else:
                                    # wat
                                    self.mods[lonelyMod]["version"] = "NOT_USED"
                                # gtfo LonelyMod, noone likes you anymore
                                templist.remove(lonelyMod)
        except:
            pass
            # most likely a timeout

    def CheckJenkins(self, mod):
        jsonres = self.fetch_json(self.mods[mod]["jenkins"]["url"])
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = re.search(self.mods[mod]["jenkins"]["regex"], filename)
        output = match.groupdict()
        try:
            output["change"] = jsonres["changeSet"]["items"][0]["msg"]
        except:
            pass
        return output

    def CheckMCForge2(self, mod):
        jsonres = self.fetch_json(self.mods[mod]["mcforge"]["url"])

        for promo in jsonres["promos"]:
            if promo == self.mods[mod]["mcforge"]["promo"]:
                return {
                    self.mods[mod]["mcforge"]["promoType"]: jsonres["promos"][promo]["version"],
                    "mc": jsonres["promos"][promo]["mcversion"]
                }
        return {}

    def CheckMCForge(self, mod):
        jsonres = self.fetch_json("http://files.minecraftforge.net/" + self.mods[mod]["mcforge"]["name"] + "/json")
        promotionArray = jsonres["promotions"]
        devMatch = ""
        recMatch = ""
        for promotion in promotionArray:
            if promotion["name"] == self.mods[mod]["mcforge"]["dev"]:
                for entry in promotion["files"]:
                    if entry["type"] == "universal":
                        info = entry["url"]
                        devMatch = re.search(self.mods[mod]["mcforge"]["regex"], info)
            elif promotion["name"] == self.mods[mod]["mcforge"]["rec"]:
                for entry in promotion["files"]:
                    if entry["type"] == "universal":
                        info = entry["url"]
                        recMatch = re.search(self.mods[mod]["mcforge"]["regex"], info)
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

    def CheckChickenBones(self, mod):
        result = self.fetch_page("http://www.chickenbones.net/Files/notification/version.php?version=" + self.mods[mod]["mc"] + "&file=" + mod)
        if result.startswith("Ret: "):  # Hacky I know, but this is how ChickenBones does it in his mod
            new_version = result[5:]
            if self.mods[mod]['version'] == 'dev-only' or LooseVersion(new_version) > LooseVersion(self.mods[mod]['version']):
                return {
                    "version": new_version
                }
            else:
                return {}

    def CheckmDiyo(self, mod):
        result = self.fetch_page("http://tanis.sunstrike.io/" + self.mods[mod]["mDiyo"]["location"])
        lines = result.split()
        result = ""
        for line in lines:
            if ".jar" in line.lower():
                result = line
        match = re.search(self.mods[mod]["mDiyo"]["regex"], result)
        output = match.groupdict()
        return output

    def CheckAE(self, mod):
        jsonres = self.fetch_json("http://ae-mod.info/releases")
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
            "version": relVersion,
            "dev": devVersion,
            "mc": devMC  # TODO: this doesn't seem reliable...
        }

    def CheckAE2(self, mod):
        jsonres = self.fetch_json("http://feeds.ae-mod.info/builds.json")
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

    def CheckDropBox(self, mod):
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

    def CheckHTML(self, mod):
        result = self.fetch_page(self.mods[mod]["html"]["url"])
        output = {}
        for line in result.splitlines():
            match = re.search(self.mods[mod]["html"]["regex"], line)
            if match:
                output = match.groupdict()
        return output

    def CheckSpacechase(self, mod):
        jsonres = self.fetch_json("http://spacechase0.com/core/latest.php?obj=mods/minecraft/" + self.mods[mod]["spacechase"]["slug"] + "&platform=" + self.mods[mod]["mc"])
        output = {
            "version": jsonres["version"],
            "change": jsonres["summary"]
        }
        return output

    def CheckLunatrius(self, mod):
        jsonres = self.fetch_json("http://mc.lunatri.us/json?latest&mod=" + mod + "&v=2")
        info = jsonres["mods"][mod]["latest"]
        output = {
            "version": info["version"],
            "mc": info["mc"]
        }
        if len(info['changes']) > 0:
            output["change"] = info['changes'][0]
        return output

    def CheckBigReactors(self, mod):
        info = self.fetch_json("http://big-reactors.com/version.json")

        ret = {
            'mc': info['mcVersion']
        }

        if info['stable']:
            ret['version'] = info['version']
        else:
            ret['dev'] = info['version']

        if info['changelog']:
            # send only the first line of the changelog
            ret['change'] = info['changelog'][0]

        return ret

    def CheckCurse(self, mod):
        modid = self.mods[mod]['curse'].get('id')

        # Accounts for discrepancies between NEM mod names and the Curse link format
        # Uses Curse name if there is one specified. Defaults to the mod's name in lowercase.
        modname = self.mods[mod]['curse'].get('name', mod.lower())

        # As IDs only work with newer mods we have to support two versions of the URL
        if modid:
            jsonres = self.fetch_json("http://widget.mcf.li/mc-mods/minecraft/" + modid + "-" + modname + ".json")
        else:
            jsonres = self.fetch_json("http://widget.mcf.li/mc-mods/minecraft/" + modname + ".json")

        release_type = jsonres['release_type'].lower()

        regex = re.compile(self.mods[mod]['curse']['regex'])

        releases = sorted(jsonres['files'].values(), key=lambda x: x['id'], reverse=True)

        release = releases[0]

        match = regex.search(release['name'])

        output = match.groupdict()

        res = {
            'mc': release['version']
        }

        if jsonres["download"]["type"].lower() == release_type:
            res['version'] = output['version']
        else:
            res['dev'] = output['version']

        return res

    def CheckGitHubRelease(self, mod):
        repo = self.mods[mod]['github'].get('repo')

        client_id = self.config.get('github', {}).get('client_id')
        client_secret = self.config.get('github', {}).get('client_secret')

        url = 'https://api.github.com/repos/' + repo + '/releases'

        if client_id and client_secret:
            url += '?client_id={}&client_secret={}'.format(client_id, client_secret)

        releases = self.fetch_json(url)

        type_ = self.mods[mod]['github'].get('type', 'asset')

        if type_ == 'asset':
            regex = re.compile(self.mods[mod]['github']['regex'])

            for release in releases:
                for asset in release['assets']:
                    match = regex.search(asset['name'])
                    if match:
                        result = match.groupdict()
                        if release['prerelease']:
                            result['dev'] = result['version']
                            del result['version']
                        return result
        elif type_ == 'tag':
            release = releases[0]
            if release['prerelease']:
                return {'dev': release['tag_name']}
            else:
                return {'version': release['tag_name']}
        else:
            raise ValueError('Invalid type {!r} for CheckGitHubRelease parser'.format(type_))

    def CheckBuildCraft(self, mod):
        page = self.fetch_page('https://raw.githubusercontent.com/BuildCraft/BuildCraft/master/buildcraft_resources/versions.txt')

        # filter empty lines
        lines = [line for line in page.splitlines() if line]

        mc, mod_name, version = lines[-1].split(':')

        return {
            'mc': mc,
            'version': version
        }

    def Check4Space(self, mod):
        page = self.fetch_page('http://4space.mods.center/version.html')

        parts = page.strip().replace('Version=', '').split('#')

        if len(parts) != 3:
            raise RuntimeError('Invalid amount of version parts')

        new_version = '.'.join(parts)

        if self.mods[mod]['version'] == 'dev-only' or LooseVersion(new_version) > LooseVersion(self.mods[mod]['version']):
            return {
                "version": new_version
            }
        else:
            return {}

    def CheckBotania(self, mod):
        mc = self.mods[mod]['mc']

        online_version = self.fetch_page("https://raw.githubusercontent.com/Vazkii/Botania/master/version/" + mc + ".txt")

        online_build = int(online_version.split('-')[1])

        local_build = int(self.mods[mod]['version'].split('-')[1])

        if online_build > local_build:
            return {
                'version': online_version,
                'mc': mc
            }
        else:
            return {}

    def CheckMekanism(self, mod):
        # mostly a straight port from http://git.io/vL8tB

        result = self.fetch_page('https://dl.dropbox.com/u/90411166/Mod%20Versions/Mekanism.txt').split(':')

        if len(result) > 1 and 'UTF-8' not in result and 'HTML' not in result and 'http' not in result:
            remote_version = result[0]
            local_version = self.mods[mod]['version']

            if local_version == 'dev-only' or LooseVersion(remote_version) > LooseVersion(local_version):
                return {
                    'version': result[0],
                    'change': result[1]
                }
            else:
                return {}

    def CheckAtomicStryker(self, mod, document):
        if not document:
            return self.fetch_page("http://atomicstryker.net/updatemanager/modversions.txt")

        lines = document.splitlines()
        mcver = []
        version = []

        for line in lines:
            if "mcversion" in line:
                # We have a new MC Version
                mcMatch = re.search("mcversion = Minecraft (.+?)$", line)
                mcver.append(mcMatch.group(1))
            elif self.mods[mod]["AtomicStryker"]["name"] in line:
                verMatch = re.search(self.mods[mod]["AtomicStryker"]["name"] + " = (.+?)$", line)
                version.append(verMatch.group(1))

        if len(mcver) != 0 and len(version) != 0:
            return {
                # len(version)-1 is used for the last entry to version, and the corresponding MC version (as all of his mods so far are for all MC versions (except 1.8 somewhat)
                "mc": mcver[len(version) - 1],
                "version": version[len(version) - 1]
            }

        return {}

    def is_version_valid(self, version):
        for regex in self.invalid_versions:
            if regex.search(version):
                return False
        return True

    def CheckMod(self, mod, document=None):
        try:
            # [dev change, version change]
            status = [False, False]

            if document:
                output = getattr(self, self.mods[mod]["function"])(mod, document)
            else:
                output = getattr(self, self.mods[mod]["function"])(mod)

            if "dev" in output:
                # Remove whitespace at the end and start
                self.mods[mod]["dev"] = self.mods[mod]["dev"].strip()
                output["dev"] = output["dev"].strip()

                # validate version
                if not self.is_version_valid(output['dev']):
                    raise InvalidVersion(output['dev'])

                if '_replace' in self.mods[mod]:
                    for k, v in self.mods[mod]['_replace'].iteritems():
                        output['dev'] = output['dev'].replace(k, v)

                if self.mods[mod]["dev"] != output["dev"]:
                    self.mods[mod]["dev"] = output["dev"]
                    status[0] = True

            if "version" in output:
                # Remove whitespace at the end and start
                self.mods[mod]["version"] = self.mods[mod]["version"].strip()
                output["version"] = output["version"].strip()

                # validate version
                if not self.is_version_valid(output['version']):
                    raise InvalidVersion(output['version'])

                if '_replace' in self.mods[mod]:
                    for k, v in self.mods[mod]['_replace'].iteritems():
                        output['version'] = output['version'].replace(k, v)

                if self.mods[mod]["version"] != output["version"]:
                    self.mods[mod]["version"] = output["version"]
                    status[1] = True

            if "mc" in output:
                self.mods[mod]["mc"] = output["mc"]

            if "change" in output and "changelog" not in self.mods[mod]:
                self.mods[mod]["change"] = output["change"]

            return status, False  # Everything went fine, no exception raised
        except:
            print(mod + " failed to be polled...")
            traceback.print_exc()
            return [False, False], True  # an exception was raised, so we return a True

    def CheckMods(self, mod):
        output = {}

        try:
            # We need to know what mods this SinZationalHax uses
            mods = self.SinZationalHax[self.mods[mod]["SinZationalHax"]["id"]]
            # Lets get the page/json/whatever all the mods want
            document = getattr(self, self.mods[mod]["function"])(mod, None)
            # Ok, time to parse it for each mod
            for tempMod in mods:
                output[tempMod] = self.CheckMod(tempMod, document)
        except:
            print(mod + " failed to be polled (SinZationalHax)")
            traceback.print_exc()
            if 'tempMod' in locals():
                output[tempMod] = ([False, False], True)

        return output
