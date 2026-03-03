import pytest

from ban_list import InvalidCharacterUsed, NoSuchBanGroup


class TestBanListGroups:
    def test_global_group_exists_on_init(self, ban_list):
        groups = ban_list.get_groups()
        assert "Global" in groups

    def test_define_group(self, ban_list):
        result = ban_list.define_group("TestGroup")
        assert result is True
        assert "TestGroup" in ban_list.get_groups()

    def test_define_group_already_exists(self, ban_list):
        ban_list.define_group("TestGroup")
        result = ban_list.define_group("TestGroup")
        assert result is False

    def test_get_groups(self, ban_list):
        ban_list.define_group("A")
        ban_list.define_group("B")
        groups = ban_list.get_groups()
        assert "Global" in groups
        assert "A" in groups
        assert "B" in groups


class TestBanListBanCRUD:
    def test_ban_user(self, ban_list):
        result = ban_list.ban_user("testuser")
        assert result is True

    def test_ban_user_duplicate_returns_false(self, ban_list):
        ban_list.ban_user("testuser")
        result = ban_list.ban_user("testuser")
        assert result is False

    def test_unban_user(self, ban_list):
        ban_list.ban_user("testuser")
        result = ban_list.unban_user("testuser")
        assert result is True

    def test_unban_user_not_banned(self, ban_list):
        result = ban_list.unban_user("testuser")
        assert result is False

    def test_ban_nonexistent_group_raises(self, ban_list):
        with pytest.raises(NoSuchBanGroup):
            ban_list.ban_user("user", groupName="NoSuchGroup")

    def test_unban_nonexistent_group_raises(self, ban_list):
        with pytest.raises(NoSuchBanGroup):
            ban_list.unban_user("user", groupName="NoSuchGroup")

    def test_ban_in_custom_group(self, ban_list):
        ban_list.define_group("Custom")
        result = ban_list.ban_user("testuser", groupName="Custom")
        assert result is True
        bans = ban_list.get_bans(groupName="Custom")
        assert len(bans) == 1


class TestBanListCheckBan:
    def test_check_ban_matches(self, ban_list):
        ban_list.ban_user("baduser")
        is_banned, result = ban_list.check_ban("baduser", "*", "*")
        assert is_banned is True
        assert result is not None

    def test_check_ban_no_match(self, ban_list):
        ban_list.ban_user("baduser")
        is_banned, result = ban_list.check_ban("gooduser", "ident", "host")
        assert is_banned is False
        assert result is None

    def test_check_ban_wildcard(self, ban_list):
        ban_list.ban_user("*", host="evil.com")
        is_banned, _result = ban_list.check_ban("anyone", "ident", "evil.com")
        assert is_banned is True

    def test_check_ban_nonexistent_group_raises(self, ban_list):
        with pytest.raises(NoSuchBanGroup):
            ban_list.check_ban("user", "ident", "host", groupName="Nope")


class TestBanListGetBans:
    def test_get_all_bans(self, ban_list):
        ban_list.ban_user("user1")
        ban_list.ban_user("user2")
        bans = ban_list.get_bans()
        assert len(bans) == 2

    def test_get_bans_by_group(self, ban_list):
        ban_list.define_group("A")
        ban_list.ban_user("user1", groupName="Global")
        ban_list.ban_user("user2", groupName="A")
        bans = ban_list.get_bans(groupName="A")
        assert len(bans) == 1

    def test_get_bans_nonexistent_group_raises(self, ban_list):
        with pytest.raises(NoSuchBanGroup):
            ban_list.get_bans(groupName="Nope")

    def test_get_bans_matching_string(self, ban_list):
        ban_list.ban_user("specific")
        ban_list.ban_user("other")
        bans = ban_list.get_bans(matchingString="specific!*@*")
        assert len(bans) == 1


class TestBanListClear:
    def test_clear_all_bans(self, ban_list):
        ban_list.ban_user("user1")
        ban_list.ban_user("user2")
        ban_list.clear_all_bans()
        assert ban_list.get_bans() == []

    def test_clear_group_bans(self, ban_list):
        ban_list.define_group("A")
        ban_list.ban_user("user1", groupName="Global")
        ban_list.ban_user("user2", groupName="A")
        ban_list.clear_group_bans("A")
        assert len(ban_list.get_bans(groupName="A")) == 0
        assert len(ban_list.get_bans(groupName="Global")) == 1


class TestBanListValidation:
    def test_invalid_character_raises(self, ban_list):
        with pytest.raises(InvalidCharacterUsed):
            ban_list.ban_user("user\x01")


class TestBanListEscaping:
    def test_create_sql_pattern_and_unescape_roundtrip(self, ban_list):
        original = "test[user]name"
        pattern = ban_list._create_sql_pattern(original)
        unescaped = ban_list.unescape_banstring(pattern)
        assert unescaped == original

    def test_unescape_plain_string(self, ban_list):
        assert ban_list.unescape_banstring("plainuser") == "plainuser"
