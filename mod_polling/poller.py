import asyncio
import contextlib
import json
import logging
import re
import urllib.parse

import aiohttp
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("mod_polling.poller")


class NEMPException(Exception):
    pass


class InvalidVersion(NEMPException):
    def __str__(self):
        return repr(self.args[0])


class ModPoller:
    def __init__(self):
        self.nemVersions = []
        self.mods = {}
        self.document_groups = {}
        self.invalid_versions = []
        self.session = None
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_delay: float = 0.5

        self.jinja_env = Environment(
            loader=FileSystemLoader("mod_polling"),
            autoescape=select_autoescape(["html"]),
        )

        self.load_config()
        self.load_version_blocklist()
        self.load_mc_mapping()
        self.buildModDict()

    async def fetch_page(self, url, timeout=10, decode_json=False, **kwargs):
        host = urllib.parse.urlparse(url).hostname
        if host not in self._host_locks:
            self._host_locks[host] = asyncio.Lock()

        async with self._host_locks[host]:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), **kwargs) as response:
                if 400 <= response.status < 500:
                    raise NEMPException(f"HTTP {response.status} for {url}")
                response.raise_for_status()

                if decode_json:
                    result = await response.json(content_type=None)
                else:
                    result = await response.text()

            await asyncio.sleep(self._host_delay)
            return result

    async def fetch_json(self, *args, **kwargs):
        return await self.fetch_page(*args, decode_json=True, **kwargs)

    def load_config(self):
        try:
            with open("mod_polling/config.yml") as f:
                self.config = yaml.safe_load(f)
        except:
            logger.error("You need to setup the mod_polling/config.yml file")
            raise

        self._host_delay = self.config.get("polling", {}).get("host_delay", 0.5)

    def load_version_blocklist(self):
        try:
            with open("mod_polling/version_blocklist.yml") as f:
                self.invalid_versions = yaml.safe_load(f)
        except:
            logger.error("You need to setup the mod_polling/version_blocklist.yml file")
            raise

        # compile regexes for performance
        self.invalid_versions = [re.compile(regex, re.I) for regex in self.invalid_versions[:]]

    async def load_mc_blocklist(self):
        with open("mod_polling/mc_blocklist.yml") as f:
            self.mc_blocklist = yaml.safe_load(f)  # type: list[str]

        # Load additional versions from the Mojang version manifest
        # It's ok if this happens to fail
        try:
            async with self.session.get("https://launchermeta.mojang.com/mc/game/version_manifest.json") as response:
                r = await response.json(content_type=None)

            # Add anything that isn't a release to the blocklist
            additional = [version["id"] for version in r["versions"] if version["type"] != "release"]
            self.mc_blocklist.extend(additional)
        except Exception:
            logger.warning("Failed to load additional blocked MC versions from Mojang version manifest", exc_info=True)

        # Deduplicate versions
        self.mc_blocklist = set(self.mc_blocklist)

    def load_mc_mapping(self):
        with open("mod_polling/mc_mapping.yml") as f:
            self.mc_mapping = yaml.safe_load(f)

    def _find_regex(self, data):
        """
        Internal-use recursive function to find the regex for a mod's polling
        information data dict.
        The mod's data is passed as an argument so it can be re-used for other
        things which rely on a unique 'regex' key.
        """
        if isinstance(data, dict):
            if "regex" in data:
                return data["regex"]
            else:
                for _k, v in data.items():
                    ret = self._find_regex(v)
                    if ret:
                        return ret
        else:
            # ignore other types
            return

    def compile_regex(self, mod):
        regex = self._find_regex(self.mods[mod])

        if regex:
            self.mods[mod]["_regex"] = re.compile(regex, re.I)

    def get_mod_regex(self, mod):
        return self.mods[mod].get("_regex")

    def match_mod_regex(self, mod, data):
        return self.mods[mod]["_regex"].search(data)

    def buildModDict(self):
        with open("mod_polling/mods.json", "rb") as modList:
            self.mods = json.load(modList)

        for mod in self.mods:
            self.compile_regex(mod)

            self.mods[mod]["nem_versions"] = {}

            if "document_group" in self.mods[mod]:
                if self.mods[mod]["document_group"]["id"] in self.document_groups:
                    self.document_groups[self.mods[mod]["document_group"]["id"]].append(mod)
                else:
                    self.document_groups[self.mods[mod]["document_group"]["id"]] = [mod]

    def buildHTML(self):
        self.jinja_env.get_template("index.jinja2").stream(mods=self.mods).dump("mod_polling/htdocs/index.html")

    async def QueryNEM(self):
        self.nemVersions = await self.fetch_json("https://bot.notenoughmods.com/?json")

    async def init_nem_versions(self):
        our_mods = {}

        for json_mod_name, json_info in self.mods.items():
            # The NEM mod name is set in 'name', defaults to json_mod_name
            # We then convert it to lowercase so we can make a case-insensitive comparison
            nem_mod_name = json_info.get("name", json_mod_name).lower()

            our_mods.setdefault(nem_mod_name, []).append(json_mod_name)

        # for MC version in NEM's list
        for nem_list_name in self.nemVersions:
            if nem_list_name in self.mc_mapping:
                # TODO
                continue

            # Get the NEM List for this MC Version
            nem_list = await self.fetch_json("https://bot.notenoughmods.com/" + nem_list_name + ".json")

            # For each NEM Mod...
            for nem_mod in nem_list:
                # Possible NEM name for the mod are the name itself and its aliases
                nem_mod_names = [nem_mod["name"]] + nem_mod["aliases"]

                for nem_mod_name in nem_mod_names:
                    # This is a map of NEM mod name -> internal (mods.json) mod name
                    our_names = our_mods.get(nem_mod_name.lower())

                    # Is it in our mods.json?
                    if our_names:
                        # Grab the dev and release version
                        for our_name in our_names:
                            self.mods[our_name]["nem_versions"][nem_list_name] = {
                                "dev": nem_mod.get("dev", ""),
                                "version": nem_mod.get("version", ""),
                            }

    async def CheckJenkins(self, mod, document=None, simulation=False):
        jsonres = await self.fetch_json(
            self.mods[mod]["jenkins"]["url"] + "?tree=changeSet[items[msg]],artifacts[fileName]"
        )
        filename = jsonres["artifacts"][self.mods[mod]["jenkins"]["item"]]["fileName"]
        match = self.match_mod_regex(mod, filename)
        output = match.groupdict()
        with contextlib.suppress(BaseException):
            output["change"] = jsonres["changeSet"]["items"][0]["msg"]
        return output

    async def CheckMCForge2(self, mod, document=None, simulation=False):
        jsonres = await self.fetch_json(self.mods[mod]["mcforge"]["url"])

        if self.mods[mod]["mcforge"].get("slim", False):
            result = {}

            for promo_name, version in jsonres["promos"].items():
                match = re.match(
                    r"^(?P<mc>[0-9]+(?:\.[0-9]+)+)-(?P<type>latest|recommended)$",
                    promo_name,
                )

                if not match:
                    continue

                mc_version = match.group("mc")
                promo_type = match.group("type")

                field = "version" if promo_type == "recommended" else "dev"

                result.setdefault(mc_version, {})[field] = version

            return result
        else:
            for promo in jsonres["promos"]:
                if promo == self.mods[mod]["mcforge"]["promo"]:
                    return {
                        self.mods[mod]["mcforge"]["promoType"]: jsonres["promos"][promo]["version"],
                        "mc": jsonres["promos"][promo]["mcversion"],
                    }

            return {}

    async def CheckForgeJson(self, mod, document=None, simulation=False):
        jsonres = await self.fetch_json(self.mods[mod]["forgejson"]["url"])

        if "promos" not in jsonres:
            return {}

        versions = {}

        for promo, version in jsonres["promos"].items():
            if promo == "reserved":
                # thanks Hea3veN
                continue

            mc, promo_type = promo.split("-", 1)

            version_type = "dev" if promo_type == "latest" else "version"

            versions.setdefault(mc, {})[version_type] = version

        # Finishing touches
        for mc, version_info in versions.items():
            if "dev" in version_info and "version" in version_info and version_info["dev"] == version_info["version"]:
                del versions[mc]["dev"]

        return versions

    async def CheckHTML(self, mod, document=None, simulation=False):
        page = await self.fetch_page(self.mods[mod]["html"]["url"])

        reverse = self.mods[mod]["html"].get("reverse", False)
        version_type = self.mods[mod]["html"].get("version_type", "version")
        regex = self.get_mod_regex(mod)

        versions = {}

        for match in regex.finditer(page):
            mc_version = match.group("mc")
            mod_version = match.group("version")

            if mc_version not in versions or reverse:
                versions[mc_version] = mod_version

        result = {}

        for mc_version, mod_version in versions.items():
            result[mc_version] = {version_type: mod_version}

        return result

    async def CheckSpacechase(self, mod, document=None, simulation=False):
        jsonres = await self.fetch_json(
            "http://spacechase0.com/core/latest.php?obj=mods/minecraft/" + self.mods[mod]["spacechase"]["slug"]
        )

        version = jsonres["version"]

        results = {}

        for mc in jsonres["downloads"]:
            results[mc] = {"version": version, "changelog": jsonres["summary"]}

        return results

    async def CheckLunatrius(self, mod, document=None, simulation=False):
        jsonres = await self.fetch_json("http://mc.lunatri.us/json?latest&mod=" + mod + "&v=2")
        info = jsonres["mods"][mod]["latest"]
        output = {"version": info["version"], "mc": info["mc"]}
        if len(info["changes"]) > 0:
            output["change"] = info["changes"][0]
        return output

    async def CheckBigReactors(self, mod, document=None, simulation=False):
        info = await self.fetch_json("http://big-reactors.com/version.json")

        ret = {"mc": info["mcVersion"]}

        if info["stable"]:
            ret["version"] = info["version"]
        else:
            ret["dev"] = info["version"]

        if info["changelog"]:
            # send only the first line of the changelog
            ret["change"] = info["changelog"][0]

        return ret

    async def CheckCurse(self, mod, document=None, simulation=False):
        # Field name from the JSON to be used against the regex (name or display, name by default)
        field_name = self.mods[mod]["curse"].get("field", "name")

        jsonres = await self.fetch_json("https://api.cfwidget.com/" + self.mods[mod]["curse"]["id"])

        if jsonres.get("accepted"):
            # CFWidget doesn't have the information and queued up an update
            return {}
        elif "error" in jsonres:
            raise NEMPException("cfwidget: " + jsonres.get("error"))

        release_type = "release"

        # Sometimes CFWidget returns no files, but the issue resolves itself after a while,
        # so we just temporarily return an empty result
        if not jsonres["files"]:
            return {}

        sorted_files = sorted(jsonres["files"], key=lambda x: x["id"], reverse=True)

        latest_release_id = sorted_files[0]["id"]

        versions = {}

        MC_VERSION_REGEX = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")

        for release in sorted_files:
            for mc_version in release["versions"]:
                # Skip this "mc version" if it's not actually a MC version (Forge, snapshots, Java, etc)
                if not MC_VERSION_REGEX.match(mc_version):
                    continue

                if mc_version in versions:
                    continue

                match = self.match_mod_regex(mod, release[field_name])

                if not match:
                    if release["id"] == latest_release_id:
                        raise NEMPException(
                            "Regex is outdated (doesn't match against latest release). Latest: "
                            + release[field_name]
                            + ", Regex: "
                            + self.get_mod_regex(mod).pattern
                        )

                    # If this release isn't the latest one, we just assume it's an old one and skip it
                    continue

                output = match.groupdict()

                res = {}

                version_type = "version" if release["type"].lower() == release_type else "dev"

                res[version_type] = output["version"]

                versions[mc_version] = res

        return versions

    async def CheckGitHubRelease(self, mod, document=None, simulation=False):
        repo = self.mods[mod]["github"].get("repo")

        client_id = self.config.get("github", {}).get("client_id")
        client_secret = self.config.get("github", {}).get("client_secret")

        url = "https://api.github.com/repos/" + repo + "/releases"

        if client_id and client_secret:
            releases = await self.fetch_json(url, auth=aiohttp.BasicAuth(client_id, client_secret))
        else:
            releases = await self.fetch_json(url)

        type_ = self.mods[mod]["github"].get("type", "asset")

        if type_ == "asset":
            regex = self.get_mod_regex(mod)

            for release in releases:
                for asset in release["assets"]:
                    match = regex.search(asset["name"])
                    if match:
                        result = match.groupdict()
                        if release["prerelease"]:
                            result["dev"] = result["version"]
                            del result["version"]
                        return result
        elif type_ == "tag":
            release = releases[0]

            tag_name = release["tag_name"]

            if "regex" in self.mods[mod]["github"]:
                result = self.match_mod_regex(mod, tag_name).groupdict()

                if release["prerelease"]:
                    result["dev"] = result["version"]
                    del result["version"]

                return result
            else:
                if release["prerelease"]:
                    return {"dev": tag_name}
                else:
                    return {"version": tag_name}
        else:
            raise ValueError(f"Invalid type {type_!r} for CheckGitHubRelease parser")

    async def CheckBuildCraft(self, mod, document=None, simulation=False):
        page = await self.fetch_page(
            "https://raw.githubusercontent.com/BuildCraft/BuildCraft/master/buildcraft_resources/versions.txt"
        )

        # filter empty lines
        lines = [line for line in page.splitlines() if line]

        mc, _mod_name, version = lines[-1].split(":")

        return {"mc": mc, "version": version}

    def is_version_valid(self, version):
        return all(not regex.search(version) for regex in self.invalid_versions)

    # Returns the version string with some replacements, like:
    # - whitespace (space/tab/etc) replaced by hyphen
    def clean_version(self, version):
        version = re.sub(r"\s+", "-", version)
        # remove any extra hyphens
        version = re.sub(r"-+", "-", version)
        return version

    # Trims additional ".0" at the end of the version until the
    # version has only 2 groups ("1.0")
    def clean_mc_version(self, version):
        while version.endswith(".0") and version.count(".") > 1:
            version = version[:-2]
        return version

    def get_nem_version(self, mod, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        version = self.mods[mod]["nem_versions"].get(nem_list, {}).get("version", "")

        if version == "dev-only":
            # dev-only means there's no release version, so we make that transparent to the parsers
            return ""
        else:
            return version

    def get_nem_dev_version(self, mod, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        return self.mods[mod]["nem_versions"].get(nem_list, {}).get("dev", "")

    def set_nem_version(self, mod, version, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        self.mods[mod]["nem_versions"].setdefault(nem_list, {})["version"] = version

    def set_nem_dev_version(self, mod, version, nem_list):
        mapped_list = self.mc_mapping.get(nem_list)

        if mapped_list:
            nem_list = mapped_list

        self.mods[mod]["nem_versions"].setdefault(nem_list, {})["dev"] = version

    def get_proper_name(self, mod):
        lower_mod = mod.lower()

        for mod_name in self.mods:
            if lower_mod == mod_name.lower():
                return mod_name

        return None

    async def CheckMod(self, mod, document=None, simulation=False):
        try:
            output = await getattr(self, self.mods[mod]["function"])(mod, document=document, simulation=simulation)

            if output is None:
                raise NEMPException("Parser returned null")

            if isinstance(output, dict) and ("version" in output or "dev" in output):
                # legacy parser
                if "mc" not in output:
                    if "mc" in self.mods[mod]:
                        mc = self.mods[mod]["mc"]
                    else:
                        # if it doesn't return a Minecraft version and there's no default, we bail out
                        raise NEMPException("No Minecraft version was returned by the parser")
                else:
                    mc = output["mc"]

                # convert to new format
                new_output = {mc: {}}

                if "version" in output:
                    new_output[mc]["version"] = output["version"]

                if "dev" in output:
                    new_output[mc]["dev"] = output["dev"]

                if "change" in output:
                    new_output[mc]["changelog"] = output["change"]

                output = new_output

            statuses = []

            for mc, version_info in output.items():
                # [mc version, dev version, release version, changelog]
                status = [None, "", "", None]

                mc = self.clean_mc_version(mc)

                if mc in self.mc_mapping:
                    mc = self.mc_mapping[mc]

                if mc in self.mc_blocklist:
                    logger.debug("Skipping blocked MC version %s for %s, version_info=%r", mc, mod, version_info)
                    continue

                status[0] = mc

                local_dev = self.get_nem_dev_version(mod, mc)

                if "dev" in version_info:
                    # Remove whitespace at the end and start
                    remote_dev = self.clean_version(version_info["dev"].strip())

                    # validate version
                    if not remote_dev or not self.is_version_valid(remote_dev):
                        raise InvalidVersion(remote_dev)

                    if simulation or local_dev != remote_dev:
                        status[1] = remote_dev

                local_release = self.get_nem_version(mod, mc)

                if "version" in version_info:
                    # Remove whitespace at the end and start
                    remote_release = self.clean_version(version_info["version"].strip())

                    # validate version
                    if not remote_release or not self.is_version_valid(remote_release):
                        raise InvalidVersion(remote_release)

                    if simulation or local_release != remote_release:
                        status[2] = remote_release

                if "changelog" in version_info and "changelog" not in self.mods[mod]:
                    status[3] = version_info["changelog"]

                if simulation or (status[1] or status[2]):
                    statuses.append(status)

            return (statuses, None)
        except Exception as e:
            logger.error("%s failed to be polled", mod, exc_info=True)
            return ([], e)  # an exception was raised, so we return a True

    async def CheckMods(self, mod):
        # We need to know what mods this document_group uses
        group_mod_names = self.document_groups[self.mods[mod]["document_group"]["id"]]

        # Get all functions (Check*) this document_group uses
        function_names = set(self.mods[group_mod_name]["function"] for group_mod_name in group_mod_names)
        # Sanity check: a document_group should only use one function
        if len(function_names) != 1:
            raise NEMPException(
                "Failed to poll document_group for " + mod + ": Too many functions: " + str(function_names)
            )

        func_name = next(iter(function_names))

        try:
            # Let's get the page/json/whatever all the mods want
            # TODO: Ensure the function is the same for all mods in the document group
            document = await getattr(self, func_name)(mod, document=None)
        except Exception:
            # If getting the document fails, we want to abort immediately
            logger.error("Failed to poll document_group for %s", mod, exc_info=True)
            # Pass the exception along to the polling task
            raise

        output = {}

        # Ok, time to parse it for each mod
        for tempMod in group_mod_names:
            try:
                output[tempMod] = await self.CheckMod(tempMod, document)
            except Exception as e:
                logger.error("%s failed to be polled (document_group)", tempMod, exc_info=True)
                output[tempMod] = ([], e)

        return output


async def setup():
    nem = ModPoller()
    nem.session = aiohttp.ClientSession(
        headers={"User-agent": "NotEnoughMods:Polling/2.0 (+https://github.com/NotEnoughMods/NotEnoughModPolling)"},
    )
    await nem.load_mc_blocklist()
    await nem.QueryNEM()
    await nem.init_nem_versions()
    nem.buildHTML()
    return nem
