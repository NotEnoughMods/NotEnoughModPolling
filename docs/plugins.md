# Plugin Development Guide

Plugins are Python files in the `plugins/` directory. They are loaded automatically at startup by `CommandRouter._load_plugins()` using `importlib`. Every plugin must define a module-level `PLUGIN_ID` string constant.

Two plugin styles exist. **New-style** (class-based with decorators) is preferred for new plugins.

## New-style plugins (class-based)

Define a `Plugin` class. Use `@command` and `@subcommand` decorators from `command_router` to register commands.

```python
import logging

from command_router import Permission, command, subcommand

PLUGIN_ID = "greet"

logger = logging.getLogger("cmd.greet")


class Plugin:
    def __init__(self):
        self.greet_count = 0

    async def setup(self, router, startup):
        """Called after loading. startup=True on first load, False on reload."""
        entry = router.helper.new_help("greet")
        entry.add_description("Greets you by name.")
        entry.add_argument("style", "Greeting style: 'loud' for uppercase.", optional=True)
        entry.rank = Permission.GUEST
        router.helper.register_help(entry, overwrite=True)

    async def teardown(self, router):
        """Called before unload/reload and on shutdown."""
        router.helper.unregister_help("greet")

    @command("greet", permission=Permission.GUEST, allow_private=True)
    async def greet(self, router, name, params, channel, userdata, rank, is_channel):
        """Fallback: runs when no subcommand matches, or no args given."""
        self.greet_count += 1
        await router.send_message(channel, f"Hello, {name}! (#{self.greet_count})")

    @subcommand("greet", "loud", permission=Permission.VOICED)
    async def cmd_loud(self, router, name, params, channel, userdata, rank):
        """Runs when user types: =greet loud"""
        await router.send_message(channel, f"HELLO, {name.upper()}!")
```

### How it works

The decorators attach metadata to methods (`_command_info`, `_subcommand_info`). When `CommandRouter.add_plugin()` discovers a `Plugin` class, it:

1. Instantiates the class.
2. Scans all methods for decorator metadata.
3. For commands with subcommands, creates an auto-dispatch wrapper that checks the first argument against registered subcommands, verifies permission, and routes accordingly. If no subcommand matches, the `@command` method is called as a fallback.

### Command method signature

```python
@command("name", permission=Permission.GUEST, allow_private=False)
async def name(self, router, name, params, channel, userdata, rank, is_channel):
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `router` | `CommandRouter` | The bot's command router (use for sending messages, accessing services) |
| `name` | `str` | The IRC nick of the user who invoked the command |
| `params` | `list[str]` | Remaining arguments after the command name |
| `channel` | `str` | Channel name, or nick if it's a private message |
| `userdata` | `tuple` | `(ident, host)` of the user |
| `rank` | `int` | User's permission level in the current channel |
| `is_channel` | `bool` | `True` if sent to a channel, `False` if PM |

### Subcommand method signature

```python
@subcommand("group", "subname", permission=None)
async def cmd_subname(self, router, name, params, channel, userdata, rank):
```

Note: subcommands do **not** receive `is_channel`. If `permission=None`, the parent command's permission is used.

Important: `params` passed to subcommand handlers still includes the subcommand name at `params[0]`. User arguments start at `params[1]`.

## Old-style plugins (function-based)

Define a module-level `COMMANDS` dict mapping command names to config dicts. Command functions are standalone async functions (not methods).

```python
from command_router import Permission

PLUGIN_ID = "say"


async def _say(router, name, params, channel, userdata, rank, is_channel):
    await router.send_chat_message(router.send, channel, " ".join(params))


COMMANDS = {
    "say": {"execute": _say, "permission": Permission.HIDDEN},
}
```

The `COMMANDS` dict entries support these keys:

| Key | Required | Description |
|-----|----------|-------------|
| `execute` | yes | Async callable with the command signature |
| `permission` | yes | `Permission` enum value |
| `allow_private` | no | `bool`, default `False` — whether the command works in PMs |

Old-style plugins can also define module-level `setup(router, startup)` and `teardown(router)` async functions.

## Lifecycle hooks

### `setup(router, startup)`

Called after the plugin is loaded. The `startup` parameter is `True` on the initial load (after IRC MOTD) and `False` when the plugin is reloaded via `=reload`.

Common uses:
- Register help entries (`router.helper`)
- Register events (`router.events`)
- Initialize external resources (aiohttp sessions, database connections)

### `teardown(router)`

Called before the plugin is unloaded/reloaded and during bot shutdown (`CommandRouter.close()`).

Common uses:
- Unregister events
- Close aiohttp sessions or other resources

## Permissions

The `Permission` enum is defined in `command_router.py`:

```python
class Permission(IntEnum):
    GUEST = 0     # Anyone
    VOICED = 1    # + and above
    OP = 2        # @ and above
    ADMIN = 3     # Bot operator (admin list + registered)
    HIDDEN = 4    # Not shown in command list
```

When a user invokes a command, the PRIVMSG handler checks `rank >= cmd.permission`. The user's rank is determined by their channel mode (`+`, `@`) or admin status.

## Events

Plugins can register event callbacks via `router.events`. Available event types:

| Key | Class | Description |
|-----|-------|-------------|
| `"time"` | `TimerEvent` | Fires periodically at a configurable interval |
| `"chat"` | `MsgEvent` | Fires on every channel message |
| `"channeljoin"` | `StandardEvent` | Fires when a user joins a channel |
| `"channelpart"` | `StandardEvent` | Fires when a user parts a channel |
| `"channelkick"` | `StandardEvent` | Fires when a user is kicked |
| `"userquit"` | `StandardEvent` | Fires when a user quits |
| `"nickchange"` | `StandardEvent` | Fires on nick changes |

### Timer events

```python
async def _my_timer(router, channels):
    for channel in channels:
        await router.send_message(channel, "Tick!")

# In setup() or a command handler:
router.events["time"].add_event("MyTimer", 60, _my_timer, ["#mychannel"])
```

`add_event(name, interval, function, channel=None, from_event=False)`

- `name`: Unique event identifier.
- `interval`: Seconds between firings.
- `function`: `async def callback(router, channels)`.
- `channel`: List of channels passed to the callback.
- `from_event`: Used for debug logging only. When called from within an event callback, deferral happens automatically (the event system sets an internal flag during iteration).

### Chat events

```python
async def _on_chat(router, channels, userdata, message, channel):
    if "hello" in message.lower():
        await router.send_message(channel, "Hi there!")

router.events["chat"].add_event("Greeter", _on_chat, channel=[])
```

`add_event(name, function, channel=None, from_event=False)`

Chat event callbacks receive: `(router, channels, userdata, message, channel)`.

Note: `userdata` in chat event callbacks is a `dict` with keys `name`, `ident`, `host` — unlike command handlers where it is a `tuple` of `(ident, host)`.

### Event management

```python
router.events["time"].event_exists("MyTimer")       # bool
router.events["time"].remove_event("MyTimer")
router.events["time"].add_channel("MyTimer", "#new")
router.events["time"].remove_channel("MyTimer", "#old")
router.events["time"].get_channels("MyTimer")
```

When adding or removing events from within an event callback, operations are automatically deferred until the current event cycle completes. The `from_event` parameter on `add_event()`/`remove_event()` is for debug logging only.

## Help system

Register help entries in `setup()` so users can run `=help <command>`:

```python
async def setup(router, startup):
    entry = router.helper.new_help("mycommand")
    entry.add_description("Does something useful.")
    entry.add_description("Supports multiple description lines.")
    entry.add_argument("target", "The target to act on.")
    entry.add_argument("mode", "Processing mode.", optional=True)
    entry.rank = Permission.GUEST
    router.helper.register_help(entry, overwrite=True)
```

- `add_description(text)` — appends a description line.
- `add_argument(name, description, optional=False)` — adds a named argument.
- `rank` — minimum permission level to view this help entry.
- `register_help(entry, overwrite=False)` — registers the entry; `overwrite=True` replaces on reload.

Unregister in `teardown()` with `router.helper.unregister_help("mycommand")`.

## Background tasks

The `TaskPool` lets plugins run long-lived background tasks with bidirectional communication:

```python
async def _my_worker(handle, pipe):
    """Runs as an asyncio.Task. Communicate via the pipe (asyncio.Queue)."""
    while handle.running:
        msg = await pipe.get()
        if msg.get("action") == "stop":
            break
        # Do work...
        await pipe.put({"result": "done"})

# Start the task:
router.task_pool.add_task("myWorker", _my_worker)

# From a timer event, poll for results:
if router.task_pool.poll("myWorker"):
    result = await router.task_pool.recv("myWorker")

# Send data to the task:
await router.task_pool.send("myWorker", {"action": "stop"})

# Cancel:
router.task_pool.cancel_task("myWorker")
```

## Sending messages

The `CommandRouter` provides several messaging methods:

```python
# Simple message to a channel or user
await router.send_message(channel, "Hello!")

# Message with IRC line-length handling (auto-splits at 512 bytes)
await router.send_chat_message(router.send, channel, long_message)

# NOTICE (typically used for private bot responses)
await router.send_notice(name, "You are not authorized.")
```

## Accessing bot services

Through the `router` parameter, plugins can access:

| Attribute | Description |
|-----------|-------------|
| `router.send` | Low-level `send_msg(msg, priority)` function |
| `router.events` | Event registries (dict of event types) |
| `router.ban_list` | SQLite-backed ban system (`BanList` instance) |
| `router.helper` | Help system (`HelpModule` instance) |
| `router.task_pool` | Background task manager (`TaskPool` instance) |
| `router.channels` | List of joined channels |
| `router.cmdprefix` | Command prefix string (e.g. `"="`) |
| `router.operators` | Admin user list |
| `router.auth_tracker` | User auth/registration tracker |
| `router.latency` | Current server latency |
| `router.startup_time` | Bot startup `datetime` |

## IRC handler modules

IRC protocol handlers live in `irc_handlers/`. Each is a module with:

- `ID` — the IRC command or numeric this handles (e.g. `"PRIVMSG"`, `"376"`, `"PING"`).
- `async def execute(self, send_msg, prefix, command, params)` — where `self` is the `CommandRouter`.

Naming convention: `rpl_endofmotd_376.py`, `err_nicknameinuse_433.py`, `privmsg.py`, `ping.py`.

These are loaded by `CommandRouter._load_protocol_handlers()` and dispatched in `handle()`.
