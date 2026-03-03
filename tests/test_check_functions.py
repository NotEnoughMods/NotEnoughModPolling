from unittest.mock import AsyncMock


async def test_forgejson_normal_version(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={
            "promos": {"1.8.9-recommended": "1.0.0"},
            "1.8.9": {"1.0.0": "test changelog"},
        }
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert result["1.8.9"]["version"] == "1.0.0"
    assert "dev" not in result["1.8.9"]


async def test_forgejson_dev_version(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={
            "promos": {"1.8.9-latest": "1.0.0"},
            "1.8.9": {"1.0.0": "test changelog"},
        }
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert "version" not in result["1.8.9"]
    assert result["1.8.9"]["dev"] == "1.0.0"


async def test_forgejson_both_versions_equal(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={
            "promos": {"1.8.9-latest": "1.0.0", "1.8.9-recommended": "1.0.0"},
            "1.8.9": {"1.0.0": "test changelog"},
        }
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert result["1.8.9"]["version"] == "1.0.0"
    assert "dev" not in result["1.8.9"]


async def test_forgejson_both_versions_different(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={
            "promos": {"1.8.9-latest": "1.0.1", "1.8.9-recommended": "1.0.0"},
            "1.8.9": {"1.0.0": "test changelog", "1.0.1": "other changelog"},
        }
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert "version" in result["1.8.9"]
    assert result["1.8.9"]["dev"] == "1.0.1"


async def test_forgejson_no_changelog(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={"promos": {"1.8.9-recommended": "1.0.0"}, "1.8.9": {}}
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert result["1.8.9"]["version"] == "1.0.0"
    assert "dev" not in result["1.8.9"]


async def test_forgejson_no_mcversion_data(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={"promos": {"1.8.9-recommended": "1.0.0"}}
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert "1.8.9" in result
    assert result["1.8.9"]["version"] == "1.0.0"
    assert "dev" not in result["1.8.9"]


async def test_forgejson_no_promos(mod_poller):
    mod_poller.fetch_json = AsyncMock(
        return_value={"1.8.9": {"1.0.0": "test changelog"}}
    )
    result = await mod_poller.CheckForgeJson("TestMod")
    assert result == {}
