"""Abstract Auth class for Uhome/Utec API."""

# auth.py - OAuth2 implementation

from abc import ABC, abstractmethod

from aiohttp import ClientResponse, ClientSession


class AbstractAuth(ABC):
    """Abstract Auth base for extension in integrations.

    Takes an aiohttp clientsession for extending token management.

    """

    def __init__(self, websession: ClientSession) -> None:
        """Initialise auth class."""
        self.websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token (refresh if needed)."""

    async def async_make_auth_request(
        self, method, host: str, **kwargs
    ) -> ClientResponse:
        """Perfoms authenticated request using the clientsession passed through class init function."""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)

        headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        return await self.websession.request(
            method,
            host,
            **kwargs,
            headers=headers,
        )
