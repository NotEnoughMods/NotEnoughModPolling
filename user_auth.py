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

    def user_exists(self, user):
        return user.lower() in self.users

    def is_queued(self, user):
        return user.lower() in self.userQueue

    def queue_user(self, user):
        user = user.lower()
        if user not in self.userQueue:
            self.userQueue.append(user.lower())
            self._logger.debug("Queueing user: %s", user)
            return True
        else:
            self._logger.debug("Didn't queue user; Already queued: %s", user)
            return False

    def unqueue_user(self, user):
        user = user.lower()
        if user in self.userQueue:
            self.userQueue.remove(user)
            self._logger.debug("Removing user from queue: %s", user)
            return True
        else:
            self._logger.debug("Didn't remove user from queue; Wasn't queued: %s", user)
            return False

    def is_registered(self, user):
        user = user.lower()
        return bool(user in self.users and self.users[user] is True)

    def unregister_user(self, user):
        user = user.lower()
        self.users[user] = False

        self._logger.debug("Unregistered user: %s", user)

    def register_user(self, user):
        user = user.lower()
        self.users[user] = True

        self._logger.debug("Registered user: %s", user)

    def add_user(self, user):
        user = user.lower()
        self.users[user] = False

        self._logger.debug("Added new user: %s", user)

    def remove_user(self, user):
        user = user.lower()
        if user in self.users:
            del self.users[user]
            self._logger.debug("Removed user: %s", user)
        else:
            self._logger.warning("Tried to remove user %s, but no such user exists", user)
