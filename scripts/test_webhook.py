#!/usr/bin/env python3
"""
Troubleshoot the U-Tec push notification webhook pipeline.

Five diagnostic steps, each independent:

  1. query-config     — Ask U-Tec what webhook URL they currently have on file.
  2. test-ha          — POST a simulated push payload directly to your HA webhook
                        endpoint to verify HA receives and processes it correctly.
  3. reachability     — Check whether a URL is reachable from this machine
                        (useful signal, but U-Tec's servers may differ).
  4. live-probe       — Temporarily register a public echo service as the webhook,
                        wait for U-Tec to push a state change, then restore the
                        original URL. Definitively answers "does U-Tec push at all?"
  5. trigger-and-watch — Toggle a device via the U-Tec API and watch HA logs for
                        the incoming push notification. No webhook re-registration;
                        uses whatever is already configured.

Usage examples:

    # Step 1: what URL does U-Tec have registered?
    python scripts/test_webhook.py --token TOKEN query-config

    # Step 2: does HA's webhook handler accept a mock push?
    python scripts/test_webhook.py --token TOKEN test-ha \\
        --ha-webhook-url https://your-ha/api/webhook/u_tec_push_ENTRYID \\
        --device-id DEVICE_ID

    # Step 3: is a URL reachable from this machine?
    python scripts/test_webhook.py --token TOKEN reachability \\
        --url https://your-ha/api/webhook/u_tec_push_ENTRYID

    # Step 4: does U-Tec actually fire pushes?
    python scripts/test_webhook.py --token TOKEN live-probe \\
        --device-id DEVICE_ID \\
        --restore-url https://your-ha/api/webhook/u_tec_push_ENTRYID \\
        [--restore-secret SECRET]

    # Step 5: toggle entity via HA, watch HA logs for the push (safest test)
    python scripts/test_webhook.py trigger-and-watch \\
        --entity-id switch.front_porch \\
        --ha-url http://homeassistant.local:8123 \\
        --ha-token YOUR_LONG_LIVED_ACCESS_TOKEN \\
        [--wait 30]

Getting --token:
    See scripts/test_api_behavior.py docstring, or:
    SSH into your HA server and run:
        grep -A5 '"u_tec"' /config/.storage/core.config_entries | grep access_token

Getting --ha-webhook-url:
    Settings → System → Logs (search "Webhook registered") or:
        grep -A1 "webhook_id" /config/.storage/core.config_entries

Getting --device-id:
    python scripts/test_api_behavior.py --token TOKEN --list-devices
"""

import argparse
import asyncio
import json
import sys
import time
from uuid import uuid4

import aiohttp

API_URL = "https://api.u-tec.com/action"

# Public echo service — receives POST requests and returns everything it got.
# We use this in the live-probe to check if U-Tec fires pushes.
ECHO_SERVICE = "https://httpbin.org/post"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _header(namespace: str, name: str) -> dict:
    return {
        "namespace": namespace,
        "name": name,
        "messageId": str(uuid4()),
        "payloadVersion": "1",
    }


async def _utec_post(session: aiohttp.ClientSession, token: str, payload: dict) -> tuple[int, dict]:
    async with session.post(
        API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        status = resp.status
        try:
            body = await resp.json()
        except Exception:
            body = {"_raw": await resp.text()}
        return status, body


def _print_result(label: str, ok: bool, detail: str = ""):
    icon = "✓" if ok else "✗"
    print(f"  [{icon}] {label}" + (f": {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Step 1: query-config
# ---------------------------------------------------------------------------

async def cmd_query_config(session: aiohttp.ClientSession, token: str):
    """Try to retrieve the webhook config U-Tec currently has on file."""
    print("\n=== Step 1: Query U-Tec push config ===\n")

    payload = {
        "header": _header("Uhome.Configure", "Query"),
        "payload": {},
    }
    status, body = await _utec_post(session, token, payload)
    print(f"  HTTP {status}")
    print(f"  Response: {json.dumps(body, indent=2)}")

    if status in (200, 201, 202):
        # Try to find the registered URL in the response
        raw = json.dumps(body)
        if "http" in raw.lower():
            print("\n  Webhook URL found in response — see above.")
        else:
            print("\n  Response didn't contain a URL. The Query operation may not be")
            print("  supported for Uhome.Configure (U-Tec API is not fully documented).")
    else:
        print(f"\n  Uhome.Configure/Query returned {status}. This endpoint may not exist.")

    print("\n  NOTE: If query isn't supported, the registered URL is in:")
    print("        /config/.storage/core.config_entries  (search 'webhook')")


# ---------------------------------------------------------------------------
# Step 2: test-ha
# ---------------------------------------------------------------------------

async def cmd_test_ha(
    session: aiohttp.ClientSession,
    ha_webhook_url: str,
    device_id: str,
    secret: str | None,
):
    """POST a simulated push payload directly to the HA webhook endpoint."""
    print("\n=== Step 2: Test HA webhook handler ===\n")
    print(f"  Target: {ha_webhook_url}")

    # Construct a realistic push payload (nested shape)
    mock_payload = {
        "payload": {
            "devices": [
                {
                    "id": device_id,
                    "states": [
                        {"capability": "st.switch", "name": "switch", "value": "on"},
                        {"capability": "st.healthCheck", "name": "status", "value": "Online"},
                    ],
                }
            ]
        }
    }
    if secret:
        mock_payload["access_token"] = secret

    print(f"  Payload: {json.dumps(mock_payload, indent=2)}")
    print()

    try:
        async with session.post(ha_webhook_url, json=mock_payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            status = resp.status
            try:
                body = await resp.json()
            except Exception:
                body = {"_raw": await resp.text()}

            _print_result("HA reachable", status not in (0,))
            _print_result("Webhook accepted (2xx)", 200 <= status < 300, f"HTTP {status}")
            if status == 401 or status == 403:
                print("\n  → 401/403 means the push secret doesn't match what HA has in memory.")
                print("    The secret rotates on every HA restart. Re-register the webhook")
                print("    via the integration options or by reloading the integration.")
            elif status == 404:
                print("\n  → 404 means HA doesn't recognise this webhook ID.")
                print("    Check the entry_id in the URL matches your config entry.")
            elif 200 <= status < 300:
                print(f"\n  Response: {json.dumps(body, indent=2)}")
                print("\n  HA accepted the payload. If automations still don't fire,")
                print("  the issue is on the U-Tec server side (it's not sending pushes).")
            else:
                print(f"\n  Unexpected status {status}. Response: {body}")

    except aiohttp.ClientConnectorError as err:
        _print_result("HA reachable", False, str(err))
        print("\n  → HA is not reachable at this URL from this machine.")
        print("    This is expected if HA has no public URL — and the same reason")
        print("    U-Tec's servers can't reach it either.")


# ---------------------------------------------------------------------------
# Step 3: reachability
# ---------------------------------------------------------------------------

async def cmd_reachability(session: aiohttp.ClientSession, url: str):
    """Check whether a URL responds to a POST from this machine."""
    print("\n=== Step 3: URL reachability check ===\n")
    print(f"  URL: {url}")

    local_indicators = ("192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
                        "172.2", "172.3", "homeassistant.local", "localhost", "127.")
    is_local = any(ind in url for ind in local_indicators)
    _print_result("URL looks publicly routable", not is_local,
                  "PRIVATE ADDRESS — U-Tec servers cannot reach this" if is_local else "")

    try:
        async with session.post(url, json={"test": True}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            _print_result("Reachable from this machine", True, f"HTTP {resp.status}")
    except aiohttp.ClientConnectorError as err:
        _print_result("Reachable from this machine", False, str(err))
    except asyncio.TimeoutError:
        _print_result("Reachable from this machine", False, "timed out after 10s")

    if is_local:
        print()
        print("  DIAGNOSIS: Your HA webhook URL is a private/local address.")
        print("  U-Tec's cloud servers cannot deliver push notifications to it.")
        print()
        print("  Options to fix:")
        print("    A) Nabu Casa (Home Assistant Cloud) — easiest, ~$7/mo")
        print("       Provides a public HTTPS URL for your HA instance.")
        print("    B) Port-forward TCP 443 on your router to your HA host,")
        print("       then set an external URL in HA Settings → System → Network.")
        print("    C) Cloudflare Tunnel (free) — runs a tunnel agent on your HA host.")
        print("    D) Keep polling-only mode (scan_interval: 2 in configuration.yaml).")


# ---------------------------------------------------------------------------
# Step 4: live-probe
# ---------------------------------------------------------------------------

async def cmd_live_probe(
    session: aiohttp.ClientSession,
    token: str,
    device_id: str,
    restore_url: str | None,
    restore_secret: str | None,
    wait_seconds: int = 30,
    echo_url: str = ECHO_SERVICE,
):
    """
    Temporarily register httpbin as the webhook, toggle a light, and watch
    whether U-Tec actually delivers a push notification.

    The httpbin endpoint echoes everything back, but we can't read it from here
    (no persistent listener). Instead we print the echo URL so you can check it
    in a browser, and report whether U-Tec accepted our registration.
    """
    print("\n=== Step 4: Live push probe ===\n")
    print("  This test temporarily registers a public echo service as the webhook.")
    print(f"  Echo endpoint: {echo_url}")
    print()

    probe_secret = "probe-test-secret-" + str(uuid4())[:8]

    # Register the echo endpoint
    print(f"  Registering {echo_url} with U-Tec...")
    reg_payload = {
        "header": _header("Uhome.Configure", "Set"),
        "payload": {
            "configure": {
                "notification": {
                    "access_token": probe_secret,
                    "url": echo_url,
                }
            }
        },
    }
    status, body = await _utec_post(session, token, reg_payload)
    _print_result("Registration accepted by U-Tec", 200 <= status < 300, f"HTTP {status}")
    print(f"  Response: {json.dumps(body, indent=2)}")

    if status not in (200, 201, 202, 204):
        print("\n  Registration failed — cannot continue probe.")
    else:
        # Query current state so we can restore it afterward
        print(f"\n  Querying current state of device {device_id}...")
        query_payload = {
            "header": _header("Uhome.Device", "Query"),
            "payload": {"devices": [{"id": device_id}]},
        }
        _, qresp = await _utec_post(session, token, query_payload)
        original_switch = "off"
        for state in qresp.get("payload", {}).get("devices", [{}])[0].get("states", []):
            if state.get("capability") == "st.switch" and state.get("name") == "switch":
                original_switch = state.get("value", "off")
                break
        print(f"  Device is currently: {original_switch}")

        # Toggle to the opposite state and back to generate two state change events
        opposite = "off" if original_switch == "on" else "on"
        print(f"  Toggling {original_switch} → {opposite} → {original_switch} to trigger push events...")

        async def _switch(cmd):
            p = {
                "header": _header("Uhome.Device", "Command"),
                "payload": {"devices": [{"id": device_id, "command": {"capability": "st.switch", "name": cmd}}]},
            }
            await _utec_post(session, token, p)

        await _switch(opposite)
        await asyncio.sleep(2)
        await _switch(original_switch)
        print(f"  Device restored to: {original_switch}")

        print(f"\n  Waiting {wait_seconds}s for U-Tec to deliver a push to:")
        print(f"    {echo_url}")
        print(f"  Watch that URL in your browser now for incoming requests.")
        await asyncio.sleep(wait_seconds)
        print(f"  Done waiting.")

    # Restore original webhook
    if restore_url:
        print(f"\n  Restoring original webhook URL: {restore_url}")
        restore_payload = {
            "header": _header("Uhome.Configure", "Set"),
            "payload": {
                "configure": {
                    "notification": {
                        "access_token": restore_secret or "",
                        "url": restore_url,
                    }
                }
            },
        }
        status, body = await _utec_post(session, token, restore_payload)
        _print_result("Original webhook restored", 200 <= status < 300, f"HTTP {status}")
        if restore_secret:
            print("  NOTE: HA's in-memory secret may differ from --restore-secret.")
            print("  Reload the u_tec integration in HA to re-register with a fresh secret.")
    else:
        print("\n  WARNING: --restore-url not provided. U-Tec still has the probe URL registered.")
        print("  Reload the u_tec integration in HA to re-register your real webhook.")


# ---------------------------------------------------------------------------
# Step 5: trigger-and-watch
# ---------------------------------------------------------------------------

async def _ha_get(session: aiohttp.ClientSession, ha_url: str, ha_token: str, path: str) -> tuple[int, str | dict]:
    """GET from HA REST API."""
    headers = {"Authorization": f"Bearer {ha_token}"}
    async with session.get(
        f"{ha_url}{path}", headers=headers, timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        try:
            body = await resp.json()
        except Exception:
            body = await resp.text()
        return resp.status, body


async def _ha_post(session: aiohttp.ClientSession, ha_url: str, ha_token: str, path: str, data: dict) -> tuple[int, str | dict]:
    """POST to HA REST API."""
    headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
    async with session.post(
        f"{ha_url}{path}", headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        try:
            body = await resp.json()
        except Exception:
            body = await resp.text()
        return resp.status, body


async def cmd_trigger_and_watch(
    session: aiohttp.ClientSession,
    entity_id: str,
    ha_url: str,
    ha_token: str,
    wait_seconds: int = 30,
):
    """
    Toggle a switch/light/lock entity via HA's REST API, then poll HA logs for
    evidence that U-Tec delivered a push notification. Uses whatever webhook is
    already registered — nothing gets swapped or re-registered.
    """
    print("\n=== Step 5: Trigger entity & watch HA logs ===\n")
    ha_url = ha_url.rstrip("/")

    # Verify HA is reachable
    print(f"  Checking HA at {ha_url} ...")
    status, _ = await _ha_get(session, ha_url, ha_token, "/api/")
    if status == 401:
        print("  ERROR: HA returned 401 — check your --ha-token")
        return
    if status != 200:
        print(f"  ERROR: HA returned HTTP {status} — is the URL correct?")
        return
    _print_result("HA reachable and authenticated", True)

    # Get current entity state
    print(f"\n  Querying state of {entity_id} ...")
    status, state_data = await _ha_get(session, ha_url, ha_token, f"/api/states/{entity_id}")
    if status == 404:
        print(f"  ERROR: Entity {entity_id} not found in HA.")
        print("  List U-Tec entities with: curl -sH 'Authorization: Bearer TOKEN' http://HA:8123/api/states | python3 -c \"import json,sys;[print(e['entity_id']) for e in json.load(sys.stdin) if 'u_tec' in e.get('attributes',{}).get('integration','').lower() or 'utec' in e['entity_id'].lower()]\"")
        return
    if status != 200:
        print(f"  ERROR: Unexpected HTTP {status} fetching entity state")
        return

    original_state = state_data["state"]
    domain = entity_id.split(".")[0]
    print(f"  {entity_id} is currently: {original_state}")

    # Determine the toggle services based on domain
    if domain == "switch":
        on_service, off_service = "switch/turn_on", "switch/turn_off"
    elif domain == "light":
        on_service, off_service = "light/turn_on", "light/turn_off"
    elif domain == "lock":
        on_service, off_service = "lock/lock", "lock/unlock"
    else:
        print(f"  ERROR: Unsupported domain '{domain}'. Use a switch, light, or lock entity.")
        return

    # For locks: locked = "locked", unlocked = "unlocked"
    # For switches/lights: on = "on", off = "off"
    if domain == "lock":
        opposite_service = off_service if original_state == "locked" else on_service
        restore_service = on_service if original_state == "locked" else off_service
    else:
        opposite_service = off_service if original_state == "on" else on_service
        restore_service = on_service if original_state == "on" else off_service

    # Snapshot the current log so we can diff later
    print("\n  Snapshotting current HA logs...")
    _, log_before = await _ha_get(session, ha_url, ha_token, "/api/error/all")
    if isinstance(log_before, str):
        baseline_lines = set(log_before.splitlines())
    else:
        baseline_lines = set()

    # Toggle to opposite state
    opposite_label = opposite_service.split("/")[1]
    restore_label = restore_service.split("/")[1]
    print(f"  Calling {opposite_service} on {entity_id} ...")
    status, _ = await _ha_post(session, ha_url, ha_token, f"/api/services/{opposite_service}", {"entity_id": entity_id})
    _print_result(f"Service {opposite_label} called", 200 <= status < 300, f"HTTP {status}")

    # Wait for the device to actually change, then restore
    await asyncio.sleep(3)
    print(f"  Calling {restore_service} on {entity_id} (restoring) ...")
    status, _ = await _ha_post(session, ha_url, ha_token, f"/api/services/{restore_service}", {"entity_id": entity_id})
    _print_result(f"Service {restore_label} called", 200 <= status < 300, f"HTTP {status}")
    print(f"  Entity should return to: {original_state}")

    # Now poll HA logs for new webhook-related entries
    print(f"\n  Waiting up to {wait_seconds}s for U-Tec push notification in HA logs...")
    print(f"  (looking for new 'webhook' + 'u_tec' log lines)\n")

    webhook_found = False

    for elapsed in range(0, wait_seconds, 5):
        if elapsed > 0:
            await asyncio.sleep(5)

        try:
            status, log_text = await _ha_get(session, ha_url, ha_token, "/api/error/all")
            if status == 200 and isinstance(log_text, str):
                current_lines = log_text.splitlines()
                # Find lines that are new since our baseline snapshot
                new_lines = [ln for ln in current_lines if ln not in baseline_lines]
                webhook_lines = [
                    ln for ln in new_lines
                    if "webhook" in ln.lower() and "u_tec" in ln.lower()
                ]
                if webhook_lines:
                    webhook_found = True
                    print(f"  PUSH RECEIVED! Found {len(webhook_lines)} new webhook log entry(ies):\n")
                    for ln in webhook_lines[-10:]:
                        print(f"    {ln[:250]}")
                    break
                print(f"  [{elapsed}s] No new webhook entries yet...")
            elif status != 200:
                print(f"  [{elapsed}s] HA logs returned HTTP {status}")
        except aiohttp.ClientConnectorError as err:
            print(f"  ERROR: Cannot reach HA: {err}")
            break
        except asyncio.TimeoutError:
            print(f"  [{elapsed}s] Log request timed out, retrying...")

    if not webhook_found:
        print(f"\n  No webhook push detected in HA logs after {wait_seconds}s.")
        print("  This could mean:")
        print("    1. U-Tec is still not sending pushes (contact support again)")
        print("    2. The webhook URL registered with U-Tec is wrong/unreachable")
        print("    3. HA debug logging is off — enable it with:")
        print('       logger:')
        print('         logs:')
        print('           custom_components.u_tec: debug')
        print("    4. Push notifications aren't enabled in the integration options")
    else:
        print("\n  U-Tec push notifications are working!")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="Troubleshoot the U-Tec push notification webhook."
    )
    parser.add_argument("--token", help="U-Tec OAuth2 Bearer token (required for all commands except trigger-and-watch)")
    sub = parser.add_subparsers(dest="command", required=True)

    # query-config
    sub.add_parser("query-config", help="Query what webhook URL U-Tec has registered")

    # test-ha
    p_ha = sub.add_parser("test-ha", help="POST a mock push payload to your HA webhook")
    p_ha.add_argument("--ha-webhook-url", required=True,
                      help="Full HA webhook URL (e.g. https://your-ha/api/webhook/u_tec_push_ENTRYID)")
    p_ha.add_argument("--device-id", required=True, help="Device ID to include in mock payload")
    p_ha.add_argument("--secret", help="Push secret (optional; skip to test secret-less behaviour)")

    # reachability
    p_reach = sub.add_parser("reachability", help="Check if a URL is reachable from this machine")
    p_reach.add_argument("--url", required=True, help="URL to test")

    # live-probe
    p_probe = sub.add_parser("live-probe", help="Register a probe endpoint and toggle a device")
    p_probe.add_argument("--device-id", required=True, help="Device to toggle")
    p_probe.add_argument("--echo-url", default=ECHO_SERVICE,
                         help="Public echo URL to register (default: httpbin). Use your webhook.site URL here.")
    p_probe.add_argument("--restore-url", help="Original HA webhook URL to restore after probe")
    p_probe.add_argument("--restore-secret", help="Original push secret to restore")
    p_probe.add_argument("--wait", type=int, default=30, help="Seconds to wait for push (default: 30)")

    # trigger-and-watch
    p_taw = sub.add_parser("trigger-and-watch",
                           help="Toggle an HA entity and watch logs for the push (no U-Tec token needed)")
    p_taw.add_argument("--entity-id", required=True,
                       help="HA entity to toggle (e.g. switch.front_porch, light.kitchen, lock.front_door)")
    p_taw.add_argument("--ha-url", required=True,
                       help="HA base URL (e.g. http://homeassistant.local:8123)")
    p_taw.add_argument("--ha-token", required=True,
                       help="HA long-lived access token (Profile → Security → Long-Lived Access Tokens)")
    p_taw.add_argument("--wait", type=int, default=30, help="Seconds to wait for push (default: 30)")

    args = parser.parse_args()

    # Commands that talk to U-Tec directly need --token
    needs_token = {"query-config", "live-probe"}
    if args.command in needs_token and not args.token:
        parser.error(f"--token is required for the '{args.command}' command")

    async with aiohttp.ClientSession() as session:
        if args.command == "query-config":
            await cmd_query_config(session, args.token)
        elif args.command == "test-ha":
            await cmd_test_ha(session, args.ha_webhook_url, args.device_id, args.secret)
        elif args.command == "reachability":
            await cmd_reachability(session, args.url)
        elif args.command == "live-probe":
            await cmd_live_probe(
                session, args.token, args.device_id,
                args.restore_url, args.restore_secret, args.wait,
                args.echo_url,
            )
        elif args.command == "trigger-and-watch":
            await cmd_trigger_and_watch(
                session, args.entity_id,
                args.ha_url, args.ha_token, args.wait,
            )


if __name__ == "__main__":
    asyncio.run(main())
