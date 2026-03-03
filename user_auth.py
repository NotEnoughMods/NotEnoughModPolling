import logging


class NameAlreadyExists(Exception):
    def __init__(self, eventName):
        self.name = eventName

    def __str__(self):
        return self.name


class trackVerification:
    def __init__(self, userlist):
        self.users = {}
        for item in userlist:
            self.users[item.lower()] = False
        print(self.users)
        self.userQueue = []

        self.__verify_log__ = logging.getLogger("UserVerification")
        self.__verify_log__.info("Verification Module initialized; Current users: %s", self.users.keys())

    def doesExist(self, user):
        return user.lower() in self.users

    def isQueued(self, user):
        return user.lower() in self.userQueue

    def queueUser(self, user):
        user = user.lower()
        if user not in self.userQueue:
            self.userQueue.append(user.lower())
            self.__verify_log__.debug("Queueing user: %s", user)
            return True
        else:
            self.__verify_log__.debug("Didn't queue user; Already queued: %s", user)
            return False

    def unqueueUser(self, user):
        user = user.lower()
        if user in self.userQueue:
            self.userQueue.remove(user)
            self.__verify_log__.debug("Removing user from queue: %s", user)
            return True
        else:
            self.__verify_log__.debug("Didn't remove user from queue; Wasn't queued: %s", user)
            return False

    def isRegistered(self, user):
        user = user.lower()
        return bool(user in self.users and self.users[user] is True)

    def unregisterUser(self, user):
        user = user.lower()
        self.users[user] = False

        self.__verify_log__.debug("Unregistered user: %s", user)

    def registerUser(self, user):
        user = user.lower()
        self.users[user] = True

        self.__verify_log__.debug("Registered user: %s", user)

    def addUser(self, user):
        user = user.lower()
        self.users[user] = False

        self.__verify_log__.debug("Added new user: %s", user)

    def remUser(self, user):
        user = user.lower()
        if user in self.users:
            del self.users[user]
            self.__verify_log__.debug("Removed user: %s", user)
        else:
            self.__verify_log__.warning("Tried to remove user %s, but no such user exists", user)
