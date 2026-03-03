import logging

ID = "rank"
permission = 1

logger = logging.getLogger("cmd.rank")


async def execute(self, name, params, channel, userdata, rank):
    if len(params) == 0:
        rank = self.get_user_rank_num(channel, name)
        logger.debug("User %s rank: %s", name, rank)

        await self.send_chat_message(
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
        rank = self.get_user_rank_num(channel, name)

        ranknames = ["User", "Voiced", "OP", "Bot OP"]

        if rank == -1:
            pass
        else:
            await self.send_message(
                channel,
                f"User {name} has the rank {rank} ({ranknames[rank]})",
            )
    # self.send_chat_message(self.send, channel, "You "+{
    #     "@" : "are OP", "+" : "are voiced",
    #     "" : "do not have a special rank",
    #     "@@" : "are Bot OP"
    # }[self.get_user_rank(channel, name)])
