import json
import logging
import os
from collections import OrderedDict
from string import ascii_letters, digits
from urllib.parse import quote as urlquote

import aiohttp

from command_router import Permission, command, subcommand

PLUGIN_ID = "nem"

nem_logger = logging.getLogger("NEM_Tools")

# Colour Constants for List and Multilist command
COLOURPREFIX = chr(3)
COLOUREND = COLOURPREFIX
BOLD = chr(2)

DARKGREEN = COLOURPREFIX + "03"
RED = COLOURPREFIX + "05"
PURPLE = COLOURPREFIX + "06"
ORANGE = COLOURPREFIX + "07"
BLUE = COLOURPREFIX + "12"
PINK = COLOURPREFIX + "13"
GRAY = COLOURPREFIX + "14"
LIGHTGRAY = COLOURPREFIX + "15"

ALLOWED_IN_FILENAME = f"-_.() {ascii_letters}{digits}"

cache_dir = os.path.join("plugins", "NEM", "cache")

_help_dict = {
    "list": [
        "=nem list <search> <version>",
        "Searches the NotEnoughMods database for <search> and returns all results to IRC.",
    ],
    "about": ["=nem about", "Shows some info about the NEM plugin."],
    "help": [
        "=nem help [command]",
        "Shows the help info about [command] or lists all commands for this plugin.",
    ],
    "setlist": [
        "=nem setlist <version>",
        "Sets the default version to be used by other commands to <version>.",
    ],
    "multilist": [
        "=nem multilist <mod_name or alias>",
        "Searches the NotEnoughMods database for mod_name or alias in all MC versions.",
    ],
    "compare": [
        "=nem compare <oldVersion> <newVersion>",
        "Compares the NEMP entries for two different MC versions and says how many mods "
        "haven't been updated to the new version.",
    ],
    "total": [
        "=nem total [version]",
        "Returns the total number of mods, optionally for a specific MC version.",
    ],
    "missmodid": [
        "=nem missmodid <version>",
        "Returns mods without a modid set for the given MC version.",
    ],
    "blinks": [
        "=nem blinks <version>",
        "Checks each mod link for broken URLs (non-OK HTTP status codes).",
    ],
}


def normalize_filename(name):
    return "".join(c for c in name if c in ALLOWED_IN_FILENAME)


class Plugin:
    def __init__(self):
        self.session = None
        self.versions = []
        self.version = ""
        self.cache_last_modified = {}
        self.cache_etag = {}

    async def setup(self, router, startup):
        if self.session:
            await self.session.close()
        self.session = aiohttp.ClientSession(
            headers={"User-agent": "NotEnoughMods:Tools/2.0 (+https://github.com/NotEnoughMods/NotEnoughModPolling)"},
        )
        self.versions = await self._get_latest_version()
        self.version = self.versions[-1]

    async def teardown(self, router):
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_latest_version(self):
        try:
            return await self.fetch_json("https://bot.notenoughmods.com/?json")
        except Exception:
            nem_logger.exception("Failed to get NEM versions, falling back to hard-coded.")
            return [
                "1.4.5",
                "1.4.6-1.4.7",
                "1.5.1",
                "1.5.2",
                "1.6.1",
                "1.6.2",
                "1.6.4",
                "1.7.2",
                "1.7.4",
                "1.7.5",
                "1.7.7",
                "1.7.9",
                "1.7.10",
            ]

    async def fetch_page(self, url, timeout=10, decode_json=False, cache=False):
        try:
            if cache:
                fname = normalize_filename(url)
                filepath = os.path.join(cache_dir, fname)

                if os.path.exists(filepath):
                    headers = {}

                    etag = self.cache_etag.get(url)
                    if etag:
                        headers["If-None-Match"] = etag

                    last_modified = self.cache_last_modified.get(url)
                    if last_modified:
                        headers["If-Modified-Since"] = f'"{last_modified}"'

                    async with self.session.get(
                        url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers
                    ) as response:
                        if response.status == 304:
                            with open(filepath) as f:
                                if decode_json:
                                    return json.load(f)
                                else:
                                    return f.read()
                        else:
                            text = await response.text()

                            with open(filepath, "w") as f:
                                f.write(text)

                            self.cache_etag[url] = response.headers.get("etag")
                            self.cache_last_modified[url] = response.headers.get("last-modified")

                            if decode_json:
                                return json.loads(text)
                            else:
                                return text
                else:
                    async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        text = await response.text()

                        with open(filepath, "w") as f:
                            f.write(text)

                        self.cache_etag[url] = response.headers.get("etag")
                        self.cache_last_modified[url] = response.headers.get("last-modified")

                        if decode_json:
                            return json.loads(text)
                        else:
                            return text
            else:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if decode_json:
                        return await response.json(content_type=None)
                    else:
                        return await response.text()
        except Exception:
            nem_logger.exception("Failed to fetch page: %s", url)

    async def fetch_json(self, *args, **kwargs):
        return await self.fetch_page(*args, decode_json=True, **kwargs)

    @command("nem", permission=Permission.VOICED)
    async def nem(self, router, name, params, channel, userdata, rank, is_channel):
        await router.send_message(channel, "Invalid sub-command!")
        await router.send_message(channel, 'See "=nem help" for help')

    @subcommand("nem", "list")
    async def list_cmd(self, router, name, params, channel, userdata, rank):
        if len(params) < 2:
            await router.send_message(
                channel,
                f"{name}: Insufficient amount of parameters provided.",
            )
            await router.send_message(
                channel, "{name}: {help_entry}".format(name=name, help_entry=_help_dict["list"][0])
            )
            return
        ver = params[2] if len(params) >= 3 else self.version
        try:
            result = await self.fetch_page("https://bot.notenoughmods.com/" + urlquote(ver) + ".json", cache=True)
            if not result:
                await router.send_message(
                    channel,
                    f"{name}: Could not fetch the list. Are you sure it exists?",
                )
                return
            jsonres = json.loads(result)
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
                await router.send_message(channel, name + ": no results found.")
                return
            elif count == 1:
                count = str(count) + " result"
            else:
                count = str(count) + " results"

            await router.send_message(
                channel,
                f'Listing {count} for "{params[1]}" in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD}',
            )

            for line in results:
                alias = COLOURPREFIX
                if jsonres[line]["aliases"]:
                    alias_join_text = f"{COLOUREND}, {PINK}"
                    alias_text = alias_join_text.join(jsonres[line]["aliases"])

                    alias = f"({PINK}{alias_text}{COLOUREND}) "
                comment = ""
                if jsonres[line]["comment"] != "":
                    comment = "({colour}{text}{colour_end}) ".format(
                        colour_end=COLOUREND, colour=GRAY, text=jsonres[line]["comment"]
                    )
                dev = ""
                try:
                    if jsonres[line]["dev"] != "":
                        dev = "({colour}dev{colour_end}): {colour2}{version}{colour_end})".format(
                            colour_end=COLOUREND,
                            colour=GRAY,
                            colour2=RED,
                            version=jsonres[line]["dev"],
                        )
                except Exception:
                    nem_logger.error("Error getting dev version for %s", params[1], exc_info=True)

                await router.send_message(
                    channel,
                    "{purple}{name}{colour_end} {alias_string}"
                    "{darkgreen}{version}{colour_end} {dev_string}"
                    "{comment}{orange}{shorturl}{colour_end}".format(
                        name=jsonres[line]["name"],
                        alias_string=alias,
                        dev_string=dev,
                        comment=comment,
                        version=jsonres[line]["version"],
                        shorturl=jsonres[line]["shorturl"],
                        purple=PURPLE,
                        darkgreen=DARKGREEN,
                        orange=ORANGE,
                        colour_end=COLOUREND,
                    ),
                )
        except Exception as error:
            await router.send_message(channel, f"{name}: {error}")
            nem_logger.exception("Error in list")

    @subcommand("nem", "setlist")
    async def setlist(self, router, name, params, channel, userdata, rank):
        if len(params) != 2:
            await router.send_message(
                channel,
                f"{name}: Insufficient amount of parameters provided.",
            )
            await router.send_message(
                channel,
                "{name}: {setlist_help}".format(name=name, setlist_help=_help_dict["setlist"][0]),
            )
        else:
            self.version = str(params[1])
            await router.send_message(
                channel,
                f"switched list to: {BOLD}{BLUE}{params[1]}{COLOUREND}",
            )

    @subcommand("nem", "multilist")
    async def multilist(self, router, name, params, channel, userdata, rank):
        if len(params) != 2:
            await router.send_message(
                channel,
                f"{name}: Insufficient amount of parameters provided.",
            )
            await router.send_message(
                channel,
                "{name}: {multilist_help}".format(name=name, multilist_help=_help_dict["multilist"][0]),
            )
        else:
            try:
                jsonres = {}
                results = OrderedDict()

                mod_name = params[1]

                for ver in self.versions:
                    jsonres[ver] = await self.fetch_json(
                        "https://bot.notenoughmods.com/" + urlquote(ver) + ".json",
                        cache=True,
                    )

                    for i, mod in enumerate(jsonres[ver]):
                        if mod_name.lower() == mod["name"].lower():
                            results[ver] = i
                            break
                        else:
                            aliases = [mod_alias.lower() for mod_alias in mod["aliases"]]
                            if mod_name.lower() in aliases:
                                results[ver] = i

                count = len(results)

                if count == 0:
                    await router.send_message(channel, name + ": mod not present in NEM.")
                    return
                elif count == 1:
                    count = str(count) + " MC version"
                else:
                    count = str(count) + " MC versions"

                await router.send_message(channel, "Listing " + count + ' for "' + params[1] + '":')

                for ver in results:
                    alias = ""
                    mod_data = jsonres[ver][results[ver]]

                    if mod_data["aliases"]:
                        alias_join_text = f"{COLOUREND}, {PINK}"
                        alias_text = alias_join_text.join(mod_data["aliases"])

                        alias = f"({PINK}{alias_text}{COLOUREND}) "

                    comment = ""
                    if mod_data["comment"] != "":
                        comment = "({colour}{text}{colour_end}) ".format(
                            colour_end=COLOUREND, colour=GRAY, text=mod_data["comment"]
                        )

                    dev = ""
                    try:
                        if mod_data["dev"] != "":
                            dev = "({colour}dev{colour_end}: {colour2}{version}{colour_end}) ".format(
                                colour_end=COLOUREND,
                                colour=GRAY,
                                colour2=RED,
                                version=mod_data["dev"],
                            )

                    except Exception:
                        nem_logger.error("Error getting dev version for %s in %s", mod_name, ver, exc_info=True)

                    await router.send_message(
                        channel,
                        "{bold}{blue}{mcversion}{colour_end}{bold}: "
                        "{purple}{name}{colour_end} {alias_string}"
                        "{darkgreen}{version}{colour_end} {dev_string}"
                        "{comment}{orange}{shorturl}{colour_end}".format(
                            name=mod_data["name"],
                            alias_string=alias,
                            dev_string=dev,
                            comment=comment,
                            version=mod_data["version"],
                            shorturl=mod_data["shorturl"],
                            mcversion=ver,
                            bold=BOLD,
                            blue=BLUE,
                            purple=PURPLE,
                            darkgreen=DARKGREEN,
                            orange=ORANGE,
                            colour_end=COLOUREND,
                        ),
                    )

            except Exception as error:
                await router.send_message(channel, name + ": " + str(error))
                nem_logger.exception("Error in multilist")

    @subcommand("nem", "compare")
    async def compare(self, router, name, params, channel, userdata, rank):
        try:
            old_version, new_version = params[1], params[2]

            old_json = await self.fetch_json(
                "https://bot.notenoughmods.com/" + urlquote(old_version) + ".json",
                cache=True,
            )

            new_json = await self.fetch_json(
                "https://bot.notenoughmods.com/" + urlquote(new_version) + ".json",
                cache=True,
            )

            new_mods = {mod_info["name"].lower(): True for mod_info in new_json}

            missing_mods = []

            for mod_info in old_json:
                old_mod_name = mod_info["name"].lower()
                if old_mod_name not in new_mods:
                    missing_mods.append(mod_info["name"])

            path = f"plugins/modbot.mca.d3s.co/htdocs/compare/{old_version}...{new_version}.json"
            with open(path, "w") as f:
                f.write(json.dumps(missing_mods, sort_keys=True, indent=4 * " "))

            await router.send_message(
                channel,
                f"{len(missing_mods)} mods died trying to update to {new_version}",
            )

        except Exception as error:
            await router.send_message(channel, f"{name}: {error}")
            nem_logger.exception("Error in compare")

    @subcommand("nem", "about")
    async def about(self, router, name, params, channel, userdata, rank):
        await router.send_message(channel, "Not Enough Mods toolkit for IRC by SinZ & Yoshi2 v4.0")

    @subcommand("nem", "help")
    async def help(self, router, name, params, channel, userdata, rank):
        if len(params) == 1:
            await router.send_message(channel, "{}: Available commands: {}".format(name, ", ".join(_help_dict)))
        else:
            command = params[1]
            if command in _help_dict:
                for line in _help_dict[command]:
                    await router.send_message(channel, name + ": " + line)
            else:
                await router.send_message(channel, name + ": Invalid command provided")

    @subcommand("nem", "total")
    async def total(self, router, name, params, channel, userdata, rank):
        if len(params) == 2:
            ver = params[1]
            if ver not in self.versions:
                await router.send_message(channel, f"{name}: MC version not found in NEM.")
                return
            jsonres = await self.fetch_json(f"https://bot.notenoughmods.com/{urlquote(ver)}.json", cache=True)
            if jsonres is None:
                await router.send_message(channel, f"{name}: Could not fetch the list.")
                return
            count_msg = f"{PURPLE}{len(jsonres)}{COLOUREND} mods in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD}"
            await router.send_message(channel, count_msg)
        else:
            count = 0
            for ver in self.versions:
                jsonres = await self.fetch_json(f"https://bot.notenoughmods.com/{urlquote(ver)}.json", cache=True)
                if jsonres is not None:
                    count += len(jsonres)
            await router.send_message(
                channel, f"{PURPLE}{count}{COLOUREND} mods total across {len(self.versions)} versions"
            )

    @subcommand("nem", "missmodid")
    async def missmodid(self, router, name, params, channel, userdata, rank):
        if len(params) != 2:
            await router.send_message(channel, f"{name}: Usage: =nem missmodid <version>")
            return

        ver = params[1]
        if ver not in self.versions:
            await router.send_message(channel, f"{name}: MC version not found in NEM.")
            return

        jsonres = await self.fetch_json(f"https://bot.notenoughmods.com/{urlquote(ver)}.json", cache=True)
        if jsonres is None:
            await router.send_message(channel, f"{name}: Could not fetch the list.")
            return

        missing = [mod["name"] for mod in jsonres if mod.get("modid", "") == ""]

        if not missing:
            await router.send_message(
                channel, f"{name}: All mods in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD} have a modid set."
            )
        elif len(missing) <= 5:
            for mod_name in missing:
                await router.send_message(channel, f"[{BLUE}{ver}{COLOUREND}] {mod_name}")
        elif len(missing) <= 20:
            await router.send_message(channel, f"{len(missing)} mod(s) missing modid. Sending via notice...")
            for mod_name in missing:
                await router.send_notice(name, f"[{BLUE}{ver}{COLOUREND}] {mod_name}")
        else:
            msg = f"{len(missing)} mod(s) missing modid in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD}."
            await router.send_message(channel, msg)

    @subcommand("nem", "blinks")
    async def blinks(self, router, name, params, channel, userdata, rank):
        if len(params) != 2:
            await router.send_message(channel, f"{name}: Usage: =nem blinks <version>")
            return

        ver = params[1]
        if ver not in self.versions:
            await router.send_message(channel, f"{name}: MC version not found in NEM.")
            return

        jsonres = await self.fetch_json(f"https://bot.notenoughmods.com/{urlquote(ver)}.json", cache=True)
        if jsonres is None:
            await router.send_message(channel, f"{name}: Could not fetch the list.")
            return

        await router.send_message(channel, f"[{BLUE}{ver}{COLOUREND}] Checking {len(jsonres)} mod links...")

        counts = {}
        badmods = []
        index = 0

        for mod in jsonres:
            if mod.get("longurl", "") != "":
                try:
                    async with self.session.head(
                        mod["longurl"],
                        timeout=aiohttp.ClientTimeout(total=10),
                        allow_redirects=True,
                    ) as resp:
                        code = resp.status
                        counts[code] = counts.get(code, 0) + 1
                        if code >= 400:
                            badmods.append({"name": mod["name"], "reason": code})
                except Exception as e:
                    reason = type(e).__name__
                    counts[reason] = counts.get(reason, 0) + 1
                    badmods.append({"name": mod["name"], "reason": reason})

            index += 1
            if index % 50 == 0:
                await router.send_message(channel, f"[{BLUE}{ver}{COLOUREND}] {index} mods processed...")

        if not badmods:
            await router.send_message(channel, f"[{BLUE}{ver}{COLOUREND}] No broken links found.")
        elif len(badmods) <= 5:
            await router.send_message(channel, f"{len(badmods)} broken link(s) found:")
            for mod in badmods:
                await router.send_message(channel, f"[{BLUE}{ver}{COLOUREND}] {mod['name']} ({mod['reason']})")
        elif len(badmods) <= 20:
            await router.send_message(channel, f"{len(badmods)} broken link(s) found. Sending via notice...")
            for mod in badmods:
                await router.send_notice(name, f"[{BLUE}{ver}{COLOUREND}] {mod['name']} ({mod['reason']})")
        else:
            msg = f"{len(badmods)} broken link(s) found in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD}."
            await router.send_message(channel, msg)

        await router.send_message(
            channel,
            f"[{BLUE}{ver}{COLOUREND}] Complete. {index} mods processed. Results: {counts}",
        )

    @subcommand("nem", "forceredownload", permission=Permission.ADMIN)
    async def force_cache_redownload(self, router, name, params, channel, userdata, rank):
        for ver in self.versions:
            url = "https://bot.notenoughmods.com/" + urlquote(ver) + ".json"
            normalized = normalize_filename(url)
            filepath = os.path.join(cache_dir, normalized)
            if os.path.exists(filepath):
                self.cache_last_modified[normalized] = 0

        await router.send_message(
            channel,
            "Cache Timestamps have been reset. Cache will be redownloaded on the next fetching.",
        )
