from unittest.mock import AsyncMock

import pytest

from mod_polling.poller import NEMPException


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
