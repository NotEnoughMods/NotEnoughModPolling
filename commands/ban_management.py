from fnmatch import fnmatch
from io import StringIO

from ban_list import InvalidCharacterUsed, NoSuchBanGroup
from command_router import Permission

PLUGIN_ID = "ban_management"


async def _ban(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        await router.send_notice(name, "No user string specified.")
        return

    elif len(params) >= 1:
        userstring = params[0]
        count_exclamation_mark = userstring.count("!")
        count_at = userstring.count("@")

        # We need to confirm that the string is formatted correctly:
        # 1. Exactly one ! and one @
        # 2. ! comes before @
        if (count_exclamation_mark != 1) or (count_at != 1) or (userstring.find("!") > userstring.find("@")):
            await router.send_notice(name, "User string should be formatted like this: username!ident@host")
            return
        else:
            username, _, ident_and_host = userstring.partition("!")
            ident, _sep, host = ident_and_host.partition("@")

            if username == "*" and ident == "*" and host == "*":
                await router.send_notice(name, "You can't ban everyone!")
                return

            selfstring = f"{name}!{userdata[0]}@{userdata[1]}"  # User, ident, hostname
            if _check_if_self_banned(selfstring, userstring) is True:
                await router.send_notice(name, "You can't ban yourself!")
                return

            try:
                if len(params) == 1:
                    result = router.ban_list.ban_user(username, ident, host, ban_reason="None")
                    if result is True:
                        await router.send_notice(name, f"Userstring {userstring} banned.")
                    if result is False:
                        await router.send_notice(name, f"Userstring {userstring} is already banned.")
                else:
                    group = params[1]
                    ban_reason = " ".join(params[2:]) if len(params) > 2 else "None"

                    result = router.ban_list.ban_user(username, ident, host, group, ban_reason=ban_reason)

                    if result is True:
                        await router.send_notice(
                            name,
                            f"Userstring {userstring} banned in group '{group}'.",
                        )
                    if result is False:
                        await router.send_notice(
                            name,
                            f"Userstring {userstring} is already banned in group {group}.",
                        )

            except NoSuchBanGroup as error:
                await router.send_notice(name, f"Ban group '{error.group}' does not exist.")
                return
            except InvalidCharacterUsed as error:
                await router.send_notice(
                    name,
                    f"Invalid character '{error.char}' found in position {error.pos} of '{error.string}'.",
                )
                return


def _check_if_self_banned(userstring, pattern):

    ESCAPECHAR = "/"
    TOESCAPE = "[]"

    string = StringIO()

    # fnmatch uses '!' for excluding character sets, but
    # GLOB in sqlite uses '^'. Because we only use fnmatch to
    # check if the user is banning himself, we will replace
    # occurences of ^ with !.
    pattern = pattern.replace("/[^", "/[!")

    for pos, letter in enumerate(pattern):
        if letter == ESCAPECHAR:
            continue
        if letter in TOESCAPE and pattern[pos - 1] == ESCAPECHAR:
            string.write(letter)
        elif letter in TOESCAPE:
            string.write("[" + letter + "]")
        else:
            string.write(letter)

    escaped_pattern = string.getvalue()

    return bool(fnmatch(userstring, escaped_pattern))


async def _unban(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        await router.send_notice(name, "No user string specified.")
        return

    elif len(params) >= 1:
        userstring = params[0]
        count_exclamation_mark = userstring.count("!")
        count_at = userstring.count("@")

        # We need to confirm that the string is formatted correctly:
        # 1. Exactly one ! and one @
        # 2. ! comes before @
        if (count_exclamation_mark != 1) or (count_at != 1) or (userstring.find("!") > userstring.find("@")):
            await router.send_notice(name, "User string should be formatted like this: username!ident@host")
            return
        else:
            username, _, ident_and_host = userstring.partition("!")
            ident, _sep, host = ident_and_host.partition("@")

            try:
                if len(params) == 1:
                    result = router.ban_list.unban_user(username, ident, host)
                    if result:
                        await router.send_notice(name, f"Userstring {userstring} unbanned.")
                    if not result:
                        await router.send_notice(name, f"Userstring {userstring} is not banned.")
                else:
                    group = params[1]
                    result = router.ban_list.unban_user(username, ident, host, group)
                    if result:
                        await router.send_notice(
                            name,
                            f"Userstring {userstring} unbanned in group '{group}'.",
                        )
                    if not result:
                        await router.send_notice(
                            name,
                            f"Userstring {userstring} is not banned in group {group}.",
                        )

            except NoSuchBanGroup as error:
                await router.send_notice(name, f"Ban group '{error.group}' does not exist.")
                return
            except InvalidCharacterUsed as error:
                await router.send_notice(
                    name,
                    f"Invalid character '{error.char}' found in position {error.pos} of '{error.string}'.",
                )
                return


async def _checkban(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        await router.send_notice(name, "Specify a user formated as username!ident@host.")

    if len(params) >= 1:
        userstring = params[0]

        bans = router.ban_list.get_bans(matching_string=userstring)

        output = []
        for ban in bans:
            info = f"{router.ban_list.unescape_banstring(ban[1])} [{ban[0]}] Reason: {ban[2]}"
            output.append(info)

        output = " | ".join(output)

        if len(output) == 0:
            await router.send_notice(name, "The user is not affected by any bans.")
        elif len(output) == 1:
            await router.send_notice(name, f"The user is affected by the following ban: {output}")
        elif len(output) > 1:
            await router.send_notice(name, "The user is affected by the following bans:")
            await router.send_notice(name, output)


async def _listbans(router, name, params, channel, userdata, rank, is_channel):
    if len(params) == 0:
        groups = router.ban_list.get_groups()

        await router.send_notice(
            name,
            "Specify a group. The following groups are currently defined: {}".format(", ".join(groups)),
        )

    elif len(params) >= 1:
        group_name = params[0]

        try:
            bans = [
                router.ban_list.unescape_banstring(ban_tuple[1]) for ban_tuple in router.ban_list.get_bans(group_name)
            ]
            output = ", ".join(bans)

            if len(bans) == 0:
                await router.send_notice(name, f"The group '{group_name}' contains no bans.")
            elif len(bans) == 1:
                await router.send_notice(
                    name,
                    f"The group '{group_name}' contains the following ban: {output}",
                )
            elif len(bans) > 1:
                await router.send_notice(
                    name,
                    f"The group '{group_name}' contains the following bans:",
                )
                await router.send_notice(name, output)

        except NoSuchBanGroup as error:
            await router.send_notice(name, f"Ban group '{error.group}' does not exist.")


COMMANDS = {
    "ban": {"execute": _ban, "permission": Permission.ADMIN},
    "unban": {"execute": _unban, "permission": Permission.ADMIN},
    "checkban": {"execute": _checkban, "permission": Permission.ADMIN},
    "listbans": {"execute": _listbans, "permission": Permission.ADMIN},
}
