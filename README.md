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
   cp config.cfg-dist config.cfg
   ```

   Key settings in `config.cfg`:

   | Section | Key | Description |
   |---------|-----|-------------|
   | Connection Info | `server`, `port` | IRC server to connect to |
   | Connection Info | `nickname`, `ident` | Bot identity |
   | Connection Info | `password` | Server password (optional) |
   | Administration | `channels` | Comma-separated channel list |
   | Administration | `bot operators` | Users with admin privileges |
   | Administration | `command prefix` | Command trigger (default: `=`) |
   | Administration | `logging level` | `DEBUG`, `INFO`, `WARNING`, etc. |

2. **NEMP polling config** — only needed if you want mod-polling features:

   ```bash
   cp commands/NEMP/config.example.yml commands/NEMP/config.yml
   ```

   Add your GitHub API credentials (optional, increases rate limits) and set the staff IRC channel.

## Running

```bash
uv run irc_bot.py
```

Logs are written to `BotLogs/` and the last crash traceback is saved to `exception.txt`.

## Usage

All commands use the configured prefix (default `=`). Examples:

| Command | Permission | Description |
|---------|-----------|-------------|
| `=help` | everyone | List available commands |
| `=help <cmd>` | everyone | Show help for a command |
| `=nemp running true` | op | Start polling for mod updates |
| `=nemp list` | everyone | List tracked mods |
| `=nemp status <mod>` | everyone | Check a specific mod's status |
| `=reload <cmd>` | admin | Reload a command module |
| `=join #channel` | admin | Join a channel |
| `=part #channel` | admin | Leave a channel |

Permission levels: 0 = everyone, 1 = voiced+, 2 = channel op, 3 = bot admin.

## Project structure

```
irc_bot.py              Main entry point — async IRC event loop
command_router.py       Command dispatch and dynamic plugin loading
irc_connection.py       Low-level async IRC read/write with rate limiting
config.py               Configuration file loader
bot_events.py           Timer, message, and channel event system
task_pool.py            Background async task manager
plugin_loader.py        Plugin interface definition

irc_handlers/           IRC protocol handlers (PRIVMSG, JOIN, PING, etc.)
commands/               Command plugins loaded dynamically at startup
  NEMP/                 Mod-polling subsystem
    NEMP_Class.py         Polling logic for all supported sources
    mods.json             Registry of tracked mods, their checkers, and regexes
    config.yml            GitHub API credentials and IRC settings
scripts/                Maintenance and testing utilities
  test_regexes.py         Test mod regexes against live API data
```

## Writing commands

Commands are Python files in `commands/` that are loaded automatically. Minimal example:

```python
ID = "greet"
permission = 0
privmsgEnabled = True

async def execute(self, name, params, channel, userdata, rank, chan):
    await self.send_message(channel, f"Hello, {name}!")
```

- `ID` — the command name users type after the prefix
- `permission` — minimum rank required (0–3)
- `execute()` — called when the command is invoked; `self` is the `CommandRouter`
- `setup(self, startup)` — optional, called on load/reload
- `teardown(self)` — optional, called on unload

See `commands/example_*.py` for more patterns (timer events, background tasks, etc.).

## Contributing

```bash
# Install dev dependencies
uv sync --group dev

# Lint and format
uv run ruff check .
uv run ruff format .
```

The project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. See `pyproject.toml` for the enabled rule sets.

## Credits

See [contributors](https://github.com/NotEnoughMods/NotEnoughModPolling/graphs/contributors).

## Contact

NEM Discord server: <https://discord.gg/D7vNaZM>

## License

[MIT](LICENSE) — Copyright (c) 2013–2026 Not Enough Mods

[nem]: https://bot.notenoughmods.com/
