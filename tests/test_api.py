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
