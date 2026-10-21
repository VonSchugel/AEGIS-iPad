"""Host and device discovery with observation-only Apple transports."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import ctypes.util
import json
import os
import platform
import re
import shutil
import sys
from datetime import datetime, timezone
from typing import Any

from aegis.adapters.libimobiledevice import LibimobiledeviceAdapter
from aegis.adapters.libirecovery import LibirecoveryAdapter
from aegis.adapters.process import ProcessRunner


UTILITY_NAMES = (
    "idevice_id", "ideviceinfo", "idevicebackup2", "irecovery", "usbmuxd", "iproxy",
    "palera1n", "ssh", "inetcat", "git", "clang", "llvm-readobj", "llvm-objdump", "rizin", "r2",
    "ghidra", "analyzeHeadless", "frida", "rea", "qemu-system-aarch64",
    "aarch64-linux-gnu-gcc", "make", "cmake", "powershell", "pwsh",
)
PYTHON_MODULES = {
    "pydantic": "pydantic", "typer": "typer", "click": "click", "pytest": "pytest", "pyusb": "usb",
    "lief": "lief", "capstone": "capstone", "frida": "frida",
}


def host_profile() -> dict[str, Any]:
    """Do not collect hostnames, usernames, addresses or device identifiers."""
    system = platform.system()
    return {
        "system": system, "machine": platform.machine(), "release": platform.release(),
        "processor": platform.processor(), "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(), "python_supported": sys.version_info >= (3, 12),
        "is_wsl": system == "Linux" and (
            "microsoft" in platform.release().lower() or bool(os.environ.get("WSL_INTEROP"))
        ),
    }


def _evidence(question: str, observed: str, *, source_url: str, classification: str = "VERIFIED", limitations: list[str] | None = None, reproduction: str = "aegis discover") -> dict[str, Any]:
    return {
        "question": question, "source_url": source_url, "revision": "runtime observation",
        "observed": observed, "classification": classification, "confidence": "high",
        "limitations": limitations or [], "reproduction": reproduction,
        "next_step": "Resolve listed blockers before selecting an installation workflow.",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def _python_dependencies() -> list[dict[str, Any]]:
    dependencies = []
    for distribution, module in PYTHON_MODULES.items():
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError, AttributeError):
            available = False
        try:
            version = importlib.metadata.version(distribution) if available else None
        except importlib.metadata.PackageNotFoundError:
            version = None
        dependencies.append({"name": distribution, "available": available, "version": version})
    return dependencies


def _native_libraries() -> list[dict[str, Any]]:
    libraries = []
    for name, aliases in {"libusb": ("usb-1.0", "libusb-1.0"), "libusbmuxd": ("usbmuxd-2.0", "usbmuxd")}.items():
        resolved = None
        for alias in aliases:
            try:
                resolved = ctypes.util.find_library(alias)
            except (OSError, ValueError):
                resolved = None
            if resolved:
                break
        libraries.append({"name": name, "available": bool(resolved), "resolved_name": resolved})
    return libraries


def _usb_descriptors() -> dict[str, Any]:
    """Read only numeric descriptors, never strings, configurations or interfaces."""
    try:
        import usb.core
    except ImportError:
        return {"status": "unavailable", "observations": [], "reason": "pyusb-not-installed"}
    try:
        observations = [
            {"vendor_id": f"0x{int(device.idVendor):04x}", "product_id": f"0x{int(device.idProduct):04x}"}
            for device in usb.core.find(find_all=True, idVendor=0x05AC)
        ]
        return {"status": "observed", "observations": observations, "reason": None}
    except Exception:
        # Backends can include private identifiers in exception text. Never expose it.
        return {"status": "unknown", "observations": [], "reason": "usb-backend-or-permission-unavailable"}


class DiscoveryAgent:
    """No pairing, reset, mode changes, writes or automatic retry loops."""

    def __init__(self, runner: Any | None = None) -> None:
        self.runner = runner if runner is not None else ProcessRunner()

    async def doctor(self) -> dict[str, Any]:
        host = host_profile()
        utilities = []
        for name in UTILITY_NAMES:
            path = shutil.which(name)
            utilities.append({"name": name, "available": bool(path), "path": path})
        return {
            "host": host, "utilities": utilities, "python_dependencies": _python_dependencies(), "native_libraries": _native_libraries(),
            "limitations": [
                "PATH presence does not establish binary provenance, version, driver support or working device communication.",
                "No located device or research utility is downloaded, installed or executed by doctor. Native-library lookup may consult platform helper programs.",
            ],
            "evidence": [_evidence(
                "What host environment is running discovery?",
                f"System={host['system']}; architecture={host['machine']}; Python={host['python_version']}; WSL={host['is_wsl']}",
                source_url="local://host/platform", reproduction="aegis doctor",
            )],
        }

    async def _observe_usb(self) -> dict[str, Any]:
        if not any(item["name"] == "pyusb" and item["available"] for item in _python_dependencies()):
            return {"status": "unavailable", "observations": [], "reason": "pyusb-not-installed"}
        # Isolate a potentially blocking native USB backend. A thread timeout would
        # leave the native call alive and can prevent Python from shutting down.
        script = "import json; from aegis.agents.discovery import _usb_descriptors; print(json.dumps(_usb_descriptors()))"
        try:
            result = await self.runner.run([sys.executable, "-c", script], timeout=5.0)
            if result.timed_out or result.cancelled or result.returncode != 0:
                return {"status": "unknown", "observations": [], "reason": "descriptor-query-failed"}
            payload = json.loads(result.stdout)
            observations = []
            for row in payload.get("observations", []):
                if isinstance(row, dict) and row.get("vendor_id") == "0x05ac" and re.fullmatch(r"0x[0-9a-f]{4}", str(row.get("product_id", ""))):
                    observations.append({"vendor_id": "0x05ac", "product_id": row["product_id"]})
            status = payload.get("status")
            return {"status": status if status in {"observed", "unknown", "unavailable"} else "unknown", "observations": observations, "reason": None if status == "observed" else "usb-backend-or-permission-unavailable"}
        except (OSError, ValueError, TypeError, AttributeError):
            return {"status": "unknown", "observations": [], "reason": "descriptor-query-failed"}

    async def _windows_usb_descriptors(self) -> dict[str, Any]:
        executable = "powershell" if shutil.which("powershell") else "pwsh" if shutil.which("pwsh") else None
        if executable is None:
            return {"status": "unavailable", "observations": [], "reason": "powershell-not-on-path"}
        # The PnP instance identifier is inspected in PowerShell but is never output.
        script = (
            "$ErrorActionPreference='Stop'; @(Get-PnpDevice -PresentOnly | "
            "Where-Object { $_.InstanceId -match '^USB\\\\VID_05AC&PID_[0-9A-Fa-f]{4}\\\\' } | "
            "ForEach-Object { if ($_.InstanceId -match 'VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})') "
            "{ [PSCustomObject]@{vendor_id=('0x'+$Matches[1].ToLower()); product_id=('0x'+$Matches[2].ToLower())} } }) | "
            "ConvertTo-Json -Compress"
        )
        try:
            result = await self.runner.run([executable, "-NoProfile", "-NonInteractive", "-Command", script], timeout=10.0)
            if result.timed_out or result.cancelled or result.returncode != 0:
                return {"status": "unknown", "observations": [], "reason": "pnp-observation-failed"}
            rows = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(rows, dict):
                rows = [rows]
            if not isinstance(rows, list):
                raise ValueError("invalid result shape")
            observations = [
                {"vendor_id": "0x05ac", "product_id": row["product_id"].lower()}
                for row in rows if isinstance(row, dict) and row.get("vendor_id", "").lower() == "0x05ac"
                and isinstance(row.get("product_id"), str) and re.fullmatch(r"0x[0-9A-Fa-f]{4}", row["product_id"])
            ]
            return {"status": "observed", "observations": observations, "reason": None}
        except (OSError, ValueError, TypeError, AttributeError):
            return {"status": "unknown", "observations": [], "reason": "pnp-observation-failed"}

    async def discover(self) -> dict[str, Any]:
        diagnostics = await self.doctor()
        host = diagnostics["host"]
        available = {item["name"] for item in diagnostics["utilities"] if item["available"]}
        blockers: list[str] = []
        devices: list[dict[str, Any]] = []
        interfaces: dict[str, Any] = {}
        evidence = list(diagnostics["evidence"])
        if {"idevice_id", "ideviceinfo"} <= available:
            normal = await LibimobiledeviceAdapter(self.runner).discover()
            devices.extend(normal["devices"])
            blockers.extend(normal["blockers"])
            interfaces["libimobiledevice"] = {"status": normal["status"]}
        else:
            interfaces["libimobiledevice"] = {"status": "unavailable"}
            blockers.append("normal-mode-discovery-tools-not-on-path")
        if "irecovery" in available:
            recovery = await LibirecoveryAdapter(self.runner).query()
            if recovery["device"]:
                devices.append(recovery["device"])
            blockers.extend(recovery["blockers"])
            interfaces["libirecovery"] = {"status": recovery["status"], "enumerates_all_devices": False}
        else:
            interfaces["libirecovery"] = {"status": "unavailable", "enumerates_all_devices": False}

        usb = await self._observe_usb()
        if host["system"] == "Windows" and usb["status"] != "observed":
            usb = await self._windows_usb_descriptors()
        interfaces["usb_descriptors"] = usb
        if len(devices) > 1 or len(usb["observations"]) > 1:
            blockers.append("multiple-device-observations-selection-ambiguous")
        if not devices:
            blockers.append("no-identifiable-apple-device-observed")
        for device in devices:
            if device["product_type"] is None:
                blockers.append("product-type-unknown")
            if device["product_version"] is None:
                blockers.append("firmware-version-unknown")
            if device["usb_mode"] == "unknown":
                blockers.append("usb-mode-unknown")
        if not host["python_supported"]:
            blockers.append("python-3.12-or-newer-required")
        selection = "ambiguous" if "multiple-device-observations-selection-ambiguous" in blockers else "single-observed" if len(devices) == 1 else "unknown"
        evidence.append(_evidence(
            "Can a single device and its firmware be identified through read-only interfaces?",
            f"Identifiable observations={len(devices)}; selection={selection}; USB descriptor status={usb['status']}",
            source_url="local://discovery/read-only",
            limitations=[
                "Absent tools, inaccessible drivers, locked devices and no observation do not prove that no physical device is connected.",
                "irecovery -q reports at most one recovery/DFU device and does not establish installed iPadOS firmware.",
                "USB vendor/product descriptors do not establish the product model or firmware.",
                "device_token is a local pseudonym; omit it from public reports.",
            ],
        ))
        return {"host": host, "devices": devices, "blockers": sorted(set(blockers)), "evidence": evidence, "interfaces": interfaces, "selection": selection}
