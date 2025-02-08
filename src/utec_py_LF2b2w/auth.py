"""Oauth2 abstract class and in-built handler"""

from abc import ABC, abstractmethod
import datetime
from aiohttp import ClientResponse, ClientSession
from .exceptions import AuthenticationError
from .const import TOKEN_BASE_URL, API_BASE_URL

class AbstractAuth(ABC):
    """Abstract auth class to allow for custom handling of Oauth2 config"""

    def __init__(self, websession: ClientSession, host: str):
        """Initialise the Auth handler"""
        self.websession = websession
        self.host = host

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token (refresh if needed)"""

    async def make_request(self, method, url, **kwargs) -> ClientResponse:
        """Make an authenticated API request"""
        return await self.websession.request(
            method,
            f"{self.host}/{url}",
            **kwargs,
            )
    
    async def close(self) -> None:
        """Close the session."""
        if self._websession:
            await self._websession.close()


class UtecOAuth2(AbstractAuth):
    """Library handler for Oauth2 authentication and token management"""

    def __init__(self, websession, client_id, client_secret, token=None):
        """Initialise the library handler"""
        super().__init__(websession, host=API_BASE_URL)
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None
        self._update_from_token(token)

    @property
    def is_token_expired(self):
        return datetime.datetime.now(datetime.timezone.utc) > self._expires_at if self._expires_at else True

    def _update_from_token(self, token):
        """Update current token values with values from a new token"""
        if token:
            self._access_token = token["access_token"]
            self._refresh_token = token.get("refresh_token")
            expires_in = token["expires_in"]
            self._expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in - 30)

    async def async_get_access_token(self):
        """Retrieve an access token"""
        if self.is_token_expired and self._refresh_token:
            await self.async_refresh_tokens()
        return self._access_token

    async def async_exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens"""
        if self.token is None:
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
        """Refresh access token using refresh token"""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        return await self._token_request(data)

    async def _token_request(self, data: dict) -> dict:
        """Request a token from the API"""
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