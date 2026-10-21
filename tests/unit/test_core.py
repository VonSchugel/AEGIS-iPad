from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import plistlib
import sqlite3

import pytest

from aegis.evidence import EvidenceStore, redact
from aegis.models import Evidence, State, WorkflowError
from aegis.orchestration import StateMachine
from aegis.orchestration.simulation import simulate
from aegis.safety.approval import Approval, plan_digest
from aegis.safety.backup import verify_backup


def make_backup(folder, *, date=None, encrypted=False, missing=False):
    folder.mkdir(exist_ok=True)
    identifier = "a" * 40
    device = {"product_type": "iPad7,11", "product_version": "16.7.10", "device_token": hashlib.sha256(identifier.encode()).hexdigest()}
    info = {"Target Identifier": identifier, "Product Type": device["product_type"], "Product Version": device["product_version"], "Last Backup Date": (date or datetime.now(timezone.utc)).replace(tzinfo=None)}
    for name, value in [("Info.plist", info), ("Status.plist", {"SnapshotState": "finished"}), ("Manifest.plist", {"IsEncrypted": encrypted})]:
        (folder / name).write_bytes(plistlib.dumps(value))
    file_id = "b" * 40
    with sqlite3.connect(folder / "Manifest.db") as conn:
        conn.execute("CREATE TABLE Files(fileID TEXT, flags INTEGER)")
        conn.execute("INSERT INTO Files VALUES(?,1)", (file_id,))
    if not missing:
        (folder / file_id[:2]).mkdir()
        (folder / file_id[:2] / file_id).write_bytes(b"fixture payload")
    return device


def test_backup_metadata_complete_and_readonly(tmp_path):
    device = make_backup(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    result = verify_backup(tmp_path, device)
    assert result["verified"] and result["regular_files_present"] == 1
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}


@pytest.mark.parametrize("change", ["stale", "encrypted", "missing", "wrong_target", "wrong_version"])
def test_backup_rejects_unverified(tmp_path, change):
    device = make_backup(tmp_path, date=datetime.now(timezone.utc) - timedelta(days=8) if change == "stale" else None, encrypted=change == "encrypted", missing=change == "missing")
    if change == "wrong_target":
        device["device_token"] = "c" * 64
    if change == "wrong_version":
        device["product_version"] = "18.4"
    with pytest.raises(WorkflowError, match="Backup verification failed"):
        verify_backup(tmp_path, device)


def test_approval_exact_bound_expiring_and_single_use():
    plan = {"device": "fixture", "argv": ["palera1n", "-l"]}
    with pytest.raises(WorkflowError):
        Approval.from_response(plan, "yes")
    approval = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
    with pytest.raises(WorkflowError):
        approval.check({**plan, "argv": ["palera1n", "-f"]})
    approval.consume(plan)
    with pytest.raises(WorkflowError):
        approval.consume(plan)
    expired = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
    expired.granted_at -= 301
    with pytest.raises(WorkflowError):
        expired.check(plan)


def test_state_machine_requires_current_run_evidence_and_legal_edge():
    store = EvidenceStore()
    machine = StateMachine(store)
    evidence = store.add("observation", {"devices": 1})
    with pytest.raises(WorkflowError):
        machine.advance(State.EXECUTE_SUPPORTED_JAILBREAK, [evidence], satisfied=True)
    with pytest.raises(WorkflowError):
        machine.advance(State.IDENTIFY_DEVICE, [999], satisfied=True)
    with pytest.raises(WorkflowError):
        machine.advance(State.IDENTIFY_DEVICE, [evidence], satisfied=False)
    machine.advance(State.IDENTIFY_DEVICE, [evidence], satisfied=True)
    assert machine.state == State.IDENTIFY_DEVICE
    store.run_id = "another-run"
    with pytest.raises(WorkflowError):
        machine.advance(State.VERIFY_COMPATIBILITY, [evidence], satisfied=True)
    store.close()


def test_evidence_redaction_and_persistence(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    store.add("device", {"UDID": "private", "device_token": "a" * 64, "log": "ECID: 123456789 serial=secret", "source_url": "https://example.com/" + "b" * 40, "sha256": "c" * 64})
    store.export(tmp_path / "evidence.jsonl")
    text = (tmp_path / "evidence.jsonl").read_text()
    assert '"private"' not in text and "secret" not in text and "a" * 64 not in text
    assert "b" * 40 in text and "c" * 64 in text
    store.close()


def test_private_upstream_logs_never_enter_public_export(tmp_path):
    store = EvidenceStore(tmp_path / ".aegis" / "evidence.sqlite")
    assert store.retain_private_log("upstream-stdout", "Serial Number: PRIVATE-DEVICE-ID")
    store.add("upstream_result", {"returncode": 0, "private_logs_retained": True})
    output = tmp_path / "public.jsonl"
    store.export(output)
    assert "PRIVATE-DEVICE-ID" not in output.read_text()
    logs = list((tmp_path / ".aegis" / "private").rglob("*.log"))
    assert len(logs) == 1 and "PRIVATE-DEVICE-ID" in logs[0].read_text()
    with pytest.raises(ValueError):
        store.retain_private_log("../public", "test")
    store.close()


@pytest.mark.parametrize("scenario,state", [("success", State.LINUX_FEASIBILITY_ASSESSMENT), ("timeout", State.RECOVERY_GUIDANCE), ("disconnect", State.RECOVERY_GUIDANCE), ("partial", State.RECOVERY_GUIDANCE), ("unsupported", State.VERIFY_COMPATIBILITY)])
def test_simulation_never_executes_adapter(monkeypatch, scenario, state):
    def forbidden(*args, **kwargs):
        raise AssertionError("No physical adapters allowed in simulation")
    monkeypatch.setattr("aegis.adapters.palera1n.Palera1nAdapter.execute", forbidden)
    monkeypatch.setattr("aegis.agents.discovery.DiscoveryAgent.discover", forbidden)
    store = EvidenceStore()
    result = simulate(store, scenario)
    assert result["state"] == state and result["simulated"] and result["device_modified"] is False
    assert all(t["simulated"] for t in result.get("transitions", []))
    store.close()
