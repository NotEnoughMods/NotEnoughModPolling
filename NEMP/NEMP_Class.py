import logging
import re
import requests
import simplejson
import traceback
import yaml

from bs4 import BeautifulSoup

from distutils.version import LooseVersion

logging.getLogger('urllib3').setLevel(logging.WARNING)


class NEMPException(Exception):
    pass


class InvalidVersion(NEMPException):
    def __str__(self):
        return repr(self.message)


class NotEnoughClasses():
    nemVersions = []

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
        self.load_version_blacklist()
        self.load_mc_blacklist()
        self.load_mc_mapping()
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

    def load_version_blacklist(self):
        try:
            with open('commands/NEMP/version_blacklist.yml', 'r') as f:
                self.invalid_versions = yaml.load(f)
        except:
            print('You need to setup the NEMP/version_blacklist.yml file')
            raise

        # compile regexes for performance
        for i, regex in enumerate(self.invalid_versions[:]):
            self.invalid_versions[i] = re.compile(regex, re.I)

    def load_mc_blacklist(self):
        with open('commands/NEMP/mc_blacklist.yml', 'r') as f:
            self.mc_blacklist = yaml.load(f)

    def load_mc_mapping(self):
        with open('commands/NEMP/mc_mapping.yml', 'r') as f:
            self.mc_mapping = yaml.load(f)

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
""".format(info["function"]))
                try:
                    f.write("            <td class='category'>{}</td>\r\n".format(info["category"]))
                except:
                    pass
                f.write("        </tr>\r\n")
            f.write(footerText)

    def QueryNEM(self):
        self.nemVersions = self.fetch_json("https://bot.notenoughmods.com/?json")

    def InitiateVersions(self):
        # Store a list of mods so we dont override our version
        templist = self.mods.keys()

        # for MC version in NEM's list
        for nem_list_name in self.nemVersions:
            if nem_list_name in self.mc_mapping:
                continue

            # Get the NEM List for this MC Version
            nem_list = self.fetch_json("https://bot.notenoughmods.com/" + nem_list_name + ".json")

            # For each NEM Mod...
            for nem_mod in nem_list:
                nem_mod_name = nem_mod['name']

                # Is it in our list?
                if nem_mod_name in templist:
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
                            # Grab the dev and release version
                            self.mods[lonelyMod]['nem_versions'][nem_list_name] = {
                                'dev': nem_mod.get('dev', ''),
                                'version': nem_mod.get('version', '')
                            }

    def CheckJenkins(self, mod, document=None, simulation=False):
        jsonres = self.fetch_json(self.mods[mod]["jenkins"]["url"] + '?tree=changeSet[items[msg]],artifacts[fileName]')
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = self.match_mod_regex(mod, filename)
        output = match.groupdict()
        try:
            output["change"] = jsonres["changeSet"]["items"][0]["msg"]
        except:
            pass
        return output

    def CheckMCForge2(self, mod, document=None, simulation=False):
        jsonres = self.fetch_json(self.mods[mod]["mcforge"]["url"])

        for promo in jsonres["promos"]:
            if promo == self.mods[mod]["mcforge"]["promo"]:
                return {
                    self.mods[mod]["mcforge"]["promoType"]: jsonres["promos"][promo]["version"],
                    "mc": jsonres["promos"][promo]["mcversion"]
                }
        return {}

    def CheckForgeJson(self, mod, document=None, simulation=False):
        jsonres = self.fetch_json(self.mods[mod]["forgejson"]["url"])

        if "promos" not in jsonres:
            return {}

        versions = {}

        for promo, version in jsonres['promos'].iteritems():
            if promo == 'reserved':
                # thanks Hea3veN
                continue

            mc, promo_type = promo.split('-', 1)

            if promo_type == 'latest':
                version_type = 'dev'
            else:
                version_type = 'version'

            versions.setdefault(mc, {})[version_type] = version

        # Finishing touches
        for mc, version_info in versions.iteritems():
            if 'dev' in version_info and 'version' in version_info and version_info['dev'] == version_info['version']:
                del versions[mc]['dev']

        return versions

    def CheckChickenBones(self, mod, document=None, simulation=False):
        if not document:
            p = self.fetch_page('http://chickenbones.net/Pages/links.html')

            d = BeautifulSoup(p, 'html5lib')

            versions = {}

            divs = d.find_all('div', id=re.compile(r'^[0-9.]+_Promotions$'))

            for div in divs:
                mc = div['id'].split('_', 1)[0]

                tables = div.find_all('table')

                latest_table = tables[-1]

                trs = latest_table.find_all('tr')

                for tr in trs[1:]:
                    tds = tr.find_all('td')
                    mod = tds[0].text
                    if mod == "Translocator":
                        mod = "Translocators"
                    version = tds[1].text
                    versions.setdefault(mod, {})[mc] = version

            return versions

        results = {}

        for mc, version in document[mod].iteritems():
            local_version = self.get_nem_version(mod, mc)

            if simulation or not local_version or LooseVersion(version) > LooseVersion(local_version):
                results[mc] = {
                    'version': version
                }

        return results

    def CheckHTML(self, mod, document=None, simulation=False):
        result = self.fetch_page(self.mods[mod]["html"]["url"])
        output = {}
        # TODO: Maybe change this to work like the Dropbox one
        for line in result.splitlines():
            match = self.match_mod_regex(mod, line)

            if match:
                output = match.groupdict()
        return output

    def CheckSpacechase(self, mod, document=None, simulation=False):
        jsonres = self.fetch_json("http://spacechase0.com/core/latest.php?obj=mods/minecraft/" + self.mods[mod]["spacechase"]["slug"])

        version = jsonres['version']

        results = {}

        for mc in jsonres['downloads'].iterkeys():
            results[mc] = {
                'version': version,
                'changelog': jsonres['summary']
            }

        return results

    def CheckLunatrius(self, mod, document=None, simulation=False):
        jsonres = self.fetch_json("http://mc.lunatri.us/json?latest&mod=" + mod + "&v=2")
        info = jsonres["mods"][mod]["latest"]
        output = {
            "version": info["version"],
            "mc": info["mc"]
        }
        if len(info['changes']) > 0:
            output["change"] = info['changes'][0]
        return output

    def CheckBigReactors(self, mod, document=None, simulation=False):
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

    def CheckCurse(self, mod, document=None, simulation=False):
        modid = self.mods[mod]['curse'].get('id')

        # Accounts for discrepancies between NEM mod names and the Curse link format
        # Uses Curse name if there is one specified. Defaults to the mod's name in lowercase.
        modname = self.mods[mod]['curse'].get('name', mod.lower())

        # As IDs only work with newer mods we have to support two versions of the URL
        if modid:
            jsonres = self.fetch_json("https://widget.mcf.li/mc-mods/minecraft/" + modid + "-" + modname + ".json")
        else:
            jsonres = self.fetch_json("https://widget.mcf.li/mc-mods/minecraft/" + modname + ".json")

        if jsonres.get('code') == '200' and jsonres.get('error') == 'No Files Found':
            # This automatically raises an exception and stops this mod from polling after the current cycle
            return None

        release_type = jsonres['release_type'].lower()

        latest_release = sorted(jsonres['files'].values(), key=lambda x: x['id'], reverse=True)[0]

        versions = {}

        for mc_version, releases in jsonres['versions'].iteritems():
            # the releases are ordered from newest to oldest
            release = releases[0]

            match = self.match_mod_regex(mod, release['name'])

            if not match:
                if release['id'] == latest_release['id']:
                    raise NEMPException("Regex is outdated (doesn't match against latest release)")

                # If this release isn't the latest one, we just assume it's an old one and skip it
                continue

            output = match.groupdict()

            res = {}

            if release['type'].lower() == release_type:
                version_type = 'version'
            else:
                version_type = 'dev'

            res[version_type] = output['version']

            versions[mc_version] = res

        return versions

    def CheckGitHubRelease(self, mod, document=None, simulation=False):
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

    def CheckBuildCraft(self, mod, document=None, simulation=False):
        page = self.fetch_page('https://raw.githubusercontent.com/BuildCraft/BuildCraft/master/buildcraft_resources/versions.txt')

        # filter empty lines
        lines = [line for line in page.splitlines() if line]

        mc, mod_name, version = lines[-1].split(':')

        return {
            'mc': mc,
            'version': version
        }

    def CheckBotania(self, mod, document=None, simulation=False):
        page = self.fetch_page('https://raw.githubusercontent.com/Vazkii/Botania/master/web/versions.ini')

        versions = {}

        for line in reversed(page.splitlines()):
            online_version, mc = line.split('=', 1)

            if mc in versions:
                continue

            online_build = int(online_version.split('-', 1)[1])

            local_version = self.get_nem_version(mod, mc)

            if local_version and not simulation:
                local_build = int(local_version.split('-', 1)[1])

                if online_build > local_build:
                    versions[mc] = {
                        'version': online_version
                    }
            else:
                versions[mc] = {
                    'version': online_version
                }

        return versions

    def CheckMekanism(self, mod, document=None, simulation=False):
        # mostly a straight port from https://git.io/v5X7y
        result = self.fetch_page('http://aidancbrady.com/data/versions/Mekanism.txt')

        # adapted sanity check ported from the mod's code
        if 'UTF-8' in result and 'HTML' in result and 'http' in result:
            raise NEMPException('Got an HTML page')

        lines = result.splitlines()

        versions = {}

        for line in lines:
            text = line.split(':', 2)

            mc = text[0]
            remote_version = text[1]

            local_version = self.get_nem_version(mod, mc)

            if simulation or not local_version or LooseVersion(remote_version) > LooseVersion(local_version):
                versions[mc] = {
                    'version': remote_version,
                    'changelog': text[2]
                }

        return versions

    def CheckAtomicStryker(self, mod, document=None, simulation=False):
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

    def CheckModsIO(self, mod, document=None, simulation=False):
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

    # Trims additional ".0" at the end of the version until the
    # version has only 2 groups ("1.0")
    def clean_mc_version(self, version):
        while version.endswith('.0') and version.count('.') > 1:
            version = version[:-2]
        return version

    def get_nem_version(self, mod, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        version = self.mods[mod]['nem_versions'].get(nem_list, {}).get('version', '')

        if version == 'dev-only':
            # dev-only means there's no release version, so we make that transparent to the parsers
            return ''
        else:
            return version

    def get_nem_dev_version(self, mod, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        return self.mods[mod]['nem_versions'].get(nem_list, {}).get('dev', '')

    def set_nem_version(self, mod, version, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        self.mods[mod]['nem_versions'].setdefault(nem_list, {})['version'] = version

    def set_nem_dev_version(self, mod, version, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        self.mods[mod]['nem_versions'].setdefault(nem_list, {})['dev'] = version

    def get_proper_name(self, mod):
        lower_mod = mod.lower()

        for mod_name in self.mods.iterkeys():
            if lower_mod == mod_name.lower():
                return mod_name

        return None

    def CheckMod(self, mod, document=None, simulation=False):
        try:
            output = getattr(self, self.mods[mod]["function"])(mod, document=document, simulation=simulation)

            if output is None:
                raise NEMPException('Parser returned null')

            if isinstance(output, dict) and ('version' in output or 'dev' in output):
                # legacy parser
                if not 'mc' in output:
                    if 'mc' in self.mods[mod]:
                        mc = self.mods[mod]['mc']
                    else:
                        # if it doesn't return a Minecraft version and there's no default, we bail out
                        raise NEMPException('No Minecraft version was returned by the parser')
                else:
                    mc = output['mc']

                # convert to new format
                new_output = {
                    mc: {}
                }

                if 'version' in output:
                    new_output[mc]['version'] = output['version']

                if 'dev' in output:
                    new_output[mc]['dev'] = output['dev']

                if 'change' in output:
                    new_output[mc]['changelog'] = output['change']

                output = new_output

            statuses = []

            for mc, version_info in output.iteritems():
                # [mc version, dev version, release version, changelog]
                status = [None, '', '', None]

                mc = self.clean_mc_version(mc)

                if mc in self.mc_mapping:
                    mc = self.mc_mapping[mc]

                if mc in self.mc_blacklist:
                    print 'Skipping blacklisted MC version {} for {}, version_info={!r}'.format(mc, mod, version_info)
                    continue

                status[0] = mc

                local_dev = self.get_nem_dev_version(mod, mc)

                if 'dev' in version_info:
                    # Remove whitespace at the end and start
                    remote_dev = self.clean_version(version_info['dev'].strip())

                    # validate version
                    if not remote_dev or not self.is_version_valid(remote_dev):
                        raise InvalidVersion(remote_dev)

                    if simulation or local_dev != remote_dev:
                        status[1] = remote_dev

                local_release = self.get_nem_version(mod, mc)

                if 'version' in version_info:
                    # Remove whitespace at the end and start
                    remote_release = self.clean_version(version_info['version'].strip())

                    # validate version
                    if not remote_release or not self.is_version_valid(remote_release):
                        raise InvalidVersion(remote_release)

                    if simulation or local_release != remote_release:
                        status[2] = remote_release

                if 'changelog' in version_info and 'changelog' not in self.mods[mod]:
                    status[3] = version_info['changelog']

                if simulation or (status[1] or status[2]):
                    statuses.append(status)

            return (statuses, None)
        except Exception as e:
            print(mod + " failed to be polled...")
            traceback.print_exc()
            return ([], e)  # an exception was raised, so we return a True

    def CheckMods(self, mod):
        output = {}

        try:
            # We need to know what mods this SinZationalHax uses
            mods = self.SinZationalHax[self.mods[mod]["SinZationalHax"]["id"]]
            # Lets get the page/json/whatever all the mods want
            document = getattr(self, self.mods[mod]["function"])(mod, document=None)
            # Ok, time to parse it for each mod
            for tempMod in mods:
                output[tempMod] = self.CheckMod(tempMod, document)
        except Exception as e:
            print(mod + " failed to be polled (SinZationalHax)")
            traceback.print_exc()
            # TODO: Fix this ugly hack
            if 'tempMod' in locals():
                output[tempMod] = ([], e)

        return output
