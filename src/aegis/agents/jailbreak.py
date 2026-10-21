from pathlib import Path
import asyncio
import hashlib

from aegis.adapters.palera1n import Palera1nAdapter
from aegis.evidence import EvidenceStore
from aegis.models import State, WorkflowError
from aegis.orchestration import StateMachine
from aegis.safety.approval import Approval, plan_digest
from aegis.safety.backup import verify_backup


class JailbreakAgent:
    def __init__(self, store: EvidenceStore, discovery=None, compatibility=None, adapter=None):
        from aegis.agents.discovery import DiscoveryAgent
        from aegis.agents.compatibility import CompatibilityAgent
        self.store = store
        self.discovery = discovery or DiscoveryAgent()
        self.compatibility = compatibility or CompatibilityAgent()
        self.adapter = adapter or Palera1nAdapter()
        self.machine = StateMachine(store)

    def transition(self, target: State, observation: dict, passed: bool = True):
        record = self.store.add("precondition", observation)
        self.machine.advance(target, [record], satisfied=passed)

    @staticmethod
    def singleton_inventory(discovery: dict) -> bool:
        inventory = discovery.get("interfaces", {}).get("usb_descriptors", {})
        observations = inventory.get("observations", [])
        return (not discovery.get("blockers") and discovery.get("selection") == "single-observed"
                and inventory.get("status") == "observed" and len(observations) == 1
                and observations[0].get("vendor_id") == "0x05ac")

    async def plan(self, backup: Path | None = None, binary: Path | None = None) -> dict:
        discovery = await self.discovery.discover()
        devices = discovery.get("devices", [])
        self.transition(State.IDENTIFY_DEVICE, {"device_count": len(devices), "selection": discovery.get("selection")},
                        len(devices) == 1 and self.singleton_inventory(discovery))
        device = devices[0]
        self.transition(State.VERIFY_COMPATIBILITY, {"device": device}, device.get("product_type") in {"iPad7,11", "iPad7,12"})
        decision = self.compatibility.evaluate(device, discovery["host"])
        self.transition(State.VERIFY_BACKUP, decision, decision["eligible"])
        if backup is None:
            raise WorkflowError("BACKUP_REQUIRED", "Supply a completed local backup for verification")
        receipt = verify_backup(backup, device)
        self.transition(State.PREPARE_ENVIRONMENT, receipt)
        if binary is None:
            raise WorkflowError("BINARY_REQUIRED", "Supply the locally obtained pinned upstream binary")
        artifact = await self.adapter.prepare(binary, discovery["host"])
        self.transition(State.SIMULATE, artifact)
        plan = {"simulated": False, "device": device, "host": discovery["host"], "backup": receipt,
                "artifact": artifact, "argv": [str(binary.resolve()), "-l"], "method": "palera1n", "attempt_limit": 1,
                "briefing": ["Owned and authorized research device; no lock or credential bypass.",
                             "Reviewed backup; manifest checks do not prove restoreability.",
                             "One rootless upstream invocation; operator follows upstream recovery/DFU prompts.",
                             "May reboot or change device storage and lose jailbreak state on reboot.",
                             "Disconnect other Apple devices; never reconnect another device during this experiment.",
                             "Timeout/cancellation stops host process but cannot roll back device changes."]}
        self.transition(State.AWAIT_OPERATOR_APPROVAL, {"argv": plan["argv"], "plan_digest": plan_digest(plan), "dry_run": True})
        return plan

    async def execute(self, plan: dict, approval: Approval, binary: Path, backup: Path, validation=None, operator_completion=None) -> dict:
        if self.machine.state != State.AWAIT_OPERATOR_APPROVAL or plan.get("simulated"):
            raise WorkflowError("UNPREPARED_PLAN", "Execution requires a live prepared plan in this process")
        fresh = await self.discovery.discover()
        devices = fresh.get("devices", [])
        if not self.singleton_inventory(fresh) or len(devices) != 1 or devices[0].get("usb_mode") != "normal" or not plan["device"].get("device_token") or devices[0] != plan["device"]:
            raise WorkflowError("TARGET_CHANGED", "Fresh normal-mode device identity/firmware must match the approved plan")
        if fresh["host"] != plan["host"] or not self.compatibility.evaluate(devices[0], fresh["host"])["eligible"]:
            raise WorkflowError("COMPATIBILITY_CHANGED", "Host or eligibility changed")
        if verify_backup(backup, devices[0]) != plan["backup"]:
            raise WorkflowError("BACKUP_CHANGED", "Backup changed after planning")
        approval.check(plan)
        self.transition(State.GUIDED_DEVICE_PREPARATION, {"approval_digest": approval.digest, "target_rechecked": True})
        self.transition(State.EXECUTE_SUPPORTED_JAILBREAK, {"upstream_dfU_guidance": "delegated after single-use approval; one invocation", "argv": plan["argv"]})
        try:
            result = await self.adapter.execute(binary, fresh["host"], plan, approval)
        except (OSError, WorkflowError, asyncio.CancelledError):
            self.transition(State.RECOVERY_GUIDANCE, {"reason": "Upstream invocation failed; no retry or automatic recovery"})
            raise
        try:
            private_retained = [self.store.retain_private_log("upstream-stdout", result.stdout), self.store.retain_private_log("upstream-stderr", result.stderr)]
        except OSError:
            private_retained = [False, False]
        self.store.add("upstream_result", {"returncode": result.returncode, "timed_out": result.timed_out,
                      "output_truncated": result.output_truncated, "private_logs_retained": all(private_retained),
                      "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                      "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
                      "log_policy": "Raw streams kept only in local private logs; excluded from evidence exports"})
        if result.returncode != 0 or result.timed_out:
            self.transition(State.RECOVERY_GUIDANCE, {"reason": "Nonzero exit or timeout; device state unknown"})
            return {"state": self.machine.state, "status": "UNVERIFIED", "recovery": "See docs/recovery.md. No automatic recovery action was performed."}
        self.transition(State.VALIDATE, {"tool_exited_zero": True, "jailbreak_success": "not yet independently verified"})
        if operator_completion is not None:
            try:
                operator_completion()
            except WorkflowError:
                self.transition(State.RECOVERY_GUIDANCE, {"bootstrap_completion": "unconfirmed", "automatic_action": "none"})
                raise
        if validation is None:
            from aegis.agents.validation import ValidationAgent
            validation = ValidationAgent(discovery=self.discovery)
        result = await validation.validate(expected_token=plan["device"]["device_token"])
        if not result["core_validated"]:
            self.transition(State.RECOVERY_GUIDANCE, result)
        else:
            self.transition(State.POST_JAILBREAK_RESEARCH, result)
            from aegis.agents.linux_research import LinuxResearchAgent
            research = LinuxResearchAgent().assess()
            self.transition(State.LINUX_FEASIBILITY_ASSESSMENT, research)
        return {"state": self.machine.state, "validation": result, "native_linux_boot": "NOT TESTED"}
