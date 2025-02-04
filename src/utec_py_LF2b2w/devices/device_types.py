from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Set, Type, TypedDict

class HandleType(str, Enum):
    UTEC_LOCK = "utec-lock"
    UTEC_LOCK_SENSOR = "utec-lock-sensor"
    UTEC_DIMMER = "utec-dimmer"
    UTEC_LIGHT_RGBAW = "utec-light-rgbaw-br"
    UTEC_SWITCH = "utec-switch"

class DeviceCapability(str, Enum):
    SWITCH = "Switch"
    LOCK = "Lock"
    BATTERY_LEVEL = "BatteryLevel"
    LOCK_USER = "LockUser"
    DOOR_SENSOR = "DoorSensor"
    BRIGHTNESS = "Brightness"
    COLOR = "Color"
    COLOR_TEMPERATURE = "ColorTemperature"
    SWITCH_LEVEL = "Switch Level"

@dataclass
class DeviceTypeDefinition:
    handle_type: HandleType
    capabilities: Set[DeviceCapability]
    device_class: Type['BaseDevice']  # Forward reference

# Constants for device capabilities by handle type
HANDLE_TYPE_CAPABILITIES: Dict[HandleType, Set[DeviceCapability]] = {
    HandleType.UTEC_LOCK: {
        DeviceCapability.LOCK,
        DeviceCapability.BATTERY_LEVEL,
        DeviceCapability.LOCK_USER
    },
    HandleType.UTEC_LOCK_SENSOR: {
        DeviceCapability.LOCK,
        DeviceCapability.BATTERY_LEVEL,
        DeviceCapability.DOOR_SENSOR
    },
    HandleType.UTEC_DIMMER: {
        DeviceCapability.SWITCH,
        DeviceCapability.SWITCH_LEVEL
    },
    HandleType.UTEC_LIGHT_RGBAW: {
        DeviceCapability.SWITCH,
        DeviceCapability.BRIGHTNESS,
        DeviceCapability.COLOR,
        DeviceCapability.COLOR_TEMPERATURE
    },
    HandleType.UTEC_SWITCH: {
        DeviceCapability.SWITCH
    }
}
class DeviceCategory(str, Enum):
    """Device categories as returned by the API."""
    LOCK = "smartlock"
    PLUG = "smartplug"
    SWITCH = "smartswitch"
    LIGHT = "light"
    UNKNOWN = "unknown"

class PowerState(str, Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"

@dataclass
class DeviceState:
    capability: str
    name: str
    value: Any

class DeviceCommand:
    def __init__(self, capability: str, name: str, arguments: Optional[Dict] = None):
        self.capability = capability
        self.name = name
        self.arguments = arguments

class ColorModel(str, Enum):
    RGB = "RGB"
    HSV = "HSV"

@dataclass
class ColorTemperatureRange:
    min: int
    max: int

@dataclass
class RGBColor:
    r: int
    g: int
    b: int

    def to_dict(self) -> Dict[str, int]:
        return {"r": self.r, "g": self.g, "b": self.b}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'RGBColor':
        return cls(r=data['r'], g=data['g'], b=data['b'])

class LightAttributes(TypedDict, total=False):
    colorModel: str
    colorTemperatureRange: Dict[str, int]

class LockState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    UNKNOWN = "unknown"