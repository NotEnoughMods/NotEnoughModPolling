import json
import logging
import os
from collections import OrderedDict
from string import ascii_letters, digits
from urllib.parse import quote as urlquote

import aiohttp

ID = "nem"
permission = 1

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


# Colour Constants End

# Module-level state (replaces ModPoller instance)
session = None
versions = []
version = ""
cache_dir = os.path.join("commands", "NEM", "cache")
cache_last_modified = {}
cache_etag = {}


def normalize_filename(name):
    return "".join(c for c in name if c in ALLOWED_IN_FILENAME)


async def get_latest_version():
    try:
        return await fetch_json("https://bot.notenoughmods.com/?json")
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


async def fetch_page(url, timeout=10, decode_json=False, cache=False):
    try:
        if cache:
            fname = normalize_filename(url)
            filepath = os.path.join(cache_dir, fname)

            if os.path.exists(filepath):
                headers = {}

                etag = cache_etag.get(url)
                if etag:
                    headers["If-None-Match"] = etag

                last_modified = cache_last_modified.get(url)
                if last_modified:
                    headers["If-Modified-Since"] = f'"{last_modified}"'

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as response:
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

                        cache_etag[url] = response.headers.get("etag")
                        cache_last_modified[url] = response.headers.get("last-modified")

                        if decode_json:
                            return json.loads(text)
                        else:
                            return text
            else:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    text = await response.text()

                    with open(filepath, "w") as f:
                        f.write(text)

                    cache_etag[url] = response.headers.get("etag")
                    cache_last_modified[url] = response.headers.get("last-modified")

                    if decode_json:
                        return json.loads(text)
                    else:
                        return text
        else:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if decode_json:
                    return await response.json(content_type=None)
                else:
                    return await response.text()
    except Exception:
        nem_logger.exception("Failed to fetch page: %s", url)


async def fetch_json(*args, **kwargs):
    return await fetch_page(*args, decode_json=True, **kwargs)


async def setup(self, startup):
    global session, versions, version
    if session:
        await session.close()
    session = aiohttp.ClientSession(
        headers={"User-agent": "NotEnoughMods:Tools/2.0 (+https://github.com/NotEnoughMods/NotEnoughModPolling)"},
    )
    versions = await get_latest_version()
    version = versions[-1]


async def teardown(self):
    global session
    if session:
        await session.close()
        session = None


async def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        await command(self, name, params, channel, userdata, rank)
    except Exception:
        await self.send_message(channel, "Invalid sub-command!")
        await self.send_message(channel, 'See "=nem help" for help')


async def setlist(self, name, params, channel, userdata, rank):
    global version
    if len(params) != 2:
        await self.send_message(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.send_message(
            channel,
            "{name}: {setlist_help}".format(name=name, setlist_help=help["setlist"][0]),
        )
    else:
        version = str(params[1])
        await self.send_message(
            channel,
            f"switched list to: {BOLD}{BLUE}{params[1]}{COLOUREND}",
        )


async def multilist(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        await self.send_message(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.send_message(
            channel,
            "{name}: {multilist_help}".format(name=name, multilist_help=help["multilist"][0]),
        )
    else:
        try:
            jsonres = {}
            results = OrderedDict()

            mod_name = params[1]

            for ver in versions:
                jsonres[ver] = await fetch_json(
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
                await self.send_message(channel, name + ": mod not present in NEM.")
                return
            elif count == 1:
                count = str(count) + " MC version"
            else:
                count = str(count) + " MC versions"

            await self.send_message(channel, "Listing " + count + ' for "' + params[1] + '":')

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

                await self.send_message(
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
            await self.send_message(channel, name + ": " + str(error))
            nem_logger.exception("Error in multilist")


async def list(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.send_message(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.send_message(channel, "{name}: {help_entry}".format(name=name, help_entry=help["list"][0]))
        return
    ver = params[2] if len(params) >= 3 else version
    try:
        result = await fetch_page("https://bot.notenoughmods.com/" + urlquote(ver) + ".json", cache=True)
        if not result:
            await self.send_message(
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
            await self.send_message(channel, name + ": no results found.")
            return
        elif count == 1:
            count = str(count) + " result"
        else:
            count = str(count) + " results"

        await self.send_message(
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

            await self.send_message(
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
        await self.send_message(channel, f"{name}: {error}")
        nem_logger.exception("Error in list")


async def compare(self, name, params, channel, userdata, rank):
    try:
        old_version, new_version = params[1], params[2]

        old_json = await fetch_json(
            "https://bot.notenoughmods.com/" + urlquote(old_version) + ".json",
            cache=True,
        )

        new_json = await fetch_json(
            "https://bot.notenoughmods.com/" + urlquote(new_version) + ".json",
            cache=True,
        )

        new_mods = {mod_info["name"].lower(): True for mod_info in new_json}

        missing_mods = []

        for mod_info in old_json:
            old_mod_name = mod_info["name"].lower()
            if old_mod_name not in new_mods:
                missing_mods.append(mod_info["name"])

        path = f"commands/modbot.mca.d3s.co/htdocs/compare/{old_version}...{new_version}.json"
        with open(path, "w") as f:
            f.write(json.dumps(missing_mods, sort_keys=True, indent=4 * " "))

        await self.send_message(
            channel,
            f"{len(missing_mods)} mods died trying to update to {new_version}",
        )

    except Exception as error:
        await self.send_message(channel, f"{name}: {error}")
        nem_logger.exception("Error in compare")


async def about(self, name, params, channel, userdata, rank):
    await self.send_message(channel, "Not Enough Mods toolkit for IRC by SinZ & Yoshi2 v4.0")


async def help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        await self.send_message(channel, "{}: Available commands: {}".format(name, ", ".join(help)))
    else:
        command = params[1]
        if command in help:
            for line in help[command]:
                await self.send_message(channel, name + ": " + line)
        else:
            await self.send_message(channel, name + ": Invalid command provided")


async def force_cache_redownload(self, name, params, channel, userdata, rank):
    if self.rank_values[rank] >= 3:
        for ver in versions:
            url = "https://bot.notenoughmods.com/" + urlquote(ver) + ".json"
            normalized = normalize_filename(url)
            filepath = os.path.join(cache_dir, normalized)
            if os.path.exists(filepath):
                cache_last_modified[normalized] = 0

        await self.send_message(
            channel,
            "Cache Timestamps have been reset. Cache will be redownloaded on the next fetching.",
        )


commands = {
    "list": list,
    "multilist": multilist,
    "about": about,
    "help": help,
    "setlist": setlist,
    "compare": compare,
    "forceredownload": force_cache_redownload,
}

help = {
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
}
