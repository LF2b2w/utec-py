"""Device handler for creating device instances based on discovery data"""

import logging
from typing import Dict, Type, Optional

from .exceptions import DeviceError
from .api import UHomeApi
from .devices.device import BaseDevice
from .devices.light import UtecLight
from .devices.lock import UtecLock
from .devices.switch import UtecSwitch
from .const import (
    ATTR_HANDLE_TYPE,
    ATTR_DEVICE_ID,
    HandleType,
    HANDLE_TYPE_CAPABILITIES
)

_LOGGER = logging.getLogger(__name__)


class DeviceFacilitator:
    """class for creating device instances based on discovery data"""

    # Map handle types to device classes
    _handle_type_mapping: Dict[str, Type[BaseDevice]] = {
        HandleType.UTEC_LOCK: UtecLock,
        HandleType.UTEC_LOCK_SENSOR: UtecLock,
        HandleType.UTEC_DIMMER: UtecLight,
        HandleType.UTEC_LIGHT_RGBAW: UtecLight,
        HandleType.UTEC_SWITCH: UtecSwitch
    }

    @classmethod
    def create_device(cls, discovery_data: dict, api: UHomeApi) -> Optional[BaseDevice]:
        """
        Create and return appropriate device instance based on discovery data.

        Args:
            discovery_data: Dictionary containing device discovery information
            api: Instance of UHomeApi for device communication

        Returns:
            BaseDevice: Instance of appropriate device class

        Raises:
            DeviceError: If device creation fails or handle type is not supported
        """
        try:
            # Extract required fields
            handle_type = discovery_data.get(ATTR_HANDLE_TYPE)
            device_id = discovery_data.get(ATTR_DEVICE_ID)

            if not handle_type:
                raise DeviceError(
                    f"Missing handle type in discovery data for device: {device_id}"
                )

            # Get the appropriate device class
            device_class = cls._handle_type_mapping.get(handle_type)
            if not device_class:
                _LOGGER.warning(
                    f"Unsupported handle type: {handle_type} for device: {device_id}"
                )
                return None

            # Add capabilities to discovery data
            capabilities = HANDLE_TYPE_CAPABILITIES.get(handle_type, set())
            discovery_data['supportedCapabilities'] = capabilities

            # Create device instance
            device = device_class(discovery_data, api)

            # Validate device capabilities
            cls._validate_device_capabilities(device, capabilities)

            return device

        except Exception as err:
            raise DeviceError(
                f"Failed to create device from discovery data: {err}"
            ) from err

    @staticmethod
    def _validate_device_capabilities(device: BaseDevice, required_capabilities: set) -> None:
        """
        Validate that the device has all required capabilities.

        Args:
            device: Device instance to validate
            required_capabilities: Set of required capabilities

        Raises:
            DeviceError: If device is missing required capabilities
        """
        missing_capabilities = required_capabilities - set(device.supportedCapabilities)
        if missing_capabilities:
            raise DeviceError(
                f"Device {device.device_id} missing required capabilities: {missing_capabilities}"
            )

    @classmethod
    def register_device_class(
        cls,
        handle_type: str,
        device_class: Type[BaseDevice],
        capabilities: set
    ) -> None:
        """
        Register a new device class for a handle type.

        Args:
            handle_type: Handle type identifier
            device_class: Device class to register
            capabilities: Set of capabilities required for this device type
        """
        cls._handle_type_mapping[handle_type] = device_class
        HANDLE_TYPE_CAPABILITIES[handle_type] = capabilities
        _LOGGER.debug(f"Registered new device class {device_class.__name__} for handle type {handle_type}")

    @classmethod
    def get_supported_handle_types(cls) -> list:
        """
        Get list of supported handle types.

        Returns:
            list: List of supported handle types
        """
        return list(cls._handle_type_mapping.keys())

    @classmethod
    def get_device_capabilities(cls, handle_type: str) -> set:
        """
        Get capabilities for a specific handle type.

        Args:
            handle_type: Handle type to get capabilities for

        Returns:
            set: Set of capabilities for the handle type
        """
        return HANDLE_TYPE_CAPABILITIES.get(handle_type, set())