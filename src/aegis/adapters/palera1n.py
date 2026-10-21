"""Pinned, rootless palera1n v2.4. No overrides, restore flags, or custom payloads."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re
import sys

from aegis.adapters.process import ProcessRunner
from aegis.models import WorkflowError
from aegis.safety.approval import Approval


class Palera1nAdapter:
    def __init__(self, runner=None):
        self.runner = runner or ProcessRunner()
        self.manifest = json.loads(files("aegis.data").joinpath("palera1n.json").read_text())

    def verify_artifact(self, binary: Path, host: dict) -> dict:
        if host.get("is_wsl") or host.get("system") not in {"Linux", "Darwin"}:
            raise WorkflowError("UNSUPPORTED_HOST", "Native Linux or macOS is required; Windows/WSL is blocked")
        machine = {"AMD64": "x86_64", "ARM64": "aarch64"}.get(host.get("machine"), host.get("machine"))
        if host.get("system") == "Darwin" and machine == "aarch64":
            machine = "arm64"
        asset = self.manifest["artifacts"].get(f"{host['system']}:{machine}")
        if not asset:
            raise WorkflowError("UNSUPPORTED_ARCH", "No pinned artifact for this host architecture")
        try:
            if not binary.is_file() or binary.is_symlink() or binary.stat().st_size > 128 * 1024 * 1024:
                raise OSError()
            with binary.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
        except OSError:
            raise WorkflowError("ARTIFACT_UNAVAILABLE", "Pinned binary must be a regular local file") from None
        if digest != asset["sha256"]:
            raise WorkflowError("ARTIFACT_HASH_MISMATCH", "Binary does not match the official pinned release digest")
        return {"verified": True, "version": self.manifest["version"], "sha256": digest,
                "source_url": self.manifest["source_url"], "asset": asset["name"]}

    async def prepare(self, binary: Path, host: dict) -> dict:
        artifact = self.verify_artifact(binary, host)
        result = await self.runner.run([str(binary.resolve()), "--version"], timeout=10, env=self.clean_environment())
        if result.returncode != 0 or result.timed_out or not re.search(r"(?<![\d.])v?2\.4(?![\d.])", result.stdout + result.stderr):
            raise WorkflowError("TOOL_VERSION_MISMATCH", "Pinned tool did not report version 2.4")
        return artifact

    async def execute(self, binary: Path, host: dict, plan: dict, approval: Approval):
        if not sys.stdin.isatty():
            raise WorkflowError("INTERACTIVE_APPROVAL_REQUIRED", "Physical execution requires interactive upstream DFU guidance")
        # Rehash just before invocation; approval binds the path, arguments, target and backup.
        artifact = self.verify_artifact(binary, host)
        if plan.get("artifact", {}).get("sha256") != artifact["sha256"] or plan.get("argv") != [str(binary.resolve()), "-l"]:
            raise WorkflowError("PLAN_CHANGED", "Prepared artifact or arguments changed")
        if plan.get("simulated"):
            raise WorkflowError("SIMULATION_NOT_EXECUTABLE", "Fixture plans cannot modify a device")
        approval.consume(plan)
        # No automated retry: one invocation only. Upstream owns interactive DFU guidance.
        return await self.runner.run([str(binary.resolve()), "-l"], timeout=900, interactive=True, env=self.clean_environment())

    @staticmethod
    def clean_environment() -> dict[str, str]:
        # Excludes PALERA1N_BYPASS_PASSCODE_CHECK and loader-injection variables.
        return {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C", "TERM": "dumb"}
