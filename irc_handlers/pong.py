import time

ID = "PONG"


async def execute(self, sendMsg, prefix, command, params):
    if self.lastPing is not None:
        self.latency = time.time() - self.lastPing
