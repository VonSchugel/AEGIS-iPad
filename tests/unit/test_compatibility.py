"""Compatibility boundary tests require no utilities or attached device."""

import json

import pytest

from aegis.agents.compatibility import CompatibilityAgent, load_compatibility_data


@pytest.fixture
def device():
    return {"product_type": "iPad7,11", "product_version": "16.6.1", "build_version": "20G81", "usb_mode": "normal"}


@pytest.fixture
def host():
    return {"system": "Linux", "machine": "x86_64", "is_wsl": False}


def test_supported_documented_target_permits_further_gates(device, host):
    result = CompatibilityAgent().evaluate(device, host)
    assert result["eligible"] is True
    assert result["method"] == "palera1n"
    assert result["blockers"] == []
    assert result["evidence"]
    assert "no physical experiment" in result["policy"]
    json.dumps(result)


@pytest.mark.parametrize("product", ["iPad7,11", "iPad7,12"])
@pytest.mark.parametrize("system,machine", [("Linux", "aarch64"), ("Darwin", "arm64"), ("Darwin", "x86_64")])
def test_both_target_models_on_reviewed_hosts(device, host, product, system, machine):
    device["product_type"] = product
    host.update(system=system, machine=machine)
    assert CompatibilityAgent().evaluate(device, host)["eligible"]


@pytest.mark.parametrize("version,build,eligible", [("14.8", "18H17", False), ("15.0", "19A346", True), ("18.4", "22E240", True), ("18.4.0", "22E240", True), ("18.4.1", "22E252", False), ("18.7.1", "22H31", False), ("18.7.10", "22H520", False), ("26.0", "23A341", False)])
def test_palera1n_policy_boundaries_are_not_open_ended(device, host, version, build, eligible):
    device.update(product_version=version, build_version=build)
    assert CompatibilityAgent().evaluate(device, host)["eligible"] is eligible


@pytest.mark.parametrize("field,value", [("product_type", None), ("product_type", "iPad8,1"), ("product_version", "UNKNOWN"), ("product_version", "18.4 beta 1"), ("product_version", 18.4), ("build_version", None), ("build_version", "22E5200s"), ("build_version", "19A346"), ("usb_mode", "unknown"), ("usb_mode", None)])
def test_unknown_or_inconsistent_device_properties_fail_closed(device, host, field, value):
    device[field] = value
    result = CompatibilityAgent().evaluate(device, host)
    assert result["eligible"] is False
    assert result["method"] is None
    assert result["blockers"]


@pytest.mark.parametrize("mutation", [{"system": "Windows"}, {"system": "FreeBSD"}, {"system": None}, {"system": []}, {"machine": "UNKNOWN"}, {"is_wsl": True}, {"is_wsl": None}, {"is_wsl": "false"}, {"is_virtual": True}])
def test_unsupported_host_blocks(device, host, mutation):
    host.update(mutation)
    assert not CompatibilityAgent().evaluate(device, host)["eligible"]


@pytest.mark.parametrize("mode", ["normal", "recovery", "DFU"])
def test_known_modes_can_be_assessed_without_changing_them(device, host, mode):
    device["usb_mode"] = mode
    assert CompatibilityAgent().evaluate(device, host)["eligible"]
    assert device["usb_mode"] == mode


def test_missing_host_observation_fails_closed(device):
    assert not CompatibilityAgent().evaluate(device, {})["eligible"]


def test_dopamine_current_documented_range_is_manual_only(device, host):
    device.update(product_version="18.7.1", build_version="22H31")
    result = CompatibilityAgent().evaluate(device, host)
    dopamine = next(option for option in result["options"] if option["name"] == "Dopamine")
    assert dopamine["firmware_compatible"] is True
    assert dopamine["version"] == "3.0.11"
    assert dopamine["manual_only"] is True
    assert dopamine["eligible"] is False
    assert result["method"] is None


def test_dopamine_range_does_not_extend_to_18_7_2(device, host):
    device.update(product_version="18.7.2", build_version="22H124")
    option = CompatibilityAgent().evaluate(device, host)["options"][1]
    assert option["firmware_compatible"] is False


def test_checkm8_never_becomes_installation_authorization(device, host):
    option = CompatibilityAgent().evaluate(device, host)["options"][-1]
    assert option["eligible"] is False
    assert option["firmware_compatible"] is None


def test_evidence_snapshot_complete_and_returned_by_copy(device, host):
    agent = CompatibilityAgent()
    first = agent.evaluate(device, host)
    required = {"question", "source_url", "revision", "observed", "classification", "confidence", "limitations", "reproduction", "next_step", "retrieved_at"}
    assert all(required <= item.keys() for item in first["evidence"])
    first["evidence"][0]["observed"] = "tampered"
    assert agent.evaluate(device, host)["evidence"][0]["observed"] != "tampered"


def test_output_omits_private_device_identifiers(device, host):
    device.update(udid="private-udid-example", serial_number="private-serial-example", ecid="private-ecid-example")
    serialized = json.dumps(CompatibilityAgent().evaluate(device, host))
    assert "private-" not in serialized


def test_official_digest_manifest_is_version_pinned():
    data = load_compatibility_data()
    assert data["methods"]["palera1n"]["version"] == "2.4"
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef") for value in data["methods"]["palera1n"]["artifacts"].values())
