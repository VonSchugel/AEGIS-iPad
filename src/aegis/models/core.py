from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceClass(StrEnum):
    VERIFIED = "VERIFIED"
    DOCUMENTED = "SUPPORTED BY DOCUMENTATION"
    EXPERIMENTAL = "EXPERIMENTAL"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    question: str
    source_url: str
    revision: str
    observed: str
    classification: EvidenceClass
    confidence: str
    limitations: str | list[str]
    reproduction: str
    next_step: str
    retrieved_at: str = Field(default_factory=utcnow)


class State(StrEnum):
    DISCOVER = "DISCOVER"
    IDENTIFY_DEVICE = "IDENTIFY_DEVICE"
    VERIFY_COMPATIBILITY = "VERIFY_COMPATIBILITY"
    VERIFY_BACKUP = "VERIFY_BACKUP"
    PREPARE_ENVIRONMENT = "PREPARE_ENVIRONMENT"
    SIMULATE = "SIMULATE"
    AWAIT_OPERATOR_APPROVAL = "AWAIT_OPERATOR_APPROVAL"
    GUIDED_DEVICE_PREPARATION = "GUIDED_DEVICE_PREPARATION"
    EXECUTE_SUPPORTED_JAILBREAK = "EXECUTE_SUPPORTED_JAILBREAK"
    VALIDATE = "VALIDATE"
    RECOVERY_GUIDANCE = "RECOVERY_GUIDANCE"
    POST_JAILBREAK_RESEARCH = "POST_JAILBREAK_RESEARCH"
    LINUX_FEASIBILITY_ASSESSMENT = "LINUX_FEASIBILITY_ASSESSMENT"


class Transition(BaseModel):
    source: State
    target: State
    evidence_ids: list[int] = Field(min_length=1)
    timestamp: str = Field(default_factory=utcnow)
    simulated: bool = False


class WorkflowError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code, self.message, self.details = code, message, details or {}
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}
