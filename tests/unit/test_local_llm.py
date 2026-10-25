import asyncio
import json
import random
import string

from click.testing import CliRunner
import pytest

from aegis.adapters.local_llm import LocalLLMError, LocalLLMProvider
from aegis.cli import main
from aegis.evidence import EvidenceStore


def response(ids=None, **kwargs):
    return {"done": True, "message": {"content": json.dumps({"summary": "This is a simulated observation; hardware remains unverified.", "source_ids": [1] if ids is None else ids})}, **kwargs}


def async_response(value):
    async def respond(*args, **kwargs):
        return value
    return respond


def test_sources_are_bounded_redacted_and_exclude_generated_outputs(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    first = store.add("discovery", {"udid": "private-value", "description": "x" * 6000})
    store.add("generated_advisory", {"summary": "Never re-ingest model output"})
    store.add("generated_advisory_fallback", {"reason": "unavailable"})
    sources = store.advisory_sources()
    assert len(sources) == 1 and sources[0]["id"] == first
    assert len(sources[0]["payload_text"]) <= 1600
    assert sources[0]["truncated"] is True
    assert "private-value" not in sources[0]["payload_text"]
    assert store.advisory_sources(1) == sources
    with pytest.raises(ValueError):
        store.advisory_sources(7)
    store.close()


@pytest.mark.parametrize("host", ["http://example.org", "https://127.0.0.1:11434", "http://localhost/path", "http://user:password@localhost", "http://localhost:bad"])
def test_transport_rejects_nonlocal_or_ambiguous_endpoints(host):
    with pytest.raises(LocalLLMError, match="invalid_local_endpoint"):
        LocalLLMProvider(host=host)._endpoint("/api/chat")


@pytest.mark.asyncio
async def test_summary_is_source_linked_and_has_no_authority(monkeypatch):
    provider = LocalLLMProvider()
    async def serve(path, body=None):
        assert path == "/api/chat"
        assert body["think"] is False and body["stream"] is False
        assert body["options"] == {"num_thread": 4, "num_ctx": 4096, "num_predict": 768, "temperature": 0}
        return response()

    monkeypatch.setattr(provider, "_request_http_json", serve)
    result = await provider.summarize([{"id": 1, "payload_text": "simulated: true"}])
    assert result["classification"] == "GENERATED_ADVISORY_UNVERIFIED"
    assert result["source_ids"] == [1]
    assert result["authority"].startswith("none;")


@pytest.mark.parametrize("reply", [response(ids=[999]), response(ids=[True]), response(ids=[]), response(ids=[1, 1]), response(done_reason="length"), {"done": False}, {"done": True, "message": {"content": "not json"}}])
def test_rejects_unknown_citations_and_incomplete_output(monkeypatch, reply):
    provider = LocalLLMProvider()
    monkeypatch.setattr(provider, "_request_http_json", async_response(reply))
    with pytest.raises(LocalLLMError):
        asyncio.run(provider.summarize([{"id": 1, "payload_text": "known record"}]))


def test_cli_summary_persists_advice_separately_without_touching_source(tmp_path, monkeypatch):
    database = tmp_path / "evidence.sqlite"
    store = EvidenceStore(database)
    store.add("discovery", {"simulated": True, "devices": []})
    before = store.conn.execute("SELECT payload FROM records WHERE id=1").fetchone()[0]
    store.close()
    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", async_response(response()))
    result = CliRunner().invoke(main, ["--db", str(database), "summarize-evidence"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["source_ids"] == [1] and output["record_id"] == 2
    store = EvidenceStore(database)
    rows = store.conn.execute("SELECT kind,payload FROM records ORDER BY id").fetchall()
    assert rows[0] == ("discovery", before)
    assert rows[1][0] == "generated_advisory"
    assert len(store.advisory_sources()) == 1
    store.close()


def test_unavailable_provider_records_explicit_fallback(tmp_path, monkeypatch):
    database = tmp_path / "evidence.sqlite"
    store = EvidenceStore(database)
    store.add("validation", {"status": "unknown"})
    store.close()

    async def unavailable(*args, **kwargs):
        raise LocalLLMError("service_unavailable")

    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", unavailable)
    result = CliRunner().invoke(main, ["--db", str(database), "summarize-evidence"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"]["details"]["reason"] == "service_unavailable"
    store = EvidenceStore(database)
    rows = store.conn.execute("SELECT kind,payload FROM records ORDER BY id").fetchall()
    assert rows[1][0] == "generated_advisory_fallback"
    assert json.loads(rows[1][1])["status"] == "fallback"
    assert len(store.advisory_sources()) == 1
    store.close()


def test_empty_database_never_calls_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", lambda *args: pytest.fail("No data must not trigger inference"))
    result = CliRunner().invoke(main, ["--db", str(tmp_path / "empty.sqlite"), "summarize-evidence"])
    assert result.exit_code == 2
    assert "no_source_records" in result.output


def test_status_distinguishes_missing_model_without_device_access(monkeypatch):
    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", async_response({"models": []}))
    result = CliRunner().invoke(main, ["llm-status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["reachable"] is True and data["model_installed"] is False


@pytest.mark.parametrize("text", ["界" * 1200, "".join(random.Random(7).choices(string.ascii_letters + string.digits, k=3000))])
def test_long_or_high_entropy_sources_rejected_before_http(monkeypatch, text):
    from aegis.adapters import local_llm
    monkeypatch.setattr(local_llm.asyncio, "create_subprocess_exec", lambda *args, **kwargs: pytest.fail("Over-budget content must not start a worker"))
    with pytest.raises(LocalLLMError, match="input_too_large"):
        asyncio.run(LocalLLMProvider().summarize([{"id": 1, "payload_text": text}]))


@pytest.mark.parametrize("location", ["http_envelope", "model_content"])
@pytest.mark.parametrize("malformed", ["deep_json", "oversized_integer"])
def test_malformed_json_cli_records_failure_and_preserves_canonical_source(tmp_path, monkeypatch, location, malformed):
    from aegis.adapters import local_llm
    nested = "[" * 10000 + "0" + "]" * 10000 if malformed == "deep_json" else "1" * 5000
    raw = nested.encode() if location == "http_envelope" else json.dumps({"done": True, "message": {"content": nested}}).encode()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return raw[:size]

    class Opener:
        def open(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(local_llm, "build_opener", lambda *args: Opener())
    async def parser_only(self, path, body=None):
        # Worker transport has separate integration tests; exercise its actual
        # JSON parser with a mocked HTTP response and no network or child.
        return self._http_json(path, body)
    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", parser_only)
    database = tmp_path / "evidence.sqlite"
    store = EvidenceStore(database)
    store.add("discovery", {"simulated": True, "hardware_result": "NOT TESTED"})
    before = store.conn.execute("SELECT payload FROM records WHERE id=1").fetchone()[0]
    store.close()
    result = CliRunner().invoke(main, ["--db", str(database), "summarize-evidence"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"]["details"]["reason"] == "invalid_response"
    assert nested not in result.output
    store = EvidenceStore(database)
    rows = store.conn.execute("SELECT kind,payload FROM records ORDER BY id").fetchall()
    assert rows[0] == ("discovery", before)
    assert rows[1][0] == "generated_advisory_fallback"
    fallback = json.loads(rows[1][1])
    assert fallback["reason"] == "invalid_response" and "summary" not in fallback
    store.close()


@pytest.mark.parametrize("timeout", ["nan", "inf", "not-a-number", "0", "-1"])
def test_invalid_configuration_has_structured_status_and_fallback(tmp_path, monkeypatch, timeout):
    monkeypatch.setenv("LOCAL_LLM_TIMEOUT_S", timeout)
    monkeypatch.setattr(LocalLLMProvider, "_request_http_json", lambda *args, **kwargs: pytest.fail("Invalid configuration must not contact a service"))
    runner = CliRunner()
    status = runner.invoke(main, ["llm-status"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["status"] == "invalid_configuration"
    database = tmp_path / "evidence.sqlite"
    store = EvidenceStore(database)
    store.add("validation", {"status": "UNKNOWN", "simulated": True})
    store.close()
    result = runner.invoke(main, ["--db", str(database), "summarize-evidence"])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"]["details"]["reason"] == "invalid_configuration"
    store = EvidenceStore(database)
    try:
        rows = store.conn.execute("SELECT kind,payload FROM records ORDER BY id").fetchall()
        assert rows[0][0] == "validation"
        assert rows[1][0] == "generated_advisory_fallback"
        assert json.loads(rows[1][1])["reason"] == "invalid_configuration"
    finally:
        store.close()
