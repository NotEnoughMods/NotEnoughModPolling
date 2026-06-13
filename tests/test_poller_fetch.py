import asyncio
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from mod_polling.poller import NEMPException


class _ScriptedServer:
    """A real local aiohttp server that replays a scripted sequence of responses.

    Replaces aioresponses (unmaintained, broke on aiohttp 3.14's ClientResponse
    signature). Because ``fetch_page`` re-requests the same URL on each retry,
    tests need successive requests to receive successive responses, so the
    handler pops one spec per request. Running a real server over the loopback
    interface keeps the tests decoupled from aiohttp's internal mock machinery.
    """

    def __init__(self):
        self._responses = []
        self.app = web.Application()
        self.app.router.add_route("*", "/{tail:.*}", self._handle)
        self._server = TestServer(self.app)

    def script(self, *responses):
        """Queue response specs, consumed in order (one per request).

        Each spec is a dict accepting: ``status`` (default 200), ``headers``,
        ``body`` (text) or ``json`` (serialized as JSON), and ``delay`` (seconds
        to stall before responding, used to provoke a client-side timeout).
        """
        self._responses.extend(responses)

    async def _handle(self, request):
        spec = self._responses.pop(0) if self._responses else {}
        if "delay" in spec:
            await asyncio.sleep(spec["delay"])
        status = spec.get("status", 200)
        headers = spec.get("headers")
        if "json" in spec:
            return web.json_response(spec["json"], status=status, headers=headers)
        return web.Response(status=status, text=spec.get("body", ""), headers=headers)

    async def start(self):
        await self._server.start_server()

    async def close(self):
        await self._server.close()

    def url(self, path="/"):
        return str(self._server.make_url(path))


@pytest.fixture
async def http_server():
    server = _ScriptedServer()
    await server.start()
    yield server
    await server.close()


@pytest.fixture
async def poller_with_session(mod_poller):
    mod_poller.session = aiohttp.ClientSession()
    mod_poller._host_delay = 0
    yield mod_poller
    await mod_poller.session.close()


class TestFetchPage:
    async def test_successful_text_response(self, poller_with_session, http_server):
        http_server.script({"body": "hello world"})
        result = await poller_with_session.fetch_page(http_server.url("/page"))
        assert result == "hello world"

    async def test_successful_json_response(self, poller_with_session, http_server):
        http_server.script({"json": {"key": "value"}})
        result = await poller_with_session.fetch_page(http_server.url("/data.json"), decode_json=True)
        assert result == {"key": "value"}

    async def test_4xx_raises_nemp_exception(self, poller_with_session, http_server):
        http_server.script({"status": 404})
        with pytest.raises(NEMPException, match="HTTP 404"):
            await poller_with_session.fetch_page(http_server.url("/missing"))

    async def test_5xx_raises(self, poller_with_session, http_server):
        http_server.script({"status": 500})
        with pytest.raises(aiohttp.ClientResponseError):
            await poller_with_session.fetch_page(http_server.url("/error"))

    async def test_timeout_propagation(self, poller_with_session, http_server):
        # Server stalls past the client timeout, so the ClientTimeout fires.
        http_server.script({"delay": 0.5})
        with pytest.raises(TimeoutError):
            await poller_with_session.fetch_page(http_server.url("/slow"), timeout=0.1)


class TestFetchPageRetryAfter:
    async def test_429_with_integer_retry_after_waits_and_retries(self, poller_with_session, http_server):
        url = http_server.url("/throttled")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "5"}},
            {"body": "recovered"},
        )
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        mock_sleep.assert_any_await(5.0)

    async def test_429_with_http_date_retry_after_waits_and_retries(self, poller_with_session, http_server):
        url = http_server.url("/throttled-date")
        future = datetime.now(UTC) + timedelta(seconds=30)
        http_date = format_datetime(future, usegmt=True)
        http_server.script(
            {"status": 429, "headers": {"Retry-After": http_date}},
            {"body": "recovered"},
        )
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        slept = [call.args[0] for call in mock_sleep.await_args_list]
        assert any(29 <= v <= 31 for v in slept), f"Expected ~30s sleep, got {slept}"

    async def test_429_with_asctime_obs_date_retry_after(self, poller_with_session, http_server):
        """RFC 9110 §5.6.7 obs-date allows asctime form, which has no timezone."""
        url = http_server.url("/throttled-asctime")
        future = datetime.now(UTC) + timedelta(seconds=20)
        asctime_str = future.strftime("%a %b %d %H:%M:%S %Y")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": asctime_str}},
            {"body": "recovered"},
        )
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        slept = [call.args[0] for call in mock_sleep.await_args_list]
        assert any(18 <= v <= 22 for v in slept), f"Expected ~20s sleep, got {slept}"

    async def test_429_without_retry_after_uses_exponential_backoff_fallback(self, poller_with_session, http_server):
        poller_with_session._host_delay = 0.5
        url = http_server.url("/throttled-no-header")
        http_server.script({"status": 429}, {"body": "recovered"})
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        # Backoff fires BEFORE the retry, so it's the first sleep call.
        # attempt 0 fallback: min(0.5 * 2^0, 60) = 0.5
        slept = [c.args[0] for c in mock_sleep.await_args_list]
        assert slept[0] == 0.5, f"Expected backoff 0.5 as first sleep, got: {slept}"

    async def test_429_with_garbled_retry_after_uses_exponential_backoff_fallback(
        self, poller_with_session, http_server
    ):
        poller_with_session._host_delay = 0.5
        url = http_server.url("/throttled-garbled")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "soon-ish"}},
            {"body": "recovered"},
        )
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        slept = [c.args[0] for c in mock_sleep.await_args_list]
        assert slept[0] == 0.5, f"Expected backoff 0.5 as first sleep, got: {slept}"

    async def test_429_fallback_caps_at_60s_with_large_host_delay(self, poller_with_session, http_server):
        poller_with_session._host_delay = 1000
        url = http_server.url("/throttled-big-delay")
        http_server.script({"status": 429}, {"body": "recovered"})
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "recovered"
        # min(1000 * 2^0, 60) = 60 — the cap kicks in
        mock_sleep.assert_any_await(60.0)

    async def test_429_then_429_then_success(self, poller_with_session, http_server):
        url = http_server.url("/twice-throttled")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "5"}},
            {"status": 429, "headers": {"Retry-After": "3"}},
            {"body": "finally"},
        )
        with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await poller_with_session.fetch_page(url)
        assert result == "finally"
        mock_sleep.assert_any_await(5.0)
        mock_sleep.assert_any_await(3.0)

    async def test_429_three_times_raises_after_two_retries(self, poller_with_session, http_server):
        url = http_server.url("/persistently-throttled")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "1"}},
            {"status": 429, "headers": {"Retry-After": "1"}},
            {"status": 429, "headers": {"Retry-After": "1"}},
        )
        with (
            patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(NEMPException, match="HTTP 429"),
        ):
            await poller_with_session.fetch_page(url)

    async def test_429_exhausted_logs_warning(self, poller_with_session, http_server, caplog):
        url = http_server.url("/exhausted")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "1"}},
            {"status": 429, "headers": {"Retry-After": "1"}},
            {"status": 429, "headers": {"Retry-After": "1"}},
        )
        with (
            patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level("WARNING", logger="mod_polling.poller"),
            pytest.raises(NEMPException),
        ):
            await poller_with_session.fetch_page(url)
        matching = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and url in r.getMessage() and "exhausted" in r.getMessage().lower()
        ]
        messages = [r.getMessage() for r in caplog.records]
        assert matching, f"Expected WARNING log mentioning exhausted attempts, got: {messages}"

    async def test_429_logs_cooldown_at_info(self, poller_with_session, http_server, caplog):
        url = http_server.url("/throttled-logged")
        http_server.script(
            {"status": 429, "headers": {"Retry-After": "7"}},
            {"body": "recovered"},
        )
        with (
            patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level("INFO", logger="mod_polling.poller"),
        ):
            await poller_with_session.fetch_page(url)
        matching = [
            r for r in caplog.records if r.levelname == "INFO" and url in r.getMessage() and "7" in r.getMessage()
        ]
        messages = [r.getMessage() for r in caplog.records]
        assert matching, f"Expected INFO log mentioning URL and duration, got: {messages}"


class TestFetchJson:
    async def test_delegates_to_fetch_page(self, poller_with_session, http_server):
        http_server.script({"json": {"data": [1, 2, 3]}})
        result = await poller_with_session.fetch_json(http_server.url("/api"))
        assert result == {"data": [1, 2, 3]}
