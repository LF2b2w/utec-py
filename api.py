"""U-Home API client."""

import logging
import aiohttp
from typing import List, Dict, Any, Optional
from .authenticator import AuthenticationHandler
from .device import Device
from .activity import Activity
from .exceptions import ApiError, ValidationError
from pydantic import BaseModel, Field
from typing import Any, Optional
from uuid import uuid4
import uuid
from .const import (
    DEFAULT_API_BASE_URL,
    DEFAULT_TIMEOUT,
    DEVICE_ACTION_LOCK,
    DEVICE_ACTION_UNLOCK,
    API_RETRY_ATTEMPTS,
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

    async def _send_action(
        self,
        device_id: str,
        action: str,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send action to device."""
        payload = {
            "action": action,
            "parameters": parameters or {}
        }
        return await self._api_call(
            "POST",
            f"/devices/{device_id}/actions",
            json=payload
        )

    async def _api_call(
        self,
        method: str,
        endpoint: str,
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
            f"{DEFAULT_API_BASE_URL}{endpoint}",
            **kwargs
        ) as response:
            if response.status in (200, 201, 202):
                return await response.json()
            else:
                raise ApiError(
                    response.status,
                    await response.text()
                )

    async def close(self):
        """Close the API client."""
        await self.session.close()