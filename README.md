# utec-py
Python API for U-Tec Devices. Primarily for Home Assistant, but should be able to be used anywhere.

## **This project is still under development. Expect rapid and functionality breaking changes.**

# Classes
## Oauth2.0 Authenticator
Handles most of the Oauth2 authentication process. Generates auth request URL for webauth, and token exchange. Includes token management methods, expiry validation, token refresh. Contains an Abstract method for retrieving initial token to allow for varyation of initial auth request handling.
### UtecOauth2 Constructor

## UhomeApi
U-Tec's API is a single endpoint (https://api.utec.com/action) that uses variable header information in the JSON payload to reach different API interfaces. So this class just handles packaging the variables responsible for different interfaces/actions correctly within the payload of the request.

## Device module
Provides an easy way to organise/ingest device info without much significant change to the raw response. With devices stored in the format:
```
            id=data['id'],
            name=data.get('name', ''),
            category=data.get('category', ''),
            handleType=data.get('handleType', ''),
            deviceInfo=device_info,
            capabilities=capabilities,
            customData=data.get('customData'),
            attributes=data.get('attributes'),
            state=data.get('state')
```
## Device Abstraction
Devices are abstracted via the device type files, API requests are pre-formatted and pre-filled for simple integration with downstream integrations.
Currently Utec only fully supports all functions of locks, but there is limited functionality with switches and lights.

### Methods
#### Token Management
**exchange_code**
Exchanges access token recieved by Oauth2 callback via redirect URI for an access token and a refresh token. Checks to see if client is already authenticated via checking if current token state.

**get_access_token**
Verifies current token validity before returning either a new token obtained via refresh token, or stored token that is still valid.

**_update_from_token**
Updates current token parameters, stores expires_in time and calculates expires_at with a 30s grace period.

#### API Requests
**make_request**
Handles API requests, takes a clientsession websession to perform request function.

## API Manager
**create_request**
Packages request body parameters into a Utec/Uhome compliant standard.

## Install
```
pip install utec_py
```

## Usage
**Abstract Method Auth handling**
```
from utec_py import AbstractAuth
from utec_py import UtecAPI

API = api()

class customAuthImplementation(AbstractAuth):
"""Handle Custom Auth request handling""
    def __init__(self, websession, client_id, client_secret, token=None):
        super().__init__(websession, host=API_BASE_URL)

    async def async_get_auth_implementation():
    """Return authentication for a custom auth implementation""
## API requests can be run with or without custom implementation as API class uses Abstract Auth as a parent to define request processess.
    
    async def async_make_request():
        """Perform API Request"""
```
**In built Auth Handling**
```
from utec_py import UtecOAuth2
from utec_py import UtecAPI
from utec_py import DeviceList

API = api()
Authenticator = UtecOAuth2(client_id, client_secret) # If you already have an access token stored via an application credential manager, you can pass this token to the class or it can be omitted entirely on first run
# Handle oauth web auth flow and obtain access code
Authenticator.exchange_access_code("access_code")
# Which will handle obtaining access tokens and update the stored self token values and then all token management from then on.

# Once Authenication has been completed devices can be called via API
API._discover() # Perform device discovery
API._query_device(device_id) # Query a specific devcie
API._send_command(device_id, capability, command, args)
```

