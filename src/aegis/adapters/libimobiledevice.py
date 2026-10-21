"""Read-only normal-mode discovery; identifiers stay in process memory only."""

from __future__ import annotations

import hashlib
import plistlib
import re
from typing import Any
from xml.parsers.expat import ExpatError

from aegis.adapters.process import ProcessRunner


PRODUCT_KEYS = {
    "ProductType": ("product_type", re.compile(r"(?:iPad|iPhone|iPod|AppleTV|Watch)\d+,\d+\Z")),
    "ProductVersion": ("product_version", re.compile(r"\d+(?:\.\d+){0,3}\Z")),
    "BuildVersion": ("build_version", re.compile(r"[0-9A-Za-z.]{2,32}\Z")),
}
_UDID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{8}-[0-9a-fA-F]{16})\Z")
MAX_OBSERVED_DEVICES = 16


def device_token(identifier: str) -> str:
    """Local pseudonymous binding, never a public device identifier."""
    return hashlib.sha256(identifier.strip().lower().encode("ascii")).hexdigest()


class LibimobiledeviceAdapter:
    """Only list and simple GetValue requests; never pairs or starts services."""

    def __init__(self, runner: Any | None = None) -> None:
        self.runner = runner if runner is not None else ProcessRunner()

    async def discover(self) -> dict[str, Any]:
        try:
            listing = await self.runner.run(["idevice_id", "-l"], timeout=10.0)
        except (OSError, ValueError):
            return {"devices": [], "status": "unavailable", "blockers": ["normal-mode-list-unavailable"]}
        if listing.cancelled:
            return {"devices": [], "status": "cancelled", "blockers": ["normal-mode-list-cancelled"]}
        if listing.timed_out or listing.returncode != 0:
            return {"devices": [], "status": "unknown", "blockers": ["normal-mode-list-failed"]}

        lines = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
        identifiers = list(dict.fromkeys(line for line in lines if _UDID.fullmatch(line)))
        blockers: list[str] = []
        if len(identifiers) != len(set(lines)):
            blockers.append("normal-mode-list-contained-unrecognized-data")
        if len(identifiers) > MAX_OBSERVED_DEVICES:
            blockers.append("normal-mode-device-count-exceeds-query-limit")
            identifiers = identifiers[:MAX_OBSERVED_DEVICES]
        devices: list[dict[str, Any]] = []
        for identifier in identifiers:
            profile: dict[str, Any] = {
                "product_type": None, "product_version": None, "build_version": None,
                "usb_mode": "normal", "identifiers": "REDACTED",
                "device_token": device_token(identifier), "token_scope": "local-only-pseudonymous",
                "observation_source": "libimobiledevice", "unavailable_properties": [],
            }
            for key, (field, pattern) in PRODUCT_KEYS.items():
                try:
                    # -s avoids the handshake that can initiate automatic pairing.
                    result = await self.runner.run(
                        ["ideviceinfo", "-s", "-u", identifier, "-k", key, "-x"], timeout=10.0
                    )
                    if result.cancelled:
                        return {"devices": devices, "status": "cancelled", "blockers": ["normal-mode-query-cancelled"]}
                    if result.timed_out or result.returncode != 0:
                        profile["unavailable_properties"].append(field)
                        continue
                    value = plistlib.loads(result.stdout.encode("utf-8"))
                    # Accept older wrappers returning a dictionary, but allowlist fields.
                    if isinstance(value, dict):
                        value = value.get(key)
                    if isinstance(value, str) and pattern.fullmatch(value):
                        profile[field] = value
                    else:
                        profile["unavailable_properties"].append(field)
                except (OSError, ValueError, TypeError, OverflowError, ExpatError, plistlib.InvalidFileException):
                    profile["unavailable_properties"].append(field)
            if profile["unavailable_properties"]:
                blockers.append("normal-mode-properties-inaccessible")
            devices.append(profile)
        return {"devices": devices, "status": "observed" if devices else "no-usbmux-devices-observed", "blockers": sorted(set(blockers))}
