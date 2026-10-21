"""Independent bounded verification over a device-bound USB SSH transport."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import shlex
import shutil

from aegis.adapters.libimobiledevice import device_token
from aegis.adapters.process import ProcessRunner

_UDID = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{8}-[0-9a-fA-F]{16})\Z")
_TOKEN = re.compile(r"[0-9a-f]{64}\Z")
PROBES = {
    "hardware_identity": "if test -x /var/jb/usr/sbin/sysctl; then /var/jb/usr/sbin/sysctl -n hw.machine; elif test -x /usr/sbin/sysctl; then /usr/sbin/sysctl -n hw.machine; else /sbin/sysctl -n hw.machine; fi",
    "filesystem_access": "test -r /var/jb/etc/apt/sources.list.d",
    "bootstrap": "test -d /var/jb && test -x /var/jb/usr/bin/dpkg",
    "package_manager": "/var/jb/usr/bin/dpkg --version",
    "local_command_execution": "/usr/bin/id -u",
}

def _native_posix() -> bool:
    return os.name == "posix" and platform.system() in {"Linux", "Darwin"} and "microsoft" not in platform.release().lower() and not os.environ.get("WSL_INTEROP")

def _selected_device(report: dict) -> dict | None:
    devices = report.get("devices", [])
    usb = report.get("interfaces", {}).get("usb_descriptors", {})
    observations = usb.get("observations", [])
    if report.get("selection") != "single-observed" or report.get("blockers") or len(devices) != 1:
        return None
    if usb.get("status") != "observed" or len(observations) != 1:
        return None
    descriptor = observations[0]
    if descriptor.get("vendor_id") != "0x05ac" or not re.fullmatch(r"0x[0-9a-fA-F]{4}", str(descriptor.get("product_id", ""))):
        return None
    device = devices[0]
    if device.get("usb_mode") != "normal" or not _TOKEN.fullmatch(str(device.get("device_token", ""))):
        return None
    if not re.fullmatch(r"iPad\d+,\d+", str(device.get("product_type", ""))):
        return None
    return device

class ValidationAgent:
    def __init__(self, runner=None, discovery=None):
        self.runner = runner if runner is not None else ProcessRunner()
        self.discovery = discovery

    async def validate(self, expected_token: str | None = None, ssh_port: int | None = None, identity: Path | None = None) -> dict:
        """ssh_port means the device's SSH port, never a localhost listener."""
        checks: dict[str, dict] = {}
        if self.discovery is None:
            from aegis.agents.discovery import DiscoveryAgent
            self.discovery = DiscoveryAgent(self.runner)
        bound_token = expected_token if isinstance(expected_token, str) and _TOKEN.fullmatch(expected_token) else None
        invalid_expected = expected_token is not None and bound_token is None
        bound_product = None
        samples = []
        observation_error = False
        for _ in range(3):
            try:
                device = _selected_device(await self.discovery.discover())
            except (OSError, ValueError, TypeError, AttributeError):
                device = None
                observation_error = True
            if device is not None and bound_token is None and not invalid_expected:
                bound_token = device["device_token"]
                bound_product = device["product_type"]
            if device is not None and bound_product is None:
                bound_product = device["product_type"]
            samples.append(bool(device is not None and not invalid_expected and device["device_token"] == bound_token and device["product_type"] == bound_product))
        connected = all(samples) and bool(bound_token) and not invalid_expected
        checks["connectivity"] = {"result": "PASS" if connected else "UNKNOWN" if observation_error else "FAIL", "observations": samples}
        checks["usb_reliability"] = {"result": "PASS" if connected else "UNKNOWN" if observation_error else "FAIL", "scope": "Three read-only singleton observations; not a stress test"}
        checks["device_binding"] = {"result": "UNKNOWN", "reason": "A fresh USB identifier and hardware response have not both been verified"}
        for name in [*PROBES, "ssh"]:
            checks[name] = {"result": "UNKNOWN", "reason": "A device-bound USB SSH session, identity key and preconfigured host-key pin are required"}
        port = 44 if ssh_port is None else ssh_port
        eligible = connected and identity is not None and isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535 and _native_posix()
        if eligible:
            try:
                key = Path(identity).resolve()
                ssh, inetcat, listing_tool = (shutil.which(name) for name in ("ssh", "inetcat", "idevice_id"))
                eligible = key.is_file() and bool(ssh and inetcat and listing_tool)
                if eligible:
                    eligible = all(Path(executable).is_absolute() for executable in (ssh, inetcat, listing_tool))
            except (OSError, ValueError, TypeError):
                eligible = False
        if eligible:
            try:
                listing = await self.runner.run([listing_tool, "-l"], timeout=5.0)
                lines = [line.strip() for line in listing.stdout.splitlines() if line.strip()]
                if listing.returncode != 0 or listing.timed_out or listing.cancelled:
                    checks["device_binding"] = {"result": "UNKNOWN", "reason": "Fresh USB identifier query failed"}
                elif len(lines) != 1 or not _UDID.fullmatch(lines[0]) or device_token(lines[0]) != bound_token:
                    checks["device_binding"] = {"result": "FAIL", "reason": "Fresh USB selection does not match the bound device"}
                else:
                    # Identifier remains in this local scope and transient argv only.
                    # OpenSSH expands percent tokens before invoking the shell.
                    proxy = shlex.join([str(Path(inetcat).resolve()), "-u", lines[0], "-l", str(port)]).replace("%", "%%")
                    base = [str(Path(ssh).resolve()), "-F", "/dev/null", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no", "-o", "ConnectionAttempts=1", "-o", "ConnectTimeout=5", "-o", f"HostKeyAlias=aegis-{bound_token}", "-o", f"ProxyCommand={proxy}", "-i", str(key), "root@aegis-usb"]
                    for name, command in PROBES.items():
                        try:
                            response = await self.runner.run([*base, command], timeout=10.0)
                            if response.timed_out or response.cancelled:
                                checks[name] = {"result": "UNKNOWN", "reason": "Read-only USB SSH probe timed out or was cancelled"}
                                break
                            passed = response.returncode == 0
                            if name == "hardware_identity":
                                passed = passed and response.stdout.strip() == bound_product
                            elif name == "local_command_execution":
                                passed = passed and response.stdout.strip() == "0"
                            elif name == "package_manager":
                                passed = passed and "dpkg" in response.stdout.lower()
                            checks[name] = {"result": "PASS" if passed else "FAIL", "transport": "USB-only inetcat; explicit device binding; pinned SSH host key"}
                            if name == "hardware_identity":
                                checks["device_binding"] = {"result": "PASS" if passed else "FAIL", "reason": "Fresh identifier digest and remote hw.machine compared with the selected profile"}
                                if not passed:
                                    break
                        except (OSError, ValueError):
                            checks[name] = {"result": "UNKNOWN", "reason": "USB SSH probe could not be started"}
                            break
                    checks["ssh"] = {"result": "PASS" if all(checks[name]["result"] == "PASS" for name in PROBES) else "UNKNOWN" if any(checks[name]["result"] == "UNKNOWN" for name in PROBES) else "FAIL"}
            except (OSError, ValueError):
                checks["device_binding"] = {"result": "UNKNOWN", "reason": "Fresh USB identifier query could not be started"}
        for name in ("reboot_behavior", "graphical_package_manager", "long_term_stability"):
            checks[name] = {"result": "UNKNOWN", "reason": "Requires a separate operator-controlled experiment"}
        core = all(checks[name]["result"] == "PASS" for name in ("connectivity", "usb_reliability", "device_binding", "ssh", *PROBES))
        return {"status": "CORE_VALIDATED" if core else "PARTIAL_OR_UNVERIFIED", "core_validated": core,
                "checks": checks, "stable_installation": "UNKNOWN", "classification": "VERIFIED" if core else "UNKNOWN",
                "limitations": "Three connectivity observations and fixed read-only probes establish limited core behavior only. Reboot persistence and stability remain unknown. USB-only SSH requires a native POSIX host and an operator-configured identity and known_hosts pin; no tunnel, reboot or device writes are performed."}
