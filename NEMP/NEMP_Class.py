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
            'User-agent': 'NotEnoughMods:Polling/1.X (+https://github.com/NotEnoughMods/NotEnoughModPolling)'
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

        request.raise_for_status()

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

    def _find_regex(self, data):
        """
        Internal-use recursive function to find the regex for a mod's polling
        information data dict.
        The mod's data is passed as an argument so it can be re-used for other
        things which rely on a unique 'regex' key.
        """
        if isinstance(data, dict):
            if 'regex' in data:
                return data['regex']
            else:
                for k, v in data.iteritems():
                    ret = self._find_regex(v)
                    if ret:
                        return ret
        else:
            # ignore other types
            return

    def compile_regex(self, mod):
        regex = self._find_regex(self.mods[mod])

        if regex:
            self.mods[mod]['_regex'] = re.compile(regex, re.I)

    def get_mod_regex(self, mod):
        return self.mods[mod].get('_regex')

    def match_mod_regex(self, mod, data):
        return self.mods[mod]['_regex'].search(data)

    def buildModDict(self):
        with open("commands/NEMP/mods.json", "rb") as modList:
            self.mods = simplejson.load(modList)

        for mod in self.mods:
            self.compile_regex(mod)

            self.mods[mod]['nem_versions'] = {}

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
        self.nemVersions = self.fetch_json("http://bot.notenoughmods.com/?json")

    def InitiateVersions(self):
        # Store a list of mods so we dont override our version
        templist = self.mods.keys()

        # for MC version in NEM's list
        for nem_list_name in self.nemVersions:
            # Get the NEM List for this MC Version
            nem_list = self.fetch_json("http://bot.notenoughmods.com/" + nem_list_name + ".json")

            # For each NEM Mod...
            for nem_mod in nem_list:
                nem_mod_name = nem_mod['name']

                # Is it in our list?
                if nem_mod_name in templist:
                    # Store latest MC version (since the NEM lists are sorted from oldest to newest)
                    self.mods[nem_mod_name]["mc"] = nem_list_name

                    # Grab the dev and release version
                    self.mods[nem_mod_name]['nem_versions'][nem_list_name] = {
                        'dev': nem_mod.get('dev', ''),
                        'version': nem_mod.get('version', '')
                    }

            # ok, so it wasn't directly on the list, is it indirectly on the list though.
            for lonelyMod in templist[:]:
                # Is this mod a PykerHack(tm)
                if "name" in self.mods[lonelyMod]:
                    # ok, this is a PykerHack(tm) mod, lets loop through NEM again to find it
                    for nem_mod in nem_list:
                        # Is it here?
                        if self.mods[lonelyMod]["name"] == nem_mod["name"]:
                            # Store latest MC version (since the NEM lists are sorted from oldest to newest)
                            self.mods[lonelyMod]["mc"] = nem_list_name

                            # Grab the dev and release version
                            self.mods[lonelyMod]['nem_versions'][nem_list_name] = {
                                'dev': nem_mod.get('dev', ''),
                                'version': nem_mod.get('version', '')
                            }

    def CheckJenkins(self, mod):
        jsonres = self.fetch_json(self.mods[mod]["jenkins"]["url"] + '?tree=changeSet[items[msg]],artifacts[fileName]')
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = self.match_mod_regex(mod, filename)
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
                        devMatch = self.match_mod_regex(mod, info)
            elif promotion["name"] == self.mods[mod]["mcforge"]["rec"]:
                for entry in promotion["files"]:
                    if entry["type"] == "universal":
                        info = entry["url"]
                        recMatch = self.match_mod_regex(mod, info)
        if devMatch:
            output = {}
            tmpMC = "null"
            if recMatch:
                output["version"] = recMatch.group(2)
                tmpMC = recMatch.group(1)
            if devMatch.group(1) != tmpMC:
                output["mc"] = devMatch.group(1)
            else:
                output["mc"] = tmpMC
            output["dev"] = devMatch.group(2)
            return output

    def CheckForgeJson(self, mod):
        jsonres = self.fetch_json(self.mods[mod]["forgejson"]["url"])

        if "promos" not in jsonres:
            return {}

        mc_version = self.mods[mod]["forgejson"]["mcversion"]
        promo = mc_version + "-recommended"
        dev_promo = mc_version + "-latest"

        if promo not in jsonres["promos"] and dev_promo not in jsonres["promos"]:
            return {}

        output = {"mc": mc_version}
        if promo in jsonres["promos"]:
            if dev_promo in jsonres["promos"] and jsonres["promos"][promo] != jsonres["promos"][dev_promo]:
                output["dev"] = jsonres["promos"][dev_promo]
            else:
                output["version"] = jsonres["promos"][promo]
        else:
            output["dev"] = jsonres["promos"][dev_promo]

        try:
            if "version" in output:
                version = output["version"]
            else:
                version = output["dev"]

            if jsonres[mc_version][version]:
                output["change"] = jsonres[mc_version][version]
        except:
            pass
        return output

    def CheckChickenBones(self, mod):
        mc_version = self.mods[mod]['mc']
        local_version = self.get_nem_version(mod, mc_version)

        result = self.fetch_page("http://www.chickenbones.net/Files/notification/version.php?version=" + mc_version + "&file=" + mod)
        if result.startswith("Ret: "):  # Hacky I know, but this is how ChickenBones does it in his mod
            new_version = result[5:].strip()
            if local_version == 'dev-only' or LooseVersion(new_version) > LooseVersion(local_version):
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
        match = self.match_mod_regex(mod, result)
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

        # TODO: Why do we use an iter? Do we need that? Make it better.
        for match in self.mods[mod]['_regex'].finditer(result):
            pass
        # "match" is still in this scope
        # TODO: This seems extremely unpythonic
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
        # TODO: Maybe change this to work like the Dropbox one
        for line in result.splitlines():
            match = self.match_mod_regex(mod, line)

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

        if jsonres.get('code') == '200' and jsonres.get('error') == 'No Files Found':
            return {}

        release_type = jsonres['release_type'].lower()

        releases = sorted(jsonres['files'].values(), key=lambda x: x['id'], reverse=True)

        release = releases[0]

        match = self.match_mod_regex(mod, release['name'])

        output = match.groupdict()

        res = {
            'mc': release['version']
        }

        if release['type'].lower() == release_type:
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
            regex = self.get_mod_regex(mod)

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

            tag_name = release['tag_name']

            if 'regex' in self.mods[mod]['github']:
                result = self.match_mod_regex(mod, tag_name).groupdict()

                if release['prerelease']:
                    result['dev'] = result['version']
                    del result['version']

                return result
            else:
                if release['prerelease']:
                    return {'dev': tag_name}
                else:
                    return {'version': tag_name}
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

        local_version = self.get_nem_version(mod)

        if local_version == 'dev-only' or LooseVersion(new_version) > LooseVersion(local_version):
            return {
                "version": new_version
            }
        else:
            return {}

    def CheckBotania(self, mod):
        mc = self.mods[mod]['mc']

        online_version = self.fetch_page("https://raw.githubusercontent.com/Vazkii/Botania/master/version/" + mc + ".txt")

        online_build = int(online_version.split('-')[1])

        local_build = int(self.get_nem_version(mod, mc).split('-')[1])

        if online_build > local_build:
            return {
                'version': online_version,
                'mc': mc
            }
        else:
            return {}

    def CheckMekanism(self, mod):
        # mostly a straight port from http://git.io/vL8tB

        result = self.fetch_page('https://dl.dropboxusercontent.com/u/90411166/Mod%20Versions/Mekanism.txt').split(':')

        if len(result) > 1 and 'UTF-8' not in result and 'HTML' not in result and 'http' not in result:
            remote_version = result[0]
            local_version = self.get_nem_version(mod)

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
                # TODO: Fix this mess
                verMatch = re.search(self.mods[mod]["AtomicStryker"]["name"] + " = (.+?)$", line)
                version.append(verMatch.group(1))

        if len(mcver) != 0 and len(version) != 0:
            return {
                # len(version)-1 is used for the last entry to version, and the corresponding MC version (as all of his mods so far are for all MC versions (except 1.8 somewhat)
                "mc": mcver[len(version) - 1],
                "version": version[len(version) - 1]
            }

        return {}

    def CheckModsIO(self, mod):
        mod_id = str(self.mods[mod]['modsio']['id'])

        response = self.fetch_json('https://mods.io/mods/' + mod_id + '.json')

        current_version = response['current_version']

        ret = {
            'mc': current_version['minecraft'],
            'version': current_version['name']
        }

        if current_version.get('changelog'):
            ret['change'] = current_version['changelog']

        return ret

    def is_version_valid(self, version):
        for regex in self.invalid_versions:
            if regex.search(version):
                return False
        return True

    # Returns the version string with some replacements, like:
    # - whitespace (space/tab/etc) replaced by hyphen
    def clean_version(self, version):
        version = re.sub(r'\s+', '-', version)
        # remove any extra hyphens
        version = re.sub(r'-+', '-', version)
        return version

    def get_nem_version(self, mod, nem_list=None):
        if nem_list is None:
            nem_list = self.mods[mod]['mc']
        return self.mods[mod]['nem_versions'].get(nem_list, {}).get('version', '')

    def get_nem_dev_version(self, mod, nem_list=None):
        if nem_list is None:
            nem_list = self.mods[mod]['mc']
        return self.mods[mod]['nem_versions'].get(nem_list, {}).get('dev', '')

    def set_nem_version(self, mod, version, nem_list=None):
        if nem_list is None:
            nem_list = self.mods[mod]['mc']
        self.mods[mod]['nem_versions'].setdefault(nem_list, {})['version'] = version

    def set_nem_dev_version(self, mod, version, nem_list=None):
        if nem_list is None:
            nem_list = self.mods[mod]['mc']
        self.mods[mod]['nem_versions'].setdefault(nem_list, {})['dev'] = version

    def get_proper_name(self, mod):
        lower_mod = mod.lower()

        for mod_name in self.mods.iterkeys():
            if lower_mod == mod_name.lower():
                return mod_name

        return None

    def CheckMod(self, mod, document=None):
        try:
            # [mc version, dev change, version change, previous dev, previous release]
            status = [None, False, False, '', '']

            if document:
                output = getattr(self, self.mods[mod]["function"])(mod, document)
            else:
                output = getattr(self, self.mods[mod]["function"])(mod)

            if "mc" in output:
                # Update latest NEM list for this mod
                self.mods[mod]["mc"] = output["mc"]
                mc_version = output['mc']
            else:
                # If no MC version has been specified, use the latest one we
                # have for this mod
                mc_version = None

            status[0] = mc_version

            local_dev = self.get_nem_dev_version(mod, mc_version)

            if "dev" in output:
                # Remove whitespace at the end and start
                remote_dev = self.clean_version(output['dev'].strip())

                # validate version
                if not remote_dev or not self.is_version_valid(remote_dev):
                    raise InvalidVersion(remote_dev)

                if local_dev != remote_dev:
                    self.set_nem_dev_version(mod, remote_dev, mc_version)
                    status[1] = True

            local_release = self.get_nem_version(mod, mc_version)

            if "version" in output:
                # Remove whitespace at the end and start
                remote_release = self.clean_version(output['version'].strip())

                # validate version
                if not remote_release or not self.is_version_valid(remote_release):
                    raise InvalidVersion(remote_release)

                if local_release != remote_release:
                    self.set_nem_version(mod, remote_release, mc_version)
                    status[2] = True

            if "change" in output and "changelog" not in self.mods[mod]:
                self.mods[mod]["change"] = output["change"]

            status[3] = local_dev
            status[4] = local_release

            return status, False  # Everything went fine, no exception raised
        except:
            print(mod + " failed to be polled...")
            traceback.print_exc()
            return [None, False, False, '', ''], True  # an exception was raised, so we return a True

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
            # TODO: Fix this ugly hack
            if 'tempMod' in locals():
                output[tempMod] = ([None, False, False, '', ''], True)

        return output
