import logging

from command_router import Permission

PLUGIN_ID = "rank"

logger = logging.getLogger("cmd.rank")


async def _rank(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        user_rank = router.get_user_rank_num(channel, name)
        logger.debug("User %s rank: %s", name, user_rank)

        await router.send_chat_message(
            router.send,
            channel,
            "You "
            + {
                2: "are OP",
                1: "are voiced",
                0: "do not have a special rank",
                3: "are Bot OP",
            }[user_rank],
        )
    else:
        target = params[0]
        user_rank = router.get_user_rank_num(channel, target)

        ranknames = ["User", "Voiced", "OP", "Bot OP"]

        if user_rank == -1:
            pass
        else:
            await router.send_message(
                channel,
                f"User {target} has the rank {user_rank} ({ranknames[user_rank]})",
            )


COMMANDS = {
    "rank": {"execute": _rank, "permission": Permission.VOICED},
}
