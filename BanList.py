import sqlite3
import re

from io import StringIO

ALLOWEDCHARS = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}'
ALLOWEDCHARS_IDENT = ALLOWEDCHARS+"~"
ALLOWEDCHARS_HOST = ALLOWEDCHARS + ":."

class InvalidCharacterUsed(Exception):
    def __init__(self, string, char, pos):
        self.string = string
        self.char = char
        self.pos = pos
        
    def __str__(self):
        hex_char = hex(ord(self.char))
        return "String contains invalid character {0} on position {1}".format(hex_char, self.pos)

class NoSuchBanGroup(Exception):
    def __init__(self, group_name):
        self.group = group_name
        
    def __str__(self):
        return "No such ban group exists: '{0}'".format(self.group)

class BanList:
    def __init__(self, filename):
        self.ESCAPESTRING = "/"
        self.ESCAPE = "[]"
        self.NOT_ESCAPE = "*?!^"
        
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        
        # Create table for bans
        self.cursor.execute(""" 
                            CREATE TABLE IF NOT EXISTS Banlist(groupName TEXT, pattern TEXT,
                                                               ban_reason TEXT,
                                                               timestamp INTEGER, banlength INTEGER
                                                               )
                            """)
        
        # Create table for the names of the ban groups.
        # This will be used to check if a group exists
        # when checking if a user is banned in that group.
        self.cursor.execute(""" 
                            CREATE TABLE IF NOT EXISTS Bangroups(groupName TEXT)
                            """)
        
        self.defineGroup("Global")

    # You need to define a group name if you want
    # to have your own ban groups.
    # This should prevent accidents in which an user
    # is banned in a group that doesn't exist.
    def defineGroup(self, groupName):
        doesExist = self.__groupExists__(groupName)
        
        if not doesExist:
            self.cursor.execute(""" 
                                INSERT INTO Bangroups(groupName)
                                VALUES (?)
                                """, (groupName, ) )
            self.conn.commit()
            # True means that a new group has been defined.
            return True
        
        # False means that no new group has been defined, i.e.
        # the group already exists.
        return False
        
    def banUser(self, user, ident="*", host="*", groupName="Global",
                ban_reason="None",
                timestamp=(-1), banlength=(-1)):

        banstring = self.__assembleBanstring__(user, ident, host).lower()
        
        if not self.__groupExists__(groupName):
            raise NoSuchBanGroup(groupName)
        
        if not self.__banExists__(groupName, banstring):
            self.__ban__(banstring, groupName, ban_reason, timestamp, banlength)
            
            # The operation was successful, we banned the pattern.
            return True
        else:
            # We did not ban the pattern because it was already banned.
            return False
        
    def unbanUser(self, user, ident="*", host="*",
                  groupName="Global"):
        banstring = self.__assembleBanstring__(user, ident, host).lower()
        
        if not self.__groupExists__(groupName):
            raise NoSuchBanGroup(groupName)
        
        if self.__banExists__(groupName, banstring):
            self.__unban__(banstring, groupName)
            
            # The operation was successful, the pattern was unbanned.
            return True
        else:
            # We did not unban the pattern because it was never banned in the first place.
            return False
    
    def clearBanlist_all(self):
        self.cursor.execute(""" 
                            DELETE FROM Banlist
                            """)
        self.conn.commit()
    
    def clearBanlist_group(self, groupName):
        self.cursor.execute(""" 
                            DELETE FROM Banlist
                            WHERE groupName = ?
                            """, (groupName, ) )
        self.conn.commit()
        
    
    def getBans(self, groupName=None, matchingString=None):
        if groupName is None:
            if matchingString is None:
                self.cursor.execute(""" 
                                    SELECT * FROM Banlist
                                    """)
            else:
                self.cursor.execute(""" 
                                    SELECT * FROM Banlist
                                    WHERE ? GLOB pattern
                                    """, (matchingString.lower(), ))
            
            return self.cursor.fetchall()

        else:
            if self.__groupExists__(groupName):
                if matchingString is None:
                    self.cursor.execute(""" 
                                        SELECT * FROM Banlist
                                        WHERE groupName = ?
                                        """, (groupName, ))
                else:
                    self.cursor.execute(""" 
                                        SELECT * FROM Banlist
                                        WHERE groupName = ? AND ? GLOB pattern
                                        """, (groupName, matchingString.lower()))
                    
                return self.cursor.fetchall()
                    
            else:
                raise NoSuchBanGroup(groupName)
    
    
    
    def checkBan(self, user, ident, host,
                      groupName="Global"):
        
        if not self.__groupExists__(groupName):
            raise NoSuchBanGroup(groupName)
        else:
            banstring = u"{0}!{1}@{2}".format(user, ident, host).lower()
            
            self.cursor.execute(""" 
                                SELECT * FROM Banlist
                                WHERE groupName = ? AND ? GLOB pattern
                                """, (groupName, banstring))#, self.ESCAPESTRING))
            
            result = self.cursor.fetchone()
            
            if result != None:
                return True, result
            else:
                return False, None
    
    def getGroups(self):
        self.cursor.execute(""" 
                            SELECT groupName FROM Bangroups
                            """)
        
        groupTuples = self.cursor.fetchall()
        return [groupTuple[0] for groupTuple in groupTuples]
            
    def raw_ban(self, banstring, groupName, ban_reason, timestamp=(-1), banlength=(-1)):
        self.__ban__(banstring, groupName, ban_reason, timestamp, banlength)
        
    def raw_unban(self, banstring, groupName):
        self.__unban__(banstring, groupName)
    
    # We do the reverse of what __createString_forSQL__ is doing.
    # The result is a string which should be correct for using the
    # banUser and unbanUser methods, and the ban/unban commands.
    def unescape_banstring(self, banstring):
        finstring = StringIO()
        length = len(banstring)
        
        string_iter = enumerate(banstring)
        
        for pos, char in string_iter:
            charsLeft = length - pos - 1
            
            if char == "[" and charsLeft >= 3:
                nextchar = banstring[pos+1]
                closedBracket = banstring[pos+2]
                
                if closedBracket == "]":
                    finstring.write(nextchar)
                    next(string_iter)
                    next(string_iter)
                    continue

            if char in self.ESCAPE:
                finstring.write(self.ESCAPESTRING+char)
                continue
            
            finstring.write(char)
        
        return finstring.getvalue()
    def __regex_return_unescaped__(self, match):
        pass
    
    def __ban__(self, banstring, groupName="Global", ban_reason="None", timestamp=(-1), banlength=(-1)):
        self.cursor.execute(""" 
                            INSERT INTO Banlist(groupName, pattern, ban_reason, timestamp, banlength)
                            VALUES (?, ?, ?, ?, ?)
                            """, (groupName, banstring, ban_reason, timestamp, banlength))
        
        self.conn.commit()
        
    def __unban__(self, banstring, groupName = "Global"):
        self.cursor.execute(""" 
                            DELETE FROM Banlist
                            WHERE groupName = ? AND pattern = ?
                            """, (groupName, banstring))
        
        self.conn.commit()
    
    
    def __banExists__(self, groupName, banstring):
        self.cursor.execute(""" 
                            SELECT 1 FROM Banlist
                            WHERE groupName = ? AND pattern = ?
                            """, (groupName, banstring) )
        
        result = self.cursor.fetchone()
        print(result, type(result))
        if result != None and result[0] == 1:
            return True
        else:
            return False
    
    def __groupExists__(self, groupName):
        self.cursor.execute(""" 
                            SELECT 1 FROM Bangroups
                            WHERE groupName = ?
                            """, (groupName, ) )
        
        result = self.cursor.fetchone()
        print(result, type(result))
        if result != None and result[0] == 1:
            return True
        else:
            return False
        
    def __stringIsValid__(self, string):
        for char in string:
            if char not in ALLOWEDCHARS:
                return False
        
        return True
    
    def __assembleBanstring__(self, user, ident, host):
        escapedUser = self.__createString_forSQL__(user)
        escapedIdent = self.__createString_forSQL__(ident, ident = True)
        escapedHost = self.__createString_forSQL__(host, hostname = True)
        
        banstring = u"{0}!{1}@{2}".format(escapedUser, escapedIdent, escapedHost)
        
        return banstring
    
    # The createString_forSQL function takes a string and
    # formats it according to specific rules.
    # It also prevents characters that aren't in
    # the ALLOWEDCHARS constant to be used so that
    # characters not allowed in specific IRC arguments
    # (nickname, ident, host) appear in the string.
    #
    # It is not very specific and is only useful for 
    # very simple filtering so that unicode characters
    # or special characters aren't used.
    def __createString_forSQL__(self, string, hostname = False, ident = False):
        
        newString = StringIO()
        
        # Both flags should not be set at once.
        assert not ( (hostname == True) and (ident == True) )  
        
        for pos, char in enumerate(string):
            # We try reverse-escaping: 
            # - escaped chars will be written as literals
            # - non-escaped chars included in the escape string will be escaped
            # pos == 0 is an exception because characters at this
            # position cannot be escaped in any way that makes sense.
            if char == self.ESCAPESTRING:
                continue
            if char in self.NOT_ESCAPE:
                newString.write(char)
            elif pos > 0 and string[pos-1] == self.ESCAPESTRING and char in self.ESCAPE:
                newString.write(char)
            elif char in self.ESCAPE:
                #newString.write(self.ESCAPESTRING+char)
                newString.write("["+char+"]")
            else:
                if  (
                     (not hostname and not ident and char not in ALLOWEDCHARS) 
                     or (hostname and char not in ALLOWEDCHARS_HOST)
                     or (ident and char not in ALLOWEDCHARS_IDENT)
                    ):
                    raise InvalidCharacterUsed(string, char, pos)
                else:
                    newString.write(char)
                    
        return newString.getvalue()

