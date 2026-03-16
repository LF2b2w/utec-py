"""Abstraction layer for device interaction - Light."""
# src/utec_py_LF2b2w/devices/light.py

from typing import Tuple  # noqa: UP035

from .device import BaseDevice
from .device_const import (
    BrightnessRange,
    ColorState,
    ColorTempRange,
    DeviceCapability,
    DeviceCommand,
    SwitchState,
)


class Light(BaseDevice):
    """Represents a Light device in the U-Home API.

    Maps to Home Assistant's light platform.
    """

    @property
    def is_on(self) -> bool:
        """Get light state."""
        state = self._get_state_value(DeviceCapability.SWITCH, "switch")
        return state == SwitchState.ON if state is not None else False

    @property
    def brightness(self) -> int | None:
        """Get brightness level (0-100).

        The API reports brightness under st.switchLevel / level, not st.brightness.
        """
        return self._get_state_value(DeviceCapability.SWITCH_LEVEL, "level")

    @property
    def color_temp(self) -> int | None:
        """Get color temperature in Kelvin."""
        return self._get_state_value(DeviceCapability.COLOR_TEMPERATURE, "temperature")

    @property
    def rgb_color(self) -> Tuple[int, int, int] | None:
        """Get RGB color."""
        color_data = self._get_state_value(DeviceCapability.COLOR, "color")
        if color_data:
            color = ColorState.from_dict(color_data)
            return (color.r, color.g, color.b)
        return None

    @property
    def supported_features(self) -> set:
        """Get supported features for Home Assistant."""
        features = set()
        if self.has_capability(DeviceCapability.BRIGHTNESS):
            features.add("brightness")
        if self.has_capability(DeviceCapability.COLOR):
            features.add("color")
        if self.has_capability(DeviceCapability.COLOR_TEMPERATURE):
            features.add("color_temp")
        return features

    async def turn_on(self, **kwargs) -> None:
        """Turn on the light with optional attributes.

        Per st.switch capability spec, the command name is "on" with no arguments.
        Brightness and color are set via separate commands after the switch-on.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="on",
        )
        await self.send_command(command)

        if "brightness" in kwargs:
            await self.set_brightness(kwargs["brightness"])
        if "color_temp" in kwargs:
            await self.set_color_temp(kwargs["color_temp"])
        if "rgb_color" in kwargs:
            await self.set_rgb_color(*kwargs["rgb_color"])

    async def turn_off(self) -> None:
        """Turn off the light.

        Per st.switch capability spec, the command name is "off" with no arguments.
        """
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH,
            name="off",
        )
        await self.send_command(command)

    async def set_brightness(self, brightness: int) -> None:
        """Set brightness level (1-100).

        Per st.switchLevel capability spec, command is setLevel with a
        "level" argument (integer 0-100). We clamp to 1 as the minimum
        since 0 means off per the spec — use turn_off() for that.
        """
        brightness = max(1, min(BrightnessRange.MAX, brightness))
        command = DeviceCommand(
            capability=DeviceCapability.SWITCH_LEVEL,
            name="setLevel",
            arguments={"level": brightness},
        )
        await self.send_command(command)

    async def set_color_temp(self, temp: int) -> None:
        """Set color temperature in Kelvin."""
        if not ColorTempRange.MIN <= temp <= ColorTempRange.MAX:
            raise ValueError(
                f"Color temperature must be between {ColorTempRange.MIN}K and {ColorTempRange.MAX}K"
            )
        command = DeviceCommand(
            capability=DeviceCapability.COLOR_TEMPERATURE,
            name="temperature",
            arguments={"value": temp},
        )
        await self.send_command(command)

    async def set_rgb_color(self, red: int, green: int, blue: int) -> None:
        """Set RGB color."""
        color = ColorState(r=red, g=green, b=blue)
        command = DeviceCommand(
            capability=DeviceCapability.COLOR,
            name="color",
            arguments={"value": color.to_dict()},
        )
        await self.send_command(command)
