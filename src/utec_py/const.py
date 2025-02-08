"""U-Home API constants."""
from enum import Enum
from typing import TypedDict, Optional

AUTH_BASE_URL = "https://oauth.u-tec.com/authorize?"
TOKEN_BASE_URL = "https://oauth.u-tec.com/token?"
API_BASE_URL = "https://api.u-tec.com/action"

ATTR_HANDLE_TYPE = "handleType"
ATTR_DEVICE_ID = "id"
ATTR_NAME = "name"
ATTR_CATEGORY = "category"
ATTR_DEVICE_INFO = "deviceInfo"
ATTR_ATTRIBUTES = "attributes"

class ApiNamespace(str, Enum):
    DEVICE = "Uhome.Device"
    USER = "Uhome.User"

class ApiOperation(str, Enum):
    DISCOVERY = "Discovery"
    QUERY = "Query"
    COMMAND = "Command"

class ApiHeader(TypedDict):
    namespace: str
    name: str
    messageID: str
    payloadVersion: str

class ApiRequest(TypedDict):
    header: ApiHeader
    payload: Optional[dict]