from copy import deepcopy

import pytest

from aegis.adapters.process import CommandResult
from aegis.agents.jailbreak import JailbreakAgent
from aegis.evidence import EvidenceStore
from aegis.models import State, WorkflowError
from aegis.safety.approval import Approval, plan_digest
from tests.unit.test_core import make_backup


def setup_workflow(tmp_path):
    backup = tmp_path / "backup"
    device = make_backup(backup)
    device.update(build_version="20H350", usb_mode="normal")
    report = {"devices": [device], "host": {"system": "Linux", "machine": "x86_64", "is_wsl": False}, "selection": "single-observed", "blockers": [], "interfaces": {"usb_descriptors": {"status": "observed", "observations": [{"vendor_id": "0x05ac", "product_id": "0x12a8"}]}}}
    class Discovery:
        async def discover(self):
            return deepcopy(report)
    class Adapter:
        calls = 0
        result = CommandResult(("fixture", "-l"), 0, "fixture: tool success alone is not proof")
        async def prepare(self, binary, host):
            return {"verified": True, "sha256": "fixture", "version": "2.4"}
        async def execute(self, binary, host, plan, approval):
            approval.consume(plan)
            self.calls += 1
            return self.result
    adapter = Adapter()
    store = EvidenceStore()
    agent = JailbreakAgent(store, discovery=Discovery(), adapter=adapter)
    return agent, adapter, report, backup, tmp_path / "binary", store


@pytest.mark.parametrize("outcome,state", [("core", State.LINUX_FEASIBILITY_ASSESSMENT), ("partial", State.RECOVERY_GUIDANCE), ("timeout", State.RECOVERY_GUIDANCE)])
async def test_full_fixture_workflow_approves_once_then_independently_validates(tmp_path, outcome, state):
    agent, adapter, report, backup, binary, store = setup_workflow(tmp_path)
    try:
        plan = await agent.plan(backup, binary)
        assert agent.machine.state == State.AWAIT_OPERATOR_APPROVAL and adapter.calls == 0
        approval = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
        if outcome == "timeout":
            adapter.result = CommandResult(("fixture",), -9, timed_out=True)
        class Validator:
            async def validate(self, expected_token):
                assert expected_token == report["devices"][0]["device_token"]
                return {"core_validated": outcome == "core", "stable_installation": "UNKNOWN"}
        result = await agent.execute(plan, approval, binary, backup, validation=Validator())
        assert result["state"] == state and adapter.calls == 1 and approval.consumed
        with pytest.raises(WorkflowError):
            await agent.execute(plan, approval, binary, backup, validation=Validator())
        assert adapter.calls == 1
    finally:
        store.close()


@pytest.mark.parametrize("change", ["device", "firmware", "inventory", "approval", "backup"])
async def test_changes_after_plan_never_invoke_upstream(tmp_path, change):
    agent, adapter, report, backup, binary, store = setup_workflow(tmp_path)
    try:
        plan = await agent.plan(backup, binary)
        approval = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
        if change == "device":
            report["devices"][0]["device_token"] = "c" * 64
        elif change == "firmware":
            report["devices"][0]["product_version"] = "18.4"
        elif change == "inventory":
            report["interfaces"]["usb_descriptors"]["status"] = "unknown"
        elif change == "approval":
            approval.granted_at -= 301
        elif change == "backup":
            (backup / "bb" / ("b" * 40)).unlink()
        with pytest.raises(WorkflowError):
            await agent.execute(plan, approval, binary, backup)
        assert adapter.calls == 0
        assert agent.machine.state == State.AWAIT_OPERATOR_APPROVAL
    finally:
        store.close()


async def test_incomplete_usb_inventory_cannot_prepare_physical_plan(tmp_path):
    agent, adapter, report, backup, binary, store = setup_workflow(tmp_path)
    try:
        report["interfaces"]["usb_descriptors"]["observations"] = []
        with pytest.raises(WorkflowError):
            await agent.plan(backup, binary)
        assert agent.machine.state == State.DISCOVER and adapter.calls == 0
    finally:
        store.close()
