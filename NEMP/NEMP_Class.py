import logging
import re
import requests
import simplejson
import traceback
import yaml

from bs4 import BeautifulSoup
from distutils.version import LooseVersion
from jinja2 import Environment, FileSystemLoader, select_autoescape

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

        self.jinja_env = Environment(
            loader=FileSystemLoader('commands/NEMP'),
            autoescape=select_autoescape(['html'])
        )

        self.load_config()
        self.load_version_blacklist()
        self.load_mc_blacklist()
        self.load_mc_mapping()
        self.buildModDict()
        self.QueryNEM()
        self.init_nem_versions()
        self.buildHTML()

    def fetch_page(self, url, timeout=10, decode_json=False, *args, **kwargs):
        request = self.requests_session.get(url, timeout=timeout, *args, **kwargs)

        try:
            request.raise_for_status()
        except requests.HTTPError as e:
            if request.status_code >= 400 and request.status_code < 500:
                raise NEMPException(e)
            else:
                raise

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
        self.invalid_versions = [re.compile(regex, re.I) for regex in self.invalid_versions[:]]

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
        self.jinja_env.get_template('index.jinja2').stream(mods=self.mods).dump('commands/NEMP/htdocs/index.html')

    def QueryNEM(self):
        self.nemVersions = self.fetch_json("https://bot.notenoughmods.com/?json")

    def init_nem_versions(self):
        our_mods = {}

        for json_mod_name, json_info in self.mods.iteritems():
            # The NEM mod name is set in 'name', defaults to json_mod_name
            # We then convert it to lowercase so we can make a case-insensitive comparison
            nem_mod_name = json_info.get('name', json_mod_name).lower()

            our_mods.setdefault(nem_mod_name, []).append(json_mod_name)

        # for MC version in NEM's list
        for nem_list_name in self.nemVersions:
            if nem_list_name in self.mc_mapping:
                # TODO
                continue

            # Get the NEM List for this MC Version
            nem_list = self.fetch_json("https://bot.notenoughmods.com/" + nem_list_name + ".json")

            # For each NEM Mod...
            for nem_mod in nem_list:
                nem_mod_name = nem_mod['name']

                our_names = our_mods.get(nem_mod_name.lower())

                # Is it in our mods.json?
                if our_names:
                    # Grab the dev and release version
                    for our_name in our_names:
                        self.mods[our_name]['nem_versions'][nem_list_name] = {
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
        jsonres = self.fetch_json(self.mods[mod]['mcforge']['url'])

        if self.mods[mod]['mcforge'].get('slim', False):
            result = {}

            for promo_name, version in jsonres['promos'].iteritems():
                match = re.match(r'^(?P<mc>[0-9]+(?:\.[0-9]+)+)-(?P<type>latest|recommended)$', promo_name)

                if not match:
                    continue

                mc_version = match.group('mc')
                promo_type = match.group('type')

                if promo_type == 'recommended':
                    field = 'version'
                else:
                    field = 'dev'

                result.setdefault(mc_version, {})[field] = version

            return result
        else:
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
        page = self.fetch_page(self.mods[mod]['html']['url'])

        reverse = self.mods[mod]['html'].get('reverse', False)
        version_type = self.mods[mod]['html'].get('version_type', 'version')
        regex = self.get_mod_regex(mod)

        versions = {}

        for match in regex.finditer(page):
            mc_version = match.group('mc')
            mod_version = match.group('version')

            if mc_version not in versions or reverse:
                versions[mc_version] = mod_version

        result = {}

        for mc_version, mod_version in versions.iteritems():
            result[mc_version] = {version_type: mod_version}

        return result

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

        # Sometimes it's "mc-mods/minecraft", sometimes it's "minecraft/mc-mods", sometimes it's "project"...
        base_path = self.mods[mod]['curse'].get('base_path', 'mc-mods/minecraft')

        # As IDs only work with newer mods we have to support two versions of the URL
        if modid:
            jsonres = self.fetch_json("https://api.cfwidget.com/" + base_path + "/" + modid + "-" + modname)
        else:
            jsonres = self.fetch_json("https://api.cfwidget.com/" + base_path + "/" + modname)

        if jsonres.get('error') == 'not_found':
            # This automatically raises an exception and stops this mod from polling after the current cycle
            return None
        elif jsonres.get('error') == 'in_queue':
            # The widget doesn't have the information and queued up an update
            return {}

        release_type = 'release'

        # Sometimes CFWidget returns no files, but the issue resolves itself after a while,
        # so we just temporarily return an empty result
        if not jsonres['files']:
            return {}

        sorted_files = sorted(jsonres['files'], key=lambda x: x['id'], reverse=True)

        latest_release_id = sorted_files[0]['id']

        versions = {}

        MC_VERSION_REGEX = re.compile(r'^[0-9]+(?:\.[0-9]+)+$')

        for release in sorted_files:
            for mc_version in release['versions']:
                # Skip this "mc version" if it's not actually a MC version (Forge, snapshots, Java, etc)
                if not MC_VERSION_REGEX.match(mc_version):
                    continue

                if mc_version in versions:
                    continue

                match = self.match_mod_regex(mod, release['name'])

                if not match:
                    if release['id'] == latest_release_id:
                        raise NEMPException("Regex is outdated (doesn't match against latest release). Latest: " + release['name'] + ", Regex: " + self.get_mod_regex(mod).pattern)

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
            releases = self.fetch_json(url, auth=(client_id, client_secret))
        else:
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
            # Skip empty lines
            if not line:
                continue

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
