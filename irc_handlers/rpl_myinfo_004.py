import time

ID = "004"


async def pinger(self, channels):
    if self.server is not None:
        await self.send("PING " + self.server, 0)
        # print "PING SENT TO "+self.server
        self.last_ping = time.time()


async def execute(self, send_msg, prefix, command, params):
    split = params.split(" ")

    server = split[1]
    if server[0] == ":":
        server = server[1:]

    self.server = server
    self.events["time"].add_event("server pinger", 120, pinger)
