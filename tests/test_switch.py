"""Tests for Switch device."""

import pytest

from utec_py.devices.switch import Switch


@pytest.fixture
def switch(discovery_dict, mock_api):
    return Switch(discovery_dict(handle_type="utec-switch"), mock_api)


def test_is_on_true_when_state_on(switch):
    switch._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "on"},
    ]}
    assert switch.is_on is True


def test_is_on_false_when_state_off(switch):
    switch._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "off"},
    ]}
    assert switch.is_on is False


def test_is_on_none_when_no_state(switch):
    assert switch.is_on in (None, False)  # depending on impl; both acceptable


@pytest.mark.asyncio
async def test_turn_on_sends_command(switch, mock_api):
    await switch.turn_on()
    mock_api.send_command.assert_awaited_once()
    args = mock_api.send_command.await_args.args
    # args = (device_id, capability, command, arguments)
    assert args[0] == "dev-1"
    assert args[1] == "st.switch"
    assert args[2] == "on"


@pytest.mark.asyncio
async def test_turn_off_sends_command(switch, mock_api):
    await switch.turn_off()
    args = mock_api.send_command.await_args.args
    assert args[2] == "off"
