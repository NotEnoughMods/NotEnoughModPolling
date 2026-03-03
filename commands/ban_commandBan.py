
from io import StringIO
from fnmatch import fnmatch

from BanList import InvalidCharacterUsed, NoSuchBanGroup

ID = "ban"
permission = 3

def execute(self, user, params, channel, userdata, rank):
    if len(params) == 0:
        self.sendNotice(user, "No user string specified.")
        return
    
    elif len(params) >= 1:
        userstring = params[0]
        countExclamationMark = userstring.count("!")
        countAt = userstring.count("@")
        
        # We need to confirm that the string is formatted correctly:
        # 1. Exactly one ! and one @
        # 2. ! comes before @
        if (
            (countExclamationMark != 1) 
            or (countAt != 1)
            or (userstring.find("!") > userstring.find("@"))
            ):
            self.sendNotice(user, "User string should be formatted like this: username!ident@host")
            return
        else:
            username, sep, identAndHost = userstring.partition("!")
            ident, sep, host = identAndHost.partition("@")
            
            if username == "*" and ident == "*" and host == "*":
                self.sendNotice(user, "You can't ban everyone!")
                return
            
            selfstring = "{0}!{1}@{2}".format(user, userdata[0], userdata[1]) # User, ident, hostname
            if check_if_self_banned(selfstring, userstring) is True:
                self.sendNotice(user, "You can't ban yourself!")
                return
            
            try:
                if len(params) == 1:
                    result = self.Banlist.banUser(username, ident, host, ban_reason="None")
                    if result is True:
                        self.sendNotice(user, u"Userstring {0} banned.".format(userstring))
                    if result is False:
                        self.sendNotice(user, u"Userstring {0} is already banned.".format(userstring))
                else:
                    group = params[1]
                    if len(params) > 2:
                        ban_reason = " ".join(params[2:])
                    else:
                        ban_reason = "None"

                    result = self.Banlist.banUser(username, ident, host, group, ban_reason=ban_reason)

                    if result is True:
                        self.sendNotice(user, 
                                        u"Userstring {0} banned in group '{1}'.".format(userstring, group)
                                        )
                    if result is False:
                        self.sendNotice(user, 
                                        u"Userstring {0} is already banned in group {1}.".format(userstring, group)
                                        )
                        
            except NoSuchBanGroup as error:
                self.sendNotice(user, u"Ban group '{0}' does not exist.".format(error.group))
                return
            except InvalidCharacterUsed as error:
                self.sendNotice(user, 
                                u"Invalid character '{0}' found in position {1} of '{2}'.".format(error.char,
                                                                                                  error.pos,
                                                                                                  error.string))
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
        if letter in TOESCAPE and pattern[pos-1] == ESCAPECHAR:
            string.write(letter)
        elif letter in TOESCAPE:
            string.write("["+letter+"]")
        else:
            string.write(letter)
    
    escaped_pattern = string.getvalue()
    
    if fnmatch(userstring, escaped_pattern):
        return True
    else:
        return False