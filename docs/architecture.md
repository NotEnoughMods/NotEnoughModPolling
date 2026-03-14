# Architecture Overview

This document describes the internal architecture of the NotEnoughModPolling IRC bot: how it connects to IRC, dispatches messages, routes commands, manages events, and polls for mod updates.

## High-level flow

```
asyncio.run(async_main())
  └─ IrcBot.start()
       ├─ IrcConnection.connect()        # TCP connection
       ├─ NICK/USER registration         # IRC handshake
       ├─ background: write_loop()       # Rate-limited outbound queue
       ├─ background: _timer_loop()      # 0.5s tick for timer events
       └─ main loop: read_lines()        # Process inbound IRC messages
            ├─ _dispatch_waiters()        # Resolve any wait_for() futures
            ├─ PING → PONG (inline)       # Fast path, no lock
            └─ everything else → handle() # Serialized via asyncio.Lock
```

## Entry point (`irc_bot.py`)

`async_main()` is the top-level function called by `asyncio.run()`. It:

1. Registers signal handlers for `SIGTERM` and `SIGINT`.
2. Loads configuration from `config.yml` via the `Configuration` class.
3. Enters a reconnection loop that creates an `IrcBot` and calls `start()`.
4. On disconnection (`ConnectionDown`, `OSError`, `TimeoutError`), waits with exponential backoff (5s to 300s max) before reconnecting.
5. On `asyncio.CancelledError` (from signal), exits cleanly.

### `IrcBot.start()`

1. **Connect**: Creates an `IrcConnection` and opens a TCP socket.
2. **Register**: Sends `PASS`, `NICK`, and `USER` to identify with the server.
3. **Start background tasks**: The connection's `write_loop()` (rate-limited sends) and a `_timer_loop()` (checks timer events every 0.5s).
4. **Create CommandRouter**: Initializes the command router, which loads all plugins and IRC handlers.
5. **Main loop**: Iterates over `conn.read_lines()` (an async generator). For each message:
   - Parses it into `(prefix, command, params)`.
   - Dispatches any `wait_for()` futures matching the command.
   - PING is handled inline (no serialization needed).
   - All other commands are dispatched via `_locked_handle()`, which acquires `CommandRouter._handler_lock` to serialize handler execution.
6. **Cleanup**: On exit (EOF, error, or shutdown), cancels background tasks, calls `router.close()` (which runs all plugin teardowns), flushes the write queue, and closes the connection.

## Connection layer (`irc_connection.py`)

`IrcConnection` manages the raw TCP socket via `asyncio.open_connection()`.

### Reading

`read_lines()` is an async generator. It reads 4096-byte chunks from the socket, buffers partial lines, and yields complete lines decoded as UTF-8 (with `errors="replace"`).

### Writing

Outbound messages go through an `asyncio.Queue`. The `write_loop()` coroutine drains this queue with rate limiting:

- Messages over 250 bytes: 3-second delay after sending.
- Messages under 250 bytes: 2-second delay after sending.

`send_msg(msg, priority)` strips CR/LF, appends `\r\n`, and puts the message on the queue. The `priority` parameter is accepted but not currently used for ordering.

### Reconnection

If `read_lines()` receives empty data (EOF) or an error occurs, the main loop in `IrcBot.start()` exits and raises `ConnectionDown`, triggering the reconnection logic in `async_main()`.

## Message dispatch (`command_router.py`)

`CommandRouter` is the central hub. It holds all loaded plugins, commands, IRC handlers, events, and bot services.

### Initialization

On construction, `CommandRouter`:

1. Sets up logging via `LoggingModule`.
2. Loads IRC protocol handlers from `irc_handlers/`.
3. Loads plugins from `plugins/`.
4. Initializes the event system (timer, chat, channel join/part/kick, quit, nick change).
5. Creates the `BanList`, `HelpModule`, `AuthTracker`, and `TaskPool` instances.

### `handle(send, prefix, command, params, auth)`

The main dispatch method, called for every incoming IRC message (except PING):

1. Stores a reference to `send` for plugins to use.
2. Logs the message to a bounded queue (50 entries, oldest evicted when full).
3. Looks up `command` in `self.protocol_handlers`.
4. If found, calls `handler.module.execute(self, send, prefix, command, params)`.
5. If not found, logs it as an unimplemented packet.

All calls to `handle()` are serialized by `_handler_lock` (`asyncio.Lock`) to prevent concurrent handler execution.

### IRC handlers (`irc_handlers/`)

Each handler is a Python module with:

- `ID`: A string identifying the IRC command or numeric (e.g., `"PRIVMSG"`, `"376"`, `"PING"`).
- `execute(self, send_msg, prefix, command, params)`: An async function where `self` is the `CommandRouter`.

Handlers are loaded at startup by `_load_protocol_handlers()`, which uses `importlib` to import each `.py` file and indexes them by `ID`.

**Key handlers:**

| Handler | Trigger | What it does |
|---------|---------|--------------|
| `privmsg.py` | `PRIVMSG` | Parses user messages, checks for commands, dispatches to plugins, runs chat events |
| `rpl_endofmotd_376.py` | `376` | Joins channels, waits for NAME replies, runs all plugin `setup()` functions |
| `rpl_namreply_353.py` | `353` | Populates channel user lists with mode prefixes |
| `join.py` / `part.py` / `kick.py` | `JOIN`/`PART`/`KICK` | Updates channel data, fires channel events |
| `nick.py` / `quit.py` | `NICK`/`QUIT` | Updates user tracking, fires events |
| `mode.py` | `MODE` | Updates user modes in channel data |

### Command dispatch (inside `privmsg.py`)

When a PRIVMSG arrives:

1. Parse the prefix into `(nick, ident, host)`.
2. Determine if the target is a channel (`is_channel`) or a PM.
3. Look up the user's rank from channel data.
4. If the message starts with the command prefix (e.g. `=`):
   - Look up the command in `router.commands`.
   - Check the ban list.
   - Verify `allow_private` for PMs.
   - Verify `rank >= cmd.permission`.
   - Call `cmd.execute(router, nick, params, channel, userdata, rank, is_channel)`.
5. Otherwise, pass the message to all registered chat events via `router.events["chat"].run_all_events()`.

## Event system (`bot_events.py`)

Three event classes with inheritance: `StandardEvent` (base) -> `TimerEvent`, `MsgEvent`.

### `StandardEvent`

Base class for all events. Stores events in a dict keyed by name. Each event has a callback function and a channel list.

Key behavior:
- **Deferred operations**: When `from_event=True`, add/remove operations are queued in `operation_queue` and executed after the current event cycle completes. This prevents modifying the event dict while iterating.
- **Performance tracking**: Each event tracks execution time stats (average, min, max) in `event_stats`.

### `TimerEvent`

Extends `StandardEvent` with an interval (in seconds). `run_all_events()` checks each event: if enough time has elapsed since the last execution, the callback fires. The timer loop in `IrcBot` calls this every 0.5 seconds.

Callback signature: `async def callback(router, channels)`

### `MsgEvent`

Extends `StandardEvent` for chat messages. `run_all_events()` passes extra arguments to callbacks.

Callback signature: `async def callback(router, channels, userdata, message, channel)`

### Available event types

Registered in `CommandRouter.__init__()`:

```python
self.events = {
    "time": TimerEvent(),         # Periodic timers
    "chat": MsgEvent(),           # Channel messages
    "channeljoin": StandardEvent(),
    "channelpart": StandardEvent(),
    "channelkick": StandardEvent(),
    "userquit": StandardEvent(),
    "nickchange": StandardEvent(),
}
```

## Plugin system

Plugins are loaded from `plugins/` by `_load_plugins()`. See [docs/plugins.md](plugins.md) for the full development guide.

### Loading sequence

1. List all `.py` files in `plugins/` (excluding `__init__.py`).
2. For each file, import it via `importlib.util.spec_from_file_location()`.
3. Read `PLUGIN_ID` from the module.
4. If the module defines a `Plugin` class (new-style): instantiate it and call `add_plugin()`, which scans for `@command`/`@subcommand` decorators.
5. Otherwise (old-style): read the `COMMANDS` dict and register each command.
6. Record `setup`/`teardown` functions (module-level or instance methods).

### Setup sequence

After the IRC handshake completes (MOTD received, channels joined), the `rpl_endofmotd_376` handler creates an `asyncio.Task` that calls `setup(router, True)` on every plugin that defines it.

On reload (`=reload plugin`), `teardown()` is called on the old instance, the module is reimported, and `setup(router, False)` is called on the new instance.

## Mod polling subsystem (`mod_polling/`)

The `ModPoller` class (in `poller.py`) is the polling engine. It is instantiated by the `nemp` plugin during `setup()`.

### Configuration

- `mod_polling/config.yml` — GitHub API credentials, polling interval, auto-start, staff channel.
- `mod_polling/mods.json` — Registry of ~100+ mods, each specifying a parser and its config.
- `mod_polling/mc_blocklist.yml` — Minecraft versions to exclude from results.
- `mod_polling/version_blocklist.yml` — Regex patterns for bad version strings.
- `mod_polling/mc_mapping.yml` — Minecraft version aliases.

### Polling cycle

When polling is active (started via `=nemp running true`), a timer event periodically triggers a polling cycle:

1. Iterate over all active mods in `mods.json`.
2. For each mod, dispatch to the appropriate parser method: `check_{parser}(mod)`.
3. Parsers fetch data from external APIs (CurseForge, GitHub, Jenkins, etc.) via `fetch_page()`/`fetch_json()`.
4. Compare returned versions against the current known versions.
5. Announce updates to IRC.

### Rate limiting

`fetch_page()` uses per-host `asyncio.Lock` instances and a configurable delay (`host_delay`, default 0.5s) to avoid hammering external APIs.

### Parsers

Each parser is a method on `ModPoller` named `check_{parser_name}()`. Supported parsers: `cfwidget`, `forge_json`, `mcforge_v2`, `jenkins`, `html`, `github_release`, `buildcraft`.

See [docs/mod_polling/parsers.md](mod_polling/parsers.md) for detailed documentation of each parser's configuration and behavior.

## Supporting modules

### Ban list (`ban_list.py`)

SQLite-backed system for banning users from bot commands. Supports wildcard matching (`*`, `?`) on `nick!ident@host` patterns. Bans are organized into groups.

### User auth (`user_auth.py`)

`AuthTracker` maintains a dict of known users and their registration status. Used by the permission system to determine admin access.

### Help system (`help_system.py`)

`HelpModule` stores `HelpEntity` objects registered by plugins. Each entry has descriptions, named arguments (with optional flag), and a minimum rank to view.

### Task pool (`task_pool.py`)

`TaskPool` manages long-running `asyncio.Task` instances with bidirectional communication via `asyncio.Queue`. Tasks can be polled for results, sent messages, and cancelled.

### Logging (`irc_logging.py`)

`LoggingModule` configures Python logging with both console and file output. Log files rotate daily into `BotLogs/YYYY-MM/DD-MM-YYYY.log`. A timer event checks for date changes every 60 seconds.

## Concurrency model

The bot is single-threaded async. Key concurrency patterns:

- **Handler serialization**: All IRC handler calls go through `_handler_lock`, ensuring only one handler runs at a time. This simplifies plugin code (no need for per-plugin locking).
- **PING bypass**: PING/PONG is handled outside the lock for responsiveness.
- **Background tasks**: `asyncio.create_task()` with done-callback cleanup for the write loop and timer loop.
- **Wait-for pattern**: `CommandRouter.wait_for(event, check, timeout)` returns a future that resolves when a matching IRC event arrives. Used for WHOIS queries and waiting for channel join confirmations.
- **Per-host rate limiting**: `ModPoller.fetch_page()` uses separate `asyncio.Lock` instances per hostname to serialize requests to the same host while allowing concurrent requests to different hosts.
