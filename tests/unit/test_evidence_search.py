import sqlite3

import pytest

from aegis.evidence import EvidenceStore
from aegis.evidence.search import search_evidence
from aegis.models import WorkflowError


def evidence(observed="A10 timer support remains unknown", **updates):
    return {
        "id": "source-one", "question": "Does this target support the timer?",
        "source_url": "https://example.org/original", "revision": "a" * 40,
        "observed": observed, "classification": "UNKNOWN", "confidence": "low",
        "limitations": ["No physical experiment"], "reproduction": "Read pinned source",
        "next_step": "Inspect exact device tree", "retrieved_at": "2026-11-04T00:00:00+00:00",
        **updates,
    }


def test_migrates_preexisting_database_and_preserves_provenance(tmp_path):
    path = tmp_path / "research.sqlite"
    store = EvidenceStore(path)
    first_run = store.run_id
    row = store.add_evidence(evidence())
    store.close()
    store = EvidenceStore(path)
    try:
        result = search_evidence(store, "A10 timer")
        assert result["method"] == "sqlite_fts5_literal_and"
        assert result["execution_authority"].startswith("NONE")
        match = result["results"][0]
        assert match["id"] == row and match["run_id"] == first_run
        assert match["source_url"] == "https://example.org/original"
        assert match["revision"] == "a" * 40 and match["classification"] == "UNKNOWN"
        assert match["retrieved_at"] == "2026-11-04T00:00:00+00:00"
        assert match["limitations"] == "No physical experiment"
        assert not match["truncated"] and match["metadata_truncated"] == []
        # A second lookup must neither duplicate rows nor rebuild source data.
        assert search_evidence(store, "A10 timer")["results"] == result["results"]
    finally:
        store.close()


def test_incremental_inserts_and_generated_sources_never_promote():
    store = EvidenceStore()
    try:
        assert not search_evidence(store, "new peripheral")["results"]
        store.add("generated_advisory", evidence("new peripheral invented success"))
        store.add("research_snapshot", evidence("new peripheral loose schema"))
        assert not search_evidence(store, "new peripheral")["results"]
        row = store.add_evidence(evidence("new peripheral documented only", classification="SUPPORTED BY DOCUMENTATION"))
        result = search_evidence(store, "new peripheral")
        assert [item["id"] for item in result["results"]] == [row]
        assert result["results"][0]["classification"] == "DOCUMENTED"
    finally:
        store.close()


def test_fts_syntax_is_literal_and_cannot_expand_query():
    store = EvidenceStore()
    try:
        store.add_evidence(evidence("display only"))
        row = store.add_evidence(evidence("display OR storage"))
        result = search_evidence(store, 'display OR "storage"*')
        assert result["terms"] == ["display", "OR", "storage"]
        assert [item["id"] for item in result["results"]] == [row]
        assert not search_evidence(store, "term_not_present")["results"]
    finally:
        store.close()


@pytest.mark.parametrize("query", ["", " ", "***", "x" * 257, "one two three four five six seven eight nine", "nul\0term", None])
def test_invalid_queries_fail_before_index_creation(query):
    store = EvidenceStore()
    try:
        with pytest.raises(WorkflowError) as raised:
            search_evidence(store, query)
        assert raised.value.code == "INVALID_EVIDENCE_QUERY"
        assert store.conn.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'aegis_evidence_fts%'").fetchone()[0] == 0
    finally:
        store.close()


@pytest.mark.parametrize("limit", [0, 21, True, 1.2, "5"])
def test_invalid_result_limits(limit):
    store = EvidenceStore()
    try:
        with pytest.raises(WorkflowError) as raised:
            search_evidence(store, "timer", limit)
        assert raised.value.code == "INVALID_EVIDENCE_LIMIT"
    finally:
        store.close()


def test_bounds_excerpts_candidates_and_metadata_and_skips_invalid():
    store = EvidenceStore()
    try:
        store.add("evidence", {"observed": "bounded match malformed"})
        store.add_evidence(evidence("bounded match " + "x" * 70_000))
        for _ in range(25):
            store.add_evidence(evidence("bounded match " + "x" * 900, question="q" * 600, revision="r" * 600))
        result = search_evidence(store, "bounded match", 20)
        assert len(result["results"]) == 20 and result["candidate_limit"] <= 100
        assert result["skipped_invalid_records"] == 1
        assert all(len(item["observed"]) == 800 and item["truncated"] for item in result["results"])
        assert all(item["metadata_truncated"] == ["revision", "question"] for item in result["results"])
    finally:
        store.close()


def test_fts_unavailable_is_structured_and_does_not_install_anything():
    store = EvidenceStore()
    real_connection = store.conn

    class NoFtsConnection:
        def execute(self, sql, parameters=()):
            if "CREATE VIRTUAL TABLE" in sql:
                raise sqlite3.OperationalError("no such module: fts5")
            return real_connection.execute(sql, parameters)

    store.conn = NoFtsConnection()
    try:
        with pytest.raises(WorkflowError) as raised:
            search_evidence(store, "timer")
        assert raised.value.code == "EVIDENCE_SEARCH_UNAVAILABLE"
        assert raised.value.details == {"reason": "fts5_unavailable", "automatic_dependency_changes": False}
        assert not real_connection.in_transaction
    finally:
        real_connection.close()


def test_interrupted_first_index_migration_releases_transaction():
    store = EvidenceStore()
    real_connection = store.conn

    class InterruptedConnection:
        def execute(self, sql, parameters=()):
            if "CREATE TRIGGER" in sql:
                raise KeyboardInterrupt()
            return real_connection.execute(sql, parameters)

    store.conn = InterruptedConnection()
    try:
        with pytest.raises(KeyboardInterrupt):
            search_evidence(store, "timer")
        assert not real_connection.in_transaction
        assert real_connection.execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'aegis_evidence_fts%'").fetchone()[0] == 0
        store.conn = real_connection
        store.add_evidence(evidence())
        assert len(search_evidence(store, "timer")["results"]) == 1
    finally:
        real_connection.close()
