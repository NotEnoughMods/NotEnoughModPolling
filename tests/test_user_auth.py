from user_auth import AuthTracker


class TestAuthTracker:
    def test_init_with_userlist(self):
        tracker = AuthTracker(["Alice", "Bob"])
        assert tracker.user_exists("alice")
        assert tracker.user_exists("bob")
        assert not tracker.is_registered("alice")

    def test_case_insensitive_lookup(self):
        tracker = AuthTracker(["Alice"])
        assert tracker.user_exists("ALICE")
        assert tracker.user_exists("alice")
        assert tracker.user_exists("Alice")

    def test_add_user(self):
        tracker = AuthTracker([])
        assert not tracker.user_exists("newuser")
        tracker.add_user("NewUser")
        assert tracker.user_exists("newuser")
        assert not tracker.is_registered("newuser")

    def test_remove_user(self):
        tracker = AuthTracker(["Alice"])
        tracker.remove_user("Alice")
        assert not tracker.user_exists("alice")

    def test_remove_nonexistent_user(self):
        tracker = AuthTracker([])
        # Should not raise, just logs a warning
        tracker.remove_user("nobody")

    def test_register_user(self):
        tracker = AuthTracker(["Alice"])
        assert not tracker.is_registered("alice")
        tracker.register_user("Alice")
        assert tracker.is_registered("alice")

    def test_unregister_user(self):
        tracker = AuthTracker(["Alice"])
        tracker.register_user("Alice")
        assert tracker.is_registered("alice")
        tracker.unregister_user("Alice")
        assert not tracker.is_registered("alice")

    def test_is_registered_nonexistent(self):
        tracker = AuthTracker([])
        assert not tracker.is_registered("nobody")
