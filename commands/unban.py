from ban_list import InvalidCharacterUsed, NoSuchBanGroup

ID = "unban"
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

            try:
                if len(params) == 1:
                    result = self.ban_list.unban_user(username, ident, host)
                    if result:
                        await self.send_notice(user, f"Userstring {userstring} unbanned.")
                    if not result:
                        await self.send_notice(user, f"Userstring {userstring} is not banned.")
                else:
                    group = params[1]
                    result = self.ban_list.unban_user(username, ident, host, group)
                    if result:
                        await self.send_notice(
                            user,
                            f"Userstring {userstring} unbanned in group '{group}'.",
                        )
                    if not result:
                        await self.send_notice(
                            user,
                            f"Userstring {userstring} is not banned in group {group}.",
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
