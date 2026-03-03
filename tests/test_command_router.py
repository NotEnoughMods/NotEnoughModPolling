from unittest.mock import patch

from command_router import CommandRouter


def make_router():
    """Create a CommandRouter with patched module loading and BanList."""
    with (
        patch.object(CommandRouter, "_load_modules", return_value={}),
        patch("command_router.BanList"),
        patch("command_router.LoggingModule"),
    ):
        return CommandRouter(
            channels=["#test"],
            cmdprefix="!",
            name="TestBot",
            ident="testbot",
            adminlist=["admin"],
            loglevel="INFO",
        )


class TestDefaultSplitter:
    def test_short_msg_not_split(self):
        router = make_router()
        result = router.default_splitter("short", 100, " ")
        assert result == ["short"]

    def test_long_msg_split_at_space(self):
        router = make_router()
        msg = "hello world this is a long message"
        result = router.default_splitter(msg, 15, " ")
        assert len(result) > 1
        for part in result:
            assert len(part) <= 15

    def test_custom_delimiter(self):
        router = make_router()
        msg = "part1,part2,part3"
        result = router.default_splitter(msg, 10, ",")
        assert len(result) > 1


class TestGetUserRank:
    def test_op_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user1", "@"), ("user2", "+"), ("user3", "")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank("#test", "user1") == "@"

    def test_voice_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user2", "+")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank("#test", "user2") == "+"

    def test_normal_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user3", "")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank("#test", "user3") == ""

    def test_case_insensitive(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("User1", "@")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank("#test", "user1") == "@"


class TestGetUserRankNum:
    def test_admin_registered(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("admin", "@")],
            "Topic": "",
            "Mode": "",
        }
        router.auth_tracker.register_user("admin")
        assert router.get_user_rank_num("#test", "admin") == 3

    def test_op_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user1", "@@")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank_num("#test", "user1") == 2

    def test_voice_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user2", "+")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank_num("#test", "user2") == 1

    def test_normal_rank(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("user3", "")],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank_num("#test", "user3") == 0

    def test_user_not_found(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [],
            "Topic": "",
            "Mode": "",
        }
        assert router.get_user_rank_num("#test", "nobody") == -1


class TestGetChannelTrueCase:
    def test_exact_match(self):
        router = make_router()
        router.channel_data["#Test"] = {"Userlist": [], "Topic": "", "Mode": ""}
        assert router.get_channel_true_case("#Test") == "#Test"

    def test_case_insensitive(self):
        router = make_router()
        router.channel_data["#Test"] = {"Userlist": [], "Topic": "", "Mode": ""}
        assert router.get_channel_true_case("#test") == "#Test"

    def test_not_found(self):
        router = make_router()
        assert router.get_channel_true_case("#nonexistent") is False


class TestIsUserVisible:
    def test_user_in_channel(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("visibleuser", "")],
            "Topic": "",
            "Mode": "",
        }
        assert router.is_user_visible("visibleuser") is True

    def test_user_not_in_channels(self):
        router = make_router()
        router.channel_data["#test"] = {
            "Userlist": [("other", "")],
            "Topic": "",
            "Mode": "",
        }
        assert router.is_user_visible("nobody") is False
