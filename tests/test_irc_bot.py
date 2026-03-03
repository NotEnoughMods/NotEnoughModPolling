from irc_bot import IrcBot


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
