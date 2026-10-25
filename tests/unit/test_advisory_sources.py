"""Advisory context preserves provenance without treating generated text as evidence."""
import json

import pytest

from aegis.evidence import EvidenceStore
from aegis.evidence.store import ADVISORY_CONTEXT_PAYLOAD_CHARS, ADVISORY_METADATA_CHARS


def test_metadata_after_long_description_survives_snippet_truncation():
    store = EvidenceStore()
    try:
        record = store.add("discovery", {
            "a_description": "x" * 2000, "classification": "HYPOTHESIS", "simulated": True,
            "status": "NOT_TESTED", "limitations": ["No physical experiment performed"],
            "source_url": "https://example.org/research", "revision": "reviewed-revision",
            "known_limits": {"hardware_validation": "UNKNOWN"},
        })
        source = store.advisory_sources()[0]
        assert source["id"] == record and source["truncated"] is True
        assert "HYPOTHESIS" not in source["payload_text"]
        assert len(source["payload_text"]) <= 1600
        assert source["context"] == {
            "state": "available", "classification": "HYPOTHESIS", "simulated": True, "status": "NOT_TESTED",
            "limitations": ["No physical experiment performed"], "source_url": "https://example.org/research",
            "revision": "reviewed-revision", "known_limits": {"hardware_validation": "UNKNOWN"},
            "truncated": False, "truncated_fields": [], "unknown_fields": [],
        }
    finally:
        store.close()


def test_metadata_redaction_and_explicit_truncation():
    store = EvidenceStore()
    try:
        store.add("validation", {"classification": "UNKNOWN", "simulated": False,
                  "known_limits": {"password": "private-value", "device_token": "a" * 64},
                  "limitations": ["x" * 1000], "revision": "b" * 40})
        source = store.advisory_sources()[0]
        context = source["context"]
        assert context["simulated"] is False
        assert "private-value" not in json.dumps(source) and "a" * 64 not in json.dumps(source)
        assert context["known_limits"]["password"] == "[REDACTED]"
        assert context["revision"] == "b" * 40
        assert context["truncated"] is True and context["truncated_fields"] == ["limitations"]
        assert context["limitations"]["state"] == "truncated"
        assert len(context["limitations"]["json_prefix"]) == ADVISORY_METADATA_CHARS
        assert "status" in context["unknown_fields"] and context["status"] == "UNKNOWN"
    finally:
        store.close()


@pytest.mark.parametrize("payload,reason", [
    ("{invalid", "invalid_payload_json"),
    ("[]", "payload_is_not_an_object"),
    ('{"a":"' + "x" * ADVISORY_CONTEXT_PAYLOAD_CHARS + '","simulated":true}', "payload_exceeds_context_budget"),
    ('{"counter":' + "9" * 5000 + '}', "invalid_payload_json"),
], ids=["malformed-json", "non-object", "oversized-payload", "overlong-integer"])
def test_unparseable_or_oversized_context_remains_explicitly_unknown(payload, reason):
    store = EvidenceStore()
    try:
        with store.conn:
            store.conn.execute("INSERT INTO records(run_id,kind,created_at,payload) VALUES(?,?,?,?)", (store.run_id, "discovery", "fixture-time", payload))
        source = store.advisory_sources()[0]
        assert source["context"]["state"] == "unknown" and source["context"]["reason"] == reason
        assert source["context"]["simulated"] == "UNKNOWN"
        assert source["context"]["classification"] == "UNKNOWN"
        assert len(source["payload_text"]) <= 1600
    finally:
        store.close()


def test_only_canonical_kinds_selected_with_stable_ids_and_order():
    store = EvidenceStore()
    try:
        first = store.add("evidence", {"classification": "VERIFIED", "simulated": False})
        store.add("generated_advisory", {"summary": "Never re-ingest model output"})
        second = store.add("research_snapshot", {"classification": "SUPPORTED BY DOCUMENTATION"})
        store.add("generated_advisory_fallback", {"reason": "unavailable"})
        sources = store.advisory_sources(6)
        assert [source["id"] for source in sources] == [first, second]
        assert all(source["run_id"] == store.run_id for source in sources)
        assert [source["id"] for source in store.advisory_sources(1)] == [second]
        assert "Never re-ingest" not in json.dumps(sources)
    finally:
        store.close()


@pytest.mark.parametrize("limit", [0, 7, True, "1"])
def test_source_limit_remains_bounded(limit):
    store = EvidenceStore()
    try:
        with pytest.raises(ValueError, match="between one and six"):
            store.advisory_sources(limit)
    finally:
        store.close()
