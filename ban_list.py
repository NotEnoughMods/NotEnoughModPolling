import logging
import sqlite3
from io import StringIO

logger = logging.getLogger("BanList")

ALLOWEDCHARS = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}"
ALLOWEDCHARS_IDENT = ALLOWEDCHARS + "~"
ALLOWEDCHARS_HOST = ALLOWEDCHARS + ":."


class InvalidCharacterUsed(Exception):
    def __init__(self, string, char, pos):
        self.string = string
        self.char = char
        self.pos = pos

    def __str__(self):
        hex_char = hex(ord(self.char))
        return f"String contains invalid character {hex_char} on position {self.pos}"


class NoSuchBanGroup(Exception):
    def __init__(self, group_name):
        self.group = group_name

    def __str__(self):
        return f"No such ban group exists: '{self.group}'"


class BanList:
    def __init__(self, filename):
        self.ESCAPESTRING = "/"
        self.ESCAPE = "[]"
        self.NOT_ESCAPE = "*?!^"

        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()

        self._migrate_schema()

        # Create table for bans
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS ban_list(group_name TEXT, pattern TEXT,
                                                               ban_reason TEXT,
                                                               timestamp INTEGER, banlength INTEGER
                                                               )
                            """)

        # Create table for the names of the ban groups.
        # This will be used to check if a group exists
        # when checking if a user is banned in that group.
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS ban_groups(group_name TEXT)
                            """)

        self.define_group("Global")

    def _migrate_schema(self):
        """Migrate pre-snake_case database schema."""
        tables = {row[0] for row in self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        for old, new in [("Banlist", "ban_list"), ("Bangroups", "ban_groups")]:
            if old in tables and new not in tables:
                self.cursor.execute(f"ALTER TABLE {old} RENAME TO {new}")
                logger.info("Migrated table %s -> %s", old, new)

        for table in ["ban_list", "ban_groups"]:
            columns = [row[1] for row in self.cursor.execute(f"PRAGMA table_info({table})").fetchall()]
            if "groupName" in columns and "group_name" not in columns:
                self.cursor.execute(f"ALTER TABLE {table} RENAME COLUMN groupName TO group_name")
                logger.info("Migrated column %s.groupName -> group_name", table)

        self.conn.commit()

    # You need to define a group name if you want
    # to have your own ban groups.
    # This should prevent accidents in which an user
    # is banned in a group that doesn't exist.
    def define_group(self, group_name):
        does_exist = self._group_exists(group_name)

        if not does_exist:
            self.cursor.execute(
                """
                                INSERT INTO ban_groups(group_name)
                                VALUES (?)
                                """,
                (group_name,),
            )
            self.conn.commit()
            # True means that a new group has been defined.
            return True

        # False means that no new group has been defined, i.e.
        # the group already exists.
        return False

    def ban_user(
        self,
        user,
        ident="*",
        host="*",
        group_name="Global",
        ban_reason="None",
        timestamp=(-1),
        banlength=(-1),
    ):

        banstring = self._assemble_ban_string(user, ident, host).lower()

        if not self._group_exists(group_name):
            raise NoSuchBanGroup(group_name)

        if not self._ban_exists(group_name, banstring):
            self._ban(banstring, group_name, ban_reason, timestamp, banlength)

            # The operation was successful, we banned the pattern.
            return True
        else:
            # We did not ban the pattern because it was already banned.
            return False

    def unban_user(self, user, ident="*", host="*", group_name="Global"):
        banstring = self._assemble_ban_string(user, ident, host).lower()

        if not self._group_exists(group_name):
            raise NoSuchBanGroup(group_name)

        if self._ban_exists(group_name, banstring):
            self._unban(banstring, group_name)

            # The operation was successful, the pattern was unbanned.
            return True
        else:
            # We did not unban the pattern because it was never banned in the first place.
            return False

    def clear_all_bans(self):
        self.cursor.execute("""
                            DELETE FROM ban_list
                            """)
        self.conn.commit()

    def clear_group_bans(self, group_name):
        self.cursor.execute(
            """
                            DELETE FROM ban_list
                            WHERE group_name = ?
                            """,
            (group_name,),
        )
        self.conn.commit()

    def get_bans(self, group_name=None, matching_string=None):
        if group_name is None:
            if matching_string is None:
                self.cursor.execute("""
                                    SELECT * FROM ban_list
                                    """)
            else:
                self.cursor.execute(
                    """
                                    SELECT * FROM ban_list
                                    WHERE ? GLOB pattern
                                    """,
                    (matching_string.lower(),),
                )

            return self.cursor.fetchall()

        else:
            if self._group_exists(group_name):
                if matching_string is None:
                    self.cursor.execute(
                        """
                                        SELECT * FROM ban_list
                                        WHERE group_name = ?
                                        """,
                        (group_name,),
                    )
                else:
                    self.cursor.execute(
                        """
                                        SELECT * FROM ban_list
                                        WHERE group_name = ? AND ? GLOB pattern
                                        """,
                        (group_name, matching_string.lower()),
                    )

                return self.cursor.fetchall()

            else:
                raise NoSuchBanGroup(group_name)

    def check_ban(self, user, ident, host, group_name="Global"):

        if not self._group_exists(group_name):
            raise NoSuchBanGroup(group_name)
        else:
            banstring = f"{user}!{ident}@{host}".lower()

            self.cursor.execute(
                """
                                SELECT * FROM ban_list
                                WHERE group_name = ? AND ? GLOB pattern
                                """,
                (group_name, banstring),
            )  # , self.ESCAPESTRING))

            result = self.cursor.fetchone()

            if result is not None:
                return True, result
            else:
                return False, None

    def get_groups(self):
        self.cursor.execute("""
                            SELECT group_name FROM ban_groups
                            """)

        group_tuples = self.cursor.fetchall()
        return [group_tuple[0] for group_tuple in group_tuples]

    def raw_ban(self, banstring, group_name, ban_reason, timestamp=(-1), banlength=(-1)):
        self._ban(banstring, group_name, ban_reason, timestamp, banlength)

    def raw_unban(self, banstring, group_name):
        self._unban(banstring, group_name)

    # We do the reverse of what _create_sql_pattern is doing.
    # The result is a string which should be correct for using the
    # banUser and unbanUser methods, and the ban/unban commands.
    def unescape_banstring(self, banstring):
        finstring = StringIO()
        length = len(banstring)

        string_iter = enumerate(banstring)

        for pos, char in string_iter:
            chars_left = length - pos - 1

            if char == "[" and chars_left >= 3:
                nextchar = banstring[pos + 1]
                closed_bracket = banstring[pos + 2]

                if closed_bracket == "]":
                    finstring.write(nextchar)
                    next(string_iter)
                    next(string_iter)
                    continue

            if char in self.ESCAPE:
                finstring.write(self.ESCAPESTRING + char)
                continue

            finstring.write(char)

        return finstring.getvalue()

    def _ban(
        self,
        banstring,
        group_name="Global",
        ban_reason="None",
        timestamp=(-1),
        banlength=(-1),
    ):
        self.cursor.execute(
            """
                            INSERT INTO ban_list(group_name, pattern, ban_reason, timestamp, banlength)
                            VALUES (?, ?, ?, ?, ?)
                            """,
            (group_name, banstring, ban_reason, timestamp, banlength),
        )

        self.conn.commit()

    def _unban(self, banstring, group_name="Global"):
        self.cursor.execute(
            """
                            DELETE FROM ban_list
                            WHERE group_name = ? AND pattern = ?
                            """,
            (group_name, banstring),
        )

        self.conn.commit()

    def _ban_exists(self, group_name, banstring):
        self.cursor.execute(
            """
                            SELECT 1 FROM ban_list
                            WHERE group_name = ? AND pattern = ?
                            """,
            (group_name, banstring),
        )

        result = self.cursor.fetchone()
        logger.debug("Query result: %s (type: %s)", result, type(result))
        return bool(result is not None and result[0] == 1)

    def _group_exists(self, group_name):
        self.cursor.execute(
            """
                            SELECT 1 FROM ban_groups
                            WHERE group_name = ?
                            """,
            (group_name,),
        )

        result = self.cursor.fetchone()
        logger.debug("Query result: %s (type: %s)", result, type(result))
        return bool(result is not None and result[0] == 1)

    def _is_valid_string(self, string):
        return all(char in ALLOWEDCHARS for char in string)

    def _assemble_ban_string(self, user, ident, host):
        escaped_user = self._create_sql_pattern(user)
        escaped_ident = self._create_sql_pattern(ident, ident=True)
        escaped_host = self._create_sql_pattern(host, hostname=True)

        banstring = f"{escaped_user}!{escaped_ident}@{escaped_host}"

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
    def _create_sql_pattern(self, string, hostname=False, ident=False):

        new_string = StringIO()

        # Both flags should not be set at once.
        assert not (hostname is True and ident is True)

        for pos, char in enumerate(string):
            # We try reverse-escaping:
            # - escaped chars will be written as literals
            # - non-escaped chars included in the escape string will be escaped
            # pos == 0 is an exception because characters at this
            # position cannot be escaped in any way that makes sense.
            if char == self.ESCAPESTRING:
                continue
            if char in self.NOT_ESCAPE or (pos > 0 and string[pos - 1] == self.ESCAPESTRING and char in self.ESCAPE):
                new_string.write(char)
            elif char in self.ESCAPE:
                # new_string.write(self.ESCAPESTRING+char)
                new_string.write("[" + char + "]")
            else:
                if (
                    (not hostname and not ident and char not in ALLOWEDCHARS)
                    or (hostname and char not in ALLOWEDCHARS_HOST)
                    or (ident and char not in ALLOWEDCHARS_IDENT)
                ):
                    raise InvalidCharacterUsed(string, char, pos)
                else:
                    new_string.write(char)

        return new_string.getvalue()
