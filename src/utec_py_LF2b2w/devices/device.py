from typing import Optional, Set

from .device_types import DeviceCommand, DeviceCapability, HandleType, HANDLE_TYPE_CAPABILITIES
from ..api import UHomeApi
from ..exceptions import DeviceError

class DeviceInfo:
    """Class that represents device information in the U-Home API."""

    def __init__(self, raw_data: dict):
        """Initialize a device info object."""
        self.raw_data = raw_data

    @property
    def manufacturer(self) -> str:
        """Return the manufacturer of the device."""
        return self.raw_data.get("manufacturer", "")

    @property
    def model(self) -> str:
        """Return the model of the device."""
        return self.raw_data.get("model", "")

    @property
    def serial_number(self) -> Optional[str]:
        """Return the serial number of the device."""
        return self.raw_data.get("serialNumber")

class BaseDevice:
    """Base class for all U-Home devices."""

    def __init__(self, discovery_data: dict, api: UHomeApi):
        self._discovery_data = discovery_data
        self._api = api
        self._id = discovery_data["id"]
        self._name = discovery_data["name"]
        self._handle_type = HandleType(discovery_data["handleType"])
        self._supported_capabilities = discovery_data["supportedCapabilities"]
        self._validate_capabilities()

    @property
    def id(self) -> str:
        return self._discovery_data["id"]
    
    @property
    def supported_capabilities(self) -> Set[DeviceCapability]:
        """Get the set of supported capabilities."""
        return self._supported_capabilities
    
    def has_capability(self, capability: DeviceCapability) -> bool:
        """Check if the device supports a specific capability."""
        return capability in self._supported_capabilities
    
    def _validate_capabilities(self) -> None:
        """Validate that the device has the required capabilities."""
        required_capabilities = HANDLE_TYPE_CAPABILITIES[self._handle_type]
        if not required_capabilities.issubset(self._supported_capabilities):
            missing = required_capabilities - self._supported_capabilities
            raise DeviceError(
                f"Device {self._id} missing required capabilities: {missing}"
            )

    async def send_command(self, command: DeviceCommand) -> None:
        """Send command to device."""
        response = await self.api.send_command(
            self.id,
            command.capability,
            command.name,
            command.arguments
        )
        if response and "payload" in response:
            self._state_data = response["payload"]["devices"][0]

    async def update(self) -> None:
        """Update device state."""
        response = await self.api.query_device(self.id)
        if response and "payload" in response:
            self._state_data = response["payload"]["devices"][0]