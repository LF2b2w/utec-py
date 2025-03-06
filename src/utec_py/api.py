"""Api class for Uhome/Utec API."""

from enum import Enum
import logging
from typing import Any, Dict, TypedDict
from uuid import uuid4

from attr import dataclass

from .auth import AbstractAuth
from .const import API_BASE_URL
from .exceptions import ApiError

logger = logging.getLogger(__name__)


@dataclass
class ApiNamespace(str, Enum):
    DEVICE = "Uhome.Device"
    USER = "Uhome.User"


@dataclass
class ApiOperation(str, Enum):
    DISCOVERY = "Discovery"
    QUERY = "Query"
    COMMAND = "Command"


@dataclass
class ApiHeader(TypedDict):
    namespace: str
    name: str
    messageID: str
    payloadVersion: str


@dataclass
class ApiRequest(TypedDict):
    header: ApiHeader
    payload: dict | None


class UHomeApi:
    """U-Home API client implementation."""

    def __init__(self, Auth: AbstractAuth):
        """Initialise the API."""
        self.auth = Auth

    async def async_create_request(
        self, namespace: ApiNamespace, operation: ApiOperation, parameters: dict | None
    ) -> ApiRequest:
        """Create a standardised API request."""
        header = {
            "namespace": namespace,
            "name": operation,
            "messageID": str(uuid4()),
            "payloadVersion": "1",
        }
        return {"header": header, "payload": parameters}

    async def _async_make_request(self, **kwargs):
        """Make an authenticated API request."""
        response = await self.auth.async_make_auth_request(
            "POST", API_BASE_URL, **kwargs
        )
        try:
            if response.status == 204:
                return {}
            elif response.status in (200, 201, 202):
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"API error: {response.status} - {error_text}")
                raise ApiError(response.status, error_text)
        finally:
            await response.release()

    async def validate_auth(self) -> bool:
        """Validate authentication by making a test request."""
        try:
            await self.discover_devices()
            return True  # noqa: TRY300
        except ApiError:
            return False

    async def discover_devices(self) -> Dict[str, Any]:
        """Discover available devices."""
        logger.debug("Discovering devices")
        payload = await self.async_create_request(
            ApiNamespace.DEVICE, ApiOperation.DISCOVERY, None
        )
        return await self._async_make_request(json=payload)

    async def get_device_state(
        self, device_ids: list, custom_data: dict | None
    ) -> Dict[str, Any]:
        """Query device status."""
        devices = []
        for device_id in device_ids:
            device = {"id": device_id}
            if custom_data:
                device["custom_data"] = custom_data
            devices.append(device)
        params = {"devices": devices}
        payload = await self.async_create_request(
            ApiNamespace.DEVICE, ApiOperation.QUERY, params
        )
        return await self._async_make_request(json=payload)
    
    async def query_device(self, device_id: str):
        device = [{"id": device_id}]
        params = {"devices": device}
        payload = await self.async_create_request(
            ApiNamespace.DEVICE, ApiOperation.QUERY, params
        )
        logger.debug("Querying device with device ID %s and payload %s", device_id, payload)
        return await self._async_make_request(json=payload)

    async def send_command(
        self, device_id: str, capability: str, command: str, arguments: dict | None
    ) -> Dict[str, Any]:
        """Send command to device."""
        command_data = {"capability": capability, "name": command}
        if arguments:
            command_data["arguments"] = arguments

        params = {"devices": [{"id": device_id, "command": command_data}]}

        payload = await self.async_create_request(
            ApiNamespace.DEVICE, ApiOperation.COMMAND, params
        )
        logger.debug("Sending Command %s to device %s, with payload %s", command, device_id, payload)
        return await self._async_make_request(json=payload)

    async def close(self):
        """Close the API client."""
        await self.auth.close()
