"""Tests for AbstractAuth header injection."""

import aiohttp
import pytest
from aioresponses import aioresponses

from utec_py.auth import AbstractAuth


class _FakeAuth(AbstractAuth):
    def __init__(self, session, token="tok-123"):
        super().__init__(session)
        self._token = token

    async def async_get_access_token(self):
        return self._token


@pytest.mark.asyncio
async def test_headers_include_bearer_and_json_content_type():
    async with aiohttp.ClientSession() as session:
        auth = _FakeAuth(session)
        with aioresponses() as mock:
            mock.post("https://example.test/api", payload={"ok": True})
            resp = await auth.async_make_auth_request(
                "POST", "https://example.test/api", json={"hi": 1},
            )
            assert resp.status == 200

            call = mock.requests[("POST", __import__("yarl").URL("https://example.test/api"))][0]
            headers = call.kwargs["headers"]
            assert headers["authorization"] == "Bearer tok-123"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_caller_headers_preserved_and_auth_overrides_nothing_except_auth_token():
    async with aiohttp.ClientSession() as session:
        auth = _FakeAuth(session)
        with aioresponses() as mock:
            mock.post("https://example.test/api", payload={})
            await auth.async_make_auth_request(
                "POST",
                "https://example.test/api",
                headers={"X-Request-Id": "req-42"},
                json={},
            )
            call = mock.requests[("POST", __import__("yarl").URL("https://example.test/api"))][0]
            headers = call.kwargs["headers"]
            assert headers["X-Request-Id"] == "req-42"
            assert headers["authorization"] == "Bearer tok-123"
