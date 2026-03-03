import logging


class NameAlreadyExists(Exception):
    def __init__(self, eventName):
        self.name = eventName

    def __str__(self):
        return self.name


class AuthTracker:
    def __init__(self, userlist):
        self.users = {}
        for item in userlist:
            self.users[item.lower()] = False
        print(self.users)
        self.userQueue = []

        self._logger = logging.getLogger("UserVerification")
        self._logger.info("Verification Module initialized; Current users: %s", self.users.keys())

    def doesExist(self, user):
        return user.lower() in self.users

    def isQueued(self, user):
        return user.lower() in self.userQueue

    def queueUser(self, user):
        user = user.lower()
        if user not in self.userQueue:
            self.userQueue.append(user.lower())
            self._logger.debug("Queueing user: %s", user)
            return True
        else:
            self._logger.debug("Didn't queue user; Already queued: %s", user)
            return False

    def unqueueUser(self, user):
        user = user.lower()
        if user in self.userQueue:
            self.userQueue.remove(user)
            self._logger.debug("Removing user from queue: %s", user)
            return True
        else:
            self._logger.debug("Didn't remove user from queue; Wasn't queued: %s", user)
            return False

    def isRegistered(self, user):
        user = user.lower()
        return bool(user in self.users and self.users[user] is True)

    def unregisterUser(self, user):
        user = user.lower()
        self.users[user] = False

        self._logger.debug("Unregistered user: %s", user)

    def registerUser(self, user):
        user = user.lower()
        self.users[user] = True

        self._logger.debug("Registered user: %s", user)

    def addUser(self, user):
        user = user.lower()
        self.users[user] = False

        self._logger.debug("Added new user: %s", user)

    def remUser(self, user):
        user = user.lower()
        if user in self.users:
            del self.users[user]
            self._logger.debug("Removed user: %s", user)
        else:
            self._logger.warning("Tried to remove user %s, but no such user exists", user)
