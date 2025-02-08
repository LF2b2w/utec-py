# src/utec_py_LF2b2w/devices/switch.py

from .device import BaseDevice
from .device_const import SwitchState, DeviceCapability, DeviceCommand

class Switch(BaseDevice):
    """
    Represents a Switch device in the U-Home API.
    Maps to Home Assistant's switch platform.
    """

    @property
    def is_on(self) -> bool:
        """
        Get switch state.
        Maps to Home Assistant's is_on property.
        """
        state = self._get_state_value(DeviceCapability.SWITCH, "switch")
        return state == SwitchState.ON if state is not None else False

    @property
    def available(self) -> bool:
        """Device availability for Home Assistant."""
        return self._state_data is not None

    async def turn_on(self) -> None:
        """
        Turn on the switch.
        Maps to Home Assistant's async_turn_on.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="switch",
            arguments={"value": SwitchState.ON}
        )
        await self.send_command(command)

    async def turn_off(self) -> None:
        """
        Turn off the switch.
        Maps to Home Assistant's async_turn_off.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="switch",
            arguments={"value": SwitchState.OFF}
        )
        await self.send_command(command)