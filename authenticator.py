"""U-Home authentication module."""

import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
import webbrowser
from urllib.parse import urlencode
from .const import DEFAULT_AUTH_BASE_URL
from .exceptions import AuthenticationError

_LOGGER = logging.getLogger(__name__)

class AuthenticationHandler:
    """Handles U-Home authentication."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize the authentication handler."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.token_expiry = None
        self._auth_callback = None

    async def authenticate(self, session: aiohttp.ClientSession) -> str:
        """Perform authentication and return access token."""
        auth_code = await self._get_authorization_code()
        return await self._get_access_token(session, auth_code)

    async def _get_authorization_code(self) -> str:
        """Get authorization code through OAuth flow."""
        state = str(int(datetime.now().timestamp()))
        auth_params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'all',
            'redirect_uri': self.redirect_uri,
            'state': state
        }

        auth_url = f"{DEFAULT_AUTH_BASE_URL}/authorize?{urlencode(auth_params)}"

        # Start callback server and get code
        code = await self._start_auth_server(auth_url, state)
        if not code:
            raise AuthenticationError("Failed to get authorization code")
        return code

    async def _start_auth_server(self, auth_url: str, state: str) -> str:
        """Start local server to receive OAuth callback."""
        self._auth_callback = AuthCallback()
        runner = web.AppRunner(self._auth_callback.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()

        webbrowser.open(auth_url)

        try:
            # Wait for callback
            for _ in range(60):  # 60 second timeout
                if self._auth_callback.auth_code:
                    if self._auth_callback.state != state:
                        raise AuthenticationError("State mismatch")
                    return self._auth_callback.auth_code
                await asyncio.sleep(1)
            raise AuthenticationError("Authorization timeout")
        finally:
            await runner.cleanup()

    async def _get_access_token(self, session: aiohttp.ClientSession, auth_code: str) -> str:
        """Exchange authorization code for access token."""
        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'code': auth_code
        }

        async with session.get(
            f"{DEFAULT_AUTH_BASE_URL}/token",
            params=params
        ) as response:
            if response.status != 200:
                raise AuthenticationError(f"Token request failed: {await response.text()}")

            data = await response.json()
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            return self.access_token

    def validate_token(self) -> bool:
        """Check if current token is valid."""
        return (
            self.access_token is not None
            and self.token_expiry is not None
            and datetime.now() < self.token_expiry - timedelta(minutes=5)
        )

class AuthCallback:
    """Handle OAuth callback."""

    def __init__(self):
        """Initialize callback handler."""
        self.auth_code = None
        self.state = None
        self.app = web.Application()
        self.app.router.add_get('/', self._handle_callback)

    async def _handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback."""
        self.auth_code = request.query.get('authorization_code')
        self.state = request.query.get('state')
        return web.Response(text="Authorization successful! You can close this window.")