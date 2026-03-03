import aiohttp
import pytest
from aioresponses import aioresponses

from mod_polling.poller import NEMPException


@pytest.fixture
async def poller_with_session(mod_poller):
    mod_poller.session = aiohttp.ClientSession()
    mod_poller._host_delay = 0
    yield mod_poller
    await mod_poller.session.close()


class TestFetchPage:
    async def test_successful_text_response(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/page", body="hello world")
            result = await poller_with_session.fetch_page("https://example.com/page")
            assert result == "hello world"

    async def test_successful_json_response(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/data.json", payload={"key": "value"})
            result = await poller_with_session.fetch_page("https://example.com/data.json", decode_json=True)
            assert result == {"key": "value"}

    async def test_4xx_raises_nemp_exception(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/missing", status=404)
            with pytest.raises(NEMPException, match="HTTP 404"):
                await poller_with_session.fetch_page("https://example.com/missing")

    async def test_5xx_raises(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/error", status=500)
            with pytest.raises(aiohttp.ClientResponseError):
                await poller_with_session.fetch_page("https://example.com/error")

    async def test_timeout_propagation(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/slow", exception=TimeoutError())
            with pytest.raises(TimeoutError):
                await poller_with_session.fetch_page("https://example.com/slow", timeout=1)


class TestFetchJson:
    async def test_delegates_to_fetch_page(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/api", payload={"data": [1, 2, 3]})
            result = await poller_with_session.fetch_json("https://example.com/api")
            assert result == {"data": [1, 2, 3]}
