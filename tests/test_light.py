"""Tests for Light device."""

import pytest

from utec_py.devices.light import Light


@pytest.fixture
def light(discovery_dict, mock_api):
    # category must be "LIGHT" to match DeviceCategory.LIGHT enum value
    return Light(discovery_dict(handle_type="utec-dimmer", category="LIGHT"), mock_api)


def test_is_on_true(light):
    light._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "on"},
    ]}
    assert light.is_on is True


def test_is_on_false_when_off(light):
    light._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "off"},
    ]}
    assert light.is_on is False


def test_is_on_false_when_no_state(light):
    assert light.is_on is False


def test_brightness_returns_level(light):
    light._state_data = {"states": [
        {"capability": "st.switchLevel", "name": "level", "value": 42},
    ]}
    assert light.brightness == 42


def test_brightness_none_when_no_state(light):
    assert light.brightness is None


@pytest.mark.asyncio
async def test_turn_on_plain_sends_on_command(light, mock_api):
    await light.turn_on()
    args = mock_api.send_command.await_args.args
    # BaseDevice.send_command calls api.send_command(device_id, capability, name, arguments)
    assert args[1] == "st.switch"
    assert args[2] == "on"


@pytest.mark.asyncio
async def test_turn_off_sends_off_command(light, mock_api):
    await light.turn_off()
    args = mock_api.send_command.await_args.args
    assert args[1] == "st.switch"
    assert args[2] == "off"


@pytest.mark.asyncio
async def test_turn_on_with_brightness_sets_level(light, mock_api):
    await light.turn_on(brightness=75)
    # send_command is called with capability=st.switchLevel
    calls = mock_api.send_command.await_args_list
    capabilities = [c.args[1] for c in calls]
    assert any("Level" in c or "level" in c for c in capabilities)


@pytest.mark.asyncio
async def test_set_color_temp_out_of_range_raises(light):
    # ColorTempRange.MIN=2000, MAX=9000 — 999_999 is well outside
    with pytest.raises(ValueError):
        await light.set_color_temp(999_999)


@pytest.mark.asyncio
async def test_set_color_temp_in_range_sends_command(light, mock_api):
    await light.set_color_temp(4000)
    args = mock_api.send_command.await_args.args
    assert args[1] == "st.colorTemperature"
    assert args[2] == "temperature"
    assert args[3] == {"value": 4000}
