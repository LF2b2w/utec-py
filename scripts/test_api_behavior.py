#!/usr/bin/env python3
"""
Test U-Tec API behaviors that can't be confirmed from documentation:

  1. Multi-command batching: does the API accept {"commands": [...]} (plural)?
  2. Implicit turn-on: does setLevel turn the device on if it's currently off?

Usage:
    python scripts/test_api_behavior.py --token TOKEN --device-id DEVICE_ID [options]

Getting the token:
    1. Add to configuration.yaml:
           logger:
             logs:
               custom_components.u_tec: debug
               utec_py: debug
    2. Restart HA (or reload the u_tec integration).
    3. In HA → Settings → System → Logs, search for "Authorization".
       Copy the value after "Bearer ".
    4. Pass that value as --token.

    Token lifetime is typically 1 hour. Re-fetch if you get 401 responses.

Getting a device ID:
    In HA → Developer Tools → Template:
        {% for state in states.light %}{{ state.entity_id }}: {{ state.attributes }}
        {% endfor %}
    Or just run this script with --list-devices to discover all device IDs.
"""

import argparse
import asyncio
import json
import sys
from uuid import uuid4

import aiohttp

API_URL = "https://api.u-tec.com/action"


def _header(namespace: str, name: str) -> dict:
    return {
        "namespace": namespace,
        "name": name,
        "messageID": str(uuid4()),
        "payloadVersion": "1",
    }


async def _post(session: aiohttp.ClientSession, token: str, payload: dict) -> dict:
    async with session.post(
        API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        text = await resp.text()
        print(f"  HTTP {resp.status}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"  (non-JSON response: {text!r})")
            return {}


async def list_devices(session: aiohttp.ClientSession, token: str) -> list[dict]:
    """Discover all devices and print their IDs and handle types."""
    payload = {"header": _header("Uhome.Device", "Discovery"), "payload": {}}
    data = await _post(session, token, payload)
    devices = data.get("payload", {}).get("devices", [])
    print(f"\nFound {len(devices)} device(s):")
    for d in devices:
        print(f"  id={d.get('id')}  name={d.get('name')!r}  handleType={d.get('handleType')}")
    return devices


async def query_device(session: aiohttp.ClientSession, token: str, device_id: str) -> dict:
    """Query a single device state and return the device dict."""
    payload = {
        "header": _header("Uhome.Device", "Query"),
        "payload": {"devices": [{"id": device_id}]},
    }
    data = await _post(session, token, payload)
    devices = data.get("payload", {}).get("devices", [])
    return devices[0] if devices else {}


def _get_state(device_data: dict, capability: str, attribute: str):
    for s in device_data.get("states", []):
        if s.get("capability") == capability and s.get("name") == attribute:
            return s.get("value")
    return None


async def send_single_command(
    session: aiohttp.ClientSession,
    token: str,
    device_id: str,
    capability: str,
    name: str,
    arguments: dict | None = None,
) -> dict:
    """Send a single command using the current singular {"command": {...}} format."""
    cmd: dict = {"capability": capability, "name": name}
    if arguments:
        cmd["arguments"] = arguments
    payload = {
        "header": _header("Uhome.Device", "Command"),
        "payload": {"devices": [{"id": device_id, "command": cmd}]},
    }
    return await _post(session, token, payload)


async def send_multi_command(
    session: aiohttp.ClientSession,
    token: str,
    device_id: str,
    commands: list[dict],
) -> dict:
    """Send multiple commands using the experimental {"commands": [...]} format."""
    payload = {
        "header": _header("Uhome.Device", "Command"),
        "payload": {"devices": [{"id": device_id, "commands": commands}]},
    }
    return await _post(session, token, payload)


# ---------------------------------------------------------------------------
# Test 1: multi-command batching
# ---------------------------------------------------------------------------

async def test_multi_command(session: aiohttp.ClientSession, token: str, device_id: str):
    """
    Test whether {"commands": [{on}, {setLevel: 50}]} is accepted in one call.

    Compares: 2 individual calls vs 1 batched call.
    A 2xx response with no error body means the format is accepted.
    A 4xx response (or an error field in the JSON) means it isn't.
    """
    print("\n" + "=" * 60)
    print("TEST 1: Multi-command batching")
    print("=" * 60)

    # --- baseline: current 2-call approach ---
    print("\n[Baseline] Turn off, then turn on (2 separate calls):")
    print("  Sending: turn off...")
    resp = await send_single_command(session, token, device_id, "st.switch", "off")
    print(f"  Response: {json.dumps(resp, indent=2)}")
    await asyncio.sleep(2)

    print("  Sending: turn on...")
    resp = await send_single_command(session, token, device_id, "st.switch", "on")
    print(f"  Response: {json.dumps(resp, indent=2)}")
    await asyncio.sleep(2)

    print("  Sending: set level to 50...")
    resp = await send_single_command(
        session, token, device_id, "st.switchLevel", "setLevel", {"level": 50}
    )
    print(f"  Response: {json.dumps(resp, indent=2)}")
    await asyncio.sleep(3)

    state = await query_device(session, token, device_id)
    switch = _get_state(state, "st.switch", "switch")
    level = _get_state(state, "st.switchLevel", "level")
    print(f"  Device state after baseline: switch={switch}, level={level}")

    # --- experimental: single batched call ---
    print("\n[Experiment] Turn off first, then batch {on + setLevel:75} in ONE call:")
    print("  Sending: turn off...")
    await send_single_command(session, token, device_id, "st.switch", "off")
    await asyncio.sleep(2)

    print("  Sending: batched commands [on, setLevel:75]...")
    resp = await send_multi_command(
        session,
        token,
        device_id,
        [
            {"capability": "st.switch", "name": "on"},
            {"capability": "st.switchLevel", "name": "setLevel", "arguments": {"level": 75}},
        ],
    )
    print(f"  Response: {json.dumps(resp, indent=2)}")
    await asyncio.sleep(3)

    state = await query_device(session, token, device_id)
    switch = _get_state(state, "st.switch", "switch")
    level = _get_state(state, "st.switchLevel", "level")
    print(f"  Device state after batch: switch={switch}, level={level}")

    # interpret
    print("\n[Result]")
    if "error" in str(resp).lower() or resp.get("header", {}).get("name") == "Error":
        print("  FAILED — API rejected the batched format.")
        print("  Stick with separate calls.")
    elif switch == "on" and level == 75:
        print("  SUCCESS — batch accepted and device responded correctly.")
        print("  We can combine turn_on + set_brightness into one API call.")
    else:
        print(f"  AMBIGUOUS — API responded 2xx but device state is switch={switch}, level={level}.")
        print("  Check device physically and re-run to confirm.")


# ---------------------------------------------------------------------------
# Test 2: setLevel implicit turn-on
# ---------------------------------------------------------------------------

async def test_implicit_turn_on(session: aiohttp.ClientSession, token: str, device_id: str):
    """
    Test whether sending only setLevel (no prior "on" command) turns the device on.

    If true, turn_on() with brightness can be reduced from 2 API calls to 1.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Does setLevel implicitly turn the device on?")
    print("=" * 60)

    print("\n  Turning device OFF...")
    await send_single_command(session, token, device_id, "st.switch", "off")
    await asyncio.sleep(3)

    state = await query_device(session, token, device_id)
    switch = _get_state(state, "st.switch", "switch")
    print(f"  Confirmed off: switch={switch}")
    if switch != "off":
        print("  WARNING: device didn't confirm off state — results may be unreliable.")

    print("\n  Sending setLevel:60 with NO prior 'on' command...")
    resp = await send_single_command(
        session, token, device_id, "st.switchLevel", "setLevel", {"level": 60}
    )
    print(f"  Response: {json.dumps(resp, indent=2)}")
    await asyncio.sleep(3)

    state = await query_device(session, token, device_id)
    switch = _get_state(state, "st.switch", "switch")
    level = _get_state(state, "st.switchLevel", "level")
    print(f"  Device state after setLevel: switch={switch}, level={level}")

    print("\n[Result]")
    if switch == "on":
        print("  SUCCESS — setLevel implicitly turned the device on.")
        print("  turn_on() with brightness can skip the separate 'on' command.")
    else:
        print("  NEGATIVE — setLevel did NOT turn the device on (switch still off/unknown).")
        print("  Keep sending 'on' before 'setLevel'.")

    # restore to on
    print("\n  Restoring device to on state...")
    await send_single_command(session, token, device_id, "st.switch", "on")
    await send_single_command(
        session, token, device_id, "st.switchLevel", "setLevel", {"level": 100}
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="Test U-Tec API behaviors (multi-command and implicit turn-on)."
    )
    parser.add_argument("--token", required=True, help="U-Tec OAuth2 Bearer token")
    parser.add_argument("--device-id", help="Device ID to test against (a light/dimmer)")
    parser.add_argument(
        "--list-devices", action="store_true", help="Discover and print all device IDs then exit"
    )
    parser.add_argument(
        "--test",
        choices=["multi-command", "implicit-on", "all"],
        default="all",
        help="Which test to run (default: all)",
    )
    args = parser.parse_args()

    async with aiohttp.ClientSession() as session:
        if args.list_devices:
            await list_devices(session, args.token)
            return

        if not args.device_id:
            print("ERROR: --device-id is required unless using --list-devices.")
            sys.exit(1)

        # Verify the device exists
        print(f"Querying device {args.device_id}...")
        state = await query_device(session, args.token, args.device_id)
        if not state:
            print("ERROR: Device not found or token invalid. Try --list-devices to check IDs.")
            sys.exit(1)

        switch = _get_state(state, "st.switch", "switch")
        level = _get_state(state, "st.switchLevel", "level")
        print(f"Device found. Current state: switch={switch}, level={level}")

        if args.test in ("multi-command", "all"):
            await test_multi_command(session, args.token, args.device_id)

        if args.test in ("implicit-on", "all"):
            await test_implicit_turn_on(session, args.token, args.device_id)


if __name__ == "__main__":
    asyncio.run(main())
