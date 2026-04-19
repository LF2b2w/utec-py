"""Abstraction layer for device interaction - Switch."""

# src/utec_py_LF2b2w/devices/switch.py

from .device import BaseDevice
from .device_const import DeviceCapability, DeviceCommand, SwitchState


class Switch(BaseDevice):
    """Represents a Switch device in the U-Home API.

    Maps to Home Assistant's switch platform.
    """

    @property
    def is_on(self) -> bool:
        """Get switch state."""
        state = self._get_state_value(DeviceCapability.SWITCH, "switch")
        return state == SwitchState.ON if state is not None else False

    @property
    def available(self) -> bool:
        """Device availability for Home Assistant."""
        return self._state_data is not None

    async def turn_on(self) -> None:
        """Turn on the switch.

        Per st.switch capability spec, the command name is "on" with no arguments.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="on",
        )
        await self.send_command(command)

    async def turn_off(self) -> None:
        """Turn off the switch.

        Per st.switch capability spec, the command name is "off" with no arguments.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="off",
        )
        await self.send_command(command)
