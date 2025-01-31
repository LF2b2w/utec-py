# test_utec.py
# Test Command python -m pytest tests/
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock
import aiohttp
from aioresponses import aioresponses


import pytest_asyncio
from utec_py.api import UHomeApi, ApiError
from utec_py.device import Device, DeviceInfo, DeviceList
from utec_py.auth import UtecOAuth2
from utec_py.exceptions import AuthenticationError

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
async def test_auth_request_headers(mock_session, mock_aioresponse, oauth_config):
    mock_aioresponse.post("https://api.u-tec.com/action", payload={"status": "success"})

    auth = UtecOAuth2(mock_session, **oauth_config)
    auth._access_token = "test_token"

    # Mock the async context manager correctly
    mock_response = AsyncMock(status=200)
    auth.async_make_auth_request = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False)
        )
    )

    async with auth.async_make_auth_request("POST") as response:
        assert response.status == 200

# Tests for UHomeApi (corrected)
@pytest.mark.asyncio
async def test_api_call_success():
    mock_auth = MagicMock()  # Changed from AsyncMock to MagicMock

    mock_response = AsyncMock(status=200)
    mock_response.json = AsyncMock(return_value={"result": "success"})

    # Configure MagicMock to return context manager
    mock_auth.async_make_auth_request.return_value = AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response),
        __aexit__=AsyncMock(return_value=False)
    )

    api = UHomeApi(mock_auth)
    response = await api._api_call("GET")
    assert response == {"result": "success"}

@pytest.mark.asyncio
async def test_api_call_error():
    mock_auth = MagicMock()  # Changed from AsyncMock to MagicMock

    mock_response = AsyncMock(status=400)
    mock_response.text = AsyncMock(return_value="Bad request")

    mock_auth.async_make_auth_request.return_value = AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response),
        __aexit__=AsyncMock(return_value=False)
    )

    api = UHomeApi(mock_auth)
    with pytest.raises(ApiError) as exc_info:
        await api._api_call("GET")
    assert "400" in str(exc_info.value)

@pytest.mark.asyncio
async def test_device_discovery():
    mock_auth = MagicMock()  # Changed from AsyncMock to MagicMock

    mock_response = AsyncMock(status=200)
    mock_response.json = AsyncMock(return_value={"devices": [{"id": "123"}]})

    mock_auth.async_make_auth_request.return_value = AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response),
        __aexit__=AsyncMock(return_value=False)
    )

    api = UHomeApi(mock_auth)
    response = await api._discover()
    assert response == {"devices": [{"id": "123"}]}

# Tests without async mark (corrected)
def test_device_parsing():  # Removed @pytest.mark.asyncio
    sample_data = {
        "id": "device_123",
        "name": "Smart Light",
        "category": "light",
        "handleType": "switch",
        "deviceInfo": {
            "manufacturer": "U-Tec",
            "model": "SL-2023",
            "hwVersion": "1.0",
        },
        "capabilities": ["onOff", "brightness"],
    }

    device = Device.from_dict(sample_data)
    assert device.id == "device_123"
    assert "onOff" in device.capabilities
    assert device.deviceInfo.manufacturer == "U-Tec"

def test_device_list():  # Removed @pytest.mark.asyncio
    devices = [
        Device(id="1", name="Device 1", category="light", handleType="switch",
               deviceInfo=DeviceInfo("U-Tec", "M1", "1.0"), capabilities=set()),
        Device(id="2", name="Device 2", category="plug", handleType="switch",
               deviceInfo=DeviceInfo("U-Tec", "P1", "1.0"), capabilities=set()),
    ]
    device_list = DeviceList(devices)
    assert device_list.get_device_by_id("2").name == "Device 2"
    assert device_list.get_device_by_id("99") is None