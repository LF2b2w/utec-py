"""Tests for UHomeApi — transport layer + endpoints."""

from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses

from utec_py.api import UHomeApi
from utec_py.auth import AbstractAuth
from utec_py.const import API_BASE_URL
from utec_py.exceptions import ApiError


class _FakeAuth(AbstractAuth):
    def __init__(self, session):
        super().__init__(session)

    async def async_get_access_token(self):
        return "tok"


@pytest.mark.asyncio
async def test_discover_devices_200_returns_json():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={"payload": {"devices": []}})
            result = await api.discover_devices()
            assert result == {"payload": {"devices": []}}


@pytest.mark.asyncio
async def test_discover_devices_201_returns_json():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=201, payload={"ok": 1})
            result = await api.discover_devices()
            assert result == {"ok": 1}


@pytest.mark.asyncio
async def test_discover_devices_204_returns_empty_dict():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=204)
            result = await api.discover_devices()
            assert result == {}


@pytest.mark.asyncio
async def test_discover_devices_400_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=400, body="Bad Request")
            with pytest.raises(ApiError) as exc:
                await api.discover_devices()
            assert "400" in str(exc.value)


@pytest.mark.asyncio
async def test_discover_devices_500_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=500, body="Server Error")
            with pytest.raises(ApiError):
                await api.discover_devices()


# --- Endpoint payload shapes (reads) ---


def _last_request_body(mock, url=API_BASE_URL):
    key = ("POST", __import__("yarl").URL(url))
    call = mock.requests[key][-1]
    return call.kwargs.get("json")


@pytest.mark.asyncio
async def test_discover_devices_payload_has_discovery_header():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.discover_devices()
            body = _last_request_body(mock)
            assert body["header"]["namespace"] == "Uhome.Device"
            assert body["header"]["name"] == "Discovery"
            assert body["header"]["payloadVersion"] == "1"
            assert "messageId" in body["header"]


@pytest.mark.asyncio
async def test_query_device_sends_single_device_id():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.query_device("abc")
            body = _last_request_body(mock)
            assert body["header"]["name"] == "Query"
            assert body["payload"]["devices"] == [{"id": "abc"}]


@pytest.mark.asyncio
async def test_get_device_state_multi_with_custom_data():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.get_device_state(["a", "b"], {"k": 1})
            body = _last_request_body(mock)
            devices = body["payload"]["devices"]
            assert devices == [
                {"id": "a", "custom_data": {"k": 1}},
                {"id": "b", "custom_data": {"k": 1}},
            ]


@pytest.mark.asyncio
async def test_get_device_state_multi_without_custom_data():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.get_device_state(["a"], None)
            body = _last_request_body(mock)
            assert body["payload"]["devices"] == [{"id": "a"}]
