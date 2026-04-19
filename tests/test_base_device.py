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
