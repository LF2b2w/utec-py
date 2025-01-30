"""U-Home API client."""

import logging
import aiohttp
from typing import Dict, Any, Optional

from authenticator import AuthenticationHandler
from exceptions import ApiError
from uuid import uuid4
from const import (
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

class UHomeApi:
    """U-Home API client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        session: Optional[aiohttp.ClientSession] = None
    ):
        """Initialize the API client."""
        self.session = session or aiohttp.ClientSession()
        self.authenticator = AuthenticationHandler(client_id, client_secret, redirect_uri)

    async def _generate_payload(
        self,
        namespace,
        name,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send action to device."""
        header = {
            "namespace": namespace,
            "name": name,
            "messageID": str(uuid4()),
            "payloadVersion": "1",
        }
        payload={
            "header": header,
            "payload": parameters
        }
        return await self._api_call(
            "POST",
            json=payload
        )   

    async def _api_call(
        self,
        method: str,
        endpoint = "https://api.u-tec.com/action",
        **kwargs
    ) -> Dict[str, Any]:
        """Make API call."""
        if not self.authenticator.validate_token():
            await self.authenticator.authenticate(self.session)

        headers = {
            "Authorization": f"Bearer {self.authenticator.access_token}",
            "Content-Type": "application/json"
        }

        kwargs["headers"] = headers
        kwargs["timeout"] = DEFAULT_TIMEOUT

        async with self.session.request(
            method,
            f"{endpoint}",
            **kwargs
        ) as response:
            if response.status in (200, 201, 202):
                return await response.json()
            else:
                raise ApiError(
                    response.status,
                    await response.text()
                )

    async def _discover(self):
        return self._generate_payload("Uhome.Device","Discovery",None)
    
    async def _query_device(self,device_id):
        params = {
            "devices": [
                {
                    "id": device_id
                }
            ]
        }
        return self._generate_payload("Uhome.Device","Query",params)

    async def _send_command(self, device_id, capability, command):
        params = {
            "devices": [
                {
                    "id": device_id
                },
                {
                    "command": {
                        "capability": capability,
                        "name": command
                    }
                }
            ]
        }
        return self._generate_payload("Uhome.Device", "Command", params)
    
    async def _send_command_with_arg(self, device_id, capability, command, arguments,):
        params = {
            "devices": [
                {
                    "id": device_id
                },
                {
                    "command": {
                        "capability": capability,
                        "name": command,
                        "arguments": {
                            arguments
                        }
                    }
                }
            ]
        }

    async def close(self):
        """Close the API client."""
        await self.session.close()
    
    