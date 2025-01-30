# test_auth.py
# Created/Modified files during execution:
import pytest
import aiohttp
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from authenticator import AuthenticationHandler, AuthCallback
from exceptions import AuthenticationError
from const import DEFAULT_AUTH_BASE_URL


@pytest.mark.asyncio
async def test_auth_handler_init():
    """Test initialization of the AuthenticationHandler."""
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    assert handler.client_id == "test_client_id"
    assert handler.client_secret == "test_client_secret"
    assert handler.scope == "test_scope"
    assert handler.redirect_uri == "http://localhost/redirect"
    assert handler.access_token is None
    assert handler.token_expiry is None
    assert handler._auth_callback is None


@pytest.mark.asyncio
async def test_validate_token():
    """Test validate_token logic."""
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    # No access token saved => invalid
    assert not handler.validate_token()

    # With access token, check expiry
    handler.access_token = "fake_token"
    # Token expiry set in the future => valid
    handler.token_expiry = datetime.now() + timedelta(minutes=10)
    assert handler.validate_token()

    # Token expiry is very close => depends on the margin (5 minutes)
    handler.token_expiry = datetime.now() + timedelta(minutes=4, seconds=30)
    assert not handler.validate_token()

    # Token in the past => invalid
    handler.token_expiry = datetime.now() - timedelta(minutes=10)
    assert not handler.validate_token()


@pytest.mark.asyncio
@patch("authentication_handler.webbrowser.open")
@patch("authentication_handler.web.TCPSite.start")
@patch("authentication_handler.web.AppRunner.setup")
@patch("authentication_handler.web.TCPSite.stop")
async def test_get_authorization_code(
    mock_http_stop, mock_app_setup, mock_tcpsite_start, mock_webbrowser_open
):
    """
    Test _get_authorization_code by mocking out the local server
    and simulating that the callback eventually sets an auth_code.
    """
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    # Patch out the internal _start_auth_server method instead of actually spinning up a server
    with patch.object(handler, "_start_auth_server", return_value="test_code"):
        code = await handler._get_authorization_code()
        assert code == "test_code"
        assert mock_webbrowser_open.called
        assert mock_tcpsite_start.called
        assert mock_app_setup.called


@pytest.mark.asyncio
async def test_get_access_token_success():
    """Test _get_access_token on success."""
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    mock_response = MagicMock()
    mock_response.status = 200
    # Simulate a token JSON
    mock_response.json = MagicMock(
        return_value={
            "access_token": "abc123",
            "expires_in": 3600
        }
    )

    # We patch session.post to return our mock response
    async def mock_post(*args, **kwargs):
        return mock_response

    async with aiohttp.ClientSession() as session:
        with patch.object(session, "post", side_effect=mock_post):
            token = await handler._get_access_token(session, "dummy_code")
            assert token == "abc123"
            assert handler.access_token == "abc123"
            assert handler.token_expiry is not None
            # The difference between now and token_expiry should be around 1 hour
            assert abs((handler.token_expiry - datetime.now()).total_seconds() - 3600) < 5


@pytest.mark.asyncio
async def test_get_access_token_failure():
    """Test _get_access_token on failure (non-200 status code)."""
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    mock_response = MagicMock()
    mock_response.status = 400
    mock_response.text = MagicMock(return_value="Bad request")

    async def mock_post(*args, **kwargs):
        return mock_response

    async with aiohttp.ClientSession() as session:
        with patch.object(session, "post", side_effect=mock_post):
            with pytest.raises(AuthenticationError) as exc:
                await handler._get_access_token(session, "dummy_code")
            assert "Token request failed" in str(exc.value)


@pytest.mark.asyncio
async def test_authenticate():
    """
    Test the full authenticate method. We'll mock out everything so it never does a real request or opens a browser.
    """
    handler = AuthenticationHandler(
        client_id="test_client_id",
        client_secret="test_client_secret",
        scope="test_scope",
        redirect_uri="http://localhost/redirect"
    )

    with patch.object(handler, "_get_authorization_code", return_value="mock_code") as mock_auth_code:
        with patch.object(handler, "_get_access_token", return_value="mock_token") as mock_token:
            async with aiohttp.ClientSession() as session:
                token = await handler.authenticate(session)
                assert token == "mock_token"
                mock_auth_code.assert_called_once()
                mock_token.assert_called_once_with(session, "mock_code")