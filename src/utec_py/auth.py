# auth.py - OAuth2 implementation
from abc import ABC, abstractmethod
from aiohttp import ClientResponse, ClientSession

class AbstractAuth(ABC):
    def __init__(self, websession: ClientSession, host: str):
        self.websession = websession
        self.host = host

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token (refresh if needed)"""
    
    async def async_make_auth_request(self, method, **kwargs) -> ClientResponse:
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)
        
        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        return await self.websession.request(
            method,
            self.host,
            **kwargs,
            header =headers,
            )