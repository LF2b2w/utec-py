"""Base device implementation for U-Home API devices."""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Set

from ..api import UHomeApi
from ..exceptions import DeviceError
from .device_const import HANDLE_TYPE_CAPABILITIES, DeviceCategory, DeviceCommand

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Class that represents device information in the U-Home API."""

    manufacturer: str
    model: str
    hw_version: str
    serial_number: str | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceInfo":
        """Create DeviceInfo instance from API response dictionary."""
        return cls(
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
            hw_version=data.get("hwVersion", ""),
            serial_number=data.get("serialNumber"),
        )


class BaseDevice:
    """Base class for all U-Home devices."""

    def __init__(self, discovery_data: dict, api: UHomeApi) -> None:
        """Initialize the device with discovery data.

        Args:
            discovery_data: Dictionary containing device discovery information
            api: UHomeApi instance for device communication

        Raises:
            DeviceError: If required device information is missing

        """
        self._api = api
        self._discovery_data = discovery_data
        self._state_data: Dict | None = None
        self._last_update: datetime | None = None

        # Extract required fields
        try:
            self._id = discovery_data["id"]
            self._name = discovery_data["name"]
            self._handle_type = discovery_data["handleType"]
            self._category = discovery_data.get("category", "unknown")

            # Parse device info
            device_info_data = discovery_data.get("deviceInfo", {})
            self._device_info = DeviceInfo.from_dict(device_info_data)

            # Get attributes and capabilities
            self._attributes = discovery_data.get("attributes", {})
            self._supported_capabilities = HANDLE_TYPE_CAPABILITIES.get(
                self._handle_type, set()
            )

            self._validate_capabilities()

        except KeyError as err:
            raise DeviceError(
                f"Missing required field in discovery data: {err}"
            ) from err

    @property
    def device_id(self) -> str:
        """Get the unique device ID."""
        return self._id

    @property
    def name(self) -> str:
        """Get the device name."""
        return self._name

    @property
    def handle_type(self) -> str:
        """Get the device handle type."""
        return self._handle_type

    @property
    def category(self) -> DeviceCategory:
        """Get the device category."""
        return DeviceCategory(self._category)

    @property
    def manufacturer(self) -> str:
        """Get the device manufacturer."""
        return self._device_info.manufacturer

    @property
    def model(self) -> str:
        """Get the device model."""
        return self._device_info.model

    @property
    def hw_version(self) -> str:
        """Get the device hardware version."""
        return self._device_info.hw_version

    @property
    def serial_number(self) -> str | None:
        """Get the device serial number."""
        return self._device_info.serial_number

    @property
    def supported_capabilities(self) -> Set[str]:
        """Get the set of supported capabilities."""
        return self._supported_capabilities

    @property
    def available(self) -> bool:
        """Indicate if the device is available."""
        if not self._state_data:
            return False
        return self._get_state_value("st.healthCheck", "status") == "Online"

    @property
    def attributes(self) -> Dict[str, Any]:
        """Get device attributes."""
        return self._attributes

    def has_capability(self, capability: str) -> bool:
        """Check if the device supports a specific capability."""
        return capability in self._supported_capabilities

    def _validate_capabilities(self) -> None:
        """Validate that the device has all required capabilities.

        Raises:
            DeviceError: If device is missing required capabilities

        """
        required_capabilities = HANDLE_TYPE_CAPABILITIES.get(self._handle_type, set())
        if not required_capabilities.issubset(self._supported_capabilities):
            missing = required_capabilities - self._supported_capabilities
            raise DeviceError(
                f"Device {self._id} missing required capabilities: {missing}"
            )

    def _get_state_value(self, capability: str, attribute: str) -> Any:
        """Get a specific state value from device state data.

        Args:
            capability: The capability namespace
            attribute: The attribute name

        Returns:
            The state value if found, None otherwise

        """
        if not self._state_data:
            logger.debug("No state data available for device %s", self.device_id)
            return None

        states = self._state_data.get("states", [])

        if not states:
            logger.debug("Empty states array for device %s", self.device_id)
            return None

        for state in states:
            if state.get("capability") == capability and state.get("name") == attribute:
                logger.debug(
                    "Found %s.%s = %s", capability, attribute, state.get("value")
                )
                return state.get("value")
        logger.debug(
            "State %s.%s not found for device %s", capability, attribute, self.device_id
        )
        return None

    def get_state_data(self) -> dict:
        """Get the current device states in a standardized format."""
        states = {}
        if self._state_data and "states" in self._state_data:
            for state in self._state_data["states"]:
                capability = state.get("capability")
                name = state.get("name")
                value = state.get("value")
                if capability and name:
                    if capability not in states:
                        states[capability] = {}
                    states[capability][name] = value
        return states

    async def send_command(self, command: DeviceCommand) -> None:
        """Send a command to the device.

        Args:
            command: DeviceCommand instance containing command details

        Raises:
            DeviceError: If command sending fails

        """
        logger.debug(
            "Sending command %s for device ID %s", command.name, self.device_id
        )
        try:
            await self._api.send_command(
                self.device_id, command.capability, command.name, command.arguments
            )

            self._last_update = datetime.now()

        except Exception as err:
            raise DeviceError(f"Failed to send command to device: {err}") from err

    async def update(self) -> None:
        """Update device state data.

        Raises:
            DeviceError: If update fails

        """
        logger.debug("updating device %s", self.device_id)
        try:
            response = await self._api.query_device(self.device_id)
            if response and "payload" in response:
                devices = response["payload"].get("devices", [])
                if devices:
                    self._state_data = devices[0]
                    logger.debug(
                        "Updated device %s with data: %s",
                        self.device_id,
                        self._state_data,
                    )
                    self._last_update = datetime.now()

        except Exception as err:
            raise DeviceError(f"Failed to update device state: {err}") from err

    async def update_state_data(self, push_data: dict ) -> Dict[str, Any] | None:
        """Update device data from push data"""
        if "states" in push_data:
            self._state_data = push_data
            logger.debug(
                "Updated device %s with push data: %s",
                self.device_id,
                push_data
            )
            self._last_update = datetime.now()
        else:
            logger.warning(
                "Invalid push data format for device %s: %s",
                self.device_id,
                push_data
            )

    @property
    def device_info(self) -> Dict[str, Any]:
        """Get device information for Home Assistant."""
        return {
            "identifiers": {("uhome", self.device_id)},
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "hw_version": self.hw_version,
        }

    def __str__(self) -> str:
        """Return string representation of the device."""
        return f"{self.__class__.__name__}(id={self.device_id}, name={self.name})"

    def __repr__(self) -> str:
        """Return detailed string representation of the device."""
        return (
            f"{self.__class__.__name__}("
            f"id={self.device_id}, "
            f"name={self.name}, "
            f"type={self.handle_type}, "
            f"category={self.category})"
        )
