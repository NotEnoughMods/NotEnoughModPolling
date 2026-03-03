import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_events import EventAlreadyExists


class TestStandardEvent:
    async def test_add_and_run_event(self, standard_event):
        handler = MagicMock()
        standard_event.add_event("test", handler)
        assert standard_event.event_exists("test")

        cmd_handler = MagicMock()
        await standard_event.run_all_events(cmd_handler)
        handler.assert_called_once()

    async def test_add_async_event(self, standard_event):
        handler = AsyncMock()
        standard_event.add_event("test", handler)
        cmd_handler = MagicMock()
        await standard_event.run_all_events(cmd_handler)
        handler.assert_awaited_once()

    async def test_remove_event(self, standard_event):
        standard_event.add_event("test", MagicMock())
        standard_event.remove_event("test")
        assert not standard_event.event_exists("test")

    def test_remove_nonexistent_raises(self, standard_event):
        with pytest.raises(KeyError):
            standard_event.remove_event("nope")

    def test_duplicate_event_raises(self, standard_event):
        standard_event.add_event("test", MagicMock())
        with pytest.raises(EventAlreadyExists):
            standard_event.add_event("test", MagicMock())

    def test_not_callable_raises(self, standard_event):
        with pytest.raises(TypeError):
            standard_event.add_event("test", "not callable")

    def test_channel_not_list_raises(self, standard_event):
        with pytest.raises(TypeError):
            standard_event.add_event("test", MagicMock(), channel="#chan")

    async def test_deferred_add_from_inside_event(self, standard_event):
        """Events added from inside an event handler are queued."""

        def inner_handler(cmd_handler, channels):
            standard_event.add_event("deferred", MagicMock(), from_event=True)

        standard_event.add_event("trigger", inner_handler)
        await standard_event.run_all_events(MagicMock())
        assert standard_event.event_exists("deferred")

    async def test_deferred_remove_from_inside_event(self, standard_event):
        """Events removed from inside an event handler are queued."""

        def inner_handler(cmd_handler, channels):
            standard_event.remove_event("to_remove", from_event=True)

        standard_event.add_event("to_remove", MagicMock())
        standard_event.add_event("trigger", inner_handler)
        await standard_event.run_all_events(MagicMock())
        assert not standard_event.event_exists("to_remove")

    def test_channel_scoping(self, standard_event):
        standard_event.add_event("test", MagicMock(), channel=["#a"])
        assert standard_event.get_channels("test") == ["#a"]
        standard_event.add_channel("test", "#b")
        assert "#b" in standard_event.get_channels("test")
        standard_event.remove_channel("test", "#a")
        assert standard_event.get_channels("test") == ["#b"]

    async def test_stats_tracking(self, standard_event):
        standard_event.add_event("test", MagicMock())
        await standard_event.run_all_events(MagicMock())
        stats = standard_event._events["test"]["stats"]
        assert stats["average"] is not None
        assert stats["min"] is not None
        assert stats["max"] is not None


class TestTimerEvent:
    async def test_fires_after_interval(self, timer_event):
        handler = MagicMock()
        timer_event.add_event("test", 0, handler)
        # Set lastExecTime to the past so it fires immediately
        timer_event._events["test"]["lastExecTime"] = time.time() - 10
        await timer_event.run_all_events(MagicMock())
        handler.assert_called_once()

    async def test_does_not_fire_before_interval(self, timer_event):
        handler = MagicMock()
        timer_event.add_event("test", 9999, handler)
        await timer_event.run_all_events(MagicMock())
        handler.assert_not_called()

    def test_invalid_interval_type_raises(self, timer_event):
        with pytest.raises(TypeError):
            timer_event.add_event("test", "bad", MagicMock())

    def test_negative_interval_raises(self, timer_event):
        with pytest.raises(ValueError):
            timer_event.add_event("test", -1, MagicMock())


class TestMsgEvent:
    async def test_passes_userdata_message_channel(self, msg_event):
        handler = MagicMock()
        msg_event.add_event("test", handler)
        cmd = MagicMock()
        await msg_event.run_all_events(cmd, "nick!user@host", "hello", "#chan")
        handler.assert_called_once()
        args = handler.call_args[0]
        assert args[0] is cmd
        assert args[2] == "nick!user@host"
        assert args[3] == "hello"
        assert args[4] == "#chan"

    async def test_channel_scoped_execution(self, msg_event):
        handler = MagicMock()
        msg_event.add_event("test", handler, channel=["#specific"])
        cmd = MagicMock()
        await msg_event.run_all_events(cmd, "nick!user@host", "hello", "#specific")
        handler.assert_called_once()
        # Channels are passed to the handler
        assert handler.call_args[0][1] == ["#specific"]
