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

        self.logging_module = LoggingModule(loglevel)
        self._logger = logging.getLogger("CMDHandler")

        self.name = name
        self.ident = ident
        self.protocol_handlers = self.__LoadModules__("irc_handlers")
        self.commands = self.__LoadModules__("commands")

        self.operators = adminlist
        self.auth_tracker = AuthTracker(adminlist)

        self.channels = channels
        self.channel_data = {}

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

        self.events["time"].addEvent("LogfileSwitch", 60, self.logging_module.__switch_filehandle_daily__)

        self.server = None
        self.latency = None
        self.rank_values = {"@@": 3, "@": 2, "+": 1, "": 0}
        self.startupTime = datetime.now()

        self.recent_messages = asyncio.Queue(maxsize=50)

        self.task_pool = task_pool.TaskPool()
        self.ban_list = BanList("BannedUsers.db")

        self.helper = HelpModule()
        self.auth = None

    async def handle(self, send, prefix, command, params, auth):
        self.send = send

        ## In the next few lines I implement a basic logger so the logs can be put out when the bot dies.
        ## Should come in handy when looking at what or who caused trouble
        ## There is room for 50 entries, number can be increased or lowered at a later point
        try:
            self.recent_messages.put_nowait(f"{prefix} {command} {params}")
        except asyncio.QueueFull:
            self.recent_messages.get_nowait()
            self.recent_messages.put_nowait(f"{prefix} {command} {params}")

        try:
            if command in self.protocol_handlers:
                await self.protocol_handlers[command][0].execute(self, send, prefix, command, params)
            else:
                # 0 is the lowest possible log level. Messages about unimplemented packets are
                # very common, so they will clutter up the file even if logging is set to DEBUG
                self._logger.log(0, "Unimplemented Packet: %s", command)
        except KeyError as error:
            self._logger.exception("Missing channel or other KeyError caught")
            print("Missing channel or other KeyError caught: " + str(error))

    async def timeEventChecker(self):
        await self.events["time"].tryAllEvents(self)

    def userGetRank(self, channel, username):
        for user in self.channel_data[channel]["Userlist"]:
            if user[0].lower() == username.lower():
                return user[1]

    def userGetRankNum(self, channel, username):
        if username in self.operators and self.auth_tracker.isRegistered(username):
            return 3
        else:
            for user in self.channel_data[channel]["Userlist"]:
                if user[0].lower() == username.lower():
                    if user[1] == "@@":
                        return 2
                    else:
                        return self.rank_values[user[1]]

            return -1  # No user found

    def retrieveTrueCase(self, channel):
        for chan in self.channel_data:
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
            self._logger.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await send(f"PRIVMSG {channel} :{part}")
                self._logger.debug("Sending parted message to channel/user %s: '%s'", channel, msg)
        else:
            await send(f"PRIVMSG {channel} :{msg}")
            self._logger.debug("Sending to channel/user %s: '%s'", channel, msg)

    async def sendNotice(self, destination, msg, msgsplitter=None, splitAt=" "):
        if msgsplitter is None:
            msgsplitter = self.defaultsplitter
        # NOTICE
        prefixLen = len(self.name) + len(self.ident) + 63 + 6 + len(destination) + 25
        remaining = 512 - prefixLen

        if len(msg) + prefixLen > 512:
            msgpart = msgsplitter(msg, remaining, splitAt)
            self._logger.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await self.send(f"NOTICE {destination} :{part}")
                self._logger.debug("Sending parted notice to channel/user %s: '%s'", destination, msg)
        else:
            await self.send(f"NOTICE {destination} :{msg}")
            self._logger.debug("Sending notice to channel/user %s: '%s'", destination, msg)

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
        self._logger.debug("Added DebugEntry: '%s'", entryString)
        try:
            self.recent_messages.put_nowait(entryString)
        except asyncio.QueueFull:
            self.recent_messages.get_nowait()
            self.recent_messages.put_nowait(entryString)

    async def joinChannel(self, send, channel):
        if isinstance(channel, str):
            if channel not in self.channel_data:
                self.channel_data[channel] = {"Userlist": [], "Topic": "", "Mode": ""}
            await send("JOIN " + channel, 5)
            self._logger.info("Joining channel: '%s'", channel)

        elif isinstance(channel, list):
            for chan in channel:
                if chan not in self.channel_data:
                    self.channel_data[chan] = {"Userlist": [], "Topic": "", "Mode": ""}

            await send("JOIN " + ",".join(channel), 3)
            self._logger.info("Joining several channels: '%s'", channel)
        else:
            self._logger.error(
                "Trying to join a channel, but channel is not list or string: %s [%s]",
                channel,
                type(channel),
            )
            raise TypeError
        print(self.channel_data)

    async def whoisUser(self, user):
        await self.send(f"WHOIS {user}")
        self.auth_tracker.queueUser(user)
        self._logger.debug("Sending WHOIS for user '%s'", user)

    def userInSight(self, user):
        print(self.channel_data)
        self._logger.debug(
            "Checking if user '%s' is in the following channels: %s",
            user,
            self.channel_data.keys(),
        )
        for channel in self.channel_data:
            for userD in self.channel_data[channel]["Userlist"]:
                if user == userD[0]:
                    return True
        return False

    def __ListDir__(self, dir):
        files = os.listdir(dir)
        newlist = []
        self._logger.debug("Listing files in directory '%s'", dir)
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
        self._logger.info("Loading modules in path '%s'...", path)
        Packet = {}
        for i in ModuleList:
            self._logger.debug("Loading file %s in path '%s'", i, path)
            module = self._load_source("RenolIRC_" + i[0:-3], path + "/" + i)
            Packet[module.ID] = (module, path + "/" + i)

            try:
                if not callable(module.setup):
                    module.setup = False
                    self._logger.log(0, "File %s does not use a setup function", i)
            except AttributeError:
                module.setup = False
                self._logger.log(0, "File %s does not use a setup function", i)

            Packet[module.ID] = (module, path + "/" + i)

        print("ALL MODULES LOADED")
        self._logger.info("Modules in path '%s' loaded.", path)
        return Packet
