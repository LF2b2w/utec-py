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
    ValidationError,
])
def test_other_errors_subclass_uhome_error(cls):
    assert issubclass(cls, UHomeError)


def test_device_error_is_plain_exception():
    # DeviceError inherits from Exception directly, NOT UHomeError (architectural anomaly)
    assert issubclass(DeviceError, Exception)
    assert not issubclass(DeviceError, UHomeError)


def test_unsupported_feature_error_is_device_error():
    # UnsupportedFeatureError -> DeviceError -> Exception (not UHomeError)
    assert issubclass(UnsupportedFeatureError, DeviceError)
    assert not issubclass(UnsupportedFeatureError, UHomeError)


def test_api_error_carries_status_and_message():
    err = ApiError(404, "Not Found")
    assert "404" in str(err)
