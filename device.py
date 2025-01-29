"""U-Home device module."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Set

class DeviceCategory(str, Enum):
    """Device categories supported by U-tec."""
    LOCK = "SmartLock"
    LIGHT = "Light"
    SWITCH = "SmartSwitch"
    PLUG = "SmartPlug"

class DeviceHandler(str, Enum):
    """Device handler types supported by U-tec."""
    # Lock Handlers
    UTEC_LOCK = "utec-lock"
    UTEC_LOCK_PRO = "utec-lock-sensor"

    # Light Handlers
    UTEC_BULB_DIMMABLE = "utec-dimmer"
    UTEC_BULB_COLOR_RGBW = "utec-bulb-color-rgbw"

    # Switch Handlers
    UTEC_SWITCH = "utec-switch"

class Capability(str, Enum):
    """Device capabilities supported by U-tec."""
    # Lock Capabilities
    LOCK = "st.lock"
    BATTERYLEVEL = "st.BatteryLevel"
    LOCKUSER = "st.LockUser"
    LOCKSENSOR = "st.DoorSensor"

    # Light Capabilities
    SWITCH = "st.switch"
    SWITCH_LEVEL = "st.switch Level"
    COLOR_CONTROL = "st.color"
    COLOR_TEMPERATURE = "st.colorTemperature"
    BRIGHTNESS = "st.Brightness"

    # Universal Healthcheck Capability
    HEALTHCHECK = "st.healthcheck"

@dataclass
class DeviceInfo:
    """Device information representation."""
    manufacturer: str
    model: str
    hw_version: str
    sw_version: Optional[str] = None
    serial_number: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """Create DeviceInfo instance from API response."""
        return cls(
            manufacturer=data.get('manufacturer', ''),
            model=data.get('model', ''),
            hw_version=data.get('hwVersion', ''),
            sw_version=data.get('swVersion'),
            serial_number=data.get('serialNumber')
        )

@dataclass
class Device:
    """U-Home device representation."""
    id: str
    name: str
    category: DeviceCategory
    handle_type: DeviceHandler
    device_info: DeviceInfo
    capabilities: Set[Capability]
    custom_data: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Convert string values to enums if needed."""
        if isinstance(self.category, str):
            self.category = DeviceCategory(self.category)
        if isinstance(self.handle_type, str):
            self.handle_type = DeviceHandler(self.handle_type)
        if isinstance(self.capabilities, list):
            self.capabilities = {Capability(cap) for cap in self.capabilities}

    @property
    def supports_capability(self) -> callable:
        """Returns a function to check if device supports a specific capability."""
        def _supports(capability: Capability) -> bool:
            return capability in self.capabilities
        return _supports

    @property
    def is_lock(self) -> bool:
        """Check if device is a lock."""
        return self.category == DeviceCategory.LOCK

    @property
    def is_light(self) -> bool:
        """Check if device is a light."""
        return self.category == DeviceCategory.LIGHT

    @property
    def is_switch(self) -> bool:
        """Check if device is a switch."""
        return self.category == DeviceCategory.SWITCH

    @property
    def is_plug(self) -> bool:
        """Check if device is a camera."""
        return self.category == DeviceCategory.PLUG

    # Capability-specific properties

    @property
    def supports_color_temperature(self) -> bool:
        """Check if device supports color temperature."""
        return Capability.COLOR_TEMPERATURE in self.capabilities

    @property
    def supports_dimming(self) -> bool:
        """Check if device supports dimming."""
        return Capability.SWITCH_LEVEL in self.capabilities

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """Create device instance from API response."""
        device_info = DeviceInfo.from_dict(data['deviceInfo']) if 'deviceInfo' in data else None

        # Extract capabilities from the data
        capabilities = set()
        if 'capabilities' in data:
            capabilities = {Capability(cap) for cap in data['capabilities']}

        return cls(
            id=data['id'],
            name=data.get('name', ''),
            category=data.get('category', ''),
            handle_type=data.get('handleType', ''),
            device_info=device_info,
            capabilities=capabilities,
            custom_data=data.get('customData'),
            attributes=data.get('attributes'),
            state=data.get('state')
        )

@dataclass
class ColorTemperatureRange:
    """Color temperature range representation."""
    min: int
    max: int
    step: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorTemperatureRange':
        """Create ColorTemperatureRange instance from API response."""
        return cls(
            min=data.get('min', 2000),
            max=data.get('max', 9000),
            step=data.get('step', 1)
        )

@dataclass
class DeviceList:
    """List of U-Home devices."""
    devices: List[Device]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceList':
        """Create DeviceList instance from API response."""
        devices = [Device.from_dict(device) for device in data.get('devices', [])]
        return cls(devices=devices)

    def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        return next((device for device in self.devices if device.id == device_id), None)

    def get_devices_by_category(self, category: DeviceCategory) -> List[Device]:
        """Get devices by category."""
        return [device for device in self.devices if device.category == category]

    # Convenience methods for specific device types
    def get_locks(self) -> List[Device]:
        """Get all lock devices."""
        return self.get_devices_by_category(DeviceCategory.LOCK)

    def get_lights(self) -> List[Device]:
        """Get all light devices."""
        return self.get_devices_by_category(DeviceCategory.LIGHT)

    def get_switches(self) -> List[Device]:
        """Get all switch devices."""
        return self.get_devices_by_category(DeviceCategory.SWITCH)
    
    def get_plugs(self) -> List[Device]:
        """Get all plug devices."""
        return self.get_devices_by_category(DeviceCategory.PLUG)