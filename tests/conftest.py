"""Shared pytest fixtures for utec-py tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import pytest_asyncio

from utec_py.api import UHomeApi
from utec_py.auth import AbstractAuth


class _FakeAuth(AbstractAuth):
    """Concrete AbstractAuth returning a fixed access token."""

    def __init__(self, websession: aiohttp.ClientSession, token: str = "test-token") -> None:
        super().__init__(websession)
        self._token = token

    async def async_get_access_token(self) -> str:
        return self._token


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest_asyncio.fixture
async def fake_auth(session):
    return _FakeAuth(session)


@pytest.fixture
def mock_api() -> MagicMock:
    """AsyncMock-capable UHomeApi stub for device-level tests."""
    api = MagicMock(spec=UHomeApi)
    api.send_command = AsyncMock(return_value={"payload": {"devices": []}})
    api.query_device = AsyncMock(return_value={"payload": {"devices": []}})
    api.get_device_state = AsyncMock(return_value={"payload": {"devices": []}})
    api.discover_devices = AsyncMock(return_value={"payload": {"devices": []}})
    api.set_push_status = AsyncMock(return_value={})
    api.validate_auth = AsyncMock(return_value=True)
    return api


@pytest.fixture
def discovery_dict():
    """Factory for discovery-shape device dicts."""

    def _make(
        handle_type: str = "utec-switch",
        device_id: str = "dev-1",
        name: str = "Test Device",
        category: str = "switch",
        **overrides: Any,
    ) -> dict:
        data = {
            "id": device_id,
            "name": name,
            "handleType": handle_type,
            "category": category,
            "deviceInfo": {
                "manufacturer": "U-Tec",
                "model": "M1",
                "hwVersion": "1.0",
                "serialNumber": "SN-1",
            },
            "attributes": {},
        }
        data.update(overrides)
        return data

    return _make


@pytest.fixture
def state_payload():
    """Factory for state-shape dicts consumed by BaseDevice.update_state_data."""

    def _make(device_id: str = "dev-1", states: list[dict] | None = None) -> dict:
        return {
            "id": device_id,
            "states": states or [
                {"capability": "st.healthCheck", "name": "status", "value": "Online"}
            ],
        }

    return _make
