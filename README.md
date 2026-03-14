# Not Enough Mods: Polling

An IRC bot that automatically keeps mods in [Not Enough Mods][nem] up-to-date by polling information from CurseForge, MinecraftForge, GitHub Releases, Jenkins, and other sources.

Built on the Renol IRC bot framework, fully async with `asyncio` and `aiohttp`.

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
git clone https://github.com/NotEnoughMods/NotEnoughModPolling.git
cd NotEnoughModPolling
uv sync
```

### Configuration

1. **IRC bot config** — copy the template and fill in your server details:

   ```bash
   cp config.yml.example config.yml
   ```

   Key settings in `config.yml`:

   | Section | Key | Description |
   |---------|-----|-------------|
   | connection | `server`, `port` | IRC server to connect to |
   | connection | `nickname`, `ident` | Bot identity |
   | connection | `password` | Server password (optional) |
   | administration | `channels` | Channel list |
   | administration | `operators` | Users with admin privileges |
   | administration | `command_prefix` | Command trigger (default: `=`) |
   | administration | `logging_level` | `DEBUG`, `INFO`, `WARNING`, etc. |
   | networking | `force_ipv6`, `bind_address` | Network options |

2. **NEMP polling config** — only needed if you want mod-polling features:

   ```bash
   cp mod_polling/config.yml.example mod_polling/config.yml
   ```

   Settings include GitHub API credentials (increases rate limits), polling interval (default 1800s), auto-start behavior, and the staff IRC channel.

3. **NEM relay config** (optional) — forwards mod update announcements to Discord:

   ```bash
   cp config/nem_relay.yml.example config/nem_relay.yml
   ```

   Set the Discord webhook URL and the IRC channel/nick to listen on.

## Running

```bash
uv run irc_bot.py
```

The bot automatically reconnects on disconnection with exponential backoff (5s to 300s). Logs are written to `BotLogs/` and the last crash traceback is saved to `exception.txt`.

## Usage

All commands use the configured prefix (default `=`). Examples:

| Command | Permission | Description |
|---------|-----------|-------------|
| `=help` | GUEST | List available commands |
| `=help <cmd>` | GUEST | Show help for a command |
| `=nemp enable` | OP | Start polling for mod updates |
| `=nemp list` | OP | List tracked mods |
| `=nemp status` | VOICED | Check if polling is running |
| `=reload <plugin>` | ADMIN | Reload a plugin module |
| `=join #channel` | ADMIN | Join a channel |
| `=part #channel` | ADMIN | Leave a channel |

Permission levels (from `command_router.Permission`):

| Level | Name | Description |
|-------|------|-------------|
| 0 | GUEST | Anyone |
| 1 | VOICED | `+` and above |
| 2 | OP | `@` and above |
| 3 | ADMIN | Bot operator (admin list + registered) |
| 4 | HIDDEN | Not shown in command list |

## Project structure

```
irc_bot.py              Main entry point — async IRC event loop
irc_connection.py       Low-level async IRC read/write with rate limiting
command_router.py       Command dispatch, plugin/handler loading, messaging helpers
config.py               YAML configuration loader
bot_events.py           Timer, message, and channel event system
ban_list.py             SQLite-backed ban system
user_auth.py            Auth/registration tracking
help_system.py          Self-documenting help system
task_pool.py            Background async task manager
irc_logging.py          Logging with daily file rotation

plugins/                Bot command plugins (dynamically loaded at startup)
irc_handlers/           IRC protocol handlers (PRIVMSG, JOIN, PING, numerics, etc.)
mod_polling/            Mod-polling subsystem
  poller.py               Polling engine for all supported sources
  mods.json               Registry of tracked mods and their parser configs
  config.yml.example      GitHub API, polling interval, staff channel settings
config/                 Supplementary config files (e.g., nem_relay.yml)
scripts/                Maintenance utilities (regex testing, release cadence analysis)
docs/                   Additional documentation
tests/                  Test suite
```

## Writing plugins

Plugins are Python files in `plugins/` that are loaded automatically at startup. There are two styles; the **new-style** (class-based) is preferred for new plugins.

### New-style (class-based)

```python
from command_router import Permission, command, subcommand

PLUGIN_ID = "greet"

class Plugin:
    async def setup(self, router, startup):
        """Called on load (startup=True) or reload (startup=False)."""
        pass

    async def teardown(self, router):
        """Called on shutdown or before reload."""
        pass

    @command("greet", permission=Permission.GUEST, allow_private=True)
    async def greet(self, router, name, params, channel, userdata, rank, is_channel):
        await router.send_message(channel, f"Hello, {name}!")

    @subcommand("greet", "loud", permission=Permission.VOICED)
    async def cmd_loud(self, router, name, params, channel, userdata, rank):
        await router.send_message(channel, f"HELLO, {name.upper()}!")
```

- The `@command` method is the fallback when no subcommand matches.
- Subcommands inherit the group's permission when `permission=None`.
- `setup()` and `teardown()` are optional lifecycle hooks.

### Old-style (function-based)

```python
from command_router import Permission

PLUGIN_ID = "say"

async def _say(router, name, params, channel, userdata, rank, is_channel):
    await router.send_chat_message(router.send, channel, " ".join(params))

COMMANDS = {
    "say": {"execute": _say, "permission": Permission.HIDDEN},
}
```

See `plugins/examples.py` for patterns using timer events, chat events, and background tasks.

For the full plugin development guide, see [docs/plugins.md](docs/plugins.md).

## Contributing

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

Tests run automatically on push/PR via GitHub Actions. The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. See `pyproject.toml` for the enabled rule sets.

## Credits

See [contributors](https://github.com/NotEnoughMods/NotEnoughModPolling/graphs/contributors).

## Contact

NEM Discord server: <https://discord.gg/D7vNaZM>

## License

[MIT](LICENSE) — Copyright (c) 2013–2026 Not Enough Mods

[nem]: https://bot.notenoughmods.com/
