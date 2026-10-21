from aegis.evidence import EvidenceStore
from aegis.models import State, Transition, WorkflowError

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
        if not satisfied or not self.store.has_ids(evidence_ids):
            raise WorkflowError("PRECONDITION_FAILED", f"Evidence does not satisfy {target}")
        item = Transition(source=self.state, target=target, evidence_ids=evidence_ids, simulated=self.simulated)
        self.store.add("transition", item.model_dump(mode="json"))
        self.transitions.append(item)
        self.state = target
        return item
