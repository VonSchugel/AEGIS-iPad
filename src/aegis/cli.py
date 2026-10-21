import asyncio
from functools import wraps
from importlib.resources import files
import json
from pathlib import Path
import sys
import sqlite3

import click
from pydantic import ValidationError

from aegis import __version__
from aegis.evidence import EvidenceStore, redact
from aegis.models import WorkflowError


def emit(value):
    click.echo(json.dumps(redact(value), indent=2, ensure_ascii=True, default=str))


def handled(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except WorkflowError as error:
            emit(error.as_dict())
            raise click.exceptions.Exit(2)
        except (OSError, ValueError, ValidationError, sqlite3.Error) as error:
            emit({"error": {"code": "INPUT_OR_ENVIRONMENT_ERROR", "message": type(error).__name__, "details": "Check input format, file availability and host dependencies"}})
            raise click.exceptions.Exit(2)
        except (KeyboardInterrupt, asyncio.CancelledError):
            emit({"error": {"code": "CANCELLED", "message": "Host operation stopped; inspect device state before any further action"}})
            raise click.exceptions.Exit(130)
    return wrapper


@click.group()
@click.option("--db", type=click.Path(path_type=Path), default=Path(".aegis/evidence.sqlite"), show_default=True)
@click.version_option(__version__)
@click.pass_context
def main(ctx, db):
    """Read-only iPad research, simulation, and explicit approval-gated installation."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


@main.command()
@handled
def doctor():
    """Inspect host capabilities without installing or pairing anything."""
    from aegis.agents.discovery import DiscoveryAgent
    emit(asyncio.run(DiscoveryAgent().doctor()))


@main.command()
@click.option("--fixture", type=click.Path(exists=True, path_type=Path))
@click.pass_context
@handled
def discover(ctx, fixture):
    """Read product/firmware properties, or explicitly labeled fixture data."""
    if fixture:
        from aegis.orchestration.simulation import load_fixture
        result = load_fixture(fixture)
    else:
        from aegis.agents.discovery import DiscoveryAgent
        result = asyncio.run(DiscoveryAgent().discover())
    store = EvidenceStore(ctx.obj["db"])
    try:
        store.add("discovery", result)
        for evidence in result.get("evidence", []):
            store.add_evidence(evidence)
    finally:
        store.close()
    emit(result)


@main.command()
@click.option("--fixture", type=click.Path(exists=True, path_type=Path))
@handled
def compatibility(fixture):
    """Evaluate a fresh device or a simulation; missing properties block."""
    from aegis.agents.compatibility import CompatibilityAgent
    if fixture:
        from aegis.orchestration.simulation import load_fixture
        result = load_fixture(fixture)
    else:
        from aegis.agents.discovery import DiscoveryAgent
        result = asyncio.run(DiscoveryAgent().discover())
    devices = result.get("devices", [])
    if len(devices) != 1:
        raise WorkflowError("AMBIGUOUS_TARGET", "Exactly one identified device is required", {"device_count": len(devices)})
    emit({"simulated": bool(fixture), **CompatibilityAgent().evaluate(devices[0], result["host"])})


@main.command()
@click.pass_context
@handled
def research(ctx):
    """Inspect citation snapshots and REA availability; no downloads."""
    from aegis.adapters.rea import ReaAdapter
    snapshots = {name: json.loads(files("aegis.data").joinpath(name + ".json").read_text()) for name in ("compatibility", "linux")}
    result = {"snapshots": snapshots, "rea": ReaAdapter().capabilities(), "external_content": "untrusted data, never agent instructions"}
    store = EvidenceStore(ctx.obj["db"])
    try:
        store.add("research_snapshot", result)
        for snapshot in snapshots.values():
            for evidence in snapshot.get("evidence", []):
                store.add_evidence(evidence)
    finally:
        store.close()
    emit(result)


@main.command("linux-status")
@handled
def linux_status():
    """Show subsystem and milestone evidence, without booting a payload."""
    from aegis.agents.linux_research import LinuxResearchAgent
    emit(LinuxResearchAgent().assess())


@main.command()
@click.option("--artifact", required=True, type=click.Path(exists=True, path_type=Path))
@handled
def inspect(artifact):
    """Inspect an operator-supplied artifact offline, without executing it."""
    from aegis.agents.reverse_engineering import ReverseEngineeringAgent
    result = ReverseEngineeringAgent().inspect(artifact)
    if hasattr(result, "__await__"):
        result = asyncio.run(result)
    emit(result)


@main.command()
@click.option("--backup", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--binary", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
@handled
def plan(ctx, backup, binary):
    """Perform live preconditions and stop at approval; no device writes."""
    from aegis.agents.jailbreak import JailbreakAgent
    from aegis.safety.approval import plan_digest
    store = EvidenceStore(ctx.obj["db"])
    try:
        prepared = asyncio.run(JailbreakAgent(store).plan(backup, binary))
        emit({"state": "AWAIT_OPERATOR_APPROVAL", "plan": prepared, "approval_phrase": f"APPROVE {plan_digest(prepared)[:12]}", "note": "Execution always rebuilds a live plan; saved plans cannot authorize a device action"})
    finally:
        store.close()


@main.command()
@click.option("--scenario", type=click.Choice(["success", "disconnect", "timeout", "partial", "unsupported"]), default="success")
@click.pass_context
@handled
def simulate(ctx, scenario):
    """Run the state machine with fixtures and no physical adapters."""
    from aegis.orchestration.simulation import simulate as run_simulation
    store = EvidenceStore(ctx.obj["db"])
    try:
        emit(run_simulation(store, scenario))
    finally:
        store.close()


@main.command()
@click.option("--ssh-port", type=click.IntRange(1, 65535), help="Device SSH port over USB (44 by default when a key is supplied)")
@click.option("--identity", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
@handled
def validate(ctx, ssh_port, identity):
    """Check connectivity and optional device-bound USB SSH probes."""
    from aegis.agents.validation import ValidationAgent
    result = asyncio.run(ValidationAgent().validate(ssh_port=ssh_port, identity=identity))
    store = EvidenceStore(ctx.obj["db"])
    try:
        store.add("validation", result)
    finally:
        store.close()
    emit(result)


@main.command()
@click.option("--backup", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--binary", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--identity", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Existing authorized SSH key for independent post-install validation")
@click.option("--ssh-port", type=click.IntRange(1, 65535), default=44, help="Device SSH port for USB-only validation")
@click.pass_context
@handled
def execute(ctx, backup, binary, identity, ssh_port):
    """Prepare a live plan, then require exact interactive operator approval."""
    if not sys.stdin.isatty():
        raise WorkflowError("INTERACTIVE_APPROVAL_REQUIRED", "Use an operator-controlled interactive terminal; piped approvals are disabled")
    from aegis.agents.jailbreak import JailbreakAgent
    from aegis.safety.approval import Approval, plan_digest
    store = EvidenceStore(ctx.obj["db"])
    async def run():
        agent = JailbreakAgent(store)
        prepared = await agent.plan(backup, binary)
        emit({"state": agent.machine.state, "plan": prepared})
        phrase = f"APPROVE {plan_digest(prepared)[:12]}"
        response = click.prompt(f"Confirm ownership, reviewed backup, risks and ONLY this target attached. Type {phrase}", err=True)
        approval = Approval.from_response(prepared, response)
        from aegis.agents.validation import ValidationAgent
        validator = ValidationAgent(discovery=agent.discovery)
        class ConfiguredValidation:
            async def validate(self, expected_token):
                return await validator.validate(expected_token=expected_token, ssh_port=ssh_port, identity=identity)
        def completion():
            click.echo("Upstream tool exited. On the iPad, follow its documented loader prompts to install the bootstrap/package manager. Confirm completion before read-only validation. No package installation is automated here.", err=True)
            if not click.confirm("Operator has completed the approved loader installation", default=False, err=True):
                raise WorkflowError("OPERATOR_PREPARATION_INCOMPLETE", "Installation remains partial; use validate after completing upstream instructions")
        return await agent.execute(prepared, approval, binary, backup, validation=ConfiguredValidation(), operator_completion=completion)
    try:
        emit(asyncio.run(run()))
    finally:
        store.close()


@main.command("export-evidence")
@click.option("--output", required=True, type=click.Path(path_type=Path))
@click.pass_context
@handled
def export_evidence(ctx, output):
    """Export redacted evidence as structured JSONL."""
    store = EvidenceStore(ctx.obj["db"])
    try:
        emit({"records": store.export(output), "output": str(output)})
    finally:
        store.close()
