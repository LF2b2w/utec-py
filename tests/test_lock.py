"""Tests for Lock device."""

import pytest

from utec_py.devices.lock import Lock


@pytest.fixture
def lock(discovery_dict, mock_api):
    return Lock(discovery_dict(handle_type="utec-lock", category="SmartLock"), mock_api)


@pytest.fixture
def lock_with_door_sensor(discovery_dict, mock_api):
    """Lock with door sensor capability (utec-lock-sensor handle type)."""
    return Lock(
        discovery_dict(handle_type="utec-lock-sensor", category="SmartLock"), mock_api
    )


def test_is_locked_true(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockState", "value": "Locked"},
    ]}
    assert lock.is_locked is True


def test_is_locked_false_when_unlocked(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockState", "value": "Unlocked"},
    ]}
    assert lock.is_locked is False


def test_is_jammed_true_when_state_jammed(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockState", "value": "Jammed"},
    ]}
    assert lock.is_jammed is True


def test_battery_level_returned(lock):
    lock._state_data = {"states": [
        {"capability": "st.batteryLevel", "name": "level", "value": 4},
    ]}
    assert lock.battery_level == 70


def test_door_state_when_has_door_sensor(lock_with_door_sensor):
    lock_with_door_sensor._state_data = {"states": [
        {"capability": "st.doorSensor", "name": "sensorState", "value": "Open"},
    ]}
    assert lock_with_door_sensor.is_door_open is True


@pytest.mark.asyncio
async def test_lock_sends_lock_command(lock, mock_api):
    await lock.lock()
    args = mock_api.send_command.await_args.args
    assert args[1] == "st.lock"
    assert args[2] == "lock"


@pytest.mark.asyncio
async def test_unlock_sends_unlock_command(lock, mock_api):
    await lock.unlock()
    args = mock_api.send_command.await_args.args
    assert args[2] == "unlock"
