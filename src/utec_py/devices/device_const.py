"""Device types and constants for U-Home API devices."""

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Dict, Set


class HandleType(str, Enum):
    """Device handle types supported by the API."""

    UTEC_LOCK = "utec-lock"
    UTEC_LOCK_SENSOR = "utec-lock-sensor"
    UTEC_DIMMER = "utec-dimmer"
    UTEC_LIGHT_RGBAW = "utec-light-rgbaw-br"
    UTEC_SWITCH = "utec-switch"


class DeviceCapability(str, Enum):
    """Device capabilities supported by the API."""

    SWITCH = "st.switch"
    LOCK = "st.lock"
    BATTERY_LEVEL = "st.batteryLevel"
    LOCK_USER = "st.lockUser"
    DOOR_SENSOR = "st.doorSensor"
    BRIGHTNESS = "st.brightness"
    COLOR = "st.color"
    COLOR_TEMPERATURE = "st.colorTemperature"
    HEALTH_CHECK = "st.healthCheck"


class DeviceCategory(str, Enum):
    """Device categories as returned by the API."""

    LOCK = "SmartLock"
    PLUG = "SmartPlug"
    SWITCH = "SmartSwitch"
    LIGHT = "LIGHT"
    UNKNOWN = "Unknown"


class LockState(str, Enum):
    """Lock state values from API."""

    LOCKED = "Locked"
    UNLOCKED = "Unlocked"
    JAMMED = "Jammed"
    UNKNOWN = "Unknown"


class LockMode(IntEnum):
    """Lock mode vlaues from API."""

    UNSURE = 0
    LOCKED = 1
    UNLOCKED = 2
    JAMMED = 3
    UNKNOWN = 4


class DoorState(IntEnum):
    """Door state values from API."""

    CLOSED = 1
    OPEN = 2
    UNKNOWN = 3


class SwitchState(IntEnum):
    """Switch state values from API."""

    ON = 1
    OFF = 2
    UNKNOWN = 3


@dataclass
class DeviceCommand:
    """Represents a command to be sent to a U-Home device."""

    capability: str
    name: str
    arguments: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to API-compatible dictionary format."""
        command_dict = {"capability": self.capability, "name": self.name}
        if self.arguments:
            command_dict["arguments"] = self.arguments
        return command_dict


@dataclass
class ColorState:
    """Represents color state of a light."""

    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "ColorState":
        """Create ColorState instance from dictionary."""
        return cls(r=data.get("r", 0), g=data.get("g", 0), b=data.get("b", 0))

    def to_dict(self) -> Dict[str, int]:
        """Convert color state to dictionary format."""
        return {"r": self.r, "g": self.g, "b": self.b}


@dataclass
class ColorTemperatureRange(int):
    """Represents color temperature range for lights."""

    min: int  # Minimum temperature in Kelvin
    max: int  # Maximum temperature in Kelvin
    step: int = 1  # Step size for temperature adjustment


class BrightnessRange(int):
    """Constants for brightness range."""

    MIN = 0
    MAX = 100
    STEP = 1


class ColorTempRange(int):
    """Constants for color temperature range in Kelvin."""

    MIN = 2000
    MAX = 9000
    STEP = 1


# Mapping of handle types to their required capabilities
HANDLE_TYPE_CAPABILITIES: Dict[str, Set[str]] = {
    HandleType.UTEC_LOCK: {
        DeviceCapability.LOCK,
        DeviceCapability.BATTERY_LEVEL,
        DeviceCapability.LOCK_USER,
        DeviceCapability.HEALTH_CHECK,
    },
    HandleType.UTEC_LOCK_SENSOR: {
        DeviceCapability.LOCK,
        DeviceCapability.BATTERY_LEVEL,
        DeviceCapability.DOOR_SENSOR,
        DeviceCapability.HEALTH_CHECK,
    },
    HandleType.UTEC_DIMMER: {
        DeviceCapability.SWITCH,
        DeviceCapability.BRIGHTNESS,
        DeviceCapability.HEALTH_CHECK,
    },
    HandleType.UTEC_LIGHT_RGBAW: {
        DeviceCapability.SWITCH,
        DeviceCapability.BRIGHTNESS,
        DeviceCapability.COLOR,
        DeviceCapability.COLOR_TEMPERATURE,
        DeviceCapability.HEALTH_CHECK,
    },
    HandleType.UTEC_SWITCH: {DeviceCapability.SWITCH, DeviceCapability.HEALTH_CHECK},
}


@dataclass
class DeviceState:
    """Represents a device state in the API."""

    capability: str
    name: str
    value: Any

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceState":
        """Create DeviceState instance from API response dictionary."""
        return cls(
            capability=data["capability"], name=data["name"], value=data["value"]
        )


@dataclass
class DeviceAttributes:
    """Device attributes from discovery data."""

    color_model: str | None = None
    color_temp_range: ColorTemperatureRange | None = None
    switch_type: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceAttributes":
        """Create DeviceAttributes instance from discovery data dictionary."""
        temp_range = None
        if "colorTemperatureRange" in data:
            temp_range = ColorTemperatureRange(
                min=data["colorTemperatureRange"]["min"],
                max=data["colorTemperatureRange"]["max"],
                step=data["colorTemperatureRange"].get("step", 1),
            )

        return cls(
            color_model=data.get("colorModel"),
            color_temp_range=temp_range,
            switch_type=data.get("switchType"),
        )


# State value mapping for Home Assistant integration
STATE_MAP = {
    DoorState.CLOSED: "closed",
    DoorState.OPEN: "open",
    DoorState.UNKNOWN: "unknown",
    SwitchState.ON: "on",
    SwitchState.OFF: "off",
    SwitchState.UNKNOWN: "unknown",
}

# Reverse mapping for command values
COMMAND_MAP = {
    "switch": {"on": SwitchState.ON, "off": SwitchState.OFF},
}
