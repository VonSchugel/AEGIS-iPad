"""Query-only recovery/DFU observation. No reset, payload or shell operations."""

from __future__ import annotations

import re
from typing import Any

from aegis.adapters.process import ProcessRunner


def parse_query(output: str) -> dict[str, Any] | None:
    """Allowlist public properties and discard ECID, serial, IMEI and nonces."""
    values: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().upper() in {"PRODUCT", "MODE", "CPID", "BDID"}:
            values[key.strip().upper()] = value.strip()
    if not values:
        return None
    mode = values.get("MODE", "").lower()
    # An explicitly reported mode is evidence; PID or CPID alone is not.
    usb_mode = "dfu" if mode == "dfu" else "recovery" if mode == "recovery" else "unknown"
    product = values.get("PRODUCT")
    if product is not None and not re.fullmatch(r"(?:iPad|iPhone|iPod|AppleTV|Watch)\d+,\d+", product):
        product = None
    profile: dict[str, Any] = {
        "product_type": product, "product_version": None, "build_version": None,
        "usb_mode": usb_mode, "identifiers": "REDACTED", "device_token": None,
        "observation_source": "libirecovery", "unavailable_properties": ["product_version", "build_version"],
    }
    for key in ("CPID", "BDID"):
        value = values.get(key, "")
        if re.fullmatch(r"0x[0-9a-fA-F]{1,8}", value):
            profile[key.lower()] = value.lower()
    return profile


class LibirecoveryAdapter:
    def __init__(self, runner: Any | None = None) -> None:
        self.runner = runner if runner is not None else ProcessRunner()

    async def query(self) -> dict[str, Any]:
        try:
            result = await self.runner.run(["irecovery", "-q"], timeout=10.0)
        except (OSError, ValueError):
            return {"device": None, "status": "unavailable", "blockers": ["recovery-query-unavailable"]}
        if result.cancelled:
            return {"device": None, "status": "cancelled", "blockers": ["recovery-query-cancelled"]}
        if result.timed_out or result.returncode != 0:
            return {"device": None, "status": "unknown", "blockers": []}
        device = parse_query(result.stdout)
        return {"device": device, "status": "observed" if device else "unknown", "blockers": []}
