"""Independent negative review cases: malformed backup data and approval order."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import plistlib
import time

import pytest

from aegis.agents.jailbreak import JailbreakAgent
from aegis.evidence import EvidenceStore
from aegis.models import State, WorkflowError
from aegis.safety.approval import Approval, plan_digest
from aegis.safety.backup import verify_backup


@pytest.mark.parametrize("invalid_name", ["Info.plist", "Status.plist", "Manifest.plist"])
def test_non_dictionary_backup_metadata_fails_with_structured_error(tmp_path, invalid_name):
    identifier = "a" * 40
    device = {"product_type": "iPad7,11", "product_version": "16.6.1", "device_token": hashlib.sha256(identifier.encode("ascii")).hexdigest()}
    values = {
        "Info.plist": {"Target Identifier": identifier, "Product Type": device["product_type"], "Product Version": device["product_version"], "Last Backup Date": datetime.now(timezone.utc).replace(tzinfo=None)},
        "Status.plist": {"SnapshotState": "finished"},
        "Manifest.plist": {"IsEncrypted": False},
    }
    values[invalid_name] = ["valid plist, invalid schema"]
    for name, value in values.items():
        (tmp_path / name).write_bytes(plistlib.dumps(value))
    with pytest.raises(WorkflowError) as captured:
        verify_backup(tmp_path, device)
    assert captured.value.code == "BACKUP_UNVERIFIED"


def test_expired_approval_cannot_create_approved_state_transitions(tmp_path, monkeypatch):
    device = {"product_type": "iPad7,11", "product_version": "16.6.1", "build_version": "20G81", "usb_mode": "normal", "device_token": "test-process-local-token"}
    host = {"system": "Linux", "machine": "x86_64", "is_wsl": False}
    receipt = {"verified": True, "manifest_digest": "fixture"}
    plan = {"simulated": False, "device": device, "host": host, "backup": receipt, "artifact": {"sha256": "fixture"}, "argv": [str((tmp_path / "palera1n").resolve()), "-l"]}

    class Discovery:
        async def discover(self):
            return {"devices": [deepcopy(device)], "host": deepcopy(host), "selection": "single-observed", "interfaces": {"usb_descriptors": {"status": "observed", "observations": [{"vendor_id": "0x05ac", "product_id": "0x12a8"}]}}}

    class Compatibility:
        def evaluate(self, observed_device, observed_host):
            return {"eligible": True}

    class Adapter:
        async def execute(self, binary, observed_host, prepared, approval):
            # The real adapter is the final single-use checkpoint. Earlier
            # state transitions must independently establish approval validity.
            approval.consume(prepared)
            raise AssertionError("Invalid approval reached physical adapter execution")

    monkeypatch.setattr("aegis.agents.jailbreak.verify_backup", lambda folder, observed: deepcopy(receipt))
    store = EvidenceStore()
    try:
        agent = JailbreakAgent(store, discovery=Discovery(), compatibility=Compatibility(), adapter=Adapter())
        agent.machine.state = State.AWAIT_OPERATOR_APPROVAL
        approval = Approval.from_response(plan, "APPROVE " + plan_digest(plan)[:12])
        approval.granted_at = time.monotonic() - 301
        # All asynchronous dependencies above complete immediately. Drive this
        # isolated coroutine directly so the negative gate test needs no host
        # event-loop or network initialization.
        operation = agent.execute(plan, approval, Path(plan["argv"][0]), tmp_path)
        try:
            with pytest.raises(WorkflowError):
                operation.send(None)
        finally:
            operation.close()
        assert agent.machine.state == State.AWAIT_OPERATOR_APPROVAL
        assert agent.machine.transitions == []
    finally:
        store.close()
