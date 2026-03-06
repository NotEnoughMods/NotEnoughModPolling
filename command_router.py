import asyncio
import importlib.util
import logging
import os
from collections.abc import Callable
from datetime import datetime
from enum import IntEnum
from typing import NamedTuple

import task_pool
from ban_list import BanList
from bot_events import MsgEvent, StandardEvent, TimerEvent
from help_system import HelpModule
from irc_logging import LoggingModule
from user_auth import AuthTracker


def command(name, permission, allow_private=False):
    """Decorator that marks a Plugin method as a bot command."""

    def decorator(func):
        func._command_info = {
            "name": name,
            "permission": permission,
            "allow_private": allow_private,
        }
        return func

    return decorator


def subcommand(group, name, permission=None):
    """Decorator that marks a Plugin method as a subcommand of a command group.

    If permission is None, the group's permission is used.
    """

    def decorator(func):
        func._subcommand_info = {
            "group": group,
            "name": name,
            "permission": permission,
        }
        return func

    return decorator


class Permission(IntEnum):
    """Minimum rank required to use a command.

    Each level corresponds to an IRC rank:

    ========  =====  ========================================
    Name      Value  IRC meaning
    ========  =====  ========================================
    GUEST       0    Anyone
    VOICED      1    ``+`` and above
    OP          2    ``@`` and above
    ADMIN       3    ``@@`` — bot operator (admin list + registered)
    HIDDEN      4    Not shown in command list, restricted access
    ========  =====  ========================================
    """

    GUEST = 0
    VOICED = 1
    OP = 2
    ADMIN = 3
    HIDDEN = 4


class PluginEntry(NamedTuple):
    """Lifecycle record for a loaded plugin module.

    Attributes:
        module: The loaded Python module object.
        path: Filesystem path the module was loaded from.
        command_names: Tuple of command names registered by this plugin.
        setup: ``async setup(router, startup)`` coroutine, or *None*.
        teardown: ``async teardown(router)`` coroutine, or *None*.
        instance: For new-style plugins, the ``Plugin`` class instance.
    """

    module: object
    path: str
    command_names: tuple
    setup: Callable | None
    teardown: Callable | None
    instance: object | None = None


class CommandEntry(NamedTuple):
    """Dispatch record for a single command.

    Attributes:
        execute: Async callable — signature is
            ``(router, name, params, channel, userdata, rank, is_channel)``.
        permission: Minimum :class:`Permission` level required.
        allow_private: If *True* the command works in PMs; if *False*
            (the default) it is silently ignored outside channels.
            ``is_channel`` is always passed to *execute* regardless.
        plugin_id: The ``PLUGIN_ID`` of the owning plugin.
    """

    execute: Callable
    permission: Permission
    allow_private: bool
    plugin_id: str


class HandlerEntry(NamedTuple):
    """Record for a loaded IRC protocol handler module.

    Attributes:
        module: The loaded module (must expose ``ID`` and ``async execute``).
        path: Filesystem path the module was loaded from.
    """

    module: object
    path: str


# Maps IRC user-mode prefixes to Permission values.  "@@" in the channel
# userlist means IRC-op but NOT bot-admin, so it maps to OP (2), not ADMIN.
_RANK_FROM_PREFIX = {
    "@@": Permission.OP,
    "@": Permission.OP,
    "+": Permission.VOICED,
    "": Permission.GUEST,
}


class CommandRouter:
    def __init__(self, channels, cmdprefix, name, ident, adminlist, loglevel):

        self.logging_module = LoggingModule(loglevel)
        self._logger = logging.getLogger("CMDHandler")

        self.name = name
        self.ident = ident
        self.protocol_handlers = self._load_protocol_handlers("irc_handlers")
        self.plugins, self.commands = self._load_plugins("plugins")

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
        """Call teardown() on all plugins that define one."""
        for _plugin_id, plugin in self.plugins.items():
            if plugin.teardown:
                await plugin.teardown(self)

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
                await self.protocol_handlers[command].module.execute(self, send, prefix, command, params)
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
            return Permission.ADMIN
        else:
            for user in self.channel_data[channel]["Userlist"]:
                if user[0].lower() == username.lower():
                    return _RANK_FROM_PREFIX[user[1]]

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

    def add_plugin(self, plugin_id, instance, module, path):
        """Register a new-style Plugin instance. Discovers decorated methods."""
        command_names = []
        group_commands = {}
        subcommands = {}

        for attr_name in dir(instance):
            method = getattr(instance, attr_name, None)
            if method is None:
                continue

            cmd_info = getattr(method, "_command_info", None)
            if cmd_info is not None:
                group_commands[cmd_info["name"]] = (method, cmd_info)

            sub_info = getattr(method, "_subcommand_info", None)
            if sub_info is not None:
                group = sub_info["group"]
                subcommands.setdefault(group, {})[sub_info["name"]] = (
                    method,
                    sub_info["permission"],
                )

        for cmd_name, (method, cmd_info) in group_commands.items():
            subs = subcommands.get(cmd_name)
            execute = self._make_group_dispatch(method, subs, cmd_info["permission"]) if subs else method

            self.commands[cmd_name] = CommandEntry(
                execute=execute,
                permission=cmd_info["permission"],
                allow_private=cmd_info.get("allow_private", False),
                plugin_id=plugin_id,
            )
            command_names.append(cmd_name)

        setup_fn = getattr(instance, "setup", None)
        teardown_fn = getattr(instance, "teardown", None)

        self.plugins[plugin_id] = PluginEntry(
            module=module,
            path=path,
            command_names=tuple(command_names),
            setup=setup_fn,
            teardown=teardown_fn,
            instance=instance,
        )

    def _make_group_dispatch(self, fallback, subcommands, group_permission):
        """Create an auto-dispatch function for a command group."""

        async def dispatch(router, name, params, channel, userdata, rank, is_channel):
            if params:
                sub_name = params[0].lower()
                if sub_name in subcommands:
                    method, sub_perm = subcommands[sub_name]
                    required = sub_perm if sub_perm is not None else group_permission
                    if rank >= required:
                        await method(router, name, params, channel, userdata, rank)
                    else:
                        await router.send_message(channel, "You're not authorized to use this command.")
                    return
            await fallback(router, name, params, channel, userdata, rank, is_channel)

        return dispatch

    def remove_plugin(self, plugin_id):
        """Unregister a plugin and all its commands."""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return
        for name in plugin.command_names:
            self.commands.pop(name, None)
        del self.plugins[plugin_id]

    def _load_plugins(self, path):
        """Load all plugin modules from *path*.

        Each plugin module must define ``PLUGIN_ID`` (str).

        **New-style** plugins define a ``Plugin`` class with ``@command``
        and ``@subcommand`` decorated methods.  **Old-style** plugins
        define a ``COMMANDS`` dict mapping command names to dicts with
        keys ``execute``, ``permission``, and optionally ``allow_private``.

        A module may optionally define ``async setup(router, startup)``
        and/or ``async teardown(router)`` for lifecycle hooks (old-style),
        or the ``Plugin`` class may define those methods (new-style).

        Returns:
            ``(plugins_dict, commands_dict)`` — *plugins_dict* maps plugin
            IDs to :class:`PluginEntry`; *commands_dict* maps command names
            to :class:`CommandEntry`.
        """
        file_list = self._list_dir(path)
        self._logger.info("Loading plugins in path '%s'...", path)

        # add_plugin() writes directly to self.plugins / self.commands,
        # so we initialize them here and return them at the end.
        self.plugins = {}
        self.commands = {}

        for filename in file_list:
            filepath = path + "/" + filename
            self._logger.debug("Loading file %s in path '%s'", filename, path)
            module = self._load_source("NEMP_" + filename[:-3], filepath)

            plugin_id = module.PLUGIN_ID
            plugin_cls = getattr(module, "Plugin", None)

            if plugin_cls is not None:
                instance = plugin_cls()
                self.add_plugin(plugin_id, instance, module, filepath)
            else:
                commands_dict = module.COMMANDS

                setup_fn = getattr(module, "setup", None)
                if setup_fn is not None and not callable(setup_fn):
                    setup_fn = None

                teardown_fn = getattr(module, "teardown", None)
                if teardown_fn is not None and not callable(teardown_fn):
                    teardown_fn = None

                command_names = []
                for cmd_name, cmd_info in commands_dict.items():
                    entry = CommandEntry(
                        execute=cmd_info["execute"],
                        permission=cmd_info["permission"],
                        allow_private=cmd_info.get("allow_private", False),
                        plugin_id=plugin_id,
                    )
                    self.commands[cmd_name] = entry
                    command_names.append(cmd_name)

                self.plugins[plugin_id] = PluginEntry(
                    module=module,
                    path=filepath,
                    command_names=tuple(command_names),
                    setup=setup_fn,
                    teardown=teardown_fn,
                )

        self._logger.info("Plugins in path '%s' loaded.", path)
        return self.plugins, self.commands

    def _load_protocol_handlers(self, path):
        """Load IRC protocol handler modules from *path*.

        Each handler module must define ``ID`` (the IRC command/numeric it
        handles) and ``async execute(router, send, prefix, command, params)``.

        Returns:
            A dict mapping IRC commands to :class:`HandlerEntry`.
        """
        file_list = self._list_dir(path)
        self._logger.info("Loading protocol handlers in path '%s'...", path)

        handlers = {}
        for filename in file_list:
            filepath = path + "/" + filename
            self._logger.debug("Loading file %s in path '%s'", filename, path)
            module = self._load_source("NEMP_" + filename[:-3], filepath)
            handlers[module.ID] = HandlerEntry(module=module, path=filepath)

        self._logger.info("Protocol handlers in path '%s' loaded.", path)
        return handlers
