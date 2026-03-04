import logging

from command_router import Permission

PLUGIN_ID = "operator_management"


def _find_in_list(user, userlist):
    """Return the matching name from userlist (case-insensitive), or None."""
    for name in userlist:
        if name.lower() == user.lower():
            return name
    return None


async def _addop(router, username, params, channel, userdata, rank, is_channel):
    names = params

    for name in names:
        if _find_in_list(name, router.operators) is None:
            router.operators.append(name)
            router.auth_tracker.add_user(name)
            await router.whois_user(name)

    logging.info("User '%s' has added user(s) '%s'", username, ", ".join(names))
    await router.send_chat_message(router.send, channel, "Added " + ", ".join(names))


async def _remop(router, username, params, channel, userdata, rank, is_channel):
    names = params
    notremoved = []
    removed = []

    for name in names:
        existing = _find_in_list(name, router.operators)
        if existing and existing != username:
            router.operators.remove(existing)
            removed.append(existing)
            router.auth_tracker.unregister_user(existing)
            router.auth_tracker.remove_user(existing)
            if router.auth_tracker.is_queued(existing):
                router.auth_tracker.unqueue_user(existing)
        else:
            notremoved.append(name)

    if len(removed) > 0:
        logging.info("User '%s' has removed user(s) '%s'", username, ", ".join(removed))
        await router.send_chat_message(router.send, channel, "Removed " + ", ".join(removed))
    if len(notremoved) > 0:
        await router.send_chat_message(router.send, channel, "Didn't remove " + ", ".join(notremoved))


async def _oplist(router, name, params, channel, userdata, rank, is_channel):
    if len(router.operators) > 0:
        await router.send_chat_message(
            router.send,
            channel,
            "The following users are Operators of this bot: " + ", ".join(router.operators),
        )
    if len(router.operators) == 0:
        await router.send_chat_message(router.send, channel, "Nobody is Operator of this bot!")


COMMANDS = {
    "addop": {"execute": _addop, "permission": Permission.ADMIN},
    "remop": {"execute": _remop, "permission": Permission.ADMIN},
    "oplist": {"execute": _oplist, "permission": Permission.OP},
}
