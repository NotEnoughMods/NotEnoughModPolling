class TestIsVersionValid:
    def test_valid_version(self, mod_poller):
        assert mod_poller.is_version_valid("1.2.3") is True

    def test_blocklist_jar_rejected(self, mod_poller):
        assert mod_poller.is_version_valid("mod-1.0.jar") is False

    def test_blocklist_src_rejected(self, mod_poller):
        assert mod_poller.is_version_valid("src") is False


class TestCleanVersion:
    def test_whitespace_to_hyphen(self, mod_poller):
        assert mod_poller.clean_version("1.0 beta 2") == "1.0-beta-2"

    def test_tab_to_hyphen(self, mod_poller):
        assert mod_poller.clean_version("1.0\tbeta") == "1.0-beta"

    def test_multiple_hyphens_collapsed(self, mod_poller):
        assert mod_poller.clean_version("1.0  beta") == "1.0-beta"

    def test_no_change_needed(self, mod_poller):
        assert mod_poller.clean_version("1.0.0") == "1.0.0"


class TestCleanMcVersion:
    def test_trim_trailing_zero(self, mod_poller):
        assert mod_poller.clean_mc_version("1.12.0") == "1.12"

    def test_keep_minimum_groups(self, mod_poller):
        assert mod_poller.clean_mc_version("1.0") == "1.0"

    def test_no_trailing_zero(self, mod_poller):
        assert mod_poller.clean_mc_version("1.12.2") == "1.12.2"

    def test_multiple_trailing_zeros(self, mod_poller):
        assert mod_poller.clean_mc_version("1.0.0") == "1.0"


class TestGetProperName:
    def test_exact_match(self, mod_poller):
        assert mod_poller.get_proper_name("TestMod") == "TestMod"

    def test_case_insensitive(self, mod_poller):
        assert mod_poller.get_proper_name("testmod") == "TestMod"

    def test_not_found(self, mod_poller):
        assert mod_poller.get_proper_name("NonExistent") is None


class TestCompileAndMatchRegex:
    def test_compile_regex(self, mod_poller):
        mod_poller.mods["RegexMod"] = {
            "parser": "cfwidget",
            "curse": {"id": "1", "regex": r"RegexMod-(?P<version>[0-9.]+)\.jar"},
        }
        mod_poller.compile_regex("RegexMod")
        assert mod_poller.get_mod_regex("RegexMod") is not None

    def test_match_mod_regex(self, mod_poller):
        mod_poller.mods["RegexMod"] = {
            "parser": "cfwidget",
            "curse": {"id": "1", "regex": r"RegexMod-(?P<version>[0-9.]+)\.jar"},
        }
        mod_poller.compile_regex("RegexMod")
        match = mod_poller.match_mod_regex("RegexMod", "RegexMod-1.2.3.jar")
        assert match is not None
        assert match.group("version") == "1.2.3"

    def test_no_regex(self, mod_poller):
        mod_poller.mods["NoRegex"] = {"parser": "forge_json", "forgejson": {"url": "http://x"}}
        mod_poller.compile_regex("NoRegex")
        assert mod_poller.get_mod_regex("NoRegex") is None


class TestNemVersionHelpers:
    def test_get_set_version(self, mod_poller):
        mod_poller.mods["TestMod"]["nem_versions"] = {}
        mod_poller.set_nem_version("TestMod", "1.0.0", "1.12.2")
        assert mod_poller.get_nem_version("TestMod", "1.12.2") == "1.0.0"

    def test_get_set_dev_version(self, mod_poller):
        mod_poller.mods["TestMod"]["nem_versions"] = {}
        mod_poller.set_nem_dev_version("TestMod", "2.0.0-beta", "1.12.2")
        assert mod_poller.get_nem_dev_version("TestMod", "1.12.2") == "2.0.0-beta"

    def test_dev_only_returns_empty(self, mod_poller):
        mod_poller.mods["TestMod"]["nem_versions"] = {"1.12.2": {"version": "dev-only"}}
        assert mod_poller.get_nem_version("TestMod", "1.12.2") == ""

    def test_mc_mapping_applied(self, mod_poller):
        # mc_mapping has '1.4.6' -> '1.4.7'
        mod_poller.mods["TestMod"]["nem_versions"] = {"1.4.7": {"version": "1.0.0"}}
        assert mod_poller.get_nem_version("TestMod", "1.4.6") == "1.0.0"

    def test_missing_version_returns_empty(self, mod_poller):
        mod_poller.mods["TestMod"]["nem_versions"] = {}
        assert mod_poller.get_nem_version("TestMod", "1.99") == ""
        assert mod_poller.get_nem_dev_version("TestMod", "1.99") == ""
