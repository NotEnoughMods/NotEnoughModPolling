import asyncio
import traceback


class ConnectionDown(Exception):
    def __init__(self, name, time):
        self.name = name
        self.time = time

    def __str__(self):
        return f"{self.name} has been shut down at {self.time}"


class IrcConnection:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.ready = True
        self.error = None
        self._write_queue = asyncio.Queue()
        self._linebuffer = b""

    async def connect(self, host, port, *, local_addr=None, family=0):
        self.reader, self.writer = await asyncio.open_connection(host, port, local_addr=local_addr, family=family)
        self.ready = True

    async def read_lines(self):
        """Async generator that yields complete IRC lines."""
        try:
            while self.ready:
                data = await self.reader.read(4096)
                if not data:
                    # Connection closed by server
                    self.ready = False
                    break

                self._linebuffer += data
                lines = self._linebuffer.split(b"\n")
                self._linebuffer = lines.pop()

                for line in lines:
                    line = line.rstrip()
                    yield line.decode("utf-8", errors="replace")
        except Exception as error:
            print()
            print(f"ERROR: {error}")
            print()
            self.error = traceback.format_exc()
            self.ready = False
        finally:
            print("Reader is done!")

    async def write_loop(self):
        """Drains the write queue, sending messages with rate limiting."""
        try:
            while self.ready:
                try:
                    msg = await asyncio.wait_for(self._write_queue.get(), timeout=0.1)
                except TimeoutError:
                    continue

                send_away = msg.encode("utf-8", "replace")
                self.writer.write(send_away)
                await self.writer.drain()

                if len(send_away) > 250:
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(2)
        except Exception as error:
            print()
            print(f"ERROR: {error}")
            print()
            self.error = traceback.format_exc()
            self.ready = False
        finally:
            print("Writer is done!")

    async def sendMsg(self, msg, priority=False):
        msg = msg.replace(chr(13), " ")
        msg = msg.replace(chr(10), " ")
        await self._write_queue.put(msg + "\r\n")

    async def close(self):
        self.ready = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
