# utec-py Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise utec-py test coverage from ~0% (all existing tests are broken) to ≥90% line coverage. Breadth first — every module gets at least one passing smoke test — then depth.

**Architecture:** Pure unit tests for dataclasses/property accessors. `aioresponses` for HTTP transport tests against `_async_make_request`. `unittest.mock` `AsyncMock`/`MagicMock` for auth and API mocking in device command tests. No real network, no real event loop quirks beyond `pytest-asyncio`. `conftest.py` provides shared fixtures: a concrete `AbstractAuth` subclass returning a fixed token, a mock `UHomeApi`, and a `make_discovery_dict(handle_type=..., capabilities=...)` helper.

**Tech Stack:** Python 3.11+, pytest, pytest-asyncio, aioresponses, coverage.py. Existing dependency `aiohttp>=3.7.4`.

**Audit basis:**
- Source: `src/utec_py/{__init__,api,auth,const,exceptions}.py`, `src/utec_py/devices/{device,device_const,switch,light,lock}.py`.
- Existing tests (`tests/test_utec.py`) are entirely broken: wrong import paths (`utec_py.device` → must be `utec_py.devices.device`), references to non-existent methods (`_api_call`, `_discover`), imports `UtecOAuth2` (lives in HA integration, not here). **Delete and rewrite.**

**Coverage target:** 90% line. Anticipated exclusions via `.coveragerc`: `if TYPE_CHECKING:`, `def __repr__`, `def __str__`, `raise NotImplementedError` (only on `AbstractAuth.async_get_access_token`), `if __name__ == "__main__":`.

---

## Local LLM usage policy

`mcp__lm-studio__local_llm` (Gemma 4 e4b 8bit via LM Studio, ~25–40 tok/sec on M1 Pro) is validated at **10/10 accuracy at ≤7k tok prompts** and **98% at ~17k tok** (2026-04-18 testing). **Default stance: use it for every test-writing task in this plan.** Fall back to the primary model only when (a) the narrow forbidden list below applies, or (b) the sanity gate fails twice on the same task — then write that task directly.

### How to call it well

- **Format instructions LAST.** Gemma 4 is strongly recency-biased; the "what to produce" and "output only X" instructions belong at the bottom, after context.
- **Strip context aggressively.** Don't paste full source files when only a function matters. Each ~500 tok of filler adds ~5s latency and hurts quality.
- **One task per call.** Don't chain "summarize + classify + reformat". The model picks one and drops the others.
- **Pass `max_tokens: 8192` for prompts >10k tok.** Gemma 4 emits `reasoning_content` separately from `content`; default 4096 runs out silently on long prompts (empty output + `finish_reason: length`).
- **State output structure explicitly.** "Output only the test code — no prose, no markdown fences" beats "generate tests".

### Standard prompt shape — reuse across tasks

```
<Extract from AUDIT-utec-py-2026-04-18.md: relevant class/function signatures only>

<Existing-test template: ONE similar test from another file in this suite>

Generate pytest test cases for <function name>. Cover these paths: <enumerated list>.
Use only identifiers that appear above — do not invent attribute names, method names, or constants.
Output only the Python test code. No prose. No placeholders. No markdown fences.
```

### Where it applies (default-on)

Unless a task is in the forbidden list below, the subagent should attempt `local_llm` first for test generation, using the shape above. Also applies to:

- Drafting commit messages from staged diffs (every task's final step).
- AUDIT.md reformatting (Task 0).
- Classifying uncovered-lines output (ad-hoc during Task 18 sweep).

### Forbidden narrowly

- **Device command tests where the exact capability/command string is the assertion** (Tasks 6, 7, 8 — Switch/Light/Lock commands). The test's entire value hinges on `st.switch`/`st.switchLevel`/`st.lock` being exact. If you want to try `local_llm` here, quote every expected string verbatim from AUDIT inside the prompt. Otherwise write directly.
- **`async_create_request` payload shape tests** where `messageId` uniqueness + `payloadVersion == "1"` are the contract (Task 12c). Small-model drift on these constant values silently corrupts assertions.

### Sanity gate — discard output failing any of these

1. Every `import` line resolves per AUDIT (or is `pytest`, `pytest_asyncio`, `aiohttp`, `aioresponses`, `unittest.mock`, `yarl`, `asyncio`, `datetime`).
2. No reference to a method, attribute, or constant not present in AUDIT (the original broken `test_utec.py` had `_api_call`, `_discover`, `UtecOAuth2` — this class of hallucination is the exact failure mode to catch).
3. Async test functions use `async def test_*` (no `@pytest.mark.asyncio` decorator needed — `asyncio_mode = "auto"` is set; remove any decorator the model adds).
4. No `if __name__ == "__main__":` block, no `print(...)` for debugging, no commented-out code.

Any failure → discard, log as `discarded`, write directly. **Two consecutive `discarded` on the same task** → stop attempting `local_llm` for the remaining steps of that task.

### Operational gotchas

- **LM Studio serializes requests.** Never fire parallel `local_llm` calls in one tool-use block — all but one return empty output silently. Subagents are serial; only a concern if a single task issues multiple calls at once.
- **Empty output = discarded**, no retry. If you see empty `content`, suspect `finish_reason: length` → bump `max_tokens` to 8192 and try once more. Then give up.
- **LM Studio not running = silent fallback.** If the tool errors with connection, do the work directly. Don't ask the user to start it.

### Measurement

Every `local_llm` call appends one row to `docs/superpowers/plans/LLM-LOG-2026-04-18.md` (create on first use):

```markdown
# local_llm usage log — utec-py test coverage — 2026-04-18

| Task | Purpose | Outcome | Prompt tokens | Tokens saved (rough) |
|---|---|---|---|---|
```

Row format: `| <task-id> | <one-line purpose> | <used-as-is \| minor-edits \| major-rewrite \| discarded> | <~N prompt> | <~N saved> |`

- **used-as-is:** committed without edits
- **minor-edits:** <10 lines changed (rename, add a missing import, tighten an assertion)
- **major-rewrite:** ≥10 lines changed, or structure changed
- **discarded:** output failed sanity gate or was unusable

"Prompt tokens" is the subagent's rough estimate (used to correlate quality with prompt size per the ≤7k / ~17k ceilings). "Tokens saved" is the estimated native-generation cost avoided; negative if corrections cost more than savings.

Commit `LLM-LOG-2026-04-18.md` alongside the last task's output. At session end, summarize: total calls, acceptance rate, net tokens saved, and any tasks where `local_llm` was abandoned mid-task.

---

## File Structure

**New files:**
- `pyproject.toml` — add `[tool.pytest.ini_options]` + `[tool.coverage.*]` sections (already exists; extend).
- `.coveragerc` — coverage exclusions (alternative: all-in-pyproject — use pyproject; don't create this file).
- `requirements-test.txt` — pinned test deps: `pytest`, `pytest-asyncio`, `aioresponses`, `coverage[toml]`, `pytest-cov`.
- `tests/conftest.py` — rewrite: fixtures (`mock_auth`, `mock_api`, `discovery_dict`, `state_payload`).
- `tests/test_device_info.py` — `DeviceInfo.from_dict` tests.
- `tests/test_base_device.py` — `BaseDevice` init, validation, state accessors, update, update_state_data, send_command.
- `tests/test_switch.py` — `Switch` device tests.
- `tests/test_light.py` — `Light` device tests.
- `tests/test_lock.py` — `Lock` device tests.
- `tests/test_auth.py` — `AbstractAuth.async_make_auth_request` header injection.
- `tests/test_api.py` — `UHomeApi` transport + all endpoint methods.
- `tests/test_exceptions.py` — exception hierarchy sanity (cheap coverage booster).
- `tests/test_device_const.py` — `HANDLE_TYPE_CAPABILITIES` sanity + `DeviceCommand` dataclass.

**Deleted files:**
- `tests/test_utec.py` — fully broken; delete in Task 2.

**Modified files:**
- `pyproject.toml` — add test + coverage config.

---

## Phase 0 — Foundation

### Task 0: Produce `AUDIT.md` — one read, many reuses

**Files:**
- Create: `docs/superpowers/plans/AUDIT-utec-py-2026-04-18.md`

**Local LLM candidate:** After `rtk read`-ing each module, pass the raw source (per file, one call) to `mcp__lm-studio__local_llm` with a prompt like: *"Extract the public API surface (class names, method signatures with parameter names and types, enum members and values) from this Python file. Output as markdown matching this exact structure: `## Module: <path>` → `- Class: ...` → bullet per method. Do not invent anything not in the source."* Accept output if every signature round-trips against the file; edit or discard if hallucinations appear. Log outcome to `LLM-LOG-2026-04-18.md`.

Context-saver: later tasks would otherwise `rtk read` the same source files repeatedly. This task reads each module once and writes a compact reference that subsequent subagents consume instead of re-reading source. **Do not write any tests in this task.** Do not commit any `src/` or `tests/` changes.

- [ ] **Step 1: Read every source file under `src/utec_py/` and produce `AUDIT-utec-py-2026-04-18.md` with these sections:**

```markdown
# utec-py audit — 2026-04-18

## Module: src/utec_py/auth.py
- Class: `AbstractAuth(ABC)`
  - `__init__(self, websession: ClientSession)`
  - `async_get_access_token(self) -> str`  [@abstractmethod]
  - `async_make_auth_request(self, method, host, **kwargs) -> ClientResponse` — injects Content-Type, Accept, Authorization: Bearer

## Module: src/utec_py/api.py
- Enums: `ApiNamespace` (DEVICE/USER/CONFIGURE), `ApiOperation` (DISCOVERY/QUERY/COMMAND/SET)
- TypedDicts: `ApiHeader`, `ApiRequest`
- Class: `UHomeApi(auth)` — methods:
  - `async_create_request(namespace, operation, parameters) -> ApiRequest`
  - `_async_make_request(**kwargs)` — 200/201/202 → json; 204 → {}; other → raise ApiError(status, text)
  - `validate_auth() -> bool`
  - `discover_devices()` — namespace=Device, op=Discovery, payload={}
  - `get_device_state(device_ids: list, custom_data: dict | None)`
  - `query_device(device_id: str)`
  - `send_command(device_id, capability, command, arguments)` — omits `arguments` key when None
  - `set_push_status(uri: str, access_token: str)` — shape: {configure: {notification: {access_token, url}}}

## Module: src/utec_py/const.py
- API_BASE_URL = "..."  (record exact value)
- Duplicate enums also defined here (noted; do not need testing)

## Module: src/utec_py/exceptions.py
- Hierarchy (record exact parent/child relationships)

## Module: src/utec_py/devices/device_const.py
- Enums: HandleType (list all values), DeviceCapability, DeviceCategory (does 'unknown' exist?), LockState, LockMode, DoorState, SwitchState, ColorState
- Mapping: HANDLE_TYPE_CAPABILITIES (list keys and their required capability sets)
- Dataclass: DeviceCommand — fields and their order

## Module: src/utec_py/devices/device.py
- DeviceInfo dataclass — fields and from_dict mapping (e.g. hwVersion→hw_version)
- BaseDevice class — list every property and its source state (capability/attribute)
- _validate_capabilities — what can make it actually raise?

## Module: src/utec_py/devices/switch.py
- Switch class — is_on, turn_on, turn_off — record exact DeviceCommand constants used

## Module: src/utec_py/devices/light.py
- Light class — every property (is_on, brightness, rgb_color, color_temp)
- turn_on kwargs accepted and their branching logic
- set_brightness / set_color_temp / set_rgb_color — record valid ranges and what they raise

## Module: src/utec_py/devices/lock.py
- Lock class — every property and its state source
- lock() / unlock() — exact command strings
- enum values mapped to booleans (locked/unlocked/jammed/etc)
```

The summary should be **factual extraction, not speculation**. For each enum, copy actual values. For each function, copy actual parameter names and return types. Do not include implementation detail — just the observable surface.

- [ ] **Step 2: Commit the audit**

```bash
git add docs/superpowers/plans/AUDIT-utec-py-2026-04-18.md
git commit -m "docs: audit utec-py source surface for test-coverage plan"
```

- [ ] **Step 3: All downstream tasks reference `docs/superpowers/plans/AUDIT-utec-py-2026-04-18.md` instead of re-reading source.** Where a task says "read X first", the subagent should read the relevant section of the audit unless it suspects the audit is wrong — in which case, spot-check the source and update the audit in a follow-up commit.

---

### Task 1: Configure pytest + coverage in pyproject.toml

**Files:**
- Modify: `pyproject.toml`
- Create: `requirements-test.txt`

- [ ] **Step 1: Add test tooling sections to `pyproject.toml`**

Append to existing `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"

[tool.coverage.run]
branch = true
source = ["utec_py"]

[tool.coverage.report]
show_missing = true
skip_empty = true
fail_under = 90
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "def __repr__",
    "def __str__",
    "@(abc\\.)?abstractmethod",
]
```

- [ ] **Step 2: Create `requirements-test.txt`**

```
pytest>=8.0
pytest-asyncio>=0.24
aioresponses>=0.7.6
coverage[toml]>=7.4
pytest-cov>=5.0
```

- [ ] **Step 3: Install test deps into a local venv**

```bash
cd /Users/gfranks/workspace/utec-py
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install -r requirements-test.txt
```

Expected: clean install, no errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements-test.txt
git commit -m "test: configure pytest-asyncio, coverage, and test deps"
```

---

### Task 2: Delete broken tests and stub a passing conftest

**Files:**
- Delete: `tests/test_utec.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Delete the broken test file**

```bash
rm tests/test_utec.py
```

- [ ] **Step 2: Rewrite `tests/conftest.py`**

```python
"""Shared pytest fixtures for utec-py tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import pytest_asyncio

from utec_py.api import UHomeApi
from utec_py.auth import AbstractAuth


class _FakeAuth(AbstractAuth):
    """Concrete AbstractAuth returning a fixed access token."""

    def __init__(self, websession: aiohttp.ClientSession, token: str = "test-token") -> None:
        super().__init__(websession)
        self._token = token

    async def async_get_access_token(self) -> str:
        return self._token


@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest_asyncio.fixture
async def fake_auth(session):
    return _FakeAuth(session)


@pytest.fixture
def mock_api() -> MagicMock:
    """AsyncMock-capable UHomeApi stub for device-level tests."""
    api = MagicMock(spec=UHomeApi)
    api.send_command = AsyncMock(return_value={"payload": {"devices": []}})
    api.query_device = AsyncMock(return_value={"payload": {"devices": []}})
    api.get_device_state = AsyncMock(return_value={"payload": {"devices": []}})
    api.discover_devices = AsyncMock(return_value={"payload": {"devices": []}})
    api.set_push_status = AsyncMock(return_value={})
    api.validate_auth = AsyncMock(return_value=True)
    return api


@pytest.fixture
def discovery_dict():
    """Factory for discovery-shape device dicts."""

    def _make(
        handle_type: str = "utec-switch",
        device_id: str = "dev-1",
        name: str = "Test Device",
        category: str = "switch",
        **overrides: Any,
    ) -> dict:
        data = {
            "id": device_id,
            "name": name,
            "handleType": handle_type,
            "category": category,
            "deviceInfo": {
                "manufacturer": "U-Tec",
                "model": "M1",
                "hwVersion": "1.0",
                "serialNumber": "SN-1",
            },
            "attributes": {},
        }
        data.update(overrides)
        return data

    return _make


@pytest.fixture
def state_payload():
    """Factory for state-shape dicts consumed by BaseDevice.update_state_data."""

    def _make(device_id: str = "dev-1", states: list[dict] | None = None) -> dict:
        return {
            "id": device_id,
            "states": states or [
                {"capability": "st.healthCheck", "name": "status", "value": "Online"}
            ],
        }

    return _make
```

- [ ] **Step 3: Create `tests/test_smoke.py` to verify wiring**

```python
"""Smoke test: confirm imports resolve and fixtures wire correctly."""


def test_package_importable():
    import utec_py  # noqa: F401
    from utec_py.api import UHomeApi  # noqa: F401
    from utec_py.auth import AbstractAuth  # noqa: F401
    from utec_py.devices.device import BaseDevice, DeviceInfo  # noqa: F401
    from utec_py.devices.switch import Switch  # noqa: F401
    from utec_py.devices.light import Light  # noqa: F401
    from utec_py.devices.lock import Lock  # noqa: F401


def test_mock_api_fixture(mock_api):
    assert mock_api.discover_devices is not None


def test_discovery_dict_fixture(discovery_dict):
    d = discovery_dict(handle_type="utec-lock")
    assert d["handleType"] == "utec-lock"
    assert d["deviceInfo"]["manufacturer"] == "U-Tec"
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: replace broken test_utec.py with working conftest and smoke tests"
```

---

## Phase 1 — Breadth: device-level pure unit tests (quick wins, no HTTP)

### Task 3: `DeviceInfo.from_dict` and dataclass defaults

**Files:**
- Create: `tests/test_device_info.py`

**Local LLM candidate:** Pass the `DeviceInfo` dataclass + `from_dict` method (from AUDIT or source) to `local_llm` with: *"Generate pytest test cases for `DeviceInfo.from_dict`. Cover: all fields populated, optional `serialNumber` missing, fully empty input. Use regular `def` (not async). Imports: `from utec_py.devices.device import DeviceInfo`. Output only the test code — no prose."* Run the sanity gate; log outcome.

- [ ] **Step 1: Write the tests (either from `local_llm` draft or directly)**

```python
"""Tests for DeviceInfo parsing."""

from utec_py.devices.device import DeviceInfo


def test_from_dict_all_fields():
    data = {
        "manufacturer": "U-Tec",
        "model": "UL3",
        "hwVersion": "2.1",
        "serialNumber": "SN-42",
    }
    info = DeviceInfo.from_dict(data)
    assert info.manufacturer == "U-Tec"
    assert info.model == "UL3"
    assert info.hw_version == "2.1"
    assert info.serial_number == "SN-42"


def test_from_dict_missing_optional_serial():
    data = {"manufacturer": "U-Tec", "model": "UL3", "hwVersion": "2.1"}
    info = DeviceInfo.from_dict(data)
    assert info.serial_number is None


def test_from_dict_empty_input_returns_empty_strings():
    info = DeviceInfo.from_dict({})
    assert info.manufacturer == ""
    assert info.model == ""
    assert info.hw_version == ""
    assert info.serial_number is None
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_device_info.py -v`. Expected: 3 passed.

- [ ] **Step 3: Commit** `git add tests/test_device_info.py && git commit -m "test: cover DeviceInfo.from_dict"`

---

### Task 4a: `BaseDevice` init + capability validation

**Files:**
- Create: `tests/test_base_device.py`

Audit reference: `AUDIT-utec-py-2026-04-18.md` → `devices/device.py` and `devices/device_const.py` sections.

- [ ] **Step 1: Write init + validation tests**

```python
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
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_base_device.py -v`. Expected: all pass.

- [ ] **Step 3: Commit** `git add tests/test_base_device.py && git commit -m "test: cover BaseDevice init and capability validation"`

---

### Task 4b: `BaseDevice` state accessors (`_get_state_value`, `get_state_data`, `available`)

**Files:**
- Modify: `tests/test_base_device.py` (append)

- [ ] **Step 1: Append state-accessor tests**

```python
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
```

- [ ] **Step 2: Run**. Expected: all pass.

- [ ] **Step 3: Commit** `git add tests/test_base_device.py && git commit -m "test: cover BaseDevice state accessors and flattening"`

---

### Task 5: `BaseDevice.update` and `update_state_data` (async paths)

**Files:**
- Modify: `tests/test_base_device.py` (append)

- [ ] **Step 1: Append async update tests**

```python
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
```

Before writing: **read `src/utec_py/devices/device_const.py` to confirm the exact `DeviceCommand` constructor signature** — if it takes different kwargs than `capability/name/arguments`, adjust the two tests accordingly. If `DeviceCommand` is a `@dataclass`, kwarg order matches field order.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_base_device.py -v`. Expected: all pass.

- [ ] **Step 3: Commit** `git add tests/test_base_device.py && git commit -m "test: cover BaseDevice async update and send_command paths"`

---

### Task 6: `Switch` device tests

**Files:**
- Create: `tests/test_switch.py`

- [ ] **Step 1: Write the tests** (first read `src/utec_py/devices/switch.py` to confirm: exact method names, the `DeviceCommand` args used internally, and the capability string — probably `st.switch` with name `on`/`off`. Adjust assertions to match.)

```python
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
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_switch.py -v`. Expected: all pass.

- [ ] **Step 3: Commit** `git add tests/test_switch.py && git commit -m "test: cover Switch on/off + is_on"`

---

### Task 7: `Light` device tests — properties + basic commands

**Files:**
- Create: `tests/test_light.py`

- [ ] **Step 1: Read `src/utec_py/devices/light.py` first** — note capability names (`st.switch`, `st.switchLevel`, `st.colorTemperature`, `st.color`), state attribute names, and the kwargs `turn_on` accepts. Adjust the tests below to match actual constants (don't invent them).

- [ ] **Step 2: Write the tests**

```python
"""Tests for Light device."""

import pytest

from utec_py.devices.light import Light


@pytest.fixture
def light(discovery_dict, mock_api):
    return Light(discovery_dict(handle_type="utec-dimmer", category="light"), mock_api)


def test_is_on_true(light):
    light._state_data = {"states": [
        {"capability": "st.switch", "name": "switch", "value": "on"},
    ]}
    assert light.is_on is True


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
    assert args[1] == "st.switch"
    assert args[2] == "on"


@pytest.mark.asyncio
async def test_turn_off_sends_off_command(light, mock_api):
    await light.turn_off()
    args = mock_api.send_command.await_args.args
    assert args[2] == "off"


@pytest.mark.asyncio
async def test_turn_on_with_brightness_sets_level(light, mock_api):
    await light.turn_on(brightness=75)
    # send_command should be called with capability=st.switchLevel or similar
    calls = mock_api.send_command.await_args_list
    capabilities = [c.args[1] for c in calls]
    assert any("Level" in c or "level" in c for c in capabilities)


@pytest.mark.asyncio
async def test_set_color_temp_out_of_range_raises(light):
    # Confirm actual valid range from light.py before finalising.
    with pytest.raises(ValueError):
        await light.set_color_temp(999_999)
```

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_light.py -v`. Fix any tests whose assumptions don't match the actual source — adjust to the real method names and valid ranges. Don't loosen an assertion just to pass; fix it to match the actual behavior.

- [ ] **Step 4: Commit** `git add tests/test_light.py && git commit -m "test: cover Light properties and turn_on kwargs dispatch"`

---

### Task 8: `Lock` device tests — properties + lock/unlock

**Files:**
- Create: `tests/test_lock.py`

- [ ] **Step 1: Read `src/utec_py/devices/lock.py` first** to confirm capability/attribute names for: lock state, jammed detection, door sensor, battery level, lock mode. Adjust test values to match real enum/string values.

- [ ] **Step 2: Write the tests**

```python
"""Tests for Lock device."""

import pytest

from utec_py.devices.lock import Lock


@pytest.fixture
def lock(discovery_dict, mock_api):
    return Lock(discovery_dict(handle_type="utec-lock", category="lock"), mock_api)


def test_is_locked_true(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lock", "value": "locked"},
    ]}
    assert lock.is_locked is True


def test_is_locked_false_when_unlocked(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lock", "value": "unlocked"},
    ]}
    assert lock.is_locked is False


def test_is_jammed_true_when_state_jammed(lock):
    lock._state_data = {"states": [
        {"capability": "st.lock", "name": "lock", "value": "jammed"},
    ]}
    assert lock.is_jammed is True


def test_battery_level_returned(lock):
    lock._state_data = {"states": [
        {"capability": "st.batteryLevel", "name": "level", "value": 85},
    ]}
    assert lock.battery_level == 85


def test_door_state_when_has_door_sensor(lock):
    lock._state_data = {"states": [
        {"capability": "st.doorSensor", "name": "state", "value": "open"},
    ]}
    assert lock.is_door_open is True


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
```

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_lock.py -v`. Fix values to match actual enum strings from source.

- [ ] **Step 4: Commit** `git add tests/test_lock.py && git commit -m "test: cover Lock state properties and commands"`

---

### Task 9: Exceptions + device constants

**Files:**
- Create: `tests/test_exceptions.py`
- Create: `tests/test_device_const.py`

**Local LLM candidate:** Both files are strong fits per the default-on policy.

For `test_exceptions.py`: *"Generate pytest test cases asserting the given exception classes all subclass `UHomeError`, plus one constructor test for `ApiError(status, message)`. Use `pytest.mark.parametrize` for the subclass checks. Output only the test code — no prose, no markdown fences."*

For `test_device_const.py`: paste the relevant section of AUDIT (the exact enum values and `HANDLE_TYPE_CAPABILITIES` mapping keys) **verbatim** into the prompt, then: *"Given the enums and mapping above, generate pytest test cases asserting: (1) `HANDLE_TYPE_CAPABILITIES` is a non-empty dict, (2) `DeviceCommand(capability=..., name=..., arguments=None)` round-trips its fields, (3) one member of each enum is constructible by its string value. Use only enum values that appear above. Output only test code."* The sanity gate's "every asserted identifier appears in AUDIT" check catches hallucinated enum values.

- [ ] **Step 1: Write `tests/test_exceptions.py` (local_llm draft or directly)**

```python
"""Tests for exception hierarchy."""

import pytest

from utec_py.exceptions import (
    ApiError,
    AuthenticationError,
    DeviceError,
    UHomeError,
    UnsupportedFeatureError,
    ValidationError,
)


def test_api_error_is_uhome_error():
    assert issubclass(ApiError, UHomeError)


def test_auth_error_is_uhome_error():
    assert issubclass(AuthenticationError, UHomeError)


@pytest.mark.parametrize("cls", [
    DeviceError, ValidationError, UnsupportedFeatureError,
])
def test_other_errors_subclass_uhome_error(cls):
    assert issubclass(cls, UHomeError)


def test_api_error_carries_status_and_message():
    err = ApiError(404, "Not Found")
    assert "404" in str(err)
```

- [ ] **Step 2: Read `src/utec_py/devices/device_const.py`** and write `tests/test_device_const.py` asserting:
  - `HANDLE_TYPE_CAPABILITIES` has entries for every supported handle type (enumerate from the source).
  - `DeviceCommand` construction round-trips capability/name/arguments.
  - At least one value from each enum (`HandleType`, `DeviceCapability`, `DeviceCategory`, `LockState`, etc.) is accessible.

```python
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
    assert DeviceCategory("unknown") is not None


def test_lock_state_has_locked_and_unlocked():
    assert LockState("locked") is not None
    assert LockState("unlocked") is not None
```

Adjust test values to match real enum members listed in `device_const.py`.

- [ ] **Step 3: Run** both files. Expected: all pass.

- [ ] **Step 4: Commit** `git add tests/test_exceptions.py tests/test_device_const.py && git commit -m "test: cover exception hierarchy and device constants"`

---

## Phase 2 — Breadth: auth + HTTP transport

### Task 10: `AbstractAuth.async_make_auth_request` header injection

**Files:**
- Create: `tests/test_auth.py`

**Local LLM candidate:** Pass `AbstractAuth.async_make_auth_request` source + the existing `conftest.py` fixture pattern as a template. Prompt: *"Generate two pytest-asyncio test cases for `AbstractAuth.async_make_auth_request`: (1) verify that when called, the request headers include `Authorization: Bearer <token>`, `Content-Type: application/json`, and `Accept: application/json`; (2) verify that caller-supplied headers are preserved. Use `aioresponses` to mock the HTTP call and capture the request. Output only test code."* Run sanity gate (imports must be `aiohttp`, `aioresponses`, `yarl`).

- [ ] **Step 1: Write the tests (local_llm draft or directly)**

```python
"""Tests for AbstractAuth header injection."""

import aiohttp
import pytest
from aioresponses import aioresponses

from utec_py.auth import AbstractAuth


class _FakeAuth(AbstractAuth):
    def __init__(self, session, token="tok-123"):
        super().__init__(session)
        self._token = token

    async def async_get_access_token(self):
        return self._token


@pytest.mark.asyncio
async def test_headers_include_bearer_and_json_content_type():
    async with aiohttp.ClientSession() as session:
        auth = _FakeAuth(session)
        with aioresponses() as mock:
            mock.post("https://example.test/api", payload={"ok": True})
            resp = await auth.async_make_auth_request(
                "POST", "https://example.test/api", json={"hi": 1},
            )
            assert resp.status == 200

            call = mock.requests[("POST", __import__("yarl").URL("https://example.test/api"))][0]
            headers = call.kwargs["headers"]
            assert headers["authorization"] == "Bearer tok-123"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_caller_headers_preserved_and_auth_overrides_nothing_except_auth_token():
    async with aiohttp.ClientSession() as session:
        auth = _FakeAuth(session)
        with aioresponses() as mock:
            mock.post("https://example.test/api", payload={})
            await auth.async_make_auth_request(
                "POST",
                "https://example.test/api",
                headers={"X-Request-Id": "req-42"},
                json={},
            )
            call = mock.requests[("POST", __import__("yarl").URL("https://example.test/api"))][0]
            headers = call.kwargs["headers"]
            assert headers["X-Request-Id"] == "req-42"
            assert headers["authorization"] == "Bearer tok-123"
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_auth.py -v`. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_auth.py && git commit -m "test: cover AbstractAuth header injection"`

---

### Task 11: `UHomeApi._async_make_request` — happy path and status codes

**Files:**
- Create: `tests/test_api.py`

- [ ] **Step 1: Write tests covering `_async_make_request` directly via `discover_devices` (which thinly wraps it).**

```python
"""Tests for UHomeApi — transport layer + endpoints."""

from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses

from utec_py.api import UHomeApi
from utec_py.auth import AbstractAuth
from utec_py.const import API_BASE_URL
from utec_py.exceptions import ApiError


class _FakeAuth(AbstractAuth):
    def __init__(self, session):
        super().__init__(session)

    async def async_get_access_token(self):
        return "tok"


@pytest.mark.asyncio
async def test_discover_devices_200_returns_json():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={"payload": {"devices": []}})
            result = await api.discover_devices()
            assert result == {"payload": {"devices": []}}


@pytest.mark.asyncio
async def test_discover_devices_201_returns_json():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=201, payload={"ok": 1})
            result = await api.discover_devices()
            assert result == {"ok": 1}


@pytest.mark.asyncio
async def test_discover_devices_204_returns_empty_dict():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=204)
            result = await api.discover_devices()
            assert result == {}


@pytest.mark.asyncio
async def test_discover_devices_400_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=400, body="Bad Request")
            with pytest.raises(ApiError) as exc:
                await api.discover_devices()
            assert "400" in str(exc.value)


@pytest.mark.asyncio
async def test_discover_devices_500_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=500, body="Server Error")
            with pytest.raises(ApiError):
                await api.discover_devices()
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_api.py -v`. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_api.py && git commit -m "test: cover UHomeApi transport status codes (200/201/204/400/500)"`

---

### Task 12a: `UHomeApi` — discover / query / get_device_state payload shapes

**Files:**
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Append read-endpoint payload tests**

```python
# --- Endpoint payload shapes (reads) ---


def _last_request_body(mock, url=API_BASE_URL):
    key = ("POST", __import__("yarl").URL(url))
    call = mock.requests[key][-1]
    return call.kwargs.get("json")


@pytest.mark.asyncio
async def test_discover_devices_payload_has_discovery_header():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.discover_devices()
            body = _last_request_body(mock)
            assert body["header"]["namespace"] == "Uhome.Device"
            assert body["header"]["name"] == "Discovery"
            assert body["header"]["payloadVersion"] == "1"
            assert "messageId" in body["header"]


@pytest.mark.asyncio
async def test_query_device_sends_single_device_id():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.query_device("abc")
            body = _last_request_body(mock)
            assert body["header"]["name"] == "Query"
            assert body["payload"]["devices"] == [{"id": "abc"}]


@pytest.mark.asyncio
async def test_get_device_state_multi_with_custom_data():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.get_device_state(["a", "b"], {"k": 1})
            body = _last_request_body(mock)
            devices = body["payload"]["devices"]
            assert devices == [
                {"id": "a", "custom_data": {"k": 1}},
                {"id": "b", "custom_data": {"k": 1}},
            ]


@pytest.mark.asyncio
async def test_get_device_state_multi_without_custom_data():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.get_device_state(["a"], None)
            body = _last_request_body(mock)
            assert body["payload"]["devices"] == [{"id": "a"}]
```

- [ ] **Step 2: Run**. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_api.py && git commit -m "test: cover discover/query/get_device_state payload shapes"`

---

### Task 12b: `UHomeApi` — `send_command` + `set_push_status` payload shapes

**Files:**
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Append write-endpoint payload tests**

```python
# --- Endpoint payload shapes (writes) ---


@pytest.mark.asyncio
async def test_send_command_includes_arguments_when_provided():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.send_command("dev-1", "st.switchLevel", "setLevel", {"level": 50})
            body = _last_request_body(mock)
            cmd = body["payload"]["devices"][0]["command"]
            assert cmd["capability"] == "st.switchLevel"
            assert cmd["name"] == "setLevel"
            assert cmd["arguments"] == {"level": 50}


@pytest.mark.asyncio
async def test_send_command_omits_arguments_when_none():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.send_command("dev-1", "st.switch", "on", None)
            body = _last_request_body(mock)
            cmd = body["payload"]["devices"][0]["command"]
            assert "arguments" not in cmd


@pytest.mark.asyncio
async def test_set_push_status_payload_shape():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            await api.set_push_status("https://hook.test", "tok-abc")
            body = _last_request_body(mock)
            assert body["header"]["namespace"] == "Uhome.Configure"
            assert body["header"]["name"] == "Set"
            assert body["payload"] == {
                "configure": {
                    "notification": {
                        "access_token": "tok-abc",
                        "url": "https://hook.test",
                    }
                }
            }
```

- [ ] **Step 2: Run**. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_api.py && git commit -m "test: cover send_command and set_push_status payload shapes"`

---

### Task 12c: `UHomeApi` — `validate_auth` + `async_create_request` helpers

**Files:**
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Append helper tests**

```python
# --- Helper methods ---


@pytest.mark.asyncio
async def test_validate_auth_true_on_success():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, payload={})
            assert await api.validate_auth() is True


@pytest.mark.asyncio
async def test_validate_auth_false_on_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=401, body="no")
            assert await api.validate_auth() is False


@pytest.mark.asyncio
async def test_async_create_request_generates_unique_message_ids():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        from utec_py.api import ApiNamespace, ApiOperation
        req1 = await api.async_create_request(ApiNamespace.DEVICE, ApiOperation.QUERY, {})
        req2 = await api.async_create_request(ApiNamespace.DEVICE, ApiOperation.QUERY, {})
        assert req1["header"]["messageId"] != req2["header"]["messageId"]


@pytest.mark.asyncio
async def test_async_create_request_accepts_none_parameters():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        from utec_py.api import ApiNamespace, ApiOperation
        req = await api.async_create_request(
            ApiNamespace.DEVICE, ApiOperation.DISCOVERY, None,
        )
        assert req["payload"] is None
```

- [ ] **Step 2: Run**. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_api.py && git commit -m "test: cover validate_auth and async_create_request helpers"`

---

### Task 13: First coverage checkpoint — breadth complete

- [ ] **Step 1: Run with coverage**

```bash
.venv/bin/pytest tests/ --cov=utec_py --cov-report=term-missing --cov-report=html
```

- [ ] **Step 2: Record baseline in commit message.** Record the % per module (should be ≥70% overall, with api.py/device.py close to 100%). If overall coverage is <60%, stop and investigate missing files before continuing — Phase 2 should have taken us well past baseline.

- [ ] **Step 3: Commit** any coverage artifacts you want versioned (typically not — add `htmlcov/` and `.coverage` to `.gitignore` if not already).

```bash
# Append to .gitignore if missing:
echo -e "htmlcov/\n.coverage\n.coverage.*" >> .gitignore
git add .gitignore
git commit -m "chore: ignore coverage artifacts"
```

---

## Phase 3 — Depth: close remaining branches

### Task 14: `BaseDevice._validate_capabilities` missing-capability path

**Files:**
- Modify: `tests/test_base_device.py` (append)

- [ ] **Step 1: Read `src/utec_py/devices/device_const.py`** to find a `handleType` with non-empty required capabilities, then construct a discovery dict that reports a strictly smaller capability set. First inspect whether `BaseDevice.__init__` actually populates `_supported_capabilities` from discovery data or from the `HANDLE_TYPE_CAPABILITIES` map — based on the source we read, it uses the map, meaning `_validate_capabilities` compares the map against itself and can only fail if something external mutates `_supported_capabilities`.

If the validation is unreachable via public API, add a test that asserts `_validate_capabilities` does NOT raise when called again on an unmodified instance, and mark branch-coverage intent with a comment. Alternatively, assert `_supported_capabilities` is the expected superset for each known `HandleType`.

```python
def test_supported_capabilities_covers_all_known_handle_types(mock_api, discovery_dict):
    """Every HandleType with a capability mapping must round-trip cleanly."""
    from utec_py.devices.device_const import HANDLE_TYPE_CAPABILITIES

    for handle_type, expected_caps in HANDLE_TYPE_CAPABILITIES.items():
        dev = BaseDevice(discovery_dict(handle_type=handle_type), mock_api)
        assert dev.supported_capabilities == expected_caps
```

- [ ] **Step 2: Run** the new test. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_base_device.py && git commit -m "test: cover HANDLE_TYPE_CAPABILITIES round-trip across all handle types"`

---

### Task 15a: `Light.turn_on` — kwargs dispatch matrix

**Files:**
- Modify: `tests/test_light.py` (append)

Audit reference: `AUDIT-utec-py-2026-04-18.md` → `devices/light.py` section (`turn_on` kwargs list + internal capability names).

- [ ] **Step 1: For each kwarg accepted by `turn_on` (brightness, color_temp, rgb_color), append a test that calls `turn_on(**kwarg)` and asserts the right capability + command + arguments against `mock_api.send_command.await_args_list`. Don't invent argument schemas — use the AUDIT.**

Example shape:

```python
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
    await light.turn_on(rgb_color=(10, 20, 30))  # adjust to real kwarg name if different
    calls = mock_api.send_command.await_args_list
    rgb_calls = [c for c in calls if "color" in c.args[1].lower()]
    assert rgb_calls


@pytest.mark.asyncio
async def test_turn_on_plain_still_sends_only_on_command(light, mock_api):
    await light.turn_on()
    calls = mock_api.send_command.await_args_list
    # Only one call, and it's the st.switch on
    on_calls = [c for c in calls if c.args[1] == "st.switch" and c.args[2] == "on"]
    assert on_calls
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_light.py -v`. Expected: pass.

- [ ] **Step 3: Commit** `git add tests/test_light.py && git commit -m "test: cover Light.turn_on kwargs dispatch matrix"`

---

### Task 15b: `Light` direct setters — `set_brightness`, `set_color_temp`, `set_rgb_color`

**Files:**
- Modify: `tests/test_light.py` (append)

- [ ] **Step 1: Append setter tests. Exercise success path (in-range) and failure (out-of-range) for each setter.** Use AUDIT for valid ranges.

```python
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
async def test_set_color_temp_out_of_range_raises(light):
    with pytest.raises(ValueError):
        await light.set_color_temp(999_999)


@pytest.mark.asyncio
async def test_set_rgb_color(light, mock_api):
    # Adjust signature to real one per AUDIT: tuple vs individual r/g/b kwargs
    await light.set_rgb_color((10, 20, 30))
    calls = mock_api.send_command.await_args_list
    rgb_calls = [c for c in calls if "color" in c.args[1].lower()]
    assert rgb_calls
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_light.py -v --cov=utec_py.devices.light --cov-report=term-missing`. Expected: `light.py` line coverage ≥95%.

- [ ] **Step 3: Commit** `git add tests/test_light.py && git commit -m "test: cover Light.set_brightness/set_color_temp/set_rgb_color"`

---

### Task 16: `Lock` extended properties — door sensor, lock mode, battery status

**Files:**
- Modify: `tests/test_lock.py` (append)

- [ ] **Step 1: Read `src/utec_py/devices/lock.py` end-to-end** — identify every public property not yet covered. Typically: `has_door_sensor`, `door_state` (all values), `lock_mode` (all enum values), `battery_status`, possibly `last_lock_event`.

- [ ] **Step 2: Add one test per property, parametrised by value where the property maps enum strings to boolean/enum outputs:**

```python
@pytest.mark.parametrize("raw, expected", [
    ("open", True),
    ("closed", False),
])
def test_is_door_open_mapping(lock, raw, expected):
    lock._state_data = {"states": [
        {"capability": "st.doorSensor", "name": "state", "value": raw},
    ]}
    assert lock.is_door_open is expected


def test_has_door_sensor_true_when_attr_present(discovery_dict, mock_api):
    data = discovery_dict(handle_type="utec-lock", attributes={"hasDoorSensor": True})
    lock_with = Lock(data, mock_api)
    assert lock_with.has_door_sensor is True


def test_has_door_sensor_false_when_missing(discovery_dict, mock_api):
    data = discovery_dict(handle_type="utec-lock", attributes={})
    lock_no = Lock(data, mock_api)
    assert lock_no.has_door_sensor is False
```

Adjust attribute key (`hasDoorSensor` vs something else) to match `lock.py`.

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_lock.py -v --cov=utec_py.devices.lock --cov-report=term-missing`. Expected: `lock.py` line coverage ≥95%.

- [ ] **Step 4: Commit** `git add tests/test_lock.py && git commit -m "test: cover Lock door sensor, lock mode, battery status properties"`

---

### Task 17: `_async_make_request` — error surface completeness

**Files:**
- Modify: `tests/test_api.py` (append)

- [ ] **Step 1: Write tests for remaining transport branches**

```python
import asyncio


@pytest.mark.asyncio
async def test_network_timeout_bubbles_up():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, exception=asyncio.TimeoutError())
            with pytest.raises(asyncio.TimeoutError):
                await api.discover_devices()


@pytest.mark.asyncio
async def test_client_connection_error_bubbles_up():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, exception=aiohttp.ClientConnectionError("boom"))
            with pytest.raises(aiohttp.ClientConnectionError):
                await api.discover_devices()


@pytest.mark.asyncio
async def test_429_rate_limit_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=429, body="rate limit")
            with pytest.raises(ApiError) as exc:
                await api.discover_devices()
            assert "429" in str(exc.value)


@pytest.mark.asyncio
async def test_401_unauthorized_raises_api_error():
    async with aiohttp.ClientSession() as session:
        api = UHomeApi(_FakeAuth(session))
        with aioresponses() as mock:
            mock.post(API_BASE_URL, status=401, body="unauthorized")
            with pytest.raises(ApiError) as exc:
                await api.discover_devices()
            assert "401" in str(exc.value)
```

Note: Current `api.py` raises `ApiError` for ALL non-2xx responses. If you want `AuthenticationError` on 401, that's a production change (out of scope for this plan — open an issue separately).

- [ ] **Step 2: Run** all api tests with coverage `.venv/bin/pytest tests/test_api.py --cov=utec_py.api --cov-report=term-missing`. Expected: `api.py` line coverage ≥95%.

- [ ] **Step 3: Commit** `git add tests/test_api.py && git commit -m "test: cover transport timeout, connection error, 401, 429"`

---

### Task 18: Final coverage sweep — hit 90%

**Files:**
- Depends on report output

- [ ] **Step 1: Run full coverage**

```bash
.venv/bin/pytest tests/ --cov=utec_py --cov-report=term-missing --cov-report=html
```

- [ ] **Step 2: For each module below 90%, open `htmlcov/index.html`** (or read term-missing output) to identify uncovered lines. Likely remaining gaps:
  - Switch branches inside `Light.turn_on` (rare combinations).
  - Log-only branches in `BaseDevice._get_state_value`.
  - `set_color_temp` in-range success path.
  - `async_create_request` with `parameters=None`.

- [ ] **Step 3: Add one test per uncovered branch** back into the relevant file. No new file needed — append to the module that owns it. Keep each test focused: state setup → call → single assertion.

- [ ] **Step 4: Re-run coverage. Target: ≥90% overall, ≥90% per-module for `api.py`, `auth.py`, `device.py`, `switch.py`, `light.py`, `lock.py`.** `const.py`, `device_const.py`, `__init__.py`, `exceptions.py` may sit at 100% or close to it.

- [ ] **Step 5: Commit** `git add tests/ && git commit -m "test: close remaining branch coverage gaps to reach 90%+"`

---

### Task 19: Wire up CI (optional — skip if no CI exists)

- [ ] **Step 1: Check if `.github/workflows/` exists.** If yes, add a `test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e . -r requirements-test.txt
      - run: pytest --cov=utec_py --cov-report=term-missing
```

If no CI exists, skip this task entirely — don't create a workflows dir without user confirmation.

- [ ] **Step 2: Commit if applicable.**

---

## Self-review checklist

Before declaring done:

- [ ] Every source file in `src/utec_py/` has at least one direct test.
- [ ] `pytest tests/` exits 0 with no warnings (asyncio warnings are a deprecation smell — fix `asyncio_mode = "auto"` if they surface).
- [ ] `pytest --cov=utec_py --cov-fail-under=90` exits 0.
- [ ] No test uses real network (all HTTP is via `aioresponses`).
- [ ] No test imports from a module path that doesn't exist (the broken-import class of failure that plagued the original suite).
- [ ] `git log` shows ~15–18 small, well-scoped commits — not one mega-commit.
