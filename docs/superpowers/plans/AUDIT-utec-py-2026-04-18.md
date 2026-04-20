# utec-py audit — 2026-04-18

Hand-written from source. Local LLM used on `device_const.py` only; output accepted with one correction (see LLM-LOG).

---

## Module: src/utec_py/__init__.py

Empty file — no public symbols.

---

## Module: src/utec_py/auth.py

- Class: `AbstractAuth(ABC)`
  - `__init__(self, websession: ClientSession) -> None`
    - Sets `self.websession = websession`
  - `async_get_access_token(self) -> str`  [@abstractmethod] — subclass must implement
  - `async_make_auth_request(self, method, host: str, **kwargs) -> ClientResponse`
    — injects `Content-Type: application/json`, `Accept: application/json`, `authorization: Bearer <token>`; merges with any caller-supplied headers; delegates to `self.websession.request(method, host, ...)`

---

## Module: src/utec_py/api.py

- Enum `ApiNamespace(str, Enum)`
  - `DEVICE = "Uhome.Device"`
  - `USER = "Uhome.User"`
  - `CONFIGURE = "Uhome.Configure"`

- Enum `ApiOperation(str, Enum)`
  - `DISCOVERY = "Discovery"`
  - `QUERY = "Query"`
  - `COMMAND = "Command"`
  - `SET = "Set"`

- TypedDict `ApiHeader` (also decorated `@dataclass`)
  - `namespace: str`
  - `name: str`
  - `messageId: str`
  - `payloadVersion: str`

- TypedDict `ApiRequest` (also decorated `@dataclass`)
  - `header: ApiHeader`
  - `payload: dict | None`

- Class: `UHomeApi`
  - `__init__(self, Auth: AbstractAuth) -> None` — sets `self.auth = Auth`
  - `async async_create_request(self, namespace: ApiNamespace, operation: ApiOperation, parameters: dict | None) -> ApiRequest`
    — builds header with `uuid4()` messageId, payloadVersion `"1"`; returns `{"header": ..., "payload": parameters}`
  - `async _async_make_request(self, **kwargs)`
    — POST to `API_BASE_URL`; 200/201/202 → `response.json()`; 204 → `{}`; other → raises `ApiError(status, text)`; always calls `response.release()`
  - `async validate_auth(self) -> bool`
    — calls `discover_devices()`; returns `True` on success, `False` on `ApiError`
  - `async discover_devices(self) -> Dict[str, Any]`
    — namespace=`DEVICE`, operation=`DISCOVERY`, payload=`{}`
  - `async get_device_state(self, device_ids: list, custom_data: dict | None) -> Dict[str, Any]`
    — builds `{"devices": [{"id": ..., "custom_data": ...}, ...]}` (omits `custom_data` key if `None`); namespace=`DEVICE`, op=`QUERY`
  - `async query_device(self, device_id: str)`
    — single-device query; params = `{"devices": [{"id": device_id}]}`; namespace=`DEVICE`, op=`QUERY`
  - `async send_command(self, device_id: str, capability: str, command: str, arguments: dict | None) -> Dict[str, Any]`
    — builds `{"capability": ..., "name": ...}`; omits `arguments` key when `None`; params = `{"devices": [{"id": ..., "command": ...}]}`; namespace=`DEVICE`, op=`COMMAND`
  - `async set_push_status(self, uri: str, access_token: str)`
    — params = `{"configure": {"notification": {"access_token": access_token, "url": uri}}}`; namespace=`CONFIGURE`, op=`SET`

---

## Module: src/utec_py/const.py

Constants (note: also defines duplicate/older enums not used by the rest of the package):

```
AUTH_BASE_URL = "https://oauth.u-tec.com/authorize?"
TOKEN_BASE_URL = "https://oauth.u-tec.com/token?"
API_BASE_URL   = "https://api.u-tec.com/action"

ATTR_HANDLE_TYPE  = "handleType"
ATTR_DEVICE_ID    = "id"
ATTR_NAME         = "name"
ATTR_CATEGORY     = "category"
ATTR_DEVICE_INFO  = "deviceInfo"
ATTR_ATTRIBUTES   = "attributes"
```

- Enum `ApiNamespace(str, Enum)` — **older/duplicate**, only `DEVICE` and `USER` members (no `CONFIGURE`)
  - `DEVICE = "Uhome.Device"`
  - `USER = "Uhome.User"`

- Enum `ApiOperation(str, Enum)` — **older/duplicate**, no `SET` member
  - `DISCOVERY = "Discovery"`
  - `QUERY = "Query"`
  - `COMMAND = "Command"`

- TypedDict `ApiHeader` — **older/duplicate**; field name is `messageID` (uppercase D) vs `messageId` in `api.py`
  - `namespace: ApiNamespace`
  - `name: ApiOperation`
  - `messageID: str`
  - `payloadVersion: str`

- TypedDict `ApiRequest` — **older/duplicate**
  - `header: ApiHeader`
  - `payload: Optional[dict[str, Any]]`

> Note: `api.py` defines its own enums and TypedDicts; `const.py` versions are older and not imported by current device code. `API_BASE_URL` from `const.py` is imported by `api.py`.

---

## Module: src/utec_py/exceptions.py

Hierarchy:

```
Exception
├── UHomeError
│   ├── AuthenticationError
│   ├── ApiError(status_code, message)
│   │     attrs: self.status_code, self.message
│   │     str: "API call failed: {status_code} - {message}"
│   └── ValidationError
└── DeviceError (inherits directly from Exception, NOT UHomeError)
    └── UnsupportedFeatureError
```

- `UHomeError(Exception)` — base for all U-Home errors
- `AuthenticationError(UHomeError)` — no extra fields
- `ApiError(UHomeError)` — `__init__(self, status_code, message)`; sets `self.status_code`, `self.message`
- `ValidationError(UHomeError)` — no extra fields
- `DeviceError(Exception)` — base for device errors; note: inherits from `Exception` directly, not `UHomeError`
- `UnsupportedFeatureError(DeviceError)` — no extra fields

---

## Module: src/utec_py/devices/__init__.py

Empty file — no public symbols.

---

## Module: src/utec_py/devices/device_const.py

- Enum `HandleType(str, Enum)`
  - `UTEC_LOCK = "utec-lock"`
  - `UTEC_LOCK_SENSOR = "utec-lock-sensor"`
  - `UTEC_DIMMER = "utec-dimmer"`
  - `UTEC_LIGHT_RGBAW = "utec-light-rgbaw-br"`
  - `UTEC_SWITCH = "utec-switch"`

- Enum `DeviceCapability(str, Enum)`
  - `SWITCH = "st.switch"`
  - `LOCK = "st.lock"`
  - `BATTERY_LEVEL = "st.batteryLevel"`
  - `LOCK_USER = "st.lockUser"`
  - `DOOR_SENSOR = "st.doorSensor"`
  - `BRIGHTNESS = "st.brightness"`
  - `SWITCH_LEVEL = "st.switchLevel"`
  - `COLOR = "st.color"`
  - `COLOR_TEMPERATURE = "st.colorTemperature"`
  - `HEALTH_CHECK = "st.healthCheck"`

- Enum `DeviceCategory(str, Enum)` — `"Unknown"` member exists
  - `LOCK = "SmartLock"`
  - `PLUG = "SmartPlug"`
  - `SWITCH = "SmartSwitch"`
  - `LIGHT = "LIGHT"`
  - `UNKNOWN = "Unknown"`

- Enum `LockState(str, Enum)`
  - `LOCKED = "Locked"`
  - `UNLOCKED = "Unlocked"`
  - `JAMMED = "Jammed"`
  - `UNKNOWN = "Unknown"`

- Enum `LockMode(IntEnum)` — per API spec: 0=Normal, 1=Passage, 2=Locked
  - `NORMAL = 0`
  - `PASSAGE = 1`
  - `LOCKED = 2`

- Enum `DoorState(str, Enum)`
  - `CLOSED = "Closed"`
  - `OPEN = "Open"`
  - `UNKNOWN = "Unknown"`

- Enum `SwitchState(str, Enum)` — read-only; commands use `"on"`/`"off"` strings directly
  - `ON = "on"`
  - `OFF = "off"`
  - `UNKNOWN = "Unknown"`  ← capital U

- Dataclass `DeviceCommand`
  - Fields (in order): `capability: str`, `name: str`, `arguments: Optional[Dict[str, Any]] = None`
  - `to_dict(self) -> Dict[str, Any]` — returns `{"capability": ..., "name": ...}`; adds `"arguments"` key only if `self.arguments` is truthy

- Dataclass `ColorState`
  - Fields: `r: int`, `g: int`, `b: int`  (each 0-255)
  - `from_dict(cls, data: Dict[str, int]) -> "ColorState"` — reads keys `"r"`, `"g"`, `"b"` with default 0
  - `to_dict(self) -> Dict[str, int]` — returns `{"r": ..., "g": ..., "b": ...}`

- Dataclass `ColorTemperatureRange(int)`
  - Fields: `min: int`, `max: int`, `step: int = 1`

- Class `BrightnessRange(int)` — constants only
  - `MIN = 0`
  - `MAX = 100`
  - `STEP = 1`

- Class `ColorTempRange(int)` — constants only
  - `MIN = 2000`
  - `MAX = 9000`
  - `STEP = 1`

- Mapping `HANDLE_TYPE_CAPABILITIES: Dict[str, Set[str]]`
  - `HandleType.UTEC_LOCK` → `{LOCK, BATTERY_LEVEL, LOCK_USER, HEALTH_CHECK}`
  - `HandleType.UTEC_LOCK_SENSOR` → `{LOCK, BATTERY_LEVEL, DOOR_SENSOR, HEALTH_CHECK}`
  - `HandleType.UTEC_DIMMER` → `{SWITCH, BRIGHTNESS, HEALTH_CHECK}`
  - `HandleType.UTEC_LIGHT_RGBAW` → `{SWITCH, BRIGHTNESS, COLOR, COLOR_TEMPERATURE, HEALTH_CHECK}`
  - `HandleType.UTEC_SWITCH` → `{SWITCH, HEALTH_CHECK}`

- Dataclass `DeviceState`
  - Fields: `capability: str`, `name: str`, `value: Any`
  - `from_dict(cls, data: Dict[str, Any]) -> "DeviceState"` — reads keys `"capability"`, `"name"`, `"value"` (no defaults, KeyError on missing)

- Dataclass `DeviceAttributes`
  - Fields: `color_model: str | None = None`, `color_temp_range: ColorTemperatureRange | None = None`, `switch_type: str | None = None`
  - `from_dict(cls, data: Dict[str, Any]) -> "DeviceAttributes"` — reads `"colorModel"`, `"switchType"`, `"colorTemperatureRange"` (dict with `min`/`max`/`step`)

- Dict `STATE_MAP`
  - `DoorState.CLOSED → "closed"`
  - `DoorState.OPEN → "open"`
  - `DoorState.UNKNOWN → "unknown"`
  - `SwitchState.ON → "on"`
  - `SwitchState.OFF → "off"`
  - `SwitchState.UNKNOWN → "unknown"`

---

## Module: src/utec_py/devices/device.py

- Dataclass `DeviceInfo`
  - Fields: `manufacturer: str`, `model: str`, `hw_version: str`, `serial_number: str | None = None`
  - `from_dict(cls, data: Dict[str, Any]) -> "DeviceInfo"`
    — key mapping: `"manufacturer"→manufacturer`, `"model"→model`, `"hwVersion"→hw_version`, `"serialNumber"→serial_number`
    — all except `serial_number` default to `""` on missing; `serial_number` defaults to `None`

- Class `BaseDevice`
  - `__init__(self, discovery_data: dict, api: UHomeApi) -> None`
    — extracts: `_id` ← `discovery_data["id"]`, `_name` ← `discovery_data["name"]`, `_handle_type` ← `discovery_data["handleType"]`, `_category` ← `discovery_data.get("category", "unknown")`, `_device_info` ← `DeviceInfo.from_dict(discovery_data.get("deviceInfo", {}))`, `_attributes` ← `discovery_data.get("attributes", {})`, `_supported_capabilities` ← `HANDLE_TYPE_CAPABILITIES.get(self._handle_type, set())`
    — calls `_validate_capabilities()`
    — raises `DeviceError` (wrapping `KeyError`) if `id`, `name`, or `handleType` is missing

  Properties (all read-only):
  - `device_id -> str` — `self._id`
  - `name -> str` — `self._name`
  - `handle_type -> str` — `self._handle_type`
  - `category -> DeviceCategory` — `DeviceCategory(self._category)` (raises `ValueError` on unknown value)
  - `manufacturer -> str` — `self._device_info.manufacturer`
  - `model -> str` — `self._device_info.model`
  - `hw_version -> str` — `self._device_info.hw_version`
  - `serial_number -> str | None` — `self._device_info.serial_number`
  - `supported_capabilities -> Set[str]` — `self._supported_capabilities`
  - `available -> bool` — `False` if no `_state_data`; else `_get_state_value("st.healthCheck", "status") == "Online"`
  - `attributes -> Dict[str, Any]` — `self._attributes`
  - `device_info -> Dict[str, Any]` — `{"identifiers": {("uhome", device_id)}, "name": ..., "manufacturer": ..., "model": ..., "hw_version": ...}`

  Methods:
  - `has_capability(self, capability: str) -> bool`
  - `_validate_capabilities(self) -> None`
    — raises `DeviceError` if `HANDLE_TYPE_CAPABILITIES[handle_type]` is not a subset of `_supported_capabilities`
    — **can only raise when** `_supported_capabilities` was set from `HANDLE_TYPE_CAPABILITIES` (always a full match), so in practice never raises via normal construction — but would raise if `_supported_capabilities` were manually reduced
  - `_get_state_value(self, capability: str, attribute: str) -> Any`
    — scans `_state_data["states"]` list for matching `capability`+`name`; returns `value` or `None`
  - `get_state_data(self) -> dict`
    — returns `{capability: {attribute: value, ...}, ...}` flat dict from states list
  - `async send_command(self, command: DeviceCommand) -> None`
    — calls `self._api.send_command(...)`; updates `_last_update`; raises `DeviceError` on any exception
  - `async update(self) -> None`
    — calls `self._api.query_device(device_id)`; parses `response["payload"]["devices"][0]` into `_state_data`; raises `DeviceError` on failure
  - `async update_state_data(self, push_data: dict) -> Dict[str, Any] | None`
    — if `"states"` in push_data: sets `_state_data = push_data`; else logs warning (no return value in either branch — effectively `None`)

---

## Module: src/utec_py/devices/switch.py

- Class `Switch(BaseDevice)`

  Overrides:
  - `available -> bool` — `self._state_data is not None` (simpler than BaseDevice — does not check healthCheck)

  Properties:
  - `is_on -> bool` — `_get_state_value(DeviceCapability.SWITCH, "switch") == SwitchState.ON`; `False` if state is `None`

  Methods:
  - `async turn_on(self) -> None`
    — `DeviceCommand(capability=DeviceCapability.SWITCH, name="on")`; no arguments
  - `async turn_off(self) -> None`
    — `DeviceCommand(capability=DeviceCapability.SWITCH, name="off")`; no arguments

---

## Module: src/utec_py/devices/light.py

- Class `Light(BaseDevice)`

  Properties:
  - `is_on -> bool` — `_get_state_value(DeviceCapability.SWITCH, "switch") == SwitchState.ON`; `False` if `None`
  - `brightness -> int | None` — `_get_state_value(DeviceCapability.SWITCH_LEVEL, "level")`  ← attribute is `"level"` under `st.switchLevel`, not `st.brightness`
  - `color_temp -> int | None` — `_get_state_value(DeviceCapability.COLOR_TEMPERATURE, "temperature")` in Kelvin
  - `rgb_color -> Tuple[int, int, int] | None` — `_get_state_value(DeviceCapability.COLOR, "color")` → `ColorState.from_dict(...)` → `(r, g, b)`; `None` if no data
  - `supported_features -> set` — strings `"brightness"`, `"color"`, `"color_temp"` based on `has_capability()`

  Methods:
  - `async turn_on(self, **kwargs) -> None`
    — branches on kwargs (checked in order): `"brightness"` → `set_brightness()`; `"color_temp"` → `set_color_temp()`; `"rgb_color"` → `set_rgb_color(*...)`; else sends explicit `DeviceCommand(SWITCH, "on")`
    — **only one branch executes per call** (elif chain)
  - `async turn_off(self) -> None`
    — `DeviceCommand(capability=DeviceCapability.SWITCH, name="off")`; no arguments
  - `async set_brightness(self, brightness: int) -> None`
    — clamps to `max(1, min(BrightnessRange.MAX, brightness))` i.e. 1–100
    — `DeviceCommand(capability=SWITCH_LEVEL, name="setLevel", arguments={"level": brightness})`
  - `async set_color_temp(self, temp: int) -> None`
    — raises `ValueError` if `temp` not in `[ColorTempRange.MIN, ColorTempRange.MAX]` i.e. `[2000, 9000]`
    — `DeviceCommand(capability=COLOR_TEMPERATURE, name="temperature", arguments={"value": temp})`
  - `async set_rgb_color(self, red: int, green: int, blue: int) -> None`
    — no range validation (no raises)
    — `DeviceCommand(capability=COLOR, name="color", arguments={"value": {"r": red, "g": green, "b": blue}})`

---

## Module: src/utec_py/devices/lock.py

- Class `Lock(BaseDevice)`

  Overrides:
  - `category -> DeviceCategory` — always returns `DeviceCategory.LOCK` (hardcoded, ignores `_category`)

  Properties:
  - `lock_state -> str` — `_get_state_value(DeviceCapability.LOCK, "lockState")`; `"Unknown"` if `None`
  - `has_door_sensor -> bool` — `has_capability(DeviceCapability.DOOR_SENSOR)`
  - `door_state -> str | None` — `None` if no door sensor; else `_get_state_value(DeviceCapability.DOOR_SENSOR, "sensorState")` ← attribute name is `"sensorState"`
  - `lock_mode -> str | None` — `_get_state_value(DeviceCapability.LOCK, "lockMode")`; maps `LockMode.NORMAL→"Normal"`, `LockMode.PASSAGE→"Passage"`, `LockMode.LOCKED→"Locked"`; returns `None` if not in map
  - `is_locked -> bool` — `lock_state == LockState.LOCKED`; `False` if state is `None`
  - `is_jammed -> bool` — `lock_state == LockState.JAMMED`; `False` if state is `None`
  - `is_door_open -> bool | None` — `None` if no door sensor; else `door_state == DoorState.OPEN`
  - `battery_status -> str | None` — integer level 1-5 maps to `"Critically Low"/"Low"/"Medium"/"High"/"Full"`; `None` if level not in map
  - `battery_level -> int | None` — integer level 1-5 maps to `10/30/50/70/100`; `None` if raw level is `None`; `0` if level in unexpected range

  Methods:
  - `async lock(self) -> None`
    — `DeviceCommand(capability=DeviceCapability.LOCK, name="lock")`; no arguments
  - `async unlock(self) -> None`
    — `DeviceCommand(capability=DeviceCapability.LOCK, name="unlock")`; no arguments

  Enum-to-boolean mappings in Lock:
  - `LockState.LOCKED` → `is_locked = True`
  - `LockState.JAMMED` → `is_jammed = True`
  - `LockState.UNLOCKED` / `LockState.UNKNOWN` → both `is_locked` and `is_jammed` are `False`
  - `DoorState.OPEN` → `is_door_open = True`
  - `DoorState.CLOSED` / `DoorState.UNKNOWN` → `is_door_open = False`
