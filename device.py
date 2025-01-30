"""U-Home device module."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Set
from .api import UHomeApi

@dataclass
class DeviceInfo:
    """Device information representation."""
    manufacturer: str
    model: str
    hwVersion: str
    swVersion: Optional[str] = None
    serialNumber: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """Create DeviceInfo instance from API response."""
        return cls(
            manufacturer=data.get('manufacturer', ''),
            model=data.get('model', ''),
            hwVersion=data.get('hwVersion', ''),
            swVersion=data.get('swVersion'),
            serialNumber=data.get('serialNumber')
        )

@dataclass
class Device:
    """U-Home device representation."""
    id: str
    name: str
    category: str
    handleType: str
    deviceInfo: DeviceInfo
    capabilities: Set[str]
    customData: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """Create device instance from API response."""
        device_info_data = data.get('deviceInfo')
        device_info = DeviceInfo.from_dict(device_info_data) if device_info_data else None
        capabilities = set(data.get('capabilities', []))

        return cls(
            id=data['id'],
            name=data.get('name', ''),
            category=data.get('category', ''),
            handleType=data.get('handleType', ''),
            deviceInfo=device_info,
            capabilities=capabilities,
            customData=data.get('customData'),
            attributes=data.get('attributes'),
            state=data.get('state')
        )

@dataclass
class ColorTemperatureRange:
    """Color temperature range representation."""
    min: int
    max: int
    step: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorTemperatureRange':
        """Create ColorTemperatureRange instance from API response."""
        return cls(
            min=data['min'],
            max=data['max'],
            step=data.get('step')
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