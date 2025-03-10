"""Abstraction layer for device interaction - Lock."""

from .device import BaseDevice
from .device_const import DeviceCapability, DeviceCategory, DeviceCommand, LockState


class Lock(BaseDevice):
    """Represents a Switch device in the U-Home API.

    Maps to Home Assistant's switch platform.
    """

    @property
    def has_door_sensor(self) -> bool:
        """Check if the lock has a door sensor capability."""
        return self.has_capability(DeviceCapability.DOOR_SENSOR)

    @property
    def door_state(self) -> str | None:
        """Get the door state if door sensor is present."""
        if not self.has_door_sensor:
            return None
        return self._get_state_value(DeviceCapability.DOOR_SENSOR, "sensorState")

    @property
    def category(self) -> DeviceCategory:
        """Get the device category."""
        return DeviceCategory.LOCK

    @property
    def lock_state(self) -> str:
        """Get the current lock state."""
        state = self._get_state_value(DeviceCapability.LOCK, "lockState")
        return state if state else "Unkown"

    @property
    def battery_status(self) -> str | None:
        """Get the current battery level (1-5)."""
        BattLevel = self._get_state_value(DeviceCapability.BATTERY_LEVEL, "level")
        Battery_states = {
            1: "Critically Low",
            2: "Low",
            3: "Medium",
            4: "High",
            5: "Full"
        }
        return Battery_states.get(BattLevel)
    
    @property
    def battery_level(self) -> int | None:
        """Get the current battery level and convert to percent"""
        level = self._get_state_value(DeviceCapability.BATTERY_LEVEL, "level")
        if level is None:
            return None
        batt_map = {1: 10, 2:30, 3:50, 4:70, 5:100}
        return batt_map.get(level, 0)

    @property
    def is_locked(self) -> bool:
        """Check if the lock is in locked state."""
        state = self._get_state_value(DeviceCapability.LOCK, "lockstate")
        return state == LockState.LOCKED if state is not None else False

    @property
    def is_door_closed(self) -> bool | None:
        """Check if the door is closed (binary sensor)."""
        if not self.has_door_sensor:
            return None
        return self.door_state == "Closed"

    async def lock(self) -> None:
        """Lock the device."""
        command = DeviceCommand(capability=DeviceCapability.LOCK, name="lock")
        await self.send_command(command)

    async def unlock(self) -> None:
        """Unlock the device."""
        command = DeviceCommand(capability=DeviceCapability.LOCK, name="unlock")
        await self.send_command(command)

    async def update(self) -> None:
        """Update device state."""
        await super().update()
