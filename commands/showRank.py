ID = "rank"
permission = 1


async def execute(self, name, params, channel, userdata, rank):
    if len(params) == 0:
        rank = self.userGetRankNum(channel, name)
        print(rank)

        await self.sendChatMessage(
            self.send,
            channel,
            "You "
            + {
                2: "are OP",
                1: "are voiced",
                0: "do not have a special rank",
                3: "are Bot OP",
            }[rank],
        )
    else:
        name = params[0]
        rank = self.userGetRankNum(channel, name)

        ranknames = ["User", "Voiced", "OP", "Bot OP"]

        if rank == -1:
            pass
        else:
            await self.sendMessage(
                channel,
                f"User {name} has the rank {rank} ({ranknames[rank]})",
            )
    # self.sendChatMessage(self.send, channel, "You "+{
    #     "@" : "are OP", "+" : "are voiced",
    #     "" : "do not have a special rank",
    #     "@@" : "are Bot OP"
    # }[self.userGetRank(channel, name)])
