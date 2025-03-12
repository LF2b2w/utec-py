"""Abstraction layer for sensor entities"""

from .device import BaseDevice
from .device_const import DeviceCapability, DeviceCategory, DeviceCommand, LockState

class Sensor(BaseDevice):
    """Represents a Sensor device in the U-Home API.

    Maps to Home Assistant's Sensor platform.
    """

    