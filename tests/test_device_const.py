"""Tests for device_const enums and mapping."""

from utec_py.devices.device_const import (
    DeviceCapability,
    DeviceCategory,
    DeviceCommand,
    HANDLE_TYPE_CAPABILITIES,
    HandleType,
    LockState,
)


def test_handle_type_capabilities_is_mapping():
    assert isinstance(HANDLE_TYPE_CAPABILITIES, dict)
    assert len(HANDLE_TYPE_CAPABILITIES) > 0


def test_device_command_roundtrip():
    cmd = DeviceCommand(capability="st.switch", name="on", arguments=None)
    assert cmd.capability == "st.switch"
    assert cmd.name == "on"
    assert cmd.arguments is None


def test_device_command_with_args():
    cmd = DeviceCommand(
        capability="st.switchLevel",
        name="setLevel",
        arguments={"level": 50},
    )
    assert cmd.arguments == {"level": 50}


def test_handle_type_enum_has_values():
    assert list(HandleType) != []


def test_device_category_unknown_member_exists():
    # Values are title case per source: DeviceCategory.UNKNOWN = "Unknown"
    assert DeviceCategory("Unknown") is not None


def test_lock_state_has_locked_and_unlocked():
    # Values are title case per source: LockState.LOCKED = "Locked", LockState.UNLOCKED = "Unlocked"
    assert LockState("Locked") is not None
    assert LockState("Unlocked") is not None
