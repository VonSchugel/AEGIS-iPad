"""Protect target-scoped Linux research from accidental success promotion."""

from urllib.parse import urlsplit

from aegis.agents.linux_research import LinuxResearchAgent
from aegis.models import Evidence


def test_linux_l0_through_l5_require_separate_documented_simulated_and_physical_results():
    report = LinuxResearchAgent().assess()
    milestones = report["research_milestones"]
    assert [item["id"] for item in milestones] == [f"L{i}" for i in range(6)]
    assert report["local_linux_boot_verified"] is False
    assert report["target"]["attached_device_identity"] == "UNKNOWN"
    assert report["target"]["firmware"] == "UNKNOWN"
    assert set(report["target"]["requested_models"]) == {"iPad7,11", "iPad7,12"}
    for item in milestones:
        assert item["acceptance_criteria"].strip()
        assert item["simulation_scope"].strip()
        assert item["documented_status"] in {"SOURCE_OR_DOCUMENTATION_AVAILABLE", "PARTIAL_EXPERIMENTAL_REPORTS"}
        assert item["simulated_status"] == item["physical_status"] == item["local_status"] == "NOT_TESTED"
    assert all(item["local_status"] == "NOT_TESTED" for item in report["milestones"])


def test_linux_research_references_resolve_to_typed_provenance_and_keep_source_limits():
    report = LinuxResearchAgent().assess()
    records = [Evidence.model_validate(item) for item in report["evidence"]]
    evidence_by_id = {item.id: item for item in records}
    assert None not in evidence_by_id and len(evidence_by_id) == len(records)
    for item in report["research_milestones"] + report["milestones"] + report["subsystems"]:
        assert item["evidence_ids"]
        for reference in item["evidence_ids"]:
            assert reference in evidence_by_id, f"Unresolved evidence reference: {reference}"
            evidence = evidence_by_id[reference]
            parsed = urlsplit(evidence.source_url)
            assert parsed.scheme in {"http", "https"} and parsed.netloc
            assert evidence.revision.strip() and evidence.retrieved_at.strip()
            assert evidence.limitations and evidence.confidence.strip()
