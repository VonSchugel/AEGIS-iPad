"""All device and SSH operations in this suite are mocked."""
import asyncio
import copy
import json
import shlex
from pathlib import Path
from types import SimpleNamespace

import pytest

from aegis.adapters.libimobiledevice import device_token
from aegis.agents import validation

UDID = "a" * 40
TOKEN = device_token(UDID)

def result(stdout="", returncode=0, timed_out=False, cancelled=False):
    return SimpleNamespace(stdout=stdout, stderr="secret diagnostics", returncode=returncode, timed_out=timed_out, cancelled=cancelled)

def profile():
    return {"selection": "single-observed", "blockers": [], "devices": [{"device_token": TOKEN, "product_type": "iPad7,11", "usb_mode": "normal"}], "interfaces": {"usb_descriptors": {"status": "observed", "observations": [{"vendor_id": "0x05ac", "product_id": "0x12a8"}]}}}

class Discovery:
    def __init__(self, report=None):
        self.report = report if report is not None else profile()
        self.calls = 0

    async def discover(self):
        self.calls += 1
        if isinstance(self.report, Exception):
            raise self.report
        return copy.deepcopy(self.report)

class Runner:
    def __init__(self, identifier=UDID, hardware="iPad7,11", failure=None):
        self.identifier, self.hardware, self.failure = identifier, hardware, failure
        self.calls = []

    async def run(self, argv, timeout=15):
        self.calls.append((argv, timeout))
        if self.failure is not None:
            raise self.failure
        if argv[-1] == "-l":
            return result(self.identifier)
        if argv[-1] == validation.PROBES["hardware_identity"]:
            return result(self.hardware)
        if argv[-1] == validation.PROBES["package_manager"]:
            return result("Debian dpkg package management program version 1.22")
        if argv[-1] == validation.PROBES["local_command_execution"]:
            return result("0\n")
        return result()

@pytest.fixture
def transport(tmp_path, monkeypatch):
    key = tmp_path / "operator key"
    key.write_text("synthetic fixture key")
    paths = {name: str((tmp_path / name).resolve()) for name in ("ssh", "inetcat", "idevice_id")}
    monkeypatch.setattr(validation.shutil, "which", lambda name: paths.get(name))
    monkeypatch.setattr(validation, "_native_posix", lambda: True)
    return key, paths

def test_usb_bound_validation_can_pass(transport):
    key, paths = transport
    runner, discovery = Runner(), Discovery()
    output = asyncio.run(validation.ValidationAgent(runner, discovery).validate(TOKEN, identity=key))
    assert output["core_validated"] and output["status"] == "CORE_VALIDATED"
    assert discovery.calls == 3 and len(runner.calls) == 6
    assert UDID not in json.dumps(output) and TOKEN not in json.dumps(output)
    assert output["stable_installation"] == output["checks"]["reboot_behavior"]["result"] == "UNKNOWN"
    argv = runner.calls[1][0]
    assert argv[0] == paths["ssh"] and argv[1:4] == ["-F", "/dev/null", "-T"]
    assert f"HostKeyAlias=aegis-{TOKEN}" in argv
    assert "StrictHostKeyChecking=yes" in argv and "IdentitiesOnly=yes" in argv
    assert "root@127.0.0.1" not in argv and "-p" not in argv
    proxy = next(arg for arg in argv if arg.startswith("ProxyCommand="))
    assert "-u " + UDID in proxy and "-l 44" in proxy and " -n " not in proxy
    assert shlex.split(proxy.removeprefix("ProxyCommand=")) == [
        str(Path(paths["inetcat"]).resolve()), "-u", UDID, "-l", "44"
    ]

def test_token_can_be_derived_from_singleton(transport):
    key, _ = transport
    output = asyncio.run(validation.ValidationAgent(Runner(), Discovery()).validate(identity=key, ssh_port=22))
    assert output["core_validated"]

def test_unbound_connectivity_never_claims_core_success():
    output = asyncio.run(validation.ValidationAgent(Runner(), Discovery()).validate())
    assert output["checks"]["connectivity"]["result"] == "PASS"
    assert not output["core_validated"] and output["checks"]["device_binding"]["result"] == "UNKNOWN"

@pytest.mark.parametrize("change", ["ambiguous", "usb-unknown", "usb-empty", "usb-multiple", "blocker", "different-token"])
def test_unknown_or_ambiguous_selection_prevents_transport(transport, change):
    key, _ = transport
    report = profile()
    if change == "ambiguous":
        report["selection"] = "ambiguous"
    elif change == "usb-unknown":
        report["interfaces"]["usb_descriptors"]["status"] = "unknown"
    elif change == "usb-empty":
        report["interfaces"]["usb_descriptors"]["observations"] = []
    elif change == "usb-multiple":
        report["interfaces"]["usb_descriptors"]["observations"] *= 2
    elif change == "blocker":
        report["blockers"] = ["firmware-version-unknown"]
    else:
        report["devices"][0]["device_token"] = "b" * 64
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery(report)).validate(TOKEN, identity=key))
    assert not output["core_validated"] and not runner.calls

@pytest.mark.parametrize("identifier", ["b" * 40, UDID + "\n" + "b" * 40, "malicious; reboot", ""])
def test_fresh_identifier_must_match_bound_device(transport, identifier):
    key, _ = transport
    runner = Runner(identifier=identifier)
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert not output["core_validated"] and len(runner.calls) == 1
    assert output["checks"]["device_binding"]["result"] == "FAIL"
    if identifier:
        assert identifier not in json.dumps(output)

def test_remote_hardware_mismatch_stops_remaining_probes(transport):
    key, _ = transport
    runner = Runner(hardware="iPhone10,6")
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert not output["core_validated"] and len(runner.calls) == 2
    assert output["checks"]["device_binding"]["result"] == "FAIL"

def test_query_oserror_is_structured_unknown(transport):
    key, _ = transport
    output = asyncio.run(validation.ValidationAgent(Runner(failure=OSError(UDID)), Discovery()).validate(TOKEN, identity=key))
    assert output["checks"]["device_binding"]["result"] == "UNKNOWN"
    assert UDID not in json.dumps(output) and not output["core_validated"]

def test_discovery_oserror_is_structured_unknown():
    discovery = Discovery(OSError(UDID))
    output = asyncio.run(validation.ValidationAgent(Runner(), discovery).validate(TOKEN))
    assert output["checks"]["connectivity"]["result"] == "UNKNOWN"
    assert discovery.calls == 3 and UDID not in json.dumps(output)

@pytest.mark.parametrize("port", [0, 65536, True, "44"])
def test_invalid_device_port_prevents_transport(transport, port):
    key, _ = transport
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, port, key))
    assert not output["core_validated"] and not runner.calls

def test_non_native_posix_prevents_transport(transport, monkeypatch):
    key, _ = transport
    monkeypatch.setattr(validation, "_native_posix", lambda: False)
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert not output["core_validated"] and not runner.calls

def test_missing_inetcat_prevents_transport(transport, monkeypatch):
    key, paths = transport
    monkeypatch.setattr(validation.shutil, "which", lambda name: paths.get(name) if name != "inetcat" else None)
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert not output["core_validated"] and not runner.calls

def test_remote_timeout_is_unknown_and_bounded(transport):
    key, _ = transport
    class TimeoutRunner(Runner):
        async def run(self, argv, timeout=15):
            if argv[-1] != "-l":
                self.calls.append((argv, timeout))
                return result(timed_out=True)
            return await super().run(argv, timeout)
    runner = TimeoutRunner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert len(runner.calls) == 2 and not output["core_validated"]
    assert output["checks"]["hardware_identity"]["result"] == "UNKNOWN"

def test_proxy_path_quotes_spaces_and_escapes_ssh_percent_tokens(transport):
    key, paths = transport
    paths["inetcat"] = str((key.parent / "inet%h cat").resolve())
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(TOKEN, identity=key))
    assert output["core_validated"]
    proxy = next(argument for argument in runner.calls[1][0] if argument.startswith("ProxyCommand="))
    assert "%%h" in proxy
    assert shlex.split(proxy.removeprefix("ProxyCommand=").replace("%%", "%"))[0] == str(Path(paths["inetcat"]).resolve())

@pytest.mark.parametrize("invalid", ["", "not-a-token", 123, True])
def test_invalid_expected_token_cannot_be_replaced_by_discovery(transport, invalid):
    key, _ = transport
    runner = Runner()
    output = asyncio.run(validation.ValidationAgent(runner, Discovery()).validate(invalid, identity=key))
    assert not runner.calls and not output["core_validated"]
