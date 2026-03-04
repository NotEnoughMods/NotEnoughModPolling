import time

ID = "PONG"


async def execute(self, send_msg, prefix, command, params):
    if self.last_ping is not None:
        self.latency = time.time() - self.last_ping
