ID = "commands"
permission = 0

rankdict = {"@@": 3, "@": 2, "+": 1, "": 0}
rankname = ("Guest", "Voiced", "OP", "Owner")


async def execute(self, name, params, channel, userdata, rank):

    perms = rankdict[rank]
    group = {}
    for i in range(perms + 1):
        group[i] = []

    for cmd in self.commands:
        cmdrank = self.commands[cmd][0].permission
        if perms >= cmdrank:
            group[cmdrank].append(cmd)

    await self.send_notice(name, "Available commands:")
    for i in group:
        group[i].sort()
        await self.send_notice(name, "{}: {}".format(rankname[i], " | ".join(group[i])))
