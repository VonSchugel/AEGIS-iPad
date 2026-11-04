"""Hardware-free baseline and repeatable component/retrieval measurements.

Run using the project's Python. Synthetic retrieval relevance is deliberately
simple; this harness does not measure model accuracy or hardware performance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import platform
import re
import statistics
import sys
import time
import tracemalloc


def measured(call, repetitions):
    call()  # Warm-up, reported separately from cold process startup.
    gc.collect()
    wall, cpu = [], []
    tracemalloc.start()
    for _ in range(repetitions):
        start_cpu, start_wall = time.process_time_ns(), time.perf_counter_ns()
        call()
        wall.append((time.perf_counter_ns() - start_wall) / 1e6)
        cpu.append((time.process_time_ns() - start_cpu) / 1e6)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ordered = sorted(wall)
    return {"repetitions": repetitions, "median_ms": statistics.median(wall),
            "p95_ms": ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)],
            "median_process_cpu_ms": statistics.median(cpu), "python_peak_allocated_bytes": peak}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "src")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    options = parser.parse_args()
    source = options.source.resolve()
    sys.path.insert(0, str(source))
    from aegis.agents.compatibility import CompatibilityAgent
    from aegis.evidence import EvidenceStore
    from aegis.orchestration.simulation import load_fixture, simulate
    from aegis.models import Evidence, WorkflowError

    digest = hashlib.sha256()
    for path in sorted(source.rglob("*")):
        if path.suffix in {".py", ".json"} and path.is_file():
            digest.update(path.relative_to(source).as_posix().encode())
            digest.update(b"\0" + path.read_bytes() + b"\0")
    report = {"schema_version": 1, "checked_date": "2026-11-04", "label": options.label,
              "classification": "VERIFIED", "scope": "local hardware-free software measurements",
              "source_tree_sha256": digest.hexdigest(), "host": {"system": platform.system(),
              "machine": platform.machine(), "python": platform.python_version()},
              "method": "perf_counter_ns/process_time_ns; warmed serial repetitions; tracemalloc enabled; in-memory SQLite",
              "measurements": {}, "limitations": ["No USB/jailbreak/kernel benchmark.",
                  "Python allocation peak is not RSS or whole-machine CPU utilization.",
                  "Synthetic retrieval is a lexical plumbing check, not real research precision.",
                  "LLM tokens, research tool cost and model completion accuracy are NOT_MEASURED.",
                  "Do not compare wall time across hosts or tracing configurations as a tool speed claim."]}
    fixture = load_fixture()
    agent = CompatibilityAgent()
    report["measurements"]["compatibility"] = measured(lambda: agent.evaluate(fixture["devices"][0], fixture["host"]), 100)

    def simulation():
        store = EvidenceStore()
        try:
            result = simulate(store)
            assert result["simulated"] and result["device_modified"] is False
        finally:
            store.close()
    report["measurements"]["fixture_workflow"] = measured(simulation, 20)
    stable = Counter()
    for _ in range(5):
        store = EvidenceStore()
        try:
            result = simulate(store)
            stable[hashlib.sha256(json.dumps({k: result[k] for k in ("state", "status", "device_modified", "native_linux_boot")}, sort_keys=True).encode()).hexdigest()] += 1
        finally:
            store.close()
    report["simulation_outcome_reproducibility"] = {"runs": 5, "unique_semantic_outcome_digests": len(stable), "excludes": ["run IDs", "timestamps", "row IDs"]}

    store = EvidenceStore()
    try:
        def item(question, observed):
            return Evidence(question=question, observed=observed, source_url="local://benchmark/synthetic",
                            revision="fixture-v1", classification="HYPOTHESIS", confidence="synthetic",
                            limitations="Synthetic record; not hardware or research evidence", reproduction="tools/benchmark.py", next_step="none")
        for i in range(3000):
            store.add_evidence(item(f"Synthetic unrelated record {i}", "Unrelated lexical distractor about a fictional benchmark corpus"))
        queries = ["pongoos handoff", "backup manifest", "interrupt timer", "approval expiry", "ghidra provider"]
        expected = {query: store.add_evidence(item("Synthetic relevance example", query + " unknown; assertion deliberately not validated")) for query in queries}
        store.add("generated_advisory", {"observed": " ".join(queries), "classification": "GENERATED_ADVISORY_UNVERIFIED"})

        def scan(query):
            wanted = set(re.findall(r"\w+", query.lower()))
            return [row[0] for row in store.conn.execute("SELECT id,payload FROM records WHERE kind='evidence'")
                    if wanted <= set(re.findall(r"\w+", row[1].lower()))][:5]
        report["measurements"]["python_scan_reference"] = measured(lambda: scan(queries[0]), 20)
        try:
            from aegis.evidence.search import search_evidence
        except ImportError:
            report["indexed_search"] = "UNAVAILABLE in selected source revision"
        else:
            start = time.perf_counter_ns()
            first = search_evidence(store, queries[0])
            report["measurements"]["index_build_plus_first_search_ms"] = (time.perf_counter_ns() - start) / 1e6
            report["measurements"]["indexed_search"] = measured(lambda: search_evidence(store, queries[0]), 20)
            judgments = []
            for query in queries:
                result = search_evidence(store, query)
                ids = [row["id"] for row in result["results"]]
                assert ids == scan(query), (query, ids)
                relevant = expected[query]
                judgments.append({"query": query, "returned": len(ids), "precision_of_returned": int(relevant in ids) / len(ids) if ids else 0,
                                  "recall": int(relevant in ids), "reciprocal_rank": 1 / (ids.index(relevant) + 1) if relevant in ids else 0})
            report["synthetic_retrieval"] = {"canonical_rows": 3005, "generated_distractors": 1, "queries": judgments}
    finally:
        store.close()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
