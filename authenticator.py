"""U-Home authentication module."""

from abc import ABC,abstractmethod
import logging
import secrets
import aiohttp
from datetime import datetime, timedelta
from aiohttp import ClientSession
from urllib.parse import urlencode
from const import AUTH_BASE_URL, TOKEN_BASE_URL
from exceptions import AuthenticationError

_LOGGER = logging.getLogger(__name__)

class AuthenticationHandler(ABC):
    """Handles U-Home authentication."""

    def __init__(self, client_id: str, client_secret: str,scope: str, redirect_uri: str):
        """Initialize the authentication handler."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.access_token = None
        self.token_expiry = None
        self.refresh_token = None
        self._auth_callback = None

    def generate_auth_url(self, state: str = None) -> str:
        """Generate auth U-Tec Auth URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope,
            'redirect_uri': self.redirect_uri,
            'state': state or self._generate_state()
        }
        return f"{AUTH_BASE_URL}/{urlencode(params)}"

    @abstractmethod
    async def async_get_access_token(self, session: aiohttp.ClientSession, auth_token: str) -> str:
        """Exchange auth code for access token"""
        data = {
            'grant_type': 'authorisation_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_token,
            'redirect_uri': self.redirect_uri
        }
        async with session.post(
            TOKEN_BASE_URL,
            data=data
        ) as response:
            if response.status != 200:
                raise AuthenticationError(f"Token request failed: {await response.text()}")

            token_data = await response.json()
            self._update_tokens(token_data)
            return token_data
    
    async def refresh_access_token(self, session: ClientSession) -> dict:
        """Refresh access token via token API"""
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'refresh_token': self.refresh_token,
        }

        async with session.post(
            TOKEN_BASE_URL,
            data=data,
        ) as response:
            if response.status != 200:
                raise AuthenticationError(f"Token request failed: {await response.text()}")
            
            token_data = await response.json()
            self._update_tokens(token_data)
            return token_data

    def _update_tokens(self, token_data: dict):
        """Update token data from response"""
        self.access_token = token_data['access_token']
        self.refresh_token = token_data['refresh_token']
        expires_in = token_data.get('expires_in, 3600')
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

    def _generate_state(self) -> str:
        """generate a random string to add to auth URL"""
        return secrets.token_urlsafe(16)

    @property
    def is_token_valid(self) -> bool:
        """Verify token validity"""
        return (
        self.access_token is not None
        and self.token_expiry is not None
        and datetime.now() < self.token_expiry - timedelta(minutes=5)
        )