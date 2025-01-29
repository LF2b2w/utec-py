"""U-Home API constants."""

DEFAULT_AUTH_BASE_URL = "https://oauth.u-tec.com"
DEFAULT_API_BASE_URL = "https://app.uhomelabs.com/api/v1"

DEVICE_TYPE_LOCK = "smartlock"
DEVICE_TYPE_PLUG = "SmartPlug"
DEVICE_TYPE_SWITCH = "SmartSwitch"
DEVICE_TYPE_LIGHT = "Light"

DEVICE_ACTION_LOCK = "lock"
DEVICE_ACTION_UNLOCK = "unlock"
DEVICE_ACTION_SET_TEMP = "setTemperature"
DEVICE_ACTION_TURN_ON = "turnOn"
DEVICE_ACTION_TURN_OFF = "turnOff"

DEFAULT_TIMEOUT = 10
API_RETRY_ATTEMPTS = 30