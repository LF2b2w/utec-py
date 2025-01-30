"""U-Home authentication module."""

from abc import ABC,abstractmethod
from aiohttp import ClientResponse, ClientSession

class abtractAuth(ABC):
    """Abstract class for token exchange and authentication"""
    def __init__(self, websession: ClientSession, host: str):
        """Initialise auth handler class"""
        self.websession = websession
        self.host = host
    
    @abstractmethod
    async def async_exchange_authCode_for_accessToken(self) -> str:
        """Return a valid access token"""
    
    async def async_make_auth_request(self, method, url, **kwargs) -> ClientResponse:
        """Make an authenticated request"""
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)

        access_token = await self.async_exchange_authCode_for_accessToken()
        headers["authorization"] = f"Bearer {access_token}"

        return await self.websession.request(
            method, f"{self.host}/{url}", **kwargs, headers=headers,
        )