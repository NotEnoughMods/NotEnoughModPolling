from fnmatch import fnmatch
from io import StringIO

from ban_list import InvalidCharacterUsed, NoSuchBanGroup

ID = "ban"
permission = 3


async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        await self.send_notice(user, "No user string specified.")
        return

    elif len(params) >= 1:
        userstring = params[0]
        count_exclamation_mark = userstring.count("!")
        count_at = userstring.count("@")

        # We need to confirm that the string is formatted correctly:
        # 1. Exactly one ! and one @
        # 2. ! comes before @
        if (count_exclamation_mark != 1) or (count_at != 1) or (userstring.find("!") > userstring.find("@")):
            await self.send_notice(user, "User string should be formatted like this: username!ident@host")
            return
        else:
            username, _, ident_and_host = userstring.partition("!")
            ident, _sep, host = ident_and_host.partition("@")

            if username == "*" and ident == "*" and host == "*":
                await self.send_notice(user, "You can't ban everyone!")
                return

            selfstring = f"{user}!{userdata[0]}@{userdata[1]}"  # User, ident, hostname
            if check_if_self_banned(selfstring, userstring) is True:
                await self.send_notice(user, "You can't ban yourself!")
                return

            try:
                if len(params) == 1:
                    result = self.ban_list.ban_user(username, ident, host, ban_reason="None")
                    if result is True:
                        await self.send_notice(user, f"Userstring {userstring} banned.")
                    if result is False:
                        await self.send_notice(user, f"Userstring {userstring} is already banned.")
                else:
                    group = params[1]
                    ban_reason = " ".join(params[2:]) if len(params) > 2 else "None"

                    result = self.ban_list.ban_user(username, ident, host, group, ban_reason=ban_reason)

                    if result is True:
                        await self.send_notice(
                            user,
                            f"Userstring {userstring} banned in group '{group}'.",
                        )
                    if result is False:
                        await self.send_notice(
                            user,
                            f"Userstring {userstring} is already banned in group {group}.",
                        )

            except NoSuchBanGroup as error:
                await self.send_notice(user, f"Ban group '{error.group}' does not exist.")
                return
            except InvalidCharacterUsed as error:
                await self.send_notice(
                    user,
                    f"Invalid character '{error.char}' found in position {error.pos} of '{error.string}'.",
                )
                return


def check_if_self_banned(userstring, pattern):

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
