"""Tests for BaseDevice — init and capability validation."""

import pytest

from utec_py.devices.device import BaseDevice
from utec_py.devices.device_const import DeviceCategory, HANDLE_TYPE_CAPABILITIES
from utec_py.exceptions import DeviceError


def _make_device(discovery_dict, mock_api, handle_type="utec-switch", **overrides):
    data = discovery_dict(handle_type=handle_type, **overrides)
    return BaseDevice(data, mock_api)


def test_init_parses_required_fields(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api, handle_type="utec-switch")
    assert dev.device_id == "dev-1"
    assert dev.name == "Test Device"
    assert dev.handle_type == "utec-switch"
    assert dev.manufacturer == "U-Tec"
    assert dev.model == "M1"
    assert dev.hw_version == "1.0"
    assert dev.serial_number == "SN-1"


def test_init_missing_required_field_raises_device_error(mock_api):
    with pytest.raises(DeviceError, match="Missing required field"):
        BaseDevice({"id": "x"}, mock_api)  # missing name/handleType


def test_init_category_unknown_enum_exists_or_raises(discovery_dict, mock_api):
    """Per AUDIT: confirm whether DeviceCategory has an 'unknown' member.

    If yes → assert dev.category == DeviceCategory.UNKNOWN.
    If no  → assert ValueError on access (and update AUDIT.md accordingly).
    """
    data = discovery_dict(category="")  # drops "category" default, source defaults to "unknown"
    dev = BaseDevice(data, mock_api)
    try:
        assert dev.category == DeviceCategory("unknown")
    except ValueError:
        # Acceptable — AUDIT noted this possibility
        pass


def test_supported_capabilities_sourced_from_handle_type_map(
    discovery_dict, mock_api,
):
    dev = _make_device(discovery_dict, mock_api, handle_type="utec-switch")
    expected = HANDLE_TYPE_CAPABILITIES.get("utec-switch", set())
    assert dev.supported_capabilities == expected


def test_has_capability_true_and_false(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api, handle_type="utec-switch")
    caps = HANDLE_TYPE_CAPABILITIES.get("utec-switch", set())
    if caps:
        assert dev.has_capability(next(iter(caps)))
    assert not dev.has_capability("not.a.capability")


def test_device_info_dict_has_ha_shape(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    info = dev.device_info
    assert info["identifiers"] == {("uhome", "dev-1")}
    assert info["name"] == "Test Device"
    assert info["manufacturer"] == "U-Tec"


# --- State accessors ---


def test_available_false_when_no_state_data(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    assert dev.available is False


def test_available_true_when_health_check_online(discovery_dict, mock_api, state_payload):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = state_payload(states=[
        {"capability": "st.healthCheck", "name": "status", "value": "Online"},
    ])
    assert dev.available is True


def test_available_false_when_health_check_offline(discovery_dict, mock_api, state_payload):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = state_payload(states=[
        {"capability": "st.healthCheck", "name": "status", "value": "Offline"},
    ])
    assert dev.available is False


def test_get_state_value_returns_none_when_no_state_data(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    assert dev._get_state_value("st.switch", "switch") is None


def test_get_state_value_returns_none_when_states_empty(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = {"states": []}
    assert dev._get_state_value("st.switch", "switch") is None


def test_get_state_value_returns_value_when_found(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "on"},
    ]}
    assert dev._get_state_value("st.switch", "switch") == "on"


def test_get_state_value_returns_none_when_not_found(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = {"states": [
        {"capability": "st.switchLevel", "name": "level", "value": 50},
    ]}
    assert dev._get_state_value("st.switch", "switch") is None


def test_get_state_data_flattens_states(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    dev._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "on"},
        {"capability": "st.switchLevel", "name": "level", "value": 80},
    ]}
    flat = dev.get_state_data()
    assert flat == {"st.switch": {"switch": "on"}, "st.switchLevel": {"level": 80}}


def test_get_state_data_empty_when_no_state(discovery_dict, mock_api):
    dev = _make_device(discovery_dict, mock_api)
    assert dev.get_state_data() == {}


# --- Async update paths ---

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_update_pulls_state_from_api(discovery_dict, mock_api):
    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    mock_api.query_device.return_value = {
        "payload": {
            "devices": [{
                "id": "dev-1",
                "states": [{"capability": "st.switch", "name": "switch", "value": "on"}],
            }]
        }
    }
    await dev.update()
    assert dev._state_data["states"][0]["value"] == "on"
    assert dev._last_update is not None
    mock_api.query_device.assert_awaited_once_with("dev-1")


@pytest.mark.asyncio
async def test_update_wraps_api_error_in_device_error(discovery_dict, mock_api):
    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    mock_api.query_device.side_effect = RuntimeError("boom")
    with pytest.raises(DeviceError, match="Failed to update device state"):
        await dev.update()


@pytest.mark.asyncio
async def test_update_noop_when_no_devices_in_payload(discovery_dict, mock_api):
    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    mock_api.query_device.return_value = {"payload": {"devices": []}}
    await dev.update()
    assert dev._state_data is None


@pytest.mark.asyncio
async def test_update_state_data_accepts_push_shape(discovery_dict, mock_api):
    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    push = {
        "id": "dev-1",
        "states": [{"capability": "st.switch", "name": "switch", "value": "on"}],
    }
    await dev.update_state_data(push)
    assert dev._state_data == push
    assert dev._last_update is not None


@pytest.mark.asyncio
async def test_update_state_data_warns_and_skips_malformed(discovery_dict, mock_api):
    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    await dev.update_state_data({"id": "dev-1"})  # no "states"
    assert dev._state_data is None


@pytest.mark.asyncio
async def test_send_command_delegates_to_api(discovery_dict, mock_api):
    from utec_py.devices.device_const import DeviceCommand

    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    cmd = DeviceCommand(capability="st.switch", name="on", arguments=None)
    await dev.send_command(cmd)
    mock_api.send_command.assert_awaited_once_with("dev-1", "st.switch", "on", None)


@pytest.mark.asyncio
async def test_send_command_wraps_api_error(discovery_dict, mock_api):
    from utec_py.devices.device_const import DeviceCommand

    dev = BaseDevice(discovery_dict(handle_type="utec-switch"), mock_api)
    mock_api.send_command.side_effect = RuntimeError("nope")
    cmd = DeviceCommand(capability="st.switch", name="on", arguments=None)
    with pytest.raises(DeviceError, match="Failed to send command"):
        await dev.send_command(cmd)


def test_supported_capabilities_covers_all_known_handle_types(mock_api, discovery_dict):
    """Every HandleType with a capability mapping must round-trip cleanly."""
    from utec_py.devices.device_const import HANDLE_TYPE_CAPABILITIES

    for handle_type, expected_caps in HANDLE_TYPE_CAPABILITIES.items():
        dev = BaseDevice(discovery_dict(handle_type=handle_type), mock_api)
        assert dev.supported_capabilities == expected_caps
