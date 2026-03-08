# AGENTS.md — NotEnoughModPolling

IRC bot that automatically keeps mods in Not Enough Mods up-to-date.
Python 3.14+, managed with `uv`, linted/formatted with `ruff`, tested with `pytest`.

## Build & Run

```bash
uv sync --dev          # Install all dependencies (including dev)
uv run python irc_bot.py  # Start the bot (requires config.yml)
```

## Lint

```bash
uv run ruff check .           # Lint (pyflakes, pycodestyle, isort, pyupgrade, bugbear, simplify, ruff)
uv run ruff check --fix .     # Lint with auto-fix
uv run ruff format .          # Format code
uv run ruff format --check .  # Check formatting without modifying
```

CI runs both `ruff check .` and `ruff format --check .` — both must pass.

## Test

```bash
uv run pytest                           # Run all tests
uv run pytest tests/test_ban_list.py    # Run one test file
uv run pytest tests/test_ban_list.py::TestBanListGroups  # Run one test class
uv run pytest tests/test_ban_list.py::TestBanListGroups::test_define_group  # Run single test
uv run pytest -x                        # Stop on first failure
uv run pytest --tb=short -q             # Short output (CI mode)
```

All async tests run automatically via `pytest-asyncio` with `asyncio_mode = "auto"`.

## Project Structure

Flat layout (no `src/` directory). All primary modules live at the repo root:

```
irc_bot.py          # Entry point, IrcBot class
irc_connection.py   # TCP/IRC connection handling
irc_logging.py      # Logging configuration (file + console)
config.py           # YAML config loading
command_router.py   # Central command dispatch, plugin loading
bot_events.py       # Event system (timer, chat, join events)
help_system.py      # Help database
user_auth.py        # Auth/registration tracking
ban_list.py         # SQLite-backed ban system
task_pool.py        # Async task management
plugins/            # Bot command plugins (dynamically loaded)
irc_handlers/       # IRC protocol handlers (one per command/numeric)
mod_polling/        # Mod polling engine, parsers, data files
config/             # Supplementary YAML config files
tests/              # All tests, with conftest.py for shared fixtures
```

Plugins and IRC handlers are discovered at runtime via `os.listdir()` and loaded
with `importlib.util.spec_from_file_location()`.

## Code Style

### Formatting

- **Line length**: 120 characters (configured in `pyproject.toml` under `[tool.ruff]`)
- **Indentation**: 4 spaces for Python, 2 spaces for YAML (see `.editorconfig`)
- **Final newline**: Always insert
- **Trailing whitespace**: Always trim

### Imports

- **Absolute imports only** — never use relative imports (`from . import`)
- **Ordering** (enforced by ruff/isort): stdlib → third-party → local, separated by blank lines
- `plugins` and `irc_handlers` are configured as known first-party in isort
- Use `import module` for broad usage; `from module import Name` for specific items
- Standard library modules are typically imported whole (`import asyncio`, `import logging`)

```python
import asyncio
import logging

import aiohttp
import yaml

from bot_events import MsgEvent, StandardEvent
from command_router import Permission, command
```

### Naming Conventions

| Element              | Convention         | Example                                    |
|----------------------|--------------------|--------------------------------------------|
| Modules              | `snake_case`       | `irc_connection.py`, `bot_events.py`       |
| IRC handler modules  | include numeric    | `rpl_endofmotd_376.py`, `err_nicknameinuse_433.py` |
| Classes              | `PascalCase`       | `IrcBot`, `ModPoller`, `CommandRouter`     |
| Functions/methods    | `snake_case`       | `fetch_page`, `check_mod`, `add_event`     |
| Private members      | `_underscore`      | `_parse_message`, `_handler_lock`          |
| Constants            | `UPPER_SNAKE_CASE` | `PLUGIN_ID`, `MAX_POLL_FAILURES`           |
| Plugin IDs           | `PLUGIN_ID = "x"`  | Module-level constant in every plugin      |
| IRC handler IDs      | `ID = "XXX"`       | Module-level constant (`"PRIVMSG"`, `"376"`) |
| New-style commands   | `cmd_` prefix      | `cmd_enable`, `cmd_disable`, `cmd_status`  |
| Command aliases      | `alias_` prefix    | `alias_start`, `alias_stop`                |
| Unused loop vars     | `_prefix`          | `_i`, `_k`, `_op`                         |

### Type Annotations

Type annotations are used **sparingly** — only on `NamedTuple` fields and occasional
instance variable declarations. Function signatures do not carry type hints.

- Use modern union syntax: `X | Y` (not `Optional[X]` or `Union[X, Y]`)
- Annotate `NamedTuple` fields and complex instance variables where it aids clarity

```python
class PluginEntry(NamedTuple):
    module: object
    path: str
    setup: Callable | None
    teardown: Callable | None
    instance: object | None = None

self._host_locks: dict[str, asyncio.Lock] = {}
```

### String Formatting

- **f-strings** for most string construction
- **`.format()`** only for complex IRC messages with many color-code variables
- **`%`-style** only inside `logging` calls (standard practice for lazy interpolation)

```python
f"PRIVMSG {channel} :{msg}"                          # general use
logger.info("Connected to %s", self.host)             # logging only
"{purple}{name}{end}".format(name=n, purple=P, end=E) # complex IRC messages
```

### Error Handling

- **Custom exceptions** inherit from `Exception`, define `__init__` and `__str__`:
  `ConnectionDown`, `NEMPException`, `InvalidVersion`, `EventAlreadyExists`, etc.
- `NEMPException` is a base class; `InvalidVersion` inherits from it
- **Top-level loops** use broad `except Exception` with `logger.exception()`
- **Specific catches** where meaningful: `KeyError`, `TimeoutError`, `asyncio.CancelledError`
- Use `contextlib.suppress(ExcType)` instead of bare `try/except pass`
- Validate inputs eagerly with `isinstance` checks, raising `TypeError`/`ValueError`

### Async Patterns

The codebase is fully async, built on `asyncio`:

- Entry point: `asyncio.run(async_main())` in `irc_bot.py`
- Background tasks via `asyncio.create_task()` with done-callback cleanup
- `asyncio.Lock` for serialized handler execution and per-host rate limiting
- `asyncio.Queue` for inter-task communication (with `queue.shutdown()` for cleanup)
- `asyncio.gather`, `asyncio.as_completed`, `asyncio.wait_for` for concurrency
- `async for` with async generators (`IrcConnection.read_lines()`)
- aiohttp sessions: explicit `User-Agent` header, `aiohttp.ClientTimeout`, `async with`

### Logging

- **Module-level** loggers: `logger = logging.getLogger("BanList")`
- **Instance-level** loggers: `self._logger = logging.getLogger("IRCConnection")`
- Hierarchical naming: `irc.ping`, `irc.rpl.353`, `irc.err.433`, `cmd.say`, `cmd.pycalc`
- Always use `%`-style formatting in log calls (lazy interpolation)
- Use `.exception()` for logging with tracebacks

### Plugin Architecture

Two plugin styles coexist:

**Old-style** (function-based): module-level `COMMANDS` dict + underscore-prefixed async functions:
```python
PLUGIN_ID = "say"
async def _say(router, name, params, channel, userdata, rank, is_channel): ...
COMMANDS = {"say": {"execute": _say, "permission": Permission.HIDDEN}}
```

**New-style** (class-based): `Plugin` class with `@command`/`@subcommand` decorators:
```python
PLUGIN_ID = "nemp"
class Plugin:
    async def setup(self, router, startup): ...
    async def teardown(self, router): ...
    @command("nemp", permission=Permission.VOICED, allow_private=True)
    async def nemp(self, router, name, params, channel, userdata, rank, is_channel): ...
    @subcommand("nemp", "enable", permission=Permission.OP)
    async def cmd_enable(self, router, ...): ...
```

Prefer the **new-style** class-based pattern for new plugins.

## Testing Conventions

- Test files: `tests/test_<module>.py`
- Group tests in `class TestXxx` with `test_xxx` methods
- Use `pytest.raises(ExcType, match="pattern")` for exception testing
- Use `tmp_path` fixture for file/database isolation
- Mocking: `MagicMock` (sync), `AsyncMock` (async), `patch`/`patch.object`
- HTTP mocking: `aioresponses` library for `aiohttp` requests
- Plain `assert` statements (pytest-style, no `unittest` assertions)
- Shared fixtures in `tests/conftest.py` (e.g., `mod_poller`, `ban_list`, event fixtures)

## Key Configuration

- `ruff` config: `pyproject.toml` — rules: F, E, W, I, UP, B, SIM, RUF
- `pytest` config: `pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]`
- `.editorconfig`: charset utf-8, trim whitespace, final newlines
- `.gitignore`: `config.yml`, `*.db`, `__pycache__/`, `BotLogs/`, `mod_polling/htdocs/`
- CI: `.github/workflows/tests.yml` — runs lint + tests on push/PR to `master`
