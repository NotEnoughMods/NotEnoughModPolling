from ban_list import NoSuchBanGroup

ID = "listbans"
permission = 3


async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        groups = self.Banlist.getGroups()

        await self.sendNotice(
            user,
            "Specify a group. The following groups are currently defined: {}".format(", ".join(groups)),
        )

    elif len(params) >= 1:
        groupName = params[0]

        try:
            bans = [self.Banlist.unescape_banstring(banTuple[1]) for banTuple in self.Banlist.getBans(groupName)]
            output = ", ".join(bans)

            if len(bans) == 0:
                await self.sendNotice(user, f"The group '{groupName}' contains no bans.")
            elif len(bans) == 1:
                await self.sendNotice(
                    user,
                    f"The group '{groupName}' contains the following ban: {output}",
                )
            elif len(bans) > 1:
                await self.sendNotice(
                    user,
                    f"The group '{groupName}' contains the following bans:",
                )
                await self.sendNotice(user, output)

        except NoSuchBanGroup as error:
            await self.sendNotice(user, f"Ban group '{error.group}' does not exist.")
