import json
import struct
from pathlib import Path

import pytest

from aegis.adapters.process import CommandResult
from aegis.adapters.rea import ReaAdapter, ReaResponseError, parse_mcp_evidence
from aegis.agents.linux_research import LinuxResearchAgent
from aegis.agents.reverse_engineering import ReverseEngineeringAgent, identify_header


def evidence_reply(record=None):
    record = record if record is not None else {
        "evidence_id": "ev_synthetic_only", "analysis_profile": None,
        "normalized_result": {"functions": [], "coverage": "unknown"},
        "raw_result": None, "limitations": ["Synthetic unit-test observation"],
    }
    return {"content": [{"type": "text", "text": json.dumps(record)}], "structuredContent": record}


def test_mcp_preserves_unknowns_and_is_independent_copy():
    reply = evidence_reply()
    observed = parse_mcp_evidence(reply)
    reply["structuredContent"]["limitations"].append("later mutation")
    assert observed["normalized_result"]["coverage"] == "unknown"
    assert observed["limitations"] == ["Synthetic unit-test observation"]


@pytest.mark.parametrize("missing", ["evidence_id", "analysis_profile", "normalized_result"])
def test_mcp_incomplete_evidence_rejected(missing):
    record = evidence_reply()["structuredContent"]
    record.pop(missing)
    with pytest.raises(ReaResponseError):
        parse_mcp_evidence(evidence_reply(record))


def test_mcp_tool_error_cannot_become_success():
    with pytest.raises(ReaResponseError) as error:
        parse_mcp_evidence({"isError": True, "content": [{"type": "text", "text": '{"error":{"code":"provider_unavailable"}}'}]})
    assert error.value.diagnostic["error"]["code"] == "provider_unavailable"


def test_mcp_text_mismatch_and_duplicate_members_rejected():
    reply = evidence_reply()
    reply["content"][0]["text"] = '{"evidence_id":"ev_other"}'
    with pytest.raises(ReaResponseError, match="disagree"):
        parse_mcp_evidence(reply)
    reply["content"][0]["text"] = '{"a":1,"a":2}'
    with pytest.raises(ReaResponseError, match="Duplicate"):
        parse_mcp_evidence(reply)


@pytest.mark.parametrize("reply", [
    {"content": [{"type": "text", "text": "success"}]},
    {"isError": "false", "content": []},
    {"content": "success", "structuredContent": {}},
])
def test_mcp_invalid_envelopes_rejected(reply):
    with pytest.raises(ReaResponseError):
        parse_mcp_evidence(reply)


def test_mcp_budget_and_nonfinite_values_rejected():
    with pytest.raises(ReaResponseError, match="budget"):
        parse_mcp_evidence(evidence_reply(), max_bytes=10)
    reply = evidence_reply()
    reply["structuredContent"]["normalized_result"]["bad"] = float("nan")
    with pytest.raises(ReaResponseError, match="JSON"):
        parse_mcp_evidence(reply)


def test_only_advertised_static_operations_selected():
    adapter = ReaAdapter(["open_binary", "capture_process"])
    assert adapter.select_mcp_tool("open_binary") == "open_binary"
    with pytest.raises(ReaResponseError, match="not advertised"):
        adapter.select_mcp_tool("analyze_function")
    with pytest.raises(ReaResponseError, match="outside"):
        adapter.select_mcp_tool("capture_process")


def test_capabilities_never_claim_a_provider_works(monkeypatch):
    monkeypatch.setattr("aegis.adapters.rea.shutil.which", lambda name: "/candidate/" + name)
    result = ReaAdapter().capabilities()
    assert result["rea_cli"] == "/candidate/rea"
    assert result["native_provider_verified"] is False
    assert result["mcp_connected"] is False


class FakeRunner:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    async def run(self, argv, timeout):
        self.calls.append((argv, timeout))
        response = next(self.results)
        return CommandResult(tuple(argv), **response)


@pytest.mark.asyncio
async def test_cli_probe_never_downloads_when_absent(monkeypatch):
    monkeypatch.setattr("aegis.adapters.rea.shutil.which", lambda name: None)
    runner = FakeRunner([])
    result = await ReaAdapter().probe_installed_cli(runner)
    assert result["status"] == "blocked"
    assert not runner.calls


@pytest.mark.asyncio
async def test_cli_probe_preserves_actual_reports(monkeypatch):
    monkeypatch.setattr("aegis.adapters.rea.shutil.which", lambda name: "/installed/rea")
    runner = FakeRunner([
        {"returncode": 0, "stdout": "commands: providers capabilities"},
        {"returncode": 0, "stdout": '{"providers":[]}'},
        {"returncode": 0, "stdout": '{"capabilities":[]}'},
    ])
    result = await ReaAdapter().probe_installed_cli(runner)
    assert result["status"] == "observed"
    assert result["reports"]["providers"] == {"providers": []}
    assert [call[0][1:] for call in runner.calls] == [["--help"], ["providers", "--json"], ["capabilities", "--json"]]


@pytest.mark.asyncio
async def test_cli_probe_stops_on_timeout(monkeypatch):
    monkeypatch.setattr("aegis.adapters.rea.shutil.which", lambda name: "/installed/rea")
    runner = FakeRunner([{"returncode": -1, "timed_out": True}])
    result = await ReaAdapter().probe_installed_cli(runner)
    assert result["status"] == "blocked"
    assert len(runner.calls) == 1


def test_arm64_elf_inspection_is_metadata_only(tmp_path):
    header = bytearray(64)
    header[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<H", header, 18, 183)
    artifact = tmp_path / "synthetic.elf"
    artifact.write_bytes(header)
    result = ReverseEngineeringAgent().inspect(artifact)
    assert result["artifact"]["format"] == "ELF"
    assert result["artifact"]["architecture"] == "arm64"
    assert len(result["artifact"]["sha256"]) == 64
    assert result["deep_analysis"]["status"] == "blocked"
    assert result["symbols"] is None and result["call_graph"] is None
    assert artifact.read_bytes() == header


def test_inspection_budget_and_nonregular_target(tmp_path):
    artifact = tmp_path / "large.bin"
    artifact.write_bytes(b"abc")
    with pytest.raises(ValueError, match="budget"):
        ReverseEngineeringAgent(max_bytes=2).inspect(artifact)
    with pytest.raises(ValueError, match="regular"):
        ReverseEngineeringAgent().inspect(tmp_path)


def test_macho_arm64_header_and_pe_header():
    macho = bytearray(32)
    macho[:4] = b"\xcf\xfa\xed\xfe"
    struct.pack_into("<I", macho, 4, 0x100000C)
    assert identify_header(macho, len(macho))["architecture"] == "arm64"
    pe = bytearray(128)
    pe[:2] = b"MZ"
    struct.pack_into("<I", pe, 0x3C, 64)
    pe[64:68] = b"PE\0\0"
    struct.pack_into("<H", pe, 68, 0xAA64)
    assert identify_header(pe, len(pe))["format"] == "PE"
    assert identify_header(pe, len(pe))["architecture"] == "arm64"


@pytest.mark.parametrize("header", [b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe\x00\x00\x00\x3d", b"MZ" + bytes(62)])
def test_malformed_or_ambiguous_headers_remain_unknown(header):
    assert identify_header(header, len(header))["architecture"] is None
    assert identify_header(header, len(header))["format"] == "unknown"


def test_linux_evidence_scope_and_references():
    report = LinuxResearchAgent().assess()
    assert report["local_linux_boot_verified"] is False
    assert [m["id"] for m in report["milestones"]] == list("ABCDE")
    assert all(m["local_status"] == "NOT_TESTED" for m in report["milestones"])
    ids = {e["id"] for e in report["evidence"]}
    for subsystem in report["subsystems"]:
        assert subsystem["status"] in {"Supported", "Partially implemented", "Experimental", "Unsupported", "Unknown"}
        assert set(subsystem["evidence_ids"]) <= ids
    required = {"question", "source_url", "revision", "observed", "classification", "confidence", "limitations", "reproduction", "next_step", "retrieved_at"}
    assert all(required <= e.keys() for e in report["evidence"])
    report["milestones"].clear()
    assert len(LinuxResearchAgent().assess()["milestones"]) == 5
