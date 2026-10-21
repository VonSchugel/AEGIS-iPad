"""Read-only REA capability discovery and an explicit MCP evidence boundary.

Finding an executable is a candidate, not proof of a working provider. This
module never installs REA, changes MCP configuration, or executes a target.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from collections.abc import Mapping, Sequence
from typing import Any


REA_DOCS = "https://github.com/morluto/rea/blob/main/docs/mcp-contracts.md"
STATIC_MCP_TOOLS = frozenset(
    {
        "binary_session", "open_binary", "close_binary", "binary_overview",
        "inspect_artifact", "inspect_firmware_regions", "list_procedures",
        "search_procedures", "list_strings", "search_strings", "analyze_function",
        "xrefs", "get_call_graph", "trace_call_path", "get_evidence_bundle",
        "inspect_analysis_view",
    }
)


class ReaResponseError(ValueError):
    """An error or unvalidated reply must never become an analysis finding."""

    def __init__(self, message: str, diagnostic: Any = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


def _strict_json(text: str) -> Any:
    def unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ReaResponseError("Duplicate JSON member in REA response")
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ReaResponseError("Non-finite JSON value in REA response", value)

    try:
        return json.loads(text, object_pairs_hook=unique_members, parse_constant=reject_constant)
    except (ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, ReaResponseError):
            raise
        raise ReaResponseError("REA did not return strict JSON") from exc


def parse_mcp_evidence(reply: Mapping[str, Any], *, max_bytes: int = 10_485_760) -> dict[str, Any]:
    """Validate an evidence-producing MCP reply; retain the full Evidence record.

    Session discovery tools have other schemas and must not use this parser.
    This is structural validation, not authentication of REA evidence signatures.
    A client must additionally validate the selected tool's advertised schema.
    """
    if not isinstance(reply, Mapping):
        raise ReaResponseError("MCP reply must be an object")
    try:
        encoded = json.dumps(dict(reply), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ReaResponseError("MCP reply is not JSON data") from exc
    if len(encoded) > max_bytes:
        raise ReaResponseError("REA reply exceeds the configured response budget")
    if "isError" in reply and not isinstance(reply["isError"], bool):
        raise ReaResponseError("MCP isError must be a boolean")
    blocks = reply.get("content", [])
    if not isinstance(blocks, list):
        raise ReaResponseError("MCP content must be an array")
    text_blocks = [b.get("text") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    if any(not isinstance(t, str) for t in text_blocks):
        raise ReaResponseError("MCP text blocks must contain strings")
    if reply.get("isError") is True:
        diagnostic = None
        if len(text_blocks) == 1:
            diagnostic = _strict_json(text_blocks[0])
        raise ReaResponseError("REA returned an error; no successful finding was recorded", diagnostic)
    record = reply.get("structuredContent")
    if not isinstance(record, dict):
        raise ReaResponseError("Missing structuredContent; do not infer success from text")
    if not isinstance(record.get("evidence_id"), str) or not record["evidence_id"].strip():
        raise ReaResponseError("Missing REA evidence identity")
    if "normalized_result" not in record or "analysis_profile" not in record:
        raise ReaResponseError("Incomplete canonical REA Evidence record")
    if record["analysis_profile"] is not None and not isinstance(record["analysis_profile"], dict):
        raise ReaResponseError("Invalid REA analysis profile")
    if not isinstance(record["normalized_result"], (dict, list)):
        raise ReaResponseError("Invalid normalized REA result")
    if len(text_blocks) != 1 or _strict_json(text_blocks[0]) != record:
        raise ReaResponseError("REA text projection and structured Evidence disagree")
    # Round-trip prevents callers from later changing the source reply in place.
    return _strict_json(json.dumps(record, allow_nan=False))


class ReaAdapter:
    """Report observed local candidates and select only advertised static tools."""

    def __init__(self, advertised_tools: Sequence[str] = ()) -> None:
        self.advertised_tools = frozenset(advertised_tools)

    def capabilities(self) -> dict[str, Any]:
        executable_names = (
            "rea", "analyzeHeadless", "analyzeHeadless.bat", "ghidraRun",
            "rizin", "rz-bin", "radare2", "llvm-readobj", "llvm-objdump",
            "aarch64-linux-gnu-gcc", "qemu-system-aarch64", "dtc",
        )
        paths = {name: shutil.which(name) for name in executable_names}
        packages: dict[str, bool] = {}
        for name in ("lief", "capstone", "frida"):
            try:
                packages[name] = importlib.util.find_spec(name) is not None
            except (ImportError, ValueError, AttributeError):
                packages[name] = False
        mcp = sorted(self.advertised_tools & STATIC_MCP_TOOLS)
        return {
            "rea_cli": paths["rea"],
            "path_candidates": paths,
            "python_packages": packages,
            "advertised_static_mcp_tools": mcp,
            "mcp_connected": bool(self.advertised_tools),
            "native_provider_verified": False,
            "status": "needs_provider_verification" if paths["rea"] or mcp else "unavailable",
            "classification": "VERIFIED",
            "limitations": [
                "PATH/package presence does not establish versions, host support, or successful analysis.",
                "MCP advertisements are supplied by the caller's live session; no registration is assumed.",
                "No provider started and no target or device was executed.",
            ],
            "documentation": REA_DOCS,
        }

    def select_mcp_tool(self, operation: str) -> str:
        """Fail closed for absent tools and all runtime/mutation operations."""
        if operation not in STATIC_MCP_TOOLS:
            raise ReaResponseError("Operation is outside the static REA integration")
        if operation not in self.advertised_tools:
            raise ReaResponseError("REA operation is not advertised by this connection")
        return operation

    async def probe_installed_cli(self, runner: Any) -> dict[str, Any]:
        """Run only documented diagnostics through the caller's bounded runner.

        No npx/package download fallback is allowed. The unmodified JSON reports
        are evidence about this CLI, not an assumed normalized provider catalog.
        """
        executable = shutil.which("rea")
        if not executable:
            return {"status": "blocked", "reason": "REA is absent from PATH", "commands": []}
        help_result = await runner.run([executable, "--help"], timeout=15.0)
        if help_result.returncode != 0 or help_result.timed_out or help_result.cancelled:
            return {"status": "blocked", "reason": "Installed REA help failed", "commands": [list(help_result.argv)]}
        reports: dict[str, Any] = {}
        commands = [list(help_result.argv)]
        for command in ("providers", "capabilities"):
            if command not in help_result.stdout:
                return {"status": "blocked", "reason": f"Installed CLI does not advertise {command}", "commands": commands}
            result = await runner.run([executable, command, "--json"], timeout=15.0)
            commands.append(list(result.argv))
            if result.returncode != 0 or result.timed_out or result.cancelled:
                return {"status": "blocked", "reason": f"REA {command} failed", "commands": commands}
            if len(result.stdout.encode("utf-8")) > 10_485_760:
                raise ReaResponseError("REA CLI diagnostic exceeds response budget")
            report = _strict_json(result.stdout)
            if not isinstance(report, (dict, list)) or isinstance(report, dict) and "error" in report:
                raise ReaResponseError("REA CLI diagnostic did not establish success", report)
            reports[command] = report
        return {"status": "observed", "classification": "VERIFIED", "commands": commands, "reports": reports,
                "limitations": ["Provider reports require interpretation using this installed release's schema.",
                                "No target has been opened or executed."]}

    def native_analysis_plan(self) -> dict[str, Any]:
        """A reviewable route, never an assertion that any step was performed."""
        operations = [
            "binary_session", "open_binary", "binary_overview", "list_procedures",
            "list_strings", "analyze_function", "xrefs", "get_call_graph", "close_binary",
        ]
        return {
            "status": "planned",
            "operations": [{"tool": name, "advertised": name in self.advertised_tools} for name in operations],
            "preconditions": [
                "Operator-supplied local artifact and a specific binary-only research question.",
                "Live MCP tool input/output schemas, or verified installed CLI help.",
                "Explicit provider selected from the session's available provider identities.",
                "Host/format/architecture supported by that provider; no silent provider fallback.",
            ],
            "unresolved": ["Provider selection", "Symbols, references, call relationships and decompilation"],
        }
