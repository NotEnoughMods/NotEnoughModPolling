from unittest.mock import AsyncMock, MagicMock

from irc_connection import IrcConnection


class TestSendMsg:
    async def test_sanitizes_cr_lf(self):
        conn = IrcConnection()
        msg = "PRIVMSG #chan :hello\r\nworld"
        await conn.send_msg(msg)
        queued = await conn._write_queue.get()
        # CR and LF should be replaced with spaces, then \r\n appended
        assert queued == "PRIVMSG #chan :hello  world\r\n"


class TestReadLines:
    async def test_yields_complete_lines(self):
        conn = IrcConnection()
        conn.reader = MagicMock()

        # Simulate two complete lines in one read, then connection close
        data_chunks = [b":server PING :test\n:server PONG :test\n", b""]
        call_count = 0

        async def fake_read(n):
            nonlocal call_count
            result = data_chunks[call_count]
            call_count += 1
            return result

        conn.reader.read = fake_read

        lines = []
        async for line in conn.read_lines():
            lines.append(line)

        assert len(lines) == 2
        assert lines[0] == ":server PING :test"
        assert lines[1] == ":server PONG :test"

    async def test_handles_partial_reads(self):
        conn = IrcConnection()
        conn.reader = MagicMock()

        # Line split across two reads
        data_chunks = [b":server PING", b" :test\n", b""]
        call_count = 0

        async def fake_read(n):
            nonlocal call_count
            result = data_chunks[call_count]
            call_count += 1
            return result

        conn.reader.read = fake_read

        lines = []
        async for line in conn.read_lines():
            lines.append(line)

        assert len(lines) == 1
        assert lines[0] == ":server PING :test"

    async def test_connection_closed_on_empty_read(self):
        conn = IrcConnection()
        conn.reader = MagicMock()

        async def fake_read(n):
            return b""

        conn.reader.read = fake_read

        lines = []
        async for line in conn.read_lines():
            lines.append(line)

        assert lines == []
        assert conn.ready is False


class TestClose:
    async def test_close_suppresses_oserror_from_wait_closed(self):
        conn = IrcConnection()
        conn.writer = MagicMock()
        conn.writer.close = MagicMock()
        conn.writer.wait_closed = AsyncMock(side_effect=ConnectionResetError("Connection reset by peer"))

        await conn.close()  # Should not raise

        assert conn.ready is False
        conn.writer.close.assert_called_once()

    async def test_close_works_normally(self):
        conn = IrcConnection()
        conn.writer = MagicMock()
        conn.writer.close = MagicMock()
        conn.writer.wait_closed = AsyncMock()

        await conn.close()

        assert conn.ready is False
        conn.writer.close.assert_called_once()
        conn.writer.wait_closed.assert_awaited_once()

    async def test_close_no_writer(self):
        conn = IrcConnection()
        conn.writer = None

        await conn.close()  # Should not raise

        assert conn.ready is False
