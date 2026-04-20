"""Tests for DeviceInfo parsing."""

from utec_py.devices.device import DeviceInfo


def test_from_dict_all_fields():
    data = {
        "manufacturer": "Acme Corp",
        "model": "ModelX",
        "hwVersion": "v2.1",
        "serialNumber": "SN12345",
    }
    info = DeviceInfo.from_dict(data)
    assert info.manufacturer == "Acme Corp"
    assert info.model == "ModelX"
    assert info.hw_version == "v2.1"
    assert info.serial_number == "SN12345"


def test_from_dict_missing_optional_serial():
    data = {"manufacturer": "Beta Co", "model": "ModelY", "hwVersion": "v1.0"}
    info = DeviceInfo.from_dict(data)
    assert info.manufacturer == "Beta Co"
    assert info.model == "ModelY"
    assert info.hw_version == "v1.0"
    assert info.serial_number is None


def test_from_dict_empty_input_returns_empty_strings():
    info = DeviceInfo.from_dict({})
    assert info.manufacturer == ""
    assert info.model == ""
    assert info.hw_version == ""
    assert info.serial_number is None
