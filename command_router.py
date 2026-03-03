import asyncio
import importlib.util
import logging
import os
from datetime import datetime
from time import strftime

import task_pool
from ban_list import BanList
from bot_events import MsgEvent, StandardEvent, TimerEvent
from help_system import HelpModule
from irc_logging import LoggingModule
from user_auth import AuthTracker


class CommandRouter:
    def __init__(self, channels, cmdprefix, name, ident, adminlist, loglevel):

        self.LoggingModule = LoggingModule(loglevel)
        self.__CMDHandler_log__ = logging.getLogger("CMDHandler")

        self.name = name
        self.ident = ident
        self.Plugin = self.__LoadModules__("irc_handlers")
        self.commands = self.__LoadModules__("commands")

        self.bot_userlist = adminlist
        self.Bot_Auth = AuthTracker(adminlist)

        self.channels = channels
        self.channelData = {}

        self.topic = {}
        self.cmdprefix = cmdprefix

        self.events = {
            "time": TimerEvent(),
            "chat": MsgEvent(),
            "channeljoin": StandardEvent(),
            "channelpart": StandardEvent(),
            "channelkick": StandardEvent(),
            "userquit": StandardEvent(),
            "nickchange": StandardEvent(),
        }

        self.events["time"].addEvent("LogfileSwitch", 60, self.LoggingModule.__switch_filehandle_daily__)

        self.server = None
        self.latency = None
        self.rankconvert = {"@@": 3, "@": 2, "+": 1, "": 0}
        self.startupTime = datetime.now()

        self.PacketsReceivedBeforeDeath = asyncio.Queue(maxsize=50)

        self.threading = task_pool.TaskPool()
        self.Banlist = BanList("BannedUsers.db")

        self.helper = HelpModule()
        self.auth = None

    async def handle(self, send, prefix, command, params, auth):
        self.send = send

        ## In the next few lines I implement a basic logger so the logs can be put out when the bot dies.
        ## Should come in handy when looking at what or who caused trouble
        ## There is room for 50 entries, number can be increased or lowered at a later point
        try:
            self.PacketsReceivedBeforeDeath.put_nowait(f"{prefix} {command} {params}")
        except asyncio.QueueFull:
            self.PacketsReceivedBeforeDeath.get_nowait()
            self.PacketsReceivedBeforeDeath.put_nowait(f"{prefix} {command} {params}")

        try:
            if command in self.Plugin:
                await self.Plugin[command][0].execute(self, send, prefix, command, params)
            else:
                # 0 is the lowest possible log level. Messages about unimplemented packets are
                # very common, so they will clutter up the file even if logging is set to DEBUG
                self.__CMDHandler_log__.log(0, "Unimplemented Packet: %s", command)
        except KeyError as error:
            self.__CMDHandler_log__.exception("Missing channel or other KeyError caught")
            print("Missing channel or other KeyError caught: " + str(error))

    async def timeEventChecker(self):
        await self.events["time"].tryAllEvents(self)

    def userGetRank(self, channel, username):
        for user in self.channelData[channel]["Userlist"]:
            if user[0].lower() == username.lower():
                return user[1]

    def userGetRankNum(self, channel, username):
        if username in self.bot_userlist and self.Bot_Auth.isRegistered(username):
            return 3
        else:
            for user in self.channelData[channel]["Userlist"]:
                if user[0].lower() == username.lower():
                    if user[1] == "@@":
                        return 2
                    else:
                        return self.rankconvert[user[1]]

            return -1  # No user found

    def retrieveTrueCase(self, channel):
        for chan in self.channelData:
            if chan.lower() == channel.lower():
                return chan
        return False

    # A wrapper for sendChatMessage that does not require a send argument.
    async def sendMessage(self, channel, msg, msgsplitter=None, splitAt=" "):
        await self.sendChatMessage(self.send, channel, msg, msgsplitter, splitAt)

    async def sendChatMessage(self, send, channel, msg, msgsplitter=None, splitAt=" "):
        if msgsplitter is None:
            msgsplitter = self.defaultsplitter

        prefixLen = len(self.name) + len(self.ident) + 63 + 7 + len(channel) + 25
        remaining = 512 - prefixLen

        if len(msg) + prefixLen > 512:
            msgpart = msgsplitter(msg, remaining, splitAt)
            self.__CMDHandler_log__.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await send(f"PRIVMSG {channel} :{part}")
                self.__CMDHandler_log__.debug("Sending parted message to channel/user %s: '%s'", channel, msg)
        else:
            await send(f"PRIVMSG {channel} :{msg}")
            self.__CMDHandler_log__.debug("Sending to channel/user %s: '%s'", channel, msg)

    async def sendNotice(self, destination, msg, msgsplitter=None, splitAt=" "):
        if msgsplitter is None:
            msgsplitter = self.defaultsplitter
        # NOTICE
        prefixLen = len(self.name) + len(self.ident) + 63 + 6 + len(destination) + 25
        remaining = 512 - prefixLen

        if len(msg) + prefixLen > 512:
            msgpart = msgsplitter(msg, remaining, splitAt)
            self.__CMDHandler_log__.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await self.send(f"NOTICE {destination} :{part}")
                self.__CMDHandler_log__.debug("Sending parted notice to channel/user %s: '%s'", destination, msg)
        else:
            await self.send(f"NOTICE {destination} :{msg}")
            self.__CMDHandler_log__.debug("Sending notice to channel/user %s: '%s'", destination, msg)

    def defaultsplitter(self, msg, length, splitAt):

        start = 0
        end = length
        items = []

        while end <= len(msg):
            splitpos = msg[start:end].rfind(splitAt)

            if splitpos < 0:
                items.append(msg[start:end])
                start = end
            else:
                items.append(msg[start : start + splitpos])
                start = start + splitpos + len(splitAt)

            end = start + length

        if start < len(msg):
            items.append(msg[start:])

        for _i in range(items.count("")):
            items.remove("")

        return items

    def writeQueue(self, string, modulename="no_name_given"):
        entryString = "DebugEntry at {} [{!r}]: {!r}".format(strftime("%H:%M:%S (%z)"), modulename, string)
        self.__CMDHandler_log__.debug("Added DebugEntry: '%s'", entryString)
        try:
            self.PacketsReceivedBeforeDeath.put_nowait(entryString)
        except asyncio.QueueFull:
            self.PacketsReceivedBeforeDeath.get_nowait()
            self.PacketsReceivedBeforeDeath.put_nowait(entryString)

    async def joinChannel(self, send, channel):
        if isinstance(channel, str):
            if channel not in self.channelData:
                self.channelData[channel] = {"Userlist": [], "Topic": "", "Mode": ""}
            await send("JOIN " + channel, 5)
            self.__CMDHandler_log__.info("Joining channel: '%s'", channel)

        elif isinstance(channel, list):
            for chan in channel:
                if chan not in self.channelData:
                    self.channelData[chan] = {"Userlist": [], "Topic": "", "Mode": ""}

            await send("JOIN " + ",".join(channel), 3)
            self.__CMDHandler_log__.info("Joining several channels: '%s'", channel)
        else:
            self.__CMDHandler_log__.error(
                "Trying to join a channel, but channel is not list or string: %s [%s]",
                channel,
                type(channel),
            )
            raise TypeError
        print(self.channelData)

    async def whoisUser(self, user):
        await self.send(f"WHOIS {user}")
        self.Bot_Auth.queueUser(user)
        self.__CMDHandler_log__.debug("Sending WHOIS for user '%s'", user)

    def userInSight(self, user):
        print(self.channelData)
        self.__CMDHandler_log__.debug(
            "Checking if user '%s' is in the following channels: %s",
            user,
            self.channelData.keys(),
        )
        for channel in self.channelData:
            for userD in self.channelData[channel]["Userlist"]:
                if user == userD[0]:
                    return True
        return False

    def __ListDir__(self, dir):
        files = os.listdir(dir)
        newlist = []
        self.__CMDHandler_log__.debug("Listing files in directory '%s'", dir)
        for i in files:
            if not i.startswith("__init__") and i.endswith(".py"):
                newlist.append(i)

        return newlist

    @staticmethod
    def _load_source(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def __LoadModules__(self, path):
        ModuleList = self.__ListDir__(path)
        self.__CMDHandler_log__.info("Loading modules in path '%s'...", path)
        Packet = {}
        for i in ModuleList:
            self.__CMDHandler_log__.debug("Loading file %s in path '%s'", i, path)
            module = self._load_source("RenolIRC_" + i[0:-3], path + "/" + i)
            Packet[module.ID] = (module, path + "/" + i)

            try:
                if not callable(module.setup):
                    module.setup = False
                    self.__CMDHandler_log__.log(0, "File %s does not use a setup function", i)
            except AttributeError:
                module.setup = False
                self.__CMDHandler_log__.log(0, "File %s does not use a setup function", i)

            Packet[module.ID] = (module, path + "/" + i)

        print("ALL MODULES LOADED")
        self.__CMDHandler_log__.info("Modules in path '%s' loaded.", path)
        return Packet
