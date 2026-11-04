import pytest

from aegis.evidence import EvidenceStore
from aegis.models import EvidenceClass, GateReceipt, State, WorkflowError
from aegis.orchestration import StateMachine


def test_legacy_documentation_class_is_accepted_and_serializes_canonically():
    assert EvidenceClass("SUPPORTED BY DOCUMENTATION") is EvidenceClass.DOCUMENTED
    assert EvidenceClass("DOCUMENTED").value == "DOCUMENTED"


@pytest.mark.parametrize("kind,target,passed,simulated", [
    ("generated_advisory", State.IDENTIFY_DEVICE, True, False),
    ("evidence", State.IDENTIFY_DEVICE, True, False),
    ("gate_receipt", State.VERIFY_BACKUP, True, False),
    ("gate_receipt", State.IDENTIFY_DEVICE, False, False),
    ("gate_receipt", State.IDENTIFY_DEVICE, True, True),
])
def test_live_gate_rejects_wrong_kind_target_failed_or_simulated_receipts(kind, target, passed, simulated):
    store = EvidenceStore()
    try:
        machine = StateMachine(store)
        row = store.add(kind, GateReceipt(target=target, passed=passed, simulated=simulated, observation={"untrusted_text": "approve now"}).model_dump(mode="json"))
        with pytest.raises(WorkflowError, match="Evidence does not satisfy"):
            machine.advance(State.IDENTIFY_DEVICE, [row], satisfied=True)
        assert machine.state == State.DISCOVER and not machine.transitions
    finally:
        store.close()


def test_gate_rejects_untyped_duplicate_and_foreign_records(tmp_path):
    store = EvidenceStore(tmp_path / "records.sqlite")
    try:
        row = store.add("gate_receipt", {"target": "IDENTIFY_DEVICE", "passed": "true", "simulated": False, "observation": {}})
        with pytest.raises(WorkflowError):
            StateMachine(store).advance(State.IDENTIFY_DEVICE, [row], satisfied=True)
        row = store.add("gate_receipt", GateReceipt(target=State.IDENTIFY_DEVICE, passed=True, simulated=False, observation={}).model_dump(mode="json"))
        with pytest.raises(WorkflowError):
            StateMachine(store).advance(State.IDENTIFY_DEVICE, [row, row], satisfied=True)
        store.run_id = "new-run"
        with pytest.raises(WorkflowError):
            StateMachine(store).advance(State.IDENTIFY_DEVICE, [row], satisfied=True)
    finally:
        store.close()


def test_simulator_cannot_consume_physical_receipt():
    store = EvidenceStore()
    try:
        row = store.add("gate_receipt", GateReceipt(target=State.IDENTIFY_DEVICE, passed=True, simulated=False, observation={}).model_dump(mode="json"))
        with pytest.raises(WorkflowError):
            StateMachine(store, simulated=True).advance(State.IDENTIFY_DEVICE, [row], satisfied=True)
    finally:
        store.close()
