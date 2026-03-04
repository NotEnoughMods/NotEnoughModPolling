import asyncio
import importlib.util
import logging
import os
from datetime import datetime

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
        self.protocol_handlers = self._load_modules("irc_handlers")
        self.commands = self._load_modules("commands")

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

        self.events["time"].add_event("LogfileSwitch", 60, self.logging_module._switch_filehandle_daily)

        self.server = None
        self.latency = None
        self.rank_values = {"@@": 3, "@": 2, "+": 1, "": 0}
        self.startup_time = datetime.now()

        self.recent_messages = asyncio.Queue(maxsize=50)

        self._waiters = []  # list of (event, check, future)
        self._handler_lock = asyncio.Lock()

        self.task_pool = task_pool.TaskPool()
        if os.path.exists("BannedUsers.db") and not os.path.exists("banned_users.db"):
            os.rename("BannedUsers.db", "banned_users.db")
        self.ban_list = BanList("banned_users.db")

        self.helper = HelpModule()
        self.auth = None

    async def close(self):
        """Call teardown() on all command modules that define one."""
        for cmd in self.commands:
            if self.commands[cmd][0].teardown:
                await self.commands[cmd][0].teardown(self)

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
        except KeyError:
            self._logger.exception("Missing channel or other KeyError caught")

    async def wait_for(self, event, check=None, timeout=None):
        """Wait for an IRC event matching the predicate.

        Args:
            event: IRC command/numeric to wait for (e.g. "318", "PRIVMSG")
            check: Optional callable(prefix, command, params) -> bool
            timeout: Seconds before TimeoutError (None = wait forever)

        Returns:
            Tuple of (prefix, command, params) from the matching event.
        """
        future = asyncio.get_event_loop().create_future()
        entry = (event, check, future)
        self._waiters.append(entry)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            if entry in self._waiters:
                self._waiters.remove(entry)

    def _dispatch_waiters(self, prefix, command, params):
        """Resolve any futures waiting for this event. Non-blocking."""
        for entry in self._waiters[:]:
            event, check, future = entry
            if event == command and not future.done() and (check is None or check(prefix, command, params)):
                future.set_result((prefix, command, params))

    async def check_timer_events(self):
        await self.events["time"].run_all_events(self)

    def get_user_rank(self, channel, username):
        for user in self.channel_data[channel]["Userlist"]:
            if user[0].lower() == username.lower():
                return user[1]

    def get_user_rank_num(self, channel, username):
        if username in self.operators and self.auth_tracker.is_registered(username):
            return 3
        else:
            for user in self.channel_data[channel]["Userlist"]:
                if user[0].lower() == username.lower():
                    if user[1] == "@@":
                        return 2
                    else:
                        return self.rank_values[user[1]]

            return -1  # No user found

    def get_channel_true_case(self, channel):
        for chan in self.channel_data:
            if chan.lower() == channel.lower():
                return chan
        return False

    # A wrapper for send_chat_message that does not require a send argument.
    async def send_message(self, channel, msg, msgsplitter=None, split_at=" "):
        await self.send_chat_message(self.send, channel, msg, msgsplitter, split_at)

    async def send_chat_message(self, send, channel, msg, msgsplitter=None, split_at=" "):
        if msgsplitter is None:
            msgsplitter = self.default_splitter

        prefix_len = len(self.name) + len(self.ident) + 63 + 7 + len(channel) + 25
        remaining = 512 - prefix_len

        if len(msg) + prefix_len > 512:
            msgpart = msgsplitter(msg, remaining, split_at)
            self._logger.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await send(f"PRIVMSG {channel} :{part}")
                self._logger.debug("Sending parted message to channel/user %s: '%s'", channel, msg)
        else:
            await send(f"PRIVMSG {channel} :{msg}")
            self._logger.debug("Sending to channel/user %s: '%s'", channel, msg)

    async def send_notice(self, destination, msg, msgsplitter=None, split_at=" "):
        if msgsplitter is None:
            msgsplitter = self.default_splitter
        # NOTICE
        prefix_len = len(self.name) + len(self.ident) + 63 + 6 + len(destination) + 25
        remaining = 512 - prefix_len

        if len(msg) + prefix_len > 512:
            msgpart = msgsplitter(msg, remaining, split_at)
            self._logger.debug("Breaking message %s into parts %s", msg, msgpart)

            for part in msgpart:
                await self.send(f"NOTICE {destination} :{part}")
                self._logger.debug("Sending parted notice to channel/user %s: '%s'", destination, msg)
        else:
            await self.send(f"NOTICE {destination} :{msg}")
            self._logger.debug("Sending notice to channel/user %s: '%s'", destination, msg)

    def default_splitter(self, msg, length, split_at):

        start = 0
        end = length
        items = []

        while end <= len(msg):
            splitpos = msg[start:end].rfind(split_at)

            if splitpos < 0:
                items.append(msg[start:end])
                start = end
            else:
                items.append(msg[start : start + splitpos])
                start = start + splitpos + len(split_at)

            end = start + length

        if start < len(msg):
            items.append(msg[start:])

        for _i in range(items.count("")):
            items.remove("")

        return items

    async def join_channel(self, send, channel):
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
        self._logger.debug("channel_data after join: %s", self.channel_data)

    async def whois_user(self, user):
        """Send WHOIS and wait for the response. Returns True if user is a registered operator."""
        await self.send(f"WHOIS {user}")
        self._logger.debug("Sending WHOIS for user '%s'", user)

        registered_as = None

        def on_account(prefix, command, params):
            nonlocal registered_as
            if user.lower() not in params.lower():
                return False
            fields = params.split(":")
            if fields[1].strip() == "is logged in as":
                names = fields[0].split()
                registered_as = names[2]
            return True

        # Listen for 330 (account info) — may or may not arrive depending on registration
        account_entry = ("330", on_account, asyncio.get_event_loop().create_future())
        self._waiters.append(account_entry)

        try:
            await self.wait_for(
                "318",
                check=lambda prefix, command, params: user.lower() in params.lower(),
                timeout=10,
            )
        except TimeoutError:
            self._logger.warning("WHOIS timeout for user: %s", user)
            return False
        finally:
            if account_entry in self._waiters:
                self._waiters.remove(account_entry)

        if registered_as and self.auth_tracker.user_exists(registered_as):
            self.auth_tracker.register_user(user)
            return True
        else:
            self.auth_tracker.unregister_user(user)
            return False

    def is_user_visible(self, user):
        self._logger.debug("channel_data: %s", self.channel_data)
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

    def _list_dir(self, dir):
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

    def _load_modules(self, path):
        ModuleList = self._list_dir(path)
        self._logger.info("Loading modules in path '%s'...", path)
        Packet = {}
        for i in ModuleList:
            self._logger.debug("Loading file %s in path '%s'", i, path)
            module = self._load_source("NEMP_" + i[0:-3], path + "/" + i)
            Packet[module.ID] = (module, path + "/" + i)

            try:
                if not callable(module.setup):
                    module.setup = False
                    self._logger.log(0, "File %s does not use a setup function", i)
            except AttributeError:
                module.setup = False
                self._logger.log(0, "File %s does not use a setup function", i)

            try:
                if not callable(module.teardown):
                    module.teardown = False
            except AttributeError:
                module.teardown = False

            Packet[module.ID] = (module, path + "/" + i)

        self._logger.info("Modules in path '%s' loaded.", path)
        return Packet
