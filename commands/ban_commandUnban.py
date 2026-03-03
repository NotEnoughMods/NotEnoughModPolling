from BanList import InvalidCharacterUsed, NoSuchBanGroup

ID = "unban"
permission = 3


async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        await self.sendNotice(user, "No user string specified.")
        return

    elif len(params) >= 1:
        userstring = params[0]
        countExclamationMark = userstring.count("!")
        countAt = userstring.count("@")

        # We need to confirm that the string is formatted correctly:
        # 1. Exactly one ! and one @
        # 2. ! comes before @
        if (countExclamationMark != 1) or (countAt != 1) or (userstring.find("!") > userstring.find("@")):
            await self.sendNotice(user, "User string should be formatted like this: username!ident@host")
            return
        else:
            username, _, identAndHost = userstring.partition("!")
            ident, _sep, host = identAndHost.partition("@")

            try:
                if len(params) == 1:
                    result = self.Banlist.unbanUser(username, ident, host)
                    if result:
                        await self.sendNotice(user, f"Userstring {userstring} unbanned.")
                    if not result:
                        await self.sendNotice(user, f"Userstring {userstring} is not banned.")
                else:
                    group = params[1]
                    result = self.Banlist.unbanUser(username, ident, host, group)
                    if result:
                        await self.sendNotice(
                            user,
                            f"Userstring {userstring} unbanned in group '{group}'.",
                        )
                    if not result:
                        await self.sendNotice(
                            user,
                            f"Userstring {userstring} is not banned in group {group}.",
                        )

            except NoSuchBanGroup as error:
                await self.sendNotice(user, f"Ban group '{error.group}' does not exist.")
                return
            except InvalidCharacterUsed as error:
                await self.sendNotice(
                    user,
                    f"Invalid character '{error.char}' found in position {error.pos} of '{error.string}'.",
                )
                return
