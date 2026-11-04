"""Fixtures never reach executable tool adapters or approval objects."""
from importlib.resources import files
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aegis.evidence import EvidenceStore
from aegis.models import GateReceipt, State
from aegis.orchestration.machine import StateMachine, ORDER


class FixtureDevice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_type: str | None = None
    product_version: str | None = None
    build_version: str | None = None
    usb_mode: str = "unknown"
    device_token: str | None = None


class FixtureProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    simulated: bool
    host: dict
    devices: list[FixtureDevice]


def load_fixture(path: Path | None = None) -> dict:
    text = path.read_text(encoding="utf-8") if path else files("aegis.data").joinpath("simulation.json").read_text()
    fixture = FixtureProfile.model_validate_json(text)
    if fixture.simulated is not True:
        raise ValueError("Fixture must be explicitly marked simulated=true")
    return fixture.model_dump()


def simulate(store: EvidenceStore, scenario: str = "success") -> dict:
    from aegis.agents.compatibility import CompatibilityAgent
    machine = StateMachine(store, simulated=True)
    def receipt(target: State, observation: dict) -> int:
        return store.add("gate_receipt", GateReceipt(target=target, passed=True, simulated=True, observation=observation).model_dump(mode="json"))
    fixture = load_fixture()
    device = fixture["devices"][0]
    if scenario == "unsupported":
        device["product_version"] = "99.0"
    decision = CompatibilityAgent().evaluate(device, fixture["host"])
    for target in ORDER[1:]:
        if target == State.VERIFY_BACKUP and not decision["eligible"]:
            record = store.add("simulation_block", {"simulated": True, "compatibility": decision})
            return {"simulated": True, "state": machine.state, "status": "BLOCKED", "record_id": record, "device_modified": False}
        observation = {"simulated": True, "classification": "EXPERIMENTAL", "fixture": scenario, "precondition_for": target}
        if target == State.EXECUTE_SUPPORTED_JAILBREAK:
            observation["approval"] = "SIMULATED ONLY; not an Approval instance"
        record = receipt(target, observation)
        machine.advance(target, [record], satisfied=True)
        if target == State.EXECUTE_SUPPORTED_JAILBREAK and scenario in {"timeout", "disconnect"}:
            fail = receipt(State.RECOVERY_GUIDANCE, {"simulated": True, "kind": scenario, "automatic_retries": 0})
            machine.advance(State.RECOVERY_GUIDANCE, [fail], satisfied=True)
            break
        if target == State.VALIDATE and scenario == "partial":
            fail = receipt(State.RECOVERY_GUIDANCE, {"simulated": True, "bootstrap": "UNKNOWN", "exit_code_alone_insufficient": True})
            machine.advance(State.RECOVERY_GUIDANCE, [fail], satisfied=True)
            break
    return {"simulated": True, "state": machine.state, "status": "SIMULATED", "device_modified": False,
            "native_linux_boot": "NOT TESTED", "transitions": [t.model_dump(mode="json") for t in machine.transitions]}
