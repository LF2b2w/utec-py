"""U-Home API client."""

import logging
from typing import Dict, Any, Optional
from .exceptions import ApiError
from uuid import uuid4
from .auth import AbstractAuth, UtecOAuth2

#_LOGGER = logging.getLogger(__name__)

class UHomeApi:
    """U-Home API client."""

    def __init__(self, auth: AbstractAuth):
        self.auth = auth

    async def _package_and_perform_request(
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

    async def _api_call(self, method: str, **kwargs) -> Dict[str, Any]:
        async with self.auth.async_make_auth_request(method, **kwargs) as response:
            if response.status == 204:
                return {}
            elif response.status in (200, 201, 202):
                return await response.json()
            raise ApiError(response.status, await response.text())

    async def _discover(self):
        return await self._package_and_perform_request("Uhome.Device","Discovery",None)
    
    async def _query_device(self,device_id):
        params = {
            "devices": [
                {
                    "id": device_id
                }
            ]
        }
        return await self._package_and_perform_request("Uhome.Device","Query",params)

    async def _send_command(self, device_id, capability, command):
        params = {
                "devices": [
                    {
                        "id": device_id,
                "command": {
                    "capability": capability,
                    "name": command
                        }
                    }
                ]
            }
        return await self._package_and_perform_request("Uhome.Device", "Command", params)
    
    async def _send_command_with_arg(self, device_id, capability, command, arguments: dict):
        params = {
                "devices": [
                    {
                "id": device_id,
                "command": {
                    "capability": capability,
                    "name": command,
                    "arguments": { arguments
                            }
                        }
                    }
                ]
            }   
        return await self._package_and_perform_request("Uhome.Device", "Command", params)

    async def close(self):
        """Close the API client."""
        await self.auth.close()