from aegis.evidence import EvidenceStore
from pydantic import ValidationError

from aegis.models import GateReceipt, State, Transition, WorkflowError

ORDER = [s for s in State if s != State.RECOVERY_GUIDANCE]
EDGES = {state: {ORDER[i + 1]} for i, state in enumerate(ORDER[:-1])}
EDGES[State.VALIDATE].add(State.RECOVERY_GUIDANCE)
EDGES[State.EXECUTE_SUPPORTED_JAILBREAK].add(State.RECOVERY_GUIDANCE)


class StateMachine:
    def __init__(self, store: EvidenceStore, simulated: bool = False):
        self.store, self.simulated = store, simulated
        self.state = State.DISCOVER
        self.transitions: list[Transition] = []

    def advance(self, target: State, evidence_ids: list[int], *, satisfied: bool):
        if target not in EDGES.get(self.state, set()):
            raise WorkflowError("INVALID_TRANSITION", f"Cannot transition {self.state} to {target}")
        records = self.store.current_records(evidence_ids)
        valid = bool(records)
        for record in records:
            try:
                receipt = GateReceipt.model_validate(record["payload"])
                valid = valid and record["kind"] == "gate_receipt" and receipt.target == target and receipt.passed and receipt.simulated == self.simulated
            except (ValidationError, TypeError):
                valid = False
        if satisfied is not True or not valid:
            raise WorkflowError("PRECONDITION_FAILED", f"Evidence does not satisfy {target}")
        item = Transition(source=self.state, target=target, evidence_ids=evidence_ids, simulated=self.simulated)
        self.store.add("transition", item.model_dump(mode="json"))
        self.transitions.append(item)
        self.state = target
        return item
