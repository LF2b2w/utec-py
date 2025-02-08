# test_utec.py
# Test Command: python -m pytest tests/
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from aioresponses import aioresponses
import pytest_asyncio

from src.utec_py_LF2b2w.api import UHomeApi, ApiError
from src.utec_py_LF2b2w.auth import UtecOAuth2
from src.utec_py_LF2b2w.devices.device import BaseDevice
from src.utec_py_LF2b2w.device_handler import DeviceFacilitator
from src.utec_py_LF2b2w.const import (
    API_BASE_URL,
    HandleType,
    DeviceCapability
)
from src.utec_py_LF2b2w.exceptions import AuthenticationError, DeviceError

# Fixtures
@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest_asyncio.fixture
async def mock_session():
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.fixture
def oauth_config():
    return {
        "client_id": "test_client",
        "client_secret": "test_secret",
        "token": None,
    }

@pytest.mark.asyncio
async def test_oauth2_token_refresh(mock_session, mock_aioresponse, oauth_config):
    # Setup expired token
    expired_token = {
        "access_token": "expired_token",
        "refresh_token": "valid_refresh",
        "expires_in": 0,
    }

    # Mock refresh response
    mock_aioresponse.post(
        "https://oauth.u-tec.com/token",
        payload={
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        },
    )

    # Test token refresh
    auth = UtecOAuth2(mock_session, **oauth_config)
    auth._update_from_token(expired_token)

    # Verify token refresh
    assert await auth.async_get_access_token() == "new_token"
    assert auth._access_token == "new_token"
    assert auth._expires_at > datetime.datetime.now(datetime.timezone.utc)

@pytest.mark.asyncio
async def test_async_make_request(mock_session, mock_aioresponse):
    mock_aioresponse.post(
        API_BASE_URL,
        status=200,
        payload={"status": "success"}
    )
    api = UHomeApi(mock_session, "test_token")
    response = await api.async_make_request()
    assert response == {"status": "success"}

@pytest.mark.asyncio
async def test_discover_devices_success(mock_session, mock_aioresponse):
    expected_payload = {"devices": [{"id": "123"}]}
    mock_aioresponse.post(
        API_BASE_URL,
        status=200,
        payload=expected_payload,
    )
    api = UHomeApi(mock_session, "test_token")
    response = await api.discover_devices()
    assert response == expected_payload

@pytest.mark.asyncio
async def test_api_call_error(mock_session, mock_aioresponse):
    mock_aioresponse.post(
        API_BASE_URL,
        status=400,
        body="Bad request"
    )
    api = UHomeApi(mock_session, "test_token")
    with pytest.raises(ApiError) as exc_info:
        await api.discover_devices()
    assert "400" in str(exc_info.value)

def test_device_parsing():
    sample_data = {
        "id": "device_123",
        "name": "Smart Switch",
        "handleType": HandleType.UTEC_SWITCH,
        "deviceInfo": {
            "manufacturer": "U-Tec",
            "model": "SW-2023",
            "hwVersion": "1.0",
        },
        "supportedCapabilities": {"Switch"}  # Add required field
    }
    mock_api = MagicMock(spec=UHomeApi)

    with patch.object(DeviceFacilitator, '_validate_device_capabilities') as mock_validate:
        device = DeviceFacilitator.create_device(sample_data, mock_api)
        assert device.id == "device_123"
        assert DeviceCapability.SWITCH in device.supported_capabilities
        assert device._discovery_data["deviceInfo"]["manufacturer"] == "U-Tec"
        mock_validate.assert_called_once()

def test_device_facilitator_unsupported_handle_type():
    sample_data = {
        "id": "device_456",
        "name": "Unsupported Device",
        "handleType": "unknown-handle",
        "deviceInfo": {"manufacturer": "U-Tec"}
    }
    mock_api = MagicMock(spec=UHomeApi)
    device = DeviceFacilitator.create_device(sample_data, mock_api)
    assert device is None

@pytest.mark.asyncio
async def test_send_command(mock_session, mock_aioresponse):
    mock_aioresponse.post(
        API_BASE_URL,
        status=200,
        payload={"result": "success"}
    )
    api = UHomeApi(mock_session, "test_token")
    response = await api.send_command("device_123", "Switch", "on", None)
    assert response == {"result": "success"}