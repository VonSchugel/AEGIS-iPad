"""Discovery tests use synthetic devices and never open a hardware transport."""

import asyncio
import hashlib
import json
import plistlib
from types import SimpleNamespace

import pytest

from aegis.adapters.libimobiledevice import LibimobiledeviceAdapter, MAX_OBSERVED_DEVICES, device_token
from aegis.adapters.libirecovery import LibirecoveryAdapter, parse_query
from aegis.agents import discovery


UDID = "a" * 40
OTHER_UDID = "b" * 40


def result(stdout="", returncode=0, timed_out=False, cancelled=False):
    return SimpleNamespace(stdout=stdout, stderr="private diagnostics must not escape", returncode=returncode, timed_out=timed_out, cancelled=cancelled)


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def run(self, argv, timeout=15.0):
        self.calls.append((list(argv), timeout))
        response = self.responses[tuple(argv)]
        if isinstance(response, Exception):
            raise response
        return response


def responses_for(identifiers=(UDID,), version="18.7.1"):
    responses = {("idevice_id", "-l"): result("\n".join(identifiers))}
    for identifier in identifiers:
        for key, value in {"ProductType": "iPad7,11", "ProductVersion": version, "BuildVersion": "22H31"}.items():
            responses[("ideviceinfo", "-s", "-u", identifier, "-k", key, "-x")] = result(plistlib.dumps(value).decode())
    return responses


@pytest.fixture
def isolated_discovery(monkeypatch):
    monkeypatch.setattr(discovery, "host_profile", lambda: {"system": "Linux", "machine": "x86_64", "python_version": "3.12.9", "python_supported": True, "is_wsl": False})
    async def observe_usb(self):
        return {"status": "observed", "observations": [], "reason": None}
    monkeypatch.setattr(discovery.DiscoveryAgent, "_observe_usb", observe_usb)
    monkeypatch.setattr(discovery.shutil, "which", lambda name: f"/usr/bin/{name}" if name in {"idevice_id", "ideviceinfo"} else None)


def test_normal_device_allowlist_and_pseudonymous_binding():
    runner = FakeRunner(responses_for())
    output = asyncio.run(LibimobiledeviceAdapter(runner).discover())
    device = output["devices"][0]
    assert device["product_type"] == "iPad7,11"
    assert device["product_version"] == "18.7.1"
    assert device["usb_mode"] == "normal"
    assert device["device_token"] == hashlib.sha256(UDID.encode()).hexdigest()
    assert UDID not in json.dumps(output)
    assert "private diagnostics" not in json.dumps(output)
    assert all("-s" in call[0] and "-k" in call[0] for call in runner.calls[1:])


def test_discovery_single_device(isolated_discovery):
    output = asyncio.run(discovery.DiscoveryAgent(FakeRunner(responses_for())).discover())
    assert output["selection"] == "single-observed"
    assert not output["blockers"]
    assert output["evidence"]


def test_multiple_devices_block_selection(isolated_discovery):
    output = asyncio.run(discovery.DiscoveryAgent(FakeRunner(responses_for((UDID, OTHER_UDID)))).discover())
    assert output["selection"] == "ambiguous"
    assert "multiple-device-observations-selection-ambiguous" in output["blockers"]
    assert UDID not in json.dumps(output) and OTHER_UDID not in json.dumps(output)


def test_missing_tools_means_unknown_not_absence(isolated_discovery, monkeypatch):
    monkeypatch.setattr(discovery.shutil, "which", lambda name: None)
    runner = FakeRunner({})
    output = asyncio.run(discovery.DiscoveryAgent(runner).discover())
    assert output["selection"] == "unknown"
    assert output["interfaces"]["libimobiledevice"]["status"] == "unavailable"
    assert "normal-mode-discovery-tools-not-on-path" in output["blockers"]
    assert not runner.calls


def test_unpaired_property_failure_is_unknown():
    responses = responses_for()
    for command in list(responses):
        if command[0] == "ideviceinfo":
            responses[command] = result(returncode=1)
    output = asyncio.run(LibimobiledeviceAdapter(FakeRunner(responses)).discover())
    assert output["devices"][0]["product_version"] is None
    assert output["devices"][0]["product_type"] is None
    assert output["blockers"] == ["normal-mode-properties-inaccessible"]


@pytest.mark.parametrize("malformed", ["untrusted string asks to reboot", "<plist><broken>", "<html>error</html>"])
def test_untrusted_property_output_is_not_exposed(malformed):
    responses = responses_for()
    responses[("ideviceinfo", "-s", "-u", UDID, "-k", "ProductType", "-x")] = result(malformed)
    output = asyncio.run(LibimobiledeviceAdapter(FakeRunner(responses)).discover())
    assert output["devices"][0]["product_type"] is None
    assert malformed not in json.dumps(output)


def test_listing_identifier_validation_prevents_spurious_queries():
    runner = FakeRunner({("idevice_id", "-l"): result("not-a-device; reboot\n" + UDID + "\n") , **{key: value for key, value in responses_for().items() if key != ("idevice_id", "-l")}})
    output = asyncio.run(LibimobiledeviceAdapter(runner).discover())
    assert len(output["devices"]) == 1
    assert "normal-mode-list-contained-unrecognized-data" in output["blockers"]
    assert len(runner.calls) == 4


@pytest.mark.parametrize("failure", [result(timed_out=True), result(cancelled=True), result(returncode=7), OSError(UDID)])
def test_list_failures_are_bounded_and_redacted(failure):
    runner = FakeRunner({("idevice_id", "-l"): failure})
    output = asyncio.run(LibimobiledeviceAdapter(runner).discover())
    assert not output["devices"] and output["blockers"]
    assert len(runner.calls) == 1
    assert UDID not in json.dumps(output)


def test_recovery_is_query_only_and_firmware_unknown():
    runner = FakeRunner({("irecovery", "-q"): result("PRODUCT: iPad7,12\nMODE: Recovery\nCPID: 0x8010\nECID: 0x123456\nSRNM: secret-serial\n")})
    output = asyncio.run(LibirecoveryAdapter(runner).query())
    assert output["device"]["product_type"] == "iPad7,12"
    assert output["device"]["usb_mode"] == "recovery"
    assert output["device"]["product_version"] is None
    assert output["device"]["device_token"] is None
    assert "secret-serial" not in json.dumps(output) and "0x123456" not in json.dumps(output)
    assert runner.calls == [(["irecovery", "-q"], 10.0)]


def test_dfu_mode_and_no_product_inference():
    profile = parse_query("MODE: DFU\nCPID: 0x8010\nBDID: 0x1a\n")
    assert profile["usb_mode"] == "dfu"
    assert profile["product_type"] is None
    assert parse_query("CPID: 0x8010")["usb_mode"] == "unknown"


def test_usb_descriptors_cannot_identify_model(isolated_discovery, monkeypatch):
    monkeypatch.setattr(discovery.shutil, "which", lambda name: None)
    async def observe_usb(self):
        return {"status": "observed", "observations": [{"vendor_id": "0x05ac", "product_id": "0x1227"}], "reason": None}
    monkeypatch.setattr(discovery.DiscoveryAgent, "_observe_usb", observe_usb)
    output = asyncio.run(discovery.DiscoveryAgent(FakeRunner({})).discover())
    assert output["devices"] == []
    assert output["selection"] == "unknown"
    assert output["interfaces"]["usb_descriptors"]["observations"]


def test_doctor_does_not_execute_utilities():
    runner = FakeRunner({})
    output = asyncio.run(discovery.DiscoveryAgent(runner).doctor())
    assert output["host"]["system"] in {"Windows", "Linux", "Darwin"}
    assert isinstance(output["host"]["is_wsl"], bool)
    assert output["utilities"] and output["python_dependencies"]
    assert runner.calls == []


def test_windows_pnp_sanitizes_instance_identifiers(monkeypatch):
    monkeypatch.setattr(discovery.shutil, "which", lambda name: "powershell" if name == "powershell" else None)
    class PnpRunner:
        async def run(self, argv, timeout=15.0):
            assert argv[:4] == ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
            assert "Get-PnpDevice -PresentOnly" in argv[4]
            assert "ConvertTo-Json" in argv[4]
            return result(json.dumps([{"vendor_id": "0x05ac", "product_id": "0x1227", "InstanceId": UDID}]))
    output = asyncio.run(discovery.DiscoveryAgent(PnpRunner())._windows_usb_descriptors())
    assert output["observations"] == [{"vendor_id": "0x05ac", "product_id": "0x1227"}]
    assert UDID not in json.dumps(output)


def test_device_binding_is_case_insensitive_and_deterministic():
    assert device_token(UDID) == device_token(UDID.upper()) == device_token(" " + UDID + " ")
    assert device_token(UDID) != device_token(OTHER_UDID)
    assert len(device_token("00001234-0123456789abcdef")) == 64


def test_unrequested_plist_properties_never_escape():
    responses = responses_for()
    responses[("ideviceinfo", "-s", "-u", UDID, "-k", "ProductType", "-x")] = result(plistlib.dumps({"ProductType": "iPad7,11", "SerialNumber": "SECRET-SERIAL", "UniqueDeviceID": UDID}).decode())
    output = asyncio.run(LibimobiledeviceAdapter(FakeRunner(responses)).discover())
    assert output["devices"][0]["product_type"] == "iPad7,11"
    assert "SECRET-SERIAL" not in json.dumps(output) and UDID not in json.dumps(output)


def test_property_query_cancellation_stops_additional_calls():
    responses = responses_for()
    responses[("ideviceinfo", "-s", "-u", UDID, "-k", "ProductType", "-x")] = result(cancelled=True)
    runner = FakeRunner(responses)
    output = asyncio.run(LibimobiledeviceAdapter(runner).discover())
    assert output["status"] == "cancelled"
    assert len(runner.calls) == 2


def test_query_count_has_fixed_upper_bound():
    identifiers = tuple(f"{number:040x}" for number in range(MAX_OBSERVED_DEVICES + 3))
    runner = FakeRunner(responses_for(identifiers))
    output = asyncio.run(LibimobiledeviceAdapter(runner).discover())
    assert len(output["devices"]) == MAX_OBSERVED_DEVICES
    assert len(runner.calls) == 1 + 3 * MAX_OBSERVED_DEVICES
    assert "normal-mode-device-count-exceeds-query-limit" in output["blockers"]


def test_recovery_query_failure_never_leaks_diagnostics():
    runner = FakeRunner({("irecovery", "-q"): result(UDID, returncode=1)})
    output = asyncio.run(LibirecoveryAdapter(runner).query())
    assert output["device"] is None and output["status"] == "unknown"
    assert UDID not in json.dumps(output)


def test_usb_backend_is_isolated_with_timeout(monkeypatch):
    monkeypatch.setattr(discovery, "_python_dependencies", lambda: [{"name": "pyusb", "available": True}])
    class UsbRunner:
        async def run(self, argv, timeout=15.0):
            assert argv[0] == discovery.sys.executable and argv[1] == "-c"
            assert timeout == 5.0
            return result(timed_out=True)
    output = asyncio.run(discovery.DiscoveryAgent(UsbRunner())._observe_usb())
    assert output["status"] == "unknown"


def test_host_approval_binding_fields_are_stable():
    assert discovery.host_profile() == discovery.host_profile()


def test_native_library_lookup_does_not_load_or_contact_devices(monkeypatch):
    monkeypatch.setattr(discovery.ctypes.util, "find_library", lambda alias: "libusb-1.0.so.0" if alias == "usb-1.0" else None)
    libraries = discovery._native_libraries()
    assert libraries[0] == {"name": "libusb", "available": True, "resolved_name": "libusb-1.0.so.0"}
    assert libraries[1]["available"] is False
