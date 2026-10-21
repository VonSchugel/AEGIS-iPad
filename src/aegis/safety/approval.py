from dataclasses import dataclass
import hashlib
import json
import time

from aegis.models import WorkflowError


def plan_digest(plan: dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class Approval:
    digest: str
    granted_at: float
    consumed: bool = False

    @classmethod
    def from_response(cls, plan: dict, response: str):
        digest = plan_digest(plan)
        if response != f"APPROVE {digest[:12]}":
            raise WorkflowError("APPROVAL_DENIED", "The exact approval phrase was not supplied")
        return cls(digest, time.monotonic())

    def check(self, plan: dict):
        if self.consumed or time.monotonic() - self.granted_at > 300 or self.digest != plan_digest(plan):
            raise WorkflowError("APPROVAL_INVALID", "Approval expired, was consumed, or does not match this plan")

    def consume(self, plan: dict):
        self.check(plan)
        self.consumed = True
