from unittest.mock import patch

import pytest

from config import Configuration


class TestConfiguration:
    def test_load_config_success(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "connection:\n"
            "  server: irc.example.com\n"
            "  port: 6667\n"
            "  nickname: TestBot\n"
            "  password: secret\n"
            "  ident: testbot\n"
            "  realname: Test Bot\n"
            "administration:\n"
            "  operators: [admin]\n"
            "  channels: ['#test']\n"
            "  command_prefix: '!'\n"
            "  logging_level: INFO\n"
            "networking:\n"
            "  force_ipv6: false\n"
            "  bind_address: ''\n"
        )

        cfg = Configuration()
        with patch("config.CONFIG_FILE", config_file):
            cfg.load_config()

        assert cfg.config["connection"]["server"] == "irc.example.com"
        assert cfg.config["connection"]["nickname"] == "TestBot"

    def test_load_config_missing_creates_from_example(self, tmp_path):
        config_file = tmp_path / "config.yml"
        example_file = tmp_path / "config.yml.example"
        example_file.write_text("connection:\n  server: ''\n")

        cfg = Configuration()
        with (
            patch("config.CONFIG_FILE", config_file),
            patch("config.CONFIG_EXAMPLE", example_file),
            pytest.raises(RuntimeError, match="was missing"),
        ):
            cfg.load_config()

        assert config_file.exists()

    def test_check_options_all_present(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "connection:\n"
            "  server: irc.example.com\n"
            "  port: 6667\n"
            "  nickname: TestBot\n"
            "  password: ''\n"
            "  ident: testbot\n"
            "  realname: Test Bot\n"
            "administration:\n"
            "  operators: []\n"
            "  channels: []\n"
            "  command_prefix: '!'\n"
            "  logging_level: INFO\n"
            "networking:\n"
            "  force_ipv6: false\n"
            "  bind_address: ''\n"
        )

        cfg = Configuration()
        with patch("config.CONFIG_FILE", config_file):
            cfg.load_config()
        cfg.check_options()

    def test_check_options_missing_required_raises(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "connection:\n"
            "  server: ''\n"
            "  port: 6667\n"
            "  nickname: ''\n"
            "  password: ''\n"
            "  ident: ''\n"
            "  realname: ''\n"
            "administration:\n"
            "  operators: []\n"
            "  channels: []\n"
            "  command_prefix: '!'\n"
            "  logging_level: INFO\n"
            "networking:\n"
            "  force_ipv6: false\n"
            "  bind_address: ''\n"
        )

        cfg = Configuration()
        with patch("config.CONFIG_FILE", config_file):
            cfg.load_config()
        with pytest.raises(RuntimeError, match="has no value, but is required"):
            cfg.check_options()

    def test_check_options_missing_optional_ok(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "connection:\n"
            "  server: irc.example.com\n"
            "  port: 6667\n"
            "  nickname: TestBot\n"
            "  ident: testbot\n"
            "  realname: Test Bot\n"
            "administration:\n"
            "  command_prefix: '!'\n"
            "  logging_level: INFO\n"
            "networking:\n"
            "  force_ipv6: false\n"
        )

        cfg = Configuration()
        with patch("config.CONFIG_FILE", config_file):
            cfg.load_config()
        # Should not raise — password, operators, channels, bind_address are optional
        cfg.check_options()
