import json
import logging
import os
import traceback
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

# Module-level state (replaces NotEnoughClasses instance)
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
        print("Failed to get NEM versions, falling back to hard-coded")
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
        traceback.print_exc()
        pass


async def fetch_json(*args, **kwargs):
    return await fetch_page(*args, decode_json=True, **kwargs)


async def setup(self, Startup):
    global session, versions, version
    if session:
        await session.close()
    session = aiohttp.ClientSession(
        headers={"User-agent": "NotEnoughMods:Tools/1.X (+https://github.com/NotEnoughMods/NotEnoughModPolling)"},
    )
    versions = await get_latest_version()
    version = versions[-1]


async def execute(self, name, params, channel, userdata, rank):
    try:
        command = commands[params[0]]
        await command(self, name, params, channel, userdata, rank)
    except Exception:
        await self.sendMessage(channel, "Invalid sub-command!")
        await self.sendMessage(channel, 'See "=nem help" for help')


async def setlist(self, name, params, channel, userdata, rank):
    global version
    if len(params) != 2:
        await self.sendMessage(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.sendMessage(
            channel,
            "{name}: {setlistHelp}".format(name=name, setlistHelp=help["setlist"][0]),
        )
    else:
        version = str(params[1])
        await self.sendMessage(
            channel,
            f"switched list to: {BOLD}{BLUE}{params[1]}{COLOUREND}",
        )


async def multilist(self, name, params, channel, userdata, rank):
    if len(params) != 2:
        await self.sendMessage(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.sendMessage(
            channel,
            "{name}: {multilistHelp}".format(name=name, multilistHelp=help["multilist"][0]),
        )
    else:
        try:
            jsonres = {}
            results = OrderedDict()

            modName = params[1]

            for ver in versions:
                jsonres[ver] = await fetch_json(
                    "https://bot.notenoughmods.com/" + urlquote(ver) + ".json",
                    cache=True,
                )

                for i, mod in enumerate(jsonres[ver]):
                    if modName.lower() == mod["name"].lower():
                        results[ver] = i
                        break
                    else:
                        aliases = [mod_alias.lower() for mod_alias in mod["aliases"]]
                        if modName.lower() in aliases:
                            results[ver] = i

            count = len(results)

            if count == 0:
                await self.sendMessage(channel, name + ": mod not present in NEM.")
                return
            elif count == 1:
                count = str(count) + " MC version"
            else:
                count = str(count) + " MC versions"

            await self.sendMessage(channel, "Listing " + count + ' for "' + params[1] + '":')

            for ver in results:
                alias = ""
                modData = jsonres[ver][results[ver]]

                if modData["aliases"]:
                    alias_joinText = f"{COLOUREND}, {PINK}"
                    alias_text = alias_joinText.join(modData["aliases"])

                    alias = f"({PINK}{alias_text}{COLOUREND}) "

                comment = ""
                if modData["comment"] != "":
                    comment = "({colour}{text}{colourEnd}) ".format(
                        colourEnd=COLOUREND, colour=GRAY, text=modData["comment"]
                    )

                dev = ""
                try:
                    if modData["dev"] != "":
                        dev = "({colour}dev{colourEnd}: {colour2}{version}{colourEnd}) ".format(
                            colourEnd=COLOUREND,
                            colour=GRAY,
                            colour2=RED,
                            version=modData["dev"],
                        )

                except Exception as error:
                    print(error)
                    traceback.print_exc()

                await self.sendMessage(
                    channel,
                    "{bold}{blue}{mcversion}{colourEnd}{bold}: "
                    "{purple}{name}{colourEnd} {aliasString}"
                    "{darkgreen}{version}{colourEnd} {devString}"
                    "{comment}{orange}{shorturl}{colourEnd}".format(
                        name=modData["name"],
                        aliasString=alias,
                        devString=dev,
                        comment=comment,
                        version=modData["version"],
                        shorturl=modData["shorturl"],
                        mcversion=ver,
                        bold=BOLD,
                        blue=BLUE,
                        purple=PURPLE,
                        darkgreen=DARKGREEN,
                        orange=ORANGE,
                        colourEnd=COLOUREND,
                    ),
                )

        except Exception as error:
            await self.sendMessage(channel, name + ": " + str(error))
            traceback.print_exc()


async def list(self, name, params, channel, userdata, rank):
    if len(params) < 2:
        await self.sendMessage(
            channel,
            f"{name}: Insufficient amount of parameters provided.",
        )
        await self.sendMessage(channel, "{name}: {helpEntry}".format(name=name, helpEntry=help["list"][0]))
        return
    ver = params[2] if len(params) >= 3 else version
    try:
        result = await fetch_page("https://bot.notenoughmods.com/" + urlquote(ver) + ".json", cache=True)
        if not result:
            await self.sendMessage(
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
            await self.sendMessage(channel, name + ": no results found.")
            return
        elif count == 1:
            count = str(count) + " result"
        else:
            count = str(count) + " results"

        await self.sendMessage(
            channel,
            f'Listing {count} for "{params[1]}" in {BOLD}{BLUE}{ver}{COLOUREND}{BOLD}',
        )

        for line in results:
            alias = COLOURPREFIX
            if jsonres[line]["aliases"]:
                alias_joinText = f"{COLOUREND}, {PINK}"
                alias_text = alias_joinText.join(jsonres[line]["aliases"])

                alias = f"({PINK}{alias_text}{COLOUREND}) "
            comment = ""
            if jsonres[line]["comment"] != "":
                comment = "({colour}{text}{colourEnd}) ".format(
                    colourEnd=COLOUREND, colour=GRAY, text=jsonres[line]["comment"]
                )
            dev = ""
            try:
                if jsonres[line]["dev"] != "":
                    dev = "({colour}dev{colourEnd}): {colour2}{version}{colourEnd})".format(
                        colourEnd=COLOUREND,
                        colour=GRAY,
                        colour2=RED,
                        version=jsonres[line]["dev"],
                    )
            except Exception as error:
                print(error)
                traceback.print_exc()

            await self.sendMessage(
                channel,
                "{purple}{name}{colourEnd} {aliasString}"
                "{darkgreen}{version}{colourEnd} {devString}"
                "{comment}{orange}{shorturl}{colourEnd}".format(
                    name=jsonres[line]["name"],
                    aliasString=alias,
                    devString=dev,
                    comment=comment,
                    version=jsonres[line]["version"],
                    shorturl=jsonres[line]["shorturl"],
                    purple=PURPLE,
                    darkgreen=DARKGREEN,
                    orange=ORANGE,
                    colourEnd=COLOUREND,
                ),
            )
    except Exception as error:
        await self.sendMessage(channel, f"{name}: {error}")
        traceback.print_exc()


async def compare(self, name, params, channel, userdata, rank):
    try:
        oldVersion, newVersion = params[1], params[2]

        oldJson = await fetch_json(
            "https://bot.notenoughmods.com/" + urlquote(oldVersion) + ".json",
            cache=True,
        )

        newJson = await fetch_json(
            "https://bot.notenoughmods.com/" + urlquote(newVersion) + ".json",
            cache=True,
        )

        newMods = {modInfo["name"].lower(): True for modInfo in newJson}

        missingMods = []

        for modInfo in oldJson:
            old_modName = modInfo["name"].lower()
            if old_modName not in newMods:
                missingMods.append(modInfo["name"])

        path = f"commands/modbot.mca.d3s.co/htdocs/compare/{oldVersion}...{newVersion}.json"
        with open(path, "w") as f:
            f.write(json.dumps(missingMods, sort_keys=True, indent=4 * " "))

        await self.sendMessage(
            channel,
            f"{len(missingMods)} mods died trying to update to {newVersion}",
        )

    except Exception as error:
        await self.sendMessage(channel, f"{name}: {error}")
        traceback.print_exc()


async def about(self, name, params, channel, userdata, rank):
    await self.sendMessage(channel, "Not Enough Mods toolkit for IRC by SinZ & Yoshi2 v4.0")


async def help(self, name, params, channel, userdata, rank):
    if len(params) == 1:
        await self.sendMessage(channel, "{}: Available commands: {}".format(name, ", ".join(help)))
    else:
        command = params[1]
        if command in help:
            for line in help[command]:
                await self.sendMessage(channel, name + ": " + line)
        else:
            await self.sendMessage(channel, name + ": Invalid command provided")


async def force_cacheRedownload(self, name, params, channel, userdata, rank):
    if self.rankconvert[rank] >= 3:
        for ver in versions:
            url = "https://bot.notenoughmods.com/" + urlquote(ver) + ".json"
            normalized = normalize_filename(url)
            filepath = os.path.join(cache_dir, normalized)
            if os.path.exists(filepath):
                cache_last_modified[normalized] = 0

        await self.sendMessage(
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
    "forceredownload": force_cacheRedownload,
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
        "=nem multilist <modName or alias>",
        "Searches the NotEnoughMods database for modName or alias in all MC versions.",
    ],
    "compare": [
        "=nem compare <oldVersion> <newVersion>",
        "Compares the NEMP entries for two different MC versions and says how many mods "
        "haven't been updated to the new version.",
    ],
}
