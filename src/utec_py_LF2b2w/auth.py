# auth.py - OAuth2 implementation
from abc import ABC, abstractmethod
import datetime
import time
from aiohttp import ClientResponse, ClientSession
from .exceptions import AuthenticationError
from .const import TOKEN_BASE_URL, API_BASE_URL

class AbstractAuth(ABC):
    def __init__(self, websession: ClientSession, host: str):
        self.websession = websession
        self.host = host
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None

    @property
    def is_token_expired(self):
        return datetime.datetime.now(datetime.timezone.utc) > self._expires_at if self._expires_at else True

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token (refresh if needed)"""
    
    @abstractmethod
    async def async_make_auth_request(self, method, **kwargs) -> ClientResponse:
        """Perform API request"""

class UtecOAuth2(AbstractAuth):
    def __init__(self, websession, client_id, client_secret, token=None):
        super().__init__(websession, host=API_BASE_URL)
        self.client_id = client_id
        self.client_secret = client_secret
        self._update_from_token(token)

    def _update_from_token(self, token):
        if token:
            self._access_token = token["access_token"]
            self._refresh_token = token.get("refresh_token")
            expires_in = token["expires_in"]
            self._expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in - 30)

    async def async_get_access_token(self):
        if self.is_token_expired and self._refresh_token:
            await self.async_refresh_tokens()
        return self._access_token

    async def async_exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        if self.token == None:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
            }
            return await self._token_request(data)
        else:
            return self.async_get_access_token()

    async def async_refresh_tokens(self) -> dict:
        """Refresh access token using refresh token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        return await self._token_request(data)

    async def _token_request(self, data: dict) -> dict:
        async with self.websession.post(
            TOKEN_BASE_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            if resp.status != 200:
                raise AuthenticationError(f"Token request failed: {await resp.text()}")
            token_data = await resp.json()
            self._update_from_token(token_data)
            return token_data

    async def async_make_auth_request(self, method, **kwargs) -> ClientResponse:
        access_token = await self.async_get_access_token()
        headers = kwargs.get("headers", {})
        headers.update({"Authorization": f"Bearer {access_token}"})
        kwargs["headers"] = headers
        return self.websession.request(method, self.host, **kwargs)