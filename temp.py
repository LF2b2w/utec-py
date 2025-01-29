
    async def async_get_devices(self) -> List[Device]:
        """Get list of devices."""
        response = await self._api_call("GET", "/devices")
        return [Device.from_dict(device) for device in response]

    async def async_get_device(self, device_id: str) -> Device:
        """Get device details."""
        response = await self._api_call("GET", f"/devices/{device_id}")
        return Device.from_dict(response)

    async def async_get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status."""
        return await self._api_call("GET", f"/devices/{device_id}/status")

    async def async_lock(self, device_id: str) -> Dict[str, Any]:
        """Lock a device."""
        return await self._send_action(device_id, DEVICE_ACTION_LOCK)

    async def async_unlock(self, device_id: str) -> Dict[str, Any]:
        """Unlock a device."""
        return await self._send_action(device_id, DEVICE_ACTION_UNLOCK)

    async def async_set_temperature(self, device_id: str, temperature: float) -> Dict[str, Any]:
        """Set temperature for a thermostat."""
        return await self._send_action(
            device_id,
            "setTemperature",
            {"temperature": temperature}
        )

