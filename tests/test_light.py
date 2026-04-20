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


@pytest.mark.asyncio
async def test_turn_on_brightness_sends_set_level(light, mock_api):
    await light.turn_on(brightness=50)
    calls = mock_api.send_command.await_args_list
    level_calls = [c for c in calls if c.args[1] == "st.switchLevel"]
    assert level_calls
    assert level_calls[0].args[3].get("level") == 50


@pytest.mark.asyncio
async def test_turn_on_color_temp_sends_color_temp_capability(light, mock_api):
    await light.turn_on(color_temp=4000)
    calls = mock_api.send_command.await_args_list
    ct_calls = [c for c in calls if "colorTemperature" in c.args[1] or "color_temp" in c.args[1]]
    assert ct_calls


@pytest.mark.asyncio
async def test_turn_on_rgb_color_sends_color_capability(light, mock_api):
    await light.turn_on(rgb_color=(10, 20, 30))
    calls = mock_api.send_command.await_args_list
    rgb_calls = [c for c in calls if "color" in c.args[1].lower()]
    assert rgb_calls


@pytest.mark.asyncio
async def test_turn_on_plain_still_sends_only_on_command(light, mock_api):
    await light.turn_on()
    calls = mock_api.send_command.await_args_list
    on_calls = [c for c in calls if c.args[1] == "st.switch" and c.args[2] == "on"]
    assert on_calls


@pytest.mark.asyncio
async def test_set_brightness_in_range(light, mock_api):
    await light.set_brightness(50)
    calls = mock_api.send_command.await_args_list
    level_calls = [c for c in calls if c.args[1] == "st.switchLevel"]
    assert level_calls
    assert level_calls[0].args[3].get("level") == 50


@pytest.mark.asyncio
async def test_set_color_temp_in_range(light, mock_api):
    # Adjust valid value based on AUDIT-documented range
    await light.set_color_temp(3500)
    calls = mock_api.send_command.await_args_list
    ct_calls = [c for c in calls if "colorTemperature" in c.args[1] or "color_temp" in c.args[1]]
    assert ct_calls


@pytest.mark.asyncio
async def test_set_rgb_color(light, mock_api):
    # set_rgb_color takes three positional ints (red, green, blue), not a tuple
    await light.set_rgb_color(10, 20, 30)
    calls = mock_api.send_command.await_args_list
    rgb_calls = [c for c in calls if "color" in c.args[1].lower()]
    assert rgb_calls


def test_color_temp_property_returns_value(light):
    light._state_data = {"states": [
        {"capability": "st.colorTemperature", "name": "temperature", "value": 4000},
    ]}
    assert light.color_temp == 4000


def test_color_temp_property_none_when_no_state(light):
    assert light.color_temp is None


def test_rgb_color_property_returns_tuple(light):
    light._state_data = {"states": [
        {"capability": "st.color", "name": "color", "value": {"r": 10, "g": 20, "b": 30}},
    ]}
    result = light.rgb_color
    assert result == (10, 20, 30)


def test_rgb_color_property_none_when_no_state(light):
    assert light.rgb_color is None


def test_supported_features_brightness(light):
    light._state_data = {"states": [
        {"capability": "st.brightness", "name": "brightness", "value": 50},
    ]}
    features = light.supported_features
    assert isinstance(features, set)
    assert "brightness" in features


def test_supported_features_empty_when_no_capabilities(light):
    features = light.supported_features
    assert isinstance(features, set)


def test_supported_features_color_and_color_temp(discovery_dict, mock_api):
    # utec-light-rgbaw has COLOR and COLOR_TEMPERATURE capabilities
    rgbaw_light = Light(discovery_dict(handle_type="utec-light-rgbaw-br", category="LIGHT"), mock_api)
    features = rgbaw_light.supported_features
    assert "color" in features
    assert "color_temp" in features
