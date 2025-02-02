from typing import Dict, Any, Optional
from uuid import uuid4
import logging
from .const import ApiNamespace, ApiOperation, ApiRequest
from .exceptions import ApiError
from .auth import AbstractAuth

logger = logging.getLogger(__name__)

class UHomeApi:
    """U-Home API client implementation."""

    def __init__(self, auth: AbstractAuth):
        self.auth = auth

    async def _create_request(
        self,
        namespace: ApiNamespace,
        operation: ApiOperation,
        parameters: Optional[Dict] = None
    ) -> ApiRequest:
        """Create a standardized API request."""
        header = {
            "namespace": namespace,
            "name": operation,
            "messageID": str(uuid4()),
            "payloadVersion": "1",
        }
        return {
            "header": header,
            "payload": parameters
        }

    async def _make_request(self, method: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated API request."""
        async with self.auth.async_make_auth_request(method, **kwargs) as response:
            if response.status == 204:
                return {}
            if response.status in (200, 201, 202):
                return await response.json()

            error_text = await response.text()
            logger.error(f"API error: {response.status} - {error_text}")
            raise ApiError(response.status, error_text)

    async def discover_devices(self) -> Dict[str, Any]:
        """Discover available devices."""
        payload = await self._create_request(
            ApiNamespace.DEVICE,
            ApiOperation.DISCOVERY
        )
        return await self._make_request("POST", json=payload)

    async def query_device(self, device_id: str) -> Dict[str, Any]:
        """Query device status."""
        params = {
            "devices": [{"id": device_id}]
        }
        payload = await self._create_request(
            ApiNamespace.DEVICE,
            ApiOperation.QUERY,
            params
        )
        return await self._make_request("POST", json=payload)

    async def send_command(
        self,
        device_id: str,
        capability: str,
        command: str,
        arguments: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send command to device."""
        command_data = {
            "capability": capability,
            "name": command
        }
        if arguments:
            command_data["arguments"] = arguments

        params = {
            "devices": [{
                "id": device_id,
                "command": command_data
            }]
        }

        payload = await self._create_request(
            ApiNamespace.DEVICE,
            ApiOperation.COMMAND,
            params
        )
        return await self._make_request("POST", json=payload)

    async def close(self):
        """Close the API client."""
        await self.auth.close()