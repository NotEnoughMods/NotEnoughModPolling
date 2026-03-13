import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from irc_bot import IrcBot
from irc_connection import ConnectionDown


class TestParseMessage:
    def setup_method(self):
        # Minimal config to construct IrcBot (we only test _parse_message)
        config = {
            "connection": {
                "server": "irc.example.com",
                "port": 6667,
                "nickname": "TestBot",
                "password": "",
                "ident": "testbot",
                "realname": "Test",
            },
            "administration": {
                "operators": [],
                "channels": [],
                "command_prefix": "!",
                "logging_level": "INFO",
            },
            "networking": {"force_ipv6": False, "bind_address": ""},
        }

        class FakeConfig:
            pass

        cfg = FakeConfig()
        cfg.config = config
        self.bot = IrcBot(cfg)

    def test_prefixed_message(self):
        prefix, command, params = self.bot._parse_message(":nick!user@host PRIVMSG #chan :hello world")
        assert prefix == "nick!user@host"
        assert command == "PRIVMSG"
        assert params == "#chan :hello world"

    def test_no_prefix(self):
        prefix, command, params = self.bot._parse_message("PING :server.example.com")
        assert prefix is None
        assert command == "PING"
        assert params == ":server.example.com"

    def test_no_params(self):
        prefix, command, params = self.bot._parse_message(":server 001")
        assert prefix == "server"
        assert command == "001"
        assert params == ""

    def test_numeric_command(self):
        prefix, command, params = self.bot._parse_message(":server 353 bot = #chan :@user")
        assert prefix == "server"
        assert command == "353"
        assert params == "bot = #chan :@user"


def _make_bot():
    """Create an IrcBot with minimal fake config."""
    config = {
        "connection": {
            "server": "irc.example.com",
            "port": 6667,
            "nickname": "TestBot",
            "password": "",
            "ident": "testbot",
            "realname": "Test",
        },
        "administration": {
            "operators": [],
            "channels": [],
            "command_prefix": "!",
            "logging_level": "INFO",
        },
        "networking": {"force_ipv6": False, "bind_address": ""},
    }

    class FakeConfig:
        pass

    cfg = FakeConfig()
    cfg.config = config
    return IrcBot(cfg)


def _mock_conn(lines=None):
    """Create a mock IrcConnection that yields the given lines then stops."""
    conn = MagicMock()
    conn.ready = True
    conn.error = None
    conn.send_msg = AsyncMock()
    conn.flush = AsyncMock()
    conn.close = AsyncMock()
    conn.connect = AsyncMock()
    conn.write_loop = AsyncMock()

    async def fake_read_lines():
        if lines:
            for line in lines:
                yield line
        conn.ready = False

    conn.read_lines = fake_read_lines
    return conn


def _mock_router():
    """Create a mock CommandRouter."""
    router = MagicMock()
    router._handler_lock = asyncio.Lock()
    router.handle = AsyncMock()
    router.close = AsyncMock()
    router.check_timer_events = AsyncMock()
    router.task_pool = MagicMock()
    router.task_pool.cancel_all = MagicMock()
    return router


class TestStartReconnectSignaling:
    async def test_raises_connection_down_on_connection_loss(self):
        bot = _make_bot()
        conn = _mock_conn()
        router = _mock_router()

        with (
            patch("irc_bot.IrcConnection", return_value=conn),
            patch("irc_bot.CommandRouter", return_value=router),
            pytest.raises(ConnectionDown),
        ):
            await bot.start()

    async def test_no_connection_down_on_shutdown(self):
        bot = _make_bot()
        conn = _mock_conn(lines=[":server PING :test"])
        router = _mock_router()

        async def fake_handle(send, prefix, command, params, auth):
            bot.shutdown = True

        router.handle = AsyncMock(side_effect=fake_handle)

        with (
            patch("irc_bot.IrcConnection", return_value=conn),
            patch("irc_bot.CommandRouter", return_value=router),
        ):
            await bot.start()  # Should return normally, no exception

    async def test_quit_sent_on_shutdown(self):
        bot = _make_bot()
        conn = _mock_conn(lines=[":server PING :test"])
        router = _mock_router()

        async def fake_handle(send, prefix, command, params, auth):
            bot.shutdown = True

        router.handle = AsyncMock(side_effect=fake_handle)

        with (
            patch("irc_bot.IrcConnection", return_value=conn),
            patch("irc_bot.CommandRouter", return_value=router),
        ):
            await bot.start()

        # QUIT should have been sent (one of the send_msg calls)
        quit_calls = [c for c in conn.send_msg.call_args_list if "QUIT" in str(c)]
        assert len(quit_calls) > 0

    async def test_quit_not_sent_on_connection_loss(self):
        bot = _make_bot()
        conn = _mock_conn()  # No lines, simulates connection drop
        router = _mock_router()

        with (
            patch("irc_bot.IrcConnection", return_value=conn),
            patch("irc_bot.CommandRouter", return_value=router),
            pytest.raises(ConnectionDown),
        ):
            await bot.start()

        # QUIT should NOT have been sent
        quit_calls = [c for c in conn.send_msg.call_args_list if "QUIT" in str(c)]
        assert len(quit_calls) == 0

    async def test_nickserv_auth_reset_on_start(self):
        bot = _make_bot()
        bot.nickserv_auth = "SomeNick"  # Simulate previous session's auth

        conn = _mock_conn()
        router = _mock_router()

        with (
            patch("irc_bot.IrcConnection", return_value=conn),
            patch("irc_bot.CommandRouter", return_value=router),
            pytest.raises(ConnectionDown),
        ):
            await bot.start()

        assert bot.nickserv_auth is False
