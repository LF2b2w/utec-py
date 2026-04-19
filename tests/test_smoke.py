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
