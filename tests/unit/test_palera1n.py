from pathlib import Path

import pytest

from aegis.adapters.palera1n import Palera1nAdapter
from aegis.adapters.process import CommandResult
from aegis.models import WorkflowError
from aegis.safety.approval import Approval, plan_digest


class FakeRunner:
    def __init__(self, version="palera1n v2.4"):
        self.calls = []
        self.version = version

    async def run(self, argv, timeout=15, **kwargs):
        self.calls.append((argv, timeout, kwargs))
        return CommandResult(tuple(argv), 0, self.version if "--version" in argv else "upstream fixture")


def test_artifact_hash_and_host_fail_closed(tmp_path):
    binary = tmp_path / "palera1n"
    binary.write_bytes(b"untrusted fake")
    adapter = Palera1nAdapter()
    with pytest.raises(WorkflowError) as error:
        adapter.verify_artifact(binary, {"system": "Windows", "machine": "AMD64"})
    assert error.value.code == "UNSUPPORTED_HOST"
    with pytest.raises(WorkflowError) as error:
        adapter.verify_artifact(binary, {"system": "Linux", "machine": "x86_64"})
    assert error.value.code == "ARTIFACT_HASH_MISMATCH"


async def test_only_verified_version_and_rootless_invocation(monkeypatch, tmp_path):
    runner = FakeRunner()
    adapter = Palera1nAdapter(runner)
    artifact = {"sha256": "fixture-digest", "verified": True}
    monkeypatch.setattr(adapter, "verify_artifact", lambda *a: artifact)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    binary = tmp_path / "palera1n"
    plan = {"simulated": False, "artifact": artifact, "argv": [str(binary.resolve()), "-l"]}
    await adapter.prepare(binary, {})
    approval = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
    await adapter.execute(binary, {}, plan, approval)
    assert runner.calls[-1][0] == [str(binary.resolve()), "-l"]
    assert runner.calls[-1][2]["interactive"] is True
    assert runner.calls[-1][2]["env"] == adapter.clean_environment()
    assert "PALERA1N_BYPASS_PASSCODE_CHECK" not in runner.calls[-1][2]["env"]
    with pytest.raises(WorkflowError):
        await adapter.execute(binary, {}, plan, approval)
    assert len(runner.calls) == 2


@pytest.mark.parametrize("version", ["palera1n v2.4.1", "v3.0.0-beta.3", "unknown"])
async def test_other_versions_never_prepare(monkeypatch, version, tmp_path):
    adapter = Palera1nAdapter(FakeRunner(version))
    monkeypatch.setattr(adapter, "verify_artifact", lambda *a: {"verified": True})
    with pytest.raises(WorkflowError) as error:
        await adapter.prepare(tmp_path / "binary", {})
    assert error.value.code == "TOOL_VERSION_MISMATCH"


async def test_fixture_plan_and_no_tty_never_invoke(monkeypatch, tmp_path):
    runner = FakeRunner()
    adapter = Palera1nAdapter(runner)
    monkeypatch.setattr(adapter, "verify_artifact", lambda *a: {"sha256": "fixture"})
    binary = tmp_path / "binary"
    plan = {"simulated": True, "argv": [str(binary.resolve()), "-l"], "artifact": {"sha256": "fixture"}}
    approval = Approval.from_response(plan, f"APPROVE {plan_digest(plan)[:12]}")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    with pytest.raises(WorkflowError) as error:
        await adapter.execute(binary, {}, plan, approval)
    assert error.value.code == "SIMULATION_NOT_EXECUTABLE"
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(WorkflowError):
        await adapter.execute(binary, {}, plan, approval)
    assert not runner.calls
