"""Offline, fail-closed comparison of observed properties with reviewed evidence.

This module performs no USB, network, subprocess, or device-modifying actions.
`eligible` means the reviewed palera1n adapter may proceed to further gates; it
does not mean an installation succeeded or that operator approval was granted.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from importlib.resources import files
import json
import re
from typing import Any


def load_compatibility_data() -> dict[str, Any]:
    """Load the versioned evidence snapshot shipped inside the package."""
    resource = files("aegis").joinpath("data", "compatibility.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _version(value: Any) -> tuple[int, int, int] | None:
    """Accept release versions only; never silently coerce beta labels."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?", value):
        return None
    parts = tuple(int(part) for part in value.split("."))
    return (parts + (0, 0, 0))[:3]


class CompatibilityAgent:
    """Agent B: evidence-linked method comparison, with conservative local scope."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data) if data is not None else load_compatibility_data()

    def evaluate(self, device: dict[str, Any], host: dict[str, Any]) -> dict[str, Any]:
        """Compare observations; missing or unreviewed properties block execution.

        The optional `is_virtual` host observation can block known VMs. Absence
        does not prove bare metal and must be checked by the execution briefing.
        The build train is checked for consistency, not against an IPSW catalog.
        """
        common: list[str] = []
        product = device.get("product_type")
        version = _version(device.get("product_version"))
        build = device.get("build_version")
        mode = device.get("usb_mode")
        if product not in self.data["target_product_types"]:
            common.append("Target model is unknown or outside the reviewed iPad7,11/iPad7,12 scope.")
        if version is None:
            common.append("Firmware version is unknown, malformed, or a prerelease; detect a supported release first.")
        if not isinstance(build, str) or not re.fullmatch(r"\d{2}[A-Z]\d{1,4}", build):
            common.append("Firmware build is unknown or unreviewed (including beta builds).")
        elif version and version[0] in (15, 16, 17, 18) and int(build[:2]) != version[0] + 4:
            common.append("Firmware version and build train disagree; repeat read-only identification.")
        if not isinstance(mode, str) or mode.lower() not in {"normal", "recovery", "dfu"}:
            common.append("USB state is unknown or unsupported; identify the device before planning.")

        palera1n = self.data["methods"]["palera1n"]
        pale_blockers = list(common)
        firmware_ok = bool(version and _version(palera1n["reviewed_min_version"]) <= version <= _version(palera1n["reviewed_max_version"]))
        if version and not firmware_ok:
            pale_blockers.append("Firmware is outside AEGIS's reviewed palera1n 15.0–18.4 policy; updated exact-version evidence is required.")
        system, machine = host.get("system"), host.get("machine")
        if not isinstance(system, str) or system not in palera1n["host_architectures"]:
            pale_blockers.append("palera1n requires a reviewed native Linux or macOS host; Windows is unsupported.")
        elif not isinstance(machine, str) or machine.lower() not in palera1n["host_architectures"][system]:
            pale_blockers.append("Host CPU architecture is unknown or outside this adapter's reviewed release artifacts.")
        if host.get("is_wsl") is not False:
            pale_blockers.append("WSL or unknown WSL status is unsupported for the physical palera1n workflow.")
        if host.get("is_virtual") is True:
            pale_blockers.append("Virtual-machine USB transport is outside this workflow's supported native-host scope.")

        dopamine = self.data["methods"]["dopamine"]
        dopamine_ok = bool(product in self.data["target_product_types"] and version and _version(dopamine["reviewed_min_version"]) <= version <= _version(dopamine["reviewed_max_version"]))
        dopamine_blockers = list(common)
        if version and not dopamine_ok:
            dopamine_blockers.append("Firmware is outside Dopamine 3.0.11's documented arm64 15.0–18.7.1 range.")
        dopamine_blockers.append("Manual research alternative: app installation/signing prerequisites are not implemented or verified by AEGIS.")
        options = [
            {"name": "palera1n", "version": palera1n["version"], "revision": palera1n["revision"], "firmware_compatible": firmware_ok and not common, "eligible": not pale_blockers, "manual_only": False, "blockers": pale_blockers, "classification": "SUPPORTED BY DOCUMENTATION" if firmware_ok and not common else "UNKNOWN", "persistence": "semi-tethered"},
            {"name": "Dopamine", "version": dopamine["version"], "revision": dopamine["revision"], "firmware_compatible": dopamine_ok and not common, "eligible": False, "manual_only": True, "blockers": dopamine_blockers, "classification": "SUPPORTED BY DOCUMENTATION" if dopamine_ok and not common else "UNKNOWN", "persistence": "semi-untethered"},
            {"name": "checkra1n", "version": self.data["methods"]["checkra1n"]["version"], "firmware_compatible": False, "eligible": False, "manual_only": True, "classification": "UNKNOWN", "blockers": ["Historical comparison only: no exact target/firmware execution policy or adapter is reviewed."], "persistence": "semi-tethered"},
            {"name": "checkm8", "version": None, "firmware_compatible": None, "eligible": False, "manual_only": True, "classification": "SUPPORTED BY DOCUMENTATION", "blockers": ["Boot-ROM exploit primitive, not a complete version-independent jailbreak or bootstrap."], "persistence": "boot-session primitive"},
        ]
        return {
            "eligible": not pale_blockers,
            "method": "palera1n" if not pale_blockers else None,
            "blockers": pale_blockers,
            "options": options,
            "evidence": deepcopy(self.data["evidence"]),
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_date": self.data["snapshot_date"],
            "policy": "Compatibility permits further backup/dependency/approval checks only; no physical experiment has been verified.",
            "limitations": ["Build syntax and release train consistency are checked; exact firmware/build existence is not established by this engine.", "Documentation is an upstream support claim, not an AEGIS hardware test.", "The local palera1n ceiling is narrower than the upstream general claim and is not an upstream maximum."],
        }


def evaluate(device: dict[str, Any], host: dict[str, Any]) -> dict[str, Any]:
    """Convenience interface for CLI consumers."""
    return CompatibilityAgent().evaluate(device, host)
