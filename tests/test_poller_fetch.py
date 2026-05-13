from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import AsyncMock, patch

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


class TestFetchPageRetryAfter:
    async def test_429_with_integer_retry_after_waits_and_retries(self, poller_with_session):
        url = "https://example.com/throttled"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "5"})
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            mock_sleep.assert_any_await(5.0)

    async def test_429_with_http_date_retry_after_waits_and_retries(self, poller_with_session):
        url = "https://example.com/throttled-date"
        future = datetime.now(UTC) + timedelta(seconds=30)
        http_date = format_datetime(future, usegmt=True)
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": http_date})
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            slept = [call.args[0] for call in mock_sleep.await_args_list]
            assert any(29 <= v <= 31 for v in slept), f"Expected ~30s sleep, got {slept}"

    async def test_429_with_asctime_obs_date_retry_after(self, poller_with_session):
        """RFC 9110 §5.6.7 obs-date allows asctime form, which has no timezone."""
        url = "https://example.com/throttled-asctime"
        future = datetime.now(UTC) + timedelta(seconds=20)
        asctime_str = future.strftime("%a %b %d %H:%M:%S %Y")
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": asctime_str})
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            slept = [call.args[0] for call in mock_sleep.await_args_list]
            assert any(18 <= v <= 22 for v in slept), f"Expected ~20s sleep, got {slept}"

    async def test_429_without_retry_after_uses_exponential_backoff_fallback(self, poller_with_session):
        poller_with_session._host_delay = 0.5
        url = "https://example.com/throttled-no-header"
        with aioresponses() as mocked:
            mocked.get(url, status=429)
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            # Backoff fires BEFORE the retry, so it's the first sleep call.
            # attempt 0 fallback: min(0.5 * 2^0, 60) = 0.5
            slept = [c.args[0] for c in mock_sleep.await_args_list]
            assert slept[0] == 0.5, f"Expected backoff 0.5 as first sleep, got: {slept}"

    async def test_429_with_garbled_retry_after_uses_exponential_backoff_fallback(self, poller_with_session):
        poller_with_session._host_delay = 0.5
        url = "https://example.com/throttled-garbled"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "soon-ish"})
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            slept = [c.args[0] for c in mock_sleep.await_args_list]
            assert slept[0] == 0.5, f"Expected backoff 0.5 as first sleep, got: {slept}"

    async def test_429_fallback_caps_at_60s_with_large_host_delay(self, poller_with_session):
        poller_with_session._host_delay = 1000
        url = "https://example.com/throttled-big-delay"
        with aioresponses() as mocked:
            mocked.get(url, status=429)
            mocked.get(url, body="recovered")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "recovered"
            # min(1000 * 2^0, 60) = 60 — the cap kicks in
            mock_sleep.assert_any_await(60.0)

    async def test_429_then_429_then_success(self, poller_with_session):
        url = "https://example.com/twice-throttled"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "5"})
            mocked.get(url, status=429, headers={"Retry-After": "3"})
            mocked.get(url, body="finally")
            with patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await poller_with_session.fetch_page(url)
            assert result == "finally"
            mock_sleep.assert_any_await(5.0)
            mock_sleep.assert_any_await(3.0)

    async def test_429_three_times_raises_after_two_retries(self, poller_with_session):
        url = "https://example.com/persistently-throttled"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "1"})
            mocked.get(url, status=429, headers={"Retry-After": "1"})
            mocked.get(url, status=429, headers={"Retry-After": "1"})
            with (
                patch("mod_polling.poller.asyncio.sleep", new_callable=AsyncMock),
                pytest.raises(NEMPException, match="HTTP 429"),
            ):
                await poller_with_session.fetch_page(url)

    async def test_429_exhausted_logs_warning(self, poller_with_session, caplog):
        url = "https://example.com/exhausted"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "1"})
            mocked.get(url, status=429, headers={"Retry-After": "1"})
            mocked.get(url, status=429, headers={"Retry-After": "1"})
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

    async def test_429_logs_cooldown_at_info(self, poller_with_session, caplog):
        url = "https://example.com/throttled-logged"
        with aioresponses() as mocked:
            mocked.get(url, status=429, headers={"Retry-After": "7"})
            mocked.get(url, body="recovered")
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
    async def test_delegates_to_fetch_page(self, poller_with_session):
        with aioresponses() as mocked:
            mocked.get("https://example.com/api", payload={"data": [1, 2, 3]})
            result = await poller_with_session.fetch_json("https://example.com/api")
            assert result == {"data": [1, 2, 3]}
