from BanList import NoSuchBanGroup

ID = "listbans"
permission = 3

async def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        groups = self.Banlist.getGroups()

        await self.sendNotice(user, u"Specify a group. The following groups are currently defined: {0}".format(u", ".join(groups)))

    elif len(params) >= 1:
        groupName = params[0]

        try:
            bans = [self.Banlist.unescape_banstring(banTuple[1]) for banTuple in self.Banlist.getBans(groupName)]
            output = u", ".join(bans)

            if len(bans) == 0:
                await self.sendNotice(user, u"The group '{0}' contains no bans.".format(groupName))
            elif len(bans) == 1:
                await self.sendNotice(user, u"The group '{0}' contains the following ban: {1}".format(groupName, output))
            elif len(bans) > 1:
                await self.sendNotice(user, u"The group '{0}' contains the following bans:".format(groupName))
                await self.sendNotice(user, output)

        except NoSuchBanGroup as error:
                await self.sendNotice(user, u"Ban group '{0}' does not exist.".format(error.group))