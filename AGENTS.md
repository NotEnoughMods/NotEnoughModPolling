# AGENTS.md — NotEnoughModPolling

IRC bot that automatically keeps mods in Not Enough Mods up-to-date.
Python 3.14+, managed with `uv`, linted/formatted with `ruff`, tested with `pytest`.

## Build & Run

```bash
uv sync --dev              # Install all dependencies (including dev)
uv run python irc_bot.py   # Start the bot (requires config.yml)
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

Flat layout (no `src/` directory). Primary modules live at the repo root:

- `irc_bot.py` — Entry point, `IrcBot` class
- `irc_connection.py` — TCP/IRC connection handling
- `command_router.py` — Central command dispatch, plugin loading
- `bot_events.py` — Event system (timer, chat, join events)
- `ban_list.py` — SQLite-backed ban system
- `config.py`, `irc_logging.py`, `help_system.py`, `user_auth.py`, `task_pool.py`
- `plugins/` — Bot command plugins (dynamically loaded via `importlib`)
- `irc_handlers/` — IRC protocol handlers (one per command/numeric)
- `mod_polling/` — Mod polling engine, parsers, data files
- `tests/` — All tests, with `conftest.py` for shared fixtures

## Code Style

### Formatting

- **Line length**: 120 characters (`pyproject.toml` `[tool.ruff]`)
- **Indentation**: 4 spaces for Python, 2 spaces for YAML (`.editorconfig`)
- **Final newline**: Always. **Trailing whitespace**: Always trim.

### Imports

- **Absolute imports only** — never use relative imports (`from . import`)
- **Ordering** (enforced by ruff/isort): stdlib → third-party → local, separated by blank lines
- `plugins` and `irc_handlers` are configured as known first-party in isort
- Use `import module` for broad usage; `from module import Name` for specific items

### Naming Conventions

| Element              | Convention         | Example                                    |
|----------------------|--------------------|--------------------------------------------|
| Modules              | `snake_case`       | `irc_connection.py`, `bot_events.py`       |
| IRC handler modules  | include numeric    | `rpl_endofmotd_376.py`                     |
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

Used **sparingly** — only on `NamedTuple` fields and occasional instance variables.
Function signatures do **not** carry type hints.

- Use modern union syntax: `X | Y` (not `Optional[X]` or `Union[X, Y]`)
- Annotate `NamedTuple` fields and complex instance variables where it aids clarity

### String Formatting

- **f-strings** for most string construction
- **`.format()`** only for complex IRC messages with many color-code variables
- **`%`-style** only inside `logging` calls (lazy interpolation)

### Error Handling

- Custom exceptions inherit from `Exception` with `__init__` and `__str__`
- `NEMPException` is the base for polling exceptions; `InvalidVersion` inherits from it
- `ConnectionDown` inherits directly from `Exception` (not `NEMPException`)
- Top-level loops use broad `except Exception` with `logger.exception()`
- Specific catches where meaningful: `KeyError`, `TimeoutError`, `asyncio.CancelledError`
- Use `contextlib.suppress(ExcType)` instead of bare `try/except pass`
- Validate inputs eagerly with `isinstance`, raising `TypeError`/`ValueError`

### Async Patterns

Fully async on `asyncio`. Entry point: `asyncio.run(async_main())` in `irc_bot.py`.

- Background tasks via `asyncio.create_task()` with done-callback cleanup
- `asyncio.Lock` for serialized handler execution and per-host rate limiting
- `asyncio.Queue` for inter-task communication (with `queue.shutdown()` for cleanup)
- `asyncio.gather`, `asyncio.as_completed`, `asyncio.wait_for` for concurrency
- aiohttp sessions: explicit `User-Agent` header, `aiohttp.ClientTimeout`, `async with`

### Logging

- Module-level loggers: `logger = logging.getLogger("BanList")`
- Instance-level loggers: `self._logger = logging.getLogger("IRCConnection")`
- Hierarchical naming: `irc.ping`, `irc.rpl.353`, `cmd.say`, `cmd.pycalc`
- Always `%`-style formatting in log calls. Use `.exception()` for tracebacks.

### Plugin Architecture

Two styles coexist. Prefer **new-style** (class-based) for new plugins.

**Old-style** (function-based): `COMMANDS` dict + underscore-prefixed async functions:
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

## Testing Conventions

- Test files: `tests/test_<module>.py`
- Group tests in `class TestXxx` with `test_xxx` methods
- `pytest.raises(ExcType, match="pattern")` for exception testing
- `tmp_path` fixture for file/database isolation
- Mocking: `MagicMock` (sync), `AsyncMock` (async), `patch`/`patch.object`
- HTTP mocking: `aioresponses` library for `aiohttp` requests
- Plain `assert` statements (pytest-style, no `unittest` assertions)
- Shared fixtures in `tests/conftest.py` (e.g., `mod_poller`, `ban_list`)

## Key Configuration

- `ruff` config: `pyproject.toml` — rules: F, E, W, I, UP, B, SIM, RUF
- `pytest` config: `pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]`
- `.editorconfig`: charset utf-8, trim whitespace, final newlines
- `.gitignore`: `config.yml`, `*.db`, `__pycache__/`, `BotLogs/`, `mod_polling/htdocs/`
- CI: `.github/workflows/tests.yml` — runs lint + tests on push/PR to `master`
