from typing import ClassVar
from unittest.mock import AsyncMock

import pytest

from mod_polling.poller import ModPoller, NEMPException


class TestCheckMCForge2:
    async def test_slim_mode(self, mod_poller):
        mod_poller.mods["ForgeMod"] = {
            "parser": "mcforge_v2",
            "mcforge": {"url": "https://example.com/forge.json", "slim": True},
        }
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "promos": {
                    "1.12.2-recommended": "14.23.5.2854",
                    "1.12.2-latest": "14.23.5.2860",
                }
            }
        )
        result = await mod_poller.check_mcforge_v2("ForgeMod")
        assert "1.12.2" in result
        assert result["1.12.2"]["version"] == "14.23.5.2854"
        assert result["1.12.2"]["dev"] == "14.23.5.2860"

    async def test_non_slim_mode(self, mod_poller):
        mod_poller.mods["ForgeMod"] = {
            "parser": "mcforge_v2",
            "mcforge": {
                "url": "https://example.com/forge.json",
                "promo": "recommended",
                "promoType": "version",
            },
        }
        mod_poller.fetch_json = AsyncMock(
            return_value={"promos": {"recommended": {"version": "14.23.5.2854", "mcversion": "1.12.2"}}}
        )
        result = await mod_poller.check_mcforge_v2("ForgeMod")
        assert result["version"] == "14.23.5.2854"
        assert result["mc"] == "1.12.2"

    async def test_non_slim_no_match(self, mod_poller):
        mod_poller.mods["ForgeMod"] = {
            "parser": "mcforge_v2",
            "mcforge": {
                "url": "https://example.com/forge.json",
                "promo": "nope",
                "promoType": "version",
            },
        }
        mod_poller.fetch_json = AsyncMock(return_value={"promos": {}})
        result = await mod_poller.check_mcforge_v2("ForgeMod")
        assert result == {}


class TestCheckJenkins:
    async def test_artifact_extraction(self, mod_poller):
        mod_poller.mods["JenkinsMod"] = {
            "parser": "jenkins",
            "jenkins": {"url": "https://ci.example.com/job/Mod/lastBuild", "item": 0},
            "curse": {"regex": r"Mod-(?P<version>[0-9.]+)\.jar"},
        }
        mod_poller.compile_regex("JenkinsMod")
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "artifacts": [{"fileName": "Mod-1.2.3.jar"}],
                "changeSet": {"items": [{"msg": "Fixed bug"}]},
            }
        )
        result = await mod_poller.check_jenkins("JenkinsMod")
        assert result["version"] == "1.2.3"
        assert result["change"] == "Fixed bug"

    async def test_no_changelog(self, mod_poller):
        mod_poller.mods["JenkinsMod"] = {
            "parser": "jenkins",
            "jenkins": {"url": "https://ci.example.com/job/Mod/lastBuild", "item": 0},
            "curse": {"regex": r"Mod-(?P<version>[0-9.]+)\.jar"},
        }
        mod_poller.compile_regex("JenkinsMod")
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "artifacts": [{"fileName": "Mod-1.2.3.jar"}],
                "changeSet": {"items": []},
            }
        )
        result = await mod_poller.check_jenkins("JenkinsMod")
        assert result["version"] == "1.2.3"
        assert "change" not in result


class TestCheckHTML:
    async def test_basic_parsing(self, mod_poller):
        mod_poller.mods["HTMLMod"] = {
            "parser": "html",
            "html": {"url": "https://example.com/versions.html", "regex": r"(?P<mc>[0-9.]+)/Mod-(?P<version>[0-9.]+)"},
        }
        mod_poller.compile_regex("HTMLMod")
        mod_poller.fetch_page = AsyncMock(return_value="1.12.2/Mod-1.0.0\n1.16.5/Mod-2.0.0")
        result = await mod_poller.check_html("HTMLMod")
        assert result["1.12.2"] == {"version": "1.0.0"}
        assert result["1.16.5"] == {"version": "2.0.0"}

    async def test_reverse_mode(self, mod_poller):
        mod_poller.mods["HTMLMod"] = {
            "parser": "html",
            "html": {
                "url": "https://example.com/versions.html",
                "reverse": True,
                "regex": r"(?P<mc>[0-9.]+)/Mod-(?P<version>[0-9.]+)",
            },
        }
        mod_poller.compile_regex("HTMLMod")
        mod_poller.fetch_page = AsyncMock(return_value="1.12.2/Mod-1.0.0\n1.12.2/Mod-1.1.0")
        result = await mod_poller.check_html("HTMLMod")
        # Reverse mode takes the last match
        assert result["1.12.2"] == {"version": "1.1.0"}

    async def test_dev_version_type(self, mod_poller):
        mod_poller.mods["HTMLMod"] = {
            "parser": "html",
            "html": {
                "url": "https://example.com/versions.html",
                "version_type": "dev",
                "regex": r"(?P<mc>[0-9.]+)/Mod-(?P<version>[0-9.]+)",
            },
        }
        mod_poller.compile_regex("HTMLMod")
        mod_poller.fetch_page = AsyncMock(return_value="1.12.2/Mod-1.0.0")
        result = await mod_poller.check_html("HTMLMod")
        assert result["1.12.2"] == {"dev": "1.0.0"}


class TestCheckSpongeMaven:
    async def test_latest_release_and_dev_per_mc_version(self, mod_poller):
        mod_poller.mods["SpongeForge"] = {
            "parser": "sponge_maven",
            "sponge_maven": {"url": "https://example.com/maven-metadata.xml"},
        }
        mod_poller.fetch_page = AsyncMock(
            return_value="""
                <metadata>
                  <versioning>
                    <versions>
                      <version>1.12.2-2838-7.4.7</version>
                      <version>1.12.2-2838-7.4.8-RC4138</version>
                      <version>1.12.2-2838-7.4.8</version>
                      <version>1.12.2-2838-7.4.9-RC4142</version>
                      <version>1.21.1-52.0.0-12.0.0</version>
                      <version>1.21.1-52.0.0-12.0.1-RC1</version>
                    </versions>
                  </versioning>
                </metadata>
            """
        )

        result = await mod_poller.check_sponge_maven("SpongeForge")

        assert result == {
            "1.12.2": {"version": "7.4.8", "dev": "7.4.9-RC4142"},
            "1.21.1": {"version": "12.0.0", "dev": "12.0.1-RC1"},
        }

    async def test_rejects_malformed_version(self, mod_poller):
        mod_poller.mods["SpongeForge"] = {
            "parser": "sponge_maven",
            "sponge_maven": {"url": "https://example.com/maven-metadata.xml"},
        }
        mod_poller.fetch_page = AsyncMock(
            return_value="<metadata><versioning><versions><version>invalid</version></versions></versioning></metadata>"
        )

        with pytest.raises(NEMPException, match="Unexpected SpongeForge version"):
            await mod_poller.check_sponge_maven("SpongeForge")


class TestCheckCurse:
    async def test_normal_release(self, mod_poller):
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "files": [
                    {
                        "id": 100,
                        "name": "CurseMod-1.5.0.jar",
                        "display": "CurseMod 1.5.0",
                        "type": "release",
                        "versions": ["1.12.2", "Forge"],
                    }
                ]
            }
        )
        result = await mod_poller.check_cfwidget("CurseMod")
        assert "1.12.2" in result
        assert result["1.12.2"]["version"] == "1.5.0"

    async def test_accepted_status_returns_empty(self, mod_poller):
        mod_poller.fetch_json = AsyncMock(return_value={"accepted": True})
        result = await mod_poller.check_cfwidget("CurseMod")
        assert result == {}

    async def test_error_raises(self, mod_poller):
        mod_poller.fetch_json = AsyncMock(return_value={"error": "Project not found"})
        with pytest.raises(NEMPException, match="cfwidget"):
            await mod_poller.check_cfwidget("CurseMod")

    async def test_regex_no_match_latest_raises(self, mod_poller):
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "files": [
                    {
                        "id": 100,
                        "name": "totally-different-name.jar",
                        "type": "release",
                        "versions": ["1.12.2"],
                    }
                ]
            }
        )
        with pytest.raises(NEMPException, match="Regex is outdated"):
            await mod_poller.check_cfwidget("CurseMod")

    async def test_empty_files_returns_empty(self, mod_poller):
        mod_poller.fetch_json = AsyncMock(return_value={"files": []})
        result = await mod_poller.check_cfwidget("CurseMod")
        assert result == {}


class TestCheckGitHubRelease:
    async def test_asset_type_with_regex(self, mod_poller):
        mod_poller.mods["GHMod"] = {
            "parser": "github_release",
            "github": {
                "repo": "owner/repo",
                "type": "asset",
                "regex": r"GHMod-(?P<version>[0-9.]+)\.jar",
            },
        }
        mod_poller.compile_regex("GHMod")
        mod_poller.fetch_json = AsyncMock(
            return_value=[
                {
                    "tag_name": "v1.0",
                    "prerelease": False,
                    "assets": [{"name": "GHMod-1.0.0.jar"}],
                }
            ]
        )
        result = await mod_poller.check_github_release("GHMod")
        assert result["version"] == "1.0.0"

    async def test_asset_type_prerelease(self, mod_poller):
        mod_poller.mods["GHMod"] = {
            "parser": "github_release",
            "github": {
                "repo": "owner/repo",
                "type": "asset",
                "regex": r"GHMod-(?P<version>[0-9.]+)\.jar",
            },
        }
        mod_poller.compile_regex("GHMod")
        mod_poller.fetch_json = AsyncMock(
            return_value=[
                {
                    "tag_name": "v1.0-beta",
                    "prerelease": True,
                    "assets": [{"name": "GHMod-1.0.0.jar"}],
                }
            ]
        )
        result = await mod_poller.check_github_release("GHMod")
        assert result["dev"] == "1.0.0"
        assert "version" not in result

    async def test_tag_type_without_regex(self, mod_poller):
        mod_poller.mods["GHMod"] = {
            "parser": "github_release",
            "github": {"repo": "owner/repo", "type": "tag"},
        }
        mod_poller.fetch_json = AsyncMock(return_value=[{"tag_name": "v2.0.0", "prerelease": False, "assets": []}])
        result = await mod_poller.check_github_release("GHMod")
        assert result["version"] == "v2.0.0"

    async def test_tag_type_with_regex(self, mod_poller):
        mod_poller.mods["GHMod"] = {
            "parser": "github_release",
            "github": {
                "repo": "owner/repo",
                "type": "tag",
                "regex": r"v(?P<version>[0-9.]+)",
            },
        }
        mod_poller.compile_regex("GHMod")
        mod_poller.fetch_json = AsyncMock(return_value=[{"tag_name": "v2.0.0", "prerelease": False, "assets": []}])
        result = await mod_poller.check_github_release("GHMod")
        assert result["version"] == "2.0.0"

    async def test_tag_type_prerelease(self, mod_poller):
        mod_poller.mods["GHMod"] = {
            "parser": "github_release",
            "github": {"repo": "owner/repo", "type": "tag"},
        }
        mod_poller.fetch_json = AsyncMock(return_value=[{"tag_name": "v3.0-rc1", "prerelease": True, "assets": []}])
        result = await mod_poller.check_github_release("GHMod")
        assert result["dev"] == "v3.0-rc1"
        assert "version" not in result


class TestCheckBuildCraft:
    async def test_buildcraft(self, mod_poller):
        mod_poller.mods["BuildCraft"] = {"parser": "buildcraft"}
        mod_poller.fetch_page = AsyncMock(return_value="1.12.2:BuildCraft:7.99.24\n")
        result = await mod_poller.check_buildcraft("BuildCraft")
        assert result["mc"] == "1.12.2"
        assert result["version"] == "7.99.24"


class TestCheckNeoForge:
    NEOFORGE_MOD: ClassVar[dict] = {
        "parser": "neoforge",
        "neoforge": {
            "url": "https://maven.neoforged.net/api/maven/versions/releases/net%2Fneoforged%2Fneoforge",
            "fallback_url": "https://maven.creeperhost.net/api/maven/versions/releases/net%2Fneoforged%2Fneoforge",
        },
    }

    NEOFORGE_WITH_LEGACY_MOD: ClassVar[dict] = {
        "parser": "neoforge",
        "neoforge": {
            "url": "https://maven.neoforged.net/modern",
            "fallback_url": "https://maven.creeperhost.net/modern",
            "legacy_url": "https://maven.neoforged.net/legacy",
            "legacy_fallback_url": "https://maven.creeperhost.net/legacy",
        },
    }

    async def test_multi_mc_versions(self, mod_poller):
        """Both <26 and >=26 version schemes resolve correctly."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "versions": [
                    "20.2.3-beta",
                    "20.2.86",
                    "21.1.0-beta",
                    "21.1.222",
                    "26.1.0.1-beta",
                    "26.1.1.0-beta",
                ]
            }
        )
        result = await mod_poller.check_neoforge("NeoForge")
        assert result["1.20.2"]["version"] == "20.2.86"
        assert result["1.21.1"]["version"] == "21.1.222"
        assert result["26.1"]["dev"] == "26.1.0.1-beta"
        assert result["26.1.1"]["dev"] == "26.1.1.0-beta"

    async def test_beta_only(self, mod_poller):
        """MC version with only beta releases gets dev, no version."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(return_value={"versions": ["26.1.1.0-beta"]})
        result = await mod_poller.check_neoforge("NeoForge")
        assert result["26.1.1"] == {"dev": "26.1.1.0-beta"}

    async def test_stable_suppresses_older_beta(self, mod_poller):
        """When a stable release exists, older betas are not stored as dev."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "versions": [
                    "21.1.0-beta",
                    "21.1.1-beta",
                    "21.1.50",
                    "21.1.100",
                ]
            }
        )
        result = await mod_poller.check_neoforge("NeoForge")
        assert result["1.21.1"]["version"] == "21.1.100"
        assert "dev" not in result["1.21.1"]

    async def test_skips_alpha_zero_and_snapshot(self, mod_poller):
        """Alpha, 0.x, and + (snapshot) versions are excluded."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(
            return_value={
                "versions": [
                    "0.25w14craftmine.3-beta",
                    "21.1.0-alpha.1",
                    "21.1.5+snapshot-1",
                    "21.1.100",
                ]
            }
        )
        result = await mod_poller.check_neoforge("NeoForge")
        assert "0.25" not in result
        assert result == {"1.21.1": {"version": "21.1.100"}}

    async def test_fallback_on_primary_failure(self, mod_poller):
        """Falls back to CreeperHost mirror when primary fails."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(
            side_effect=[
                Exception("primary down"),
                {"versions": ["21.1.50"]},
            ]
        )
        result = await mod_poller.check_neoforge("NeoForge")
        assert result["1.21.1"]["version"] == "21.1.50"
        assert mod_poller.fetch_json.call_count == 2

    async def test_fallback_not_attempted_without_url(self, mod_poller):
        """Without fallback_url, primary failure propagates."""
        mod_poller.mods["NeoForge"] = {
            "parser": "neoforge",
            "neoforge": {"url": "https://maven.neoforged.net/..."},
        }
        mod_poller.fetch_json = AsyncMock(side_effect=Exception("primary down"))
        with pytest.raises(Exception, match="primary down"):
            await mod_poller.check_neoforge("NeoForge")

    async def test_legacy_versions_are_merged(self, mod_poller):
        mod_poller.mods["NeoForge"] = self.NEOFORGE_WITH_LEGACY_MOD
        mod_poller.fetch_json = AsyncMock(
            side_effect=[
                {"versions": ["21.1.222"]},
                {"versions": ["1.20.1-47.1.5", "1.20.1-47.1.106"]},
            ]
        )

        result = await mod_poller.check_neoforge("NeoForge")

        assert result["1.20.1"] == {"version": "47.1.106"}
        assert result["1.21.1"] == {"version": "21.1.222"}

    async def test_legacy_fallback_on_primary_failure(self, mod_poller):
        mod_poller.mods["NeoForge"] = self.NEOFORGE_WITH_LEGACY_MOD
        mod_poller.fetch_json = AsyncMock(
            side_effect=[
                {"versions": ["21.1.222"]},
                Exception("legacy primary down"),
                {"versions": ["1.20.1-47.1.106"]},
            ]
        )

        result = await mod_poller.check_neoforge("NeoForge")

        assert result["1.20.1"] == {"version": "47.1.106"}
        assert mod_poller.fetch_json.call_count == 3

    async def test_legacy_failure_preserves_modern_results(self, mod_poller):
        mod_poller.mods["NeoForge"] = self.NEOFORGE_WITH_LEGACY_MOD
        mod_poller.fetch_json = AsyncMock(
            side_effect=[
                {"versions": ["21.1.222"]},
                Exception("legacy primary down"),
                Exception("legacy fallback down"),
            ]
        )

        result = await mod_poller.check_neoforge("NeoForge")

        assert result == {"1.21.1": {"version": "21.1.222"}}

    async def test_malformed_legacy_version_is_ignored(self, mod_poller):
        mod_poller.mods["NeoForge"] = self.NEOFORGE_WITH_LEGACY_MOD
        mod_poller.fetch_json = AsyncMock(
            side_effect=[
                {"versions": []},
                {"versions": ["1.20.1-47.1.106", "47.1.82"]},
            ]
        )

        result = await mod_poller.check_neoforge("NeoForge")

        assert result == {"1.20.1": {"version": "47.1.106"}}

    async def test_empty_versions(self, mod_poller):
        """Empty versions list returns empty result."""
        mod_poller.mods["NeoForge"] = self.NEOFORGE_MOD
        mod_poller.fetch_json = AsyncMock(return_value={"versions": []})
        result = await mod_poller.check_neoforge("NeoForge")
        assert result == {}


class TestNeoForgeMcVersion:
    """Unit tests for the MC version derivation helper."""

    def test_old_scheme(self):
        assert ModPoller._neoforge_mc_version("21.1.222") == "1.21.1"

    def test_old_scheme_beta(self):
        assert ModPoller._neoforge_mc_version("20.2.3-beta") == "1.20.2"

    def test_new_scheme_minor_zero(self):
        assert ModPoller._neoforge_mc_version("26.1.0.19-beta") == "26.1"

    def test_new_scheme_minor_nonzero(self):
        assert ModPoller._neoforge_mc_version("26.1.1.0-beta") == "26.1.1"

    def test_new_scheme_stable(self):
        assert ModPoller._neoforge_mc_version("26.1.1.5") == "26.1.1"
