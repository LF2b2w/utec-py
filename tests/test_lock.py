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


# --- Extended property tests (Task 16) ---

# lock_state

def test_lock_state_returns_value_when_present(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockState", "value": "Locked"},
    ]}
    assert lock.lock_state == "Locked"


def test_lock_state_returns_unknown_when_missing(lock):
    lock._state_data = {"states": []}
    assert lock.lock_state == "Unknown"


# has_door_sensor

def test_has_door_sensor_true_for_lock_with_sensor(lock_with_door_sensor):
    assert lock_with_door_sensor.has_door_sensor is True


def test_has_door_sensor_false_for_basic_lock(lock):
    assert lock.has_door_sensor is False


# door_state

def test_door_state_returns_none_when_no_sensor(lock):
    assert lock.door_state is None


def test_door_state_returns_value_when_sensor_present(lock_with_door_sensor):
    lock_with_door_sensor._state_data = {"states": [
        {"capability": "st.doorSensor", "name": "sensorState", "value": "Closed"},
    ]}
    assert lock_with_door_sensor.door_state == "Closed"


# is_door_open

def test_is_door_open_returns_none_when_no_sensor(lock):
    assert lock.is_door_open is None


@pytest.mark.parametrize("raw, expected", [
    ("Open", True),
    ("Closed", False),
])
def test_is_door_open_mapping(lock_with_door_sensor, raw, expected):
    lock_with_door_sensor._state_data = {"states": [
        {"capability": "st.doorSensor", "name": "sensorState", "value": raw},
    ]}
    assert lock_with_door_sensor.is_door_open is expected


# lock_mode

@pytest.mark.parametrize("raw_value, expected", [
    (0, "Normal"),
    (1, "Passage"),
    (2, "Locked"),
])
def test_lock_mode_mapping(lock, raw_value, expected):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockMode", "value": raw_value},
    ]}
    assert lock.lock_mode == expected


def test_lock_mode_returns_none_when_missing(lock):
    lock._state_data = {"states": []}
    assert lock.lock_mode is None


# is_jammed

def test_is_jammed_false_when_locked(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lockState", "value": "Locked"},
    ]}
    assert lock.is_jammed is False


def test_is_jammed_false_when_state_none(lock):
    lock._state_data = {"states": []}
    assert lock.is_jammed is False


# battery_status

@pytest.mark.parametrize("level, expected", [
    (1, "Critically Low"),
    (2, "Low"),
    (3, "Medium"),
    (4, "High"),
    (5, "Full"),
])
def test_battery_status_mapping(lock, level, expected):
    lock._state_data = {"states": [
        {"capability": "st.batteryLevel", "name": "level", "value": level},
    ]}
    assert lock.battery_status == expected


def test_battery_status_returns_none_when_missing(lock):
    lock._state_data = {"states": []}
    assert lock.battery_status is None


# battery_level

def test_battery_level_returns_none_when_missing(lock):
    lock._state_data = {"states": []}
    assert lock.battery_level is None


def test_battery_level_unknown_key_returns_zero(lock):
    lock._state_data = {"states": [
        {"capability": "st.batteryLevel", "name": "level", "value": 99},
    ]}
    assert lock.battery_level == 0


@pytest.mark.parametrize("level, expected", [
    (1, 10),
    (2, 30),
    (3, 50),
    (5, 100),
])
def test_battery_level_all_keys(lock, level, expected):
    lock._state_data = {"states": [
        {"capability": "st.batteryLevel", "name": "level", "value": level},
    ]}
    assert lock.battery_level == expected
