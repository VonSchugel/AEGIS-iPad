# Reproducible software benchmark and verification report

Checked **2026-11-04**. Classification: **VERIFIED local software observations**. Host: Windows 11 AMD64, Python 3.12.14, isolated pinned dependencies. This report establishes no physical jailbreak, payload, kernel or Linux result.

## Tests and changes

The unmodified initial source at `b99da1cb313845392279792d5ce5701cc03eab99` passed **234 tests, 2 skipped**, in **12.18 s**, with warnings treated as errors. The final reviewed source passed **269 tests, 3 skipped**, in **14.04 s**, under the same test configuration. The two existing skips require POSIX process groups; the added skip requires POSIX symbolic-link behavior because unprivileged Windows symlink creation is not assured. Collection and test-suite duration are not controlled performance benchmarks.

New checks cover typed gate kind/target/mode/success, strict booleans, duplicate and foreign IDs, legacy documentation classification input, cross-process hardware exclusion, lock release after error/process death, blocking before USB work, canonical source retrieval, old-database migration, incremental inserts, query/output bounds, generated-source exclusion, missing FTS5 and interrupted migration cleanup. Linux regressions resolve all source IDs and protect separate L0–L5 physical/simulation status. Existing tests continue to cover approval replay/expiry, changed device/backup/artifact, subprocess timeout/cancellation, simulated failures and independent validation.

Independent review exposed and corrected three integration issues during development: a Windows test assumed partial `communicate` output was available before EOF; interrupted first-use search migration could retain a transaction; and new DOCUMENTED source labels needed backward-compatible enum admission. These are verified reviewed corrections, not claims of model-weight training. Canonical serialization now uses DOCUMENTED while historical SUPPORTED BY DOCUMENTATION inputs remain accepted.

The wheel and source distribution built successfully. An isolated wheel import
matched all 35 source Python/data files byte-for-byte, then passed all five
fixture scenarios, research loading, source retrieval and Linux milestone
checks. See [package verification](package-verification.json). This is a local
working-tree build retaining version 0.2.0, not a newly published release.
Fresh live planning also stopped at identification with a structured
PRECONDITION_FAILED result; it did not reach a modifying adapter.

An additional concurrency probe used four independent SQLite connections synchronized before first lookup, then inserted new evidence. All completed and the final query returned five distinct canonical rows including the inserts. This is a focused observed probe, not a general database stress guarantee. No network model, exploit or physical device was used by the test suite.

## Measurements

The same [harness](../../tools/benchmark.py) was run against an isolated archive of the initial source and against the reviewed source. Raw sanitized outputs are [baseline](benchmark-baseline.json) and [final](benchmark-final.json). Each includes a source-tree SHA-256. Wall timing uses `perf_counter_ns`, CPU uses `process_time_ns`; all timed loops have Python allocation tracing enabled, a warm-up and garbage collection before repetitions. SQLite is in memory. Final measurement followed the test run, with no other AEGIS benchmark/test worker intentionally running in parallel.

| Component | Initial median / p95 | Final median / p95 | Repetitions and interpretation |
|---|---|---|---|
| Fixture compatibility evaluation | 0.391 / 0.442 ms | 0.391 / 0.446 ms | 100; includes dated evidence copies, no USB access. Difference is too small for an optimization claim. |
| Full fixture workflow | 4.840 / 5.778 ms | 6.437 / 6.929 ms | 20; typed gate checks add work. The roughly 1.60 ms increase is accepted for demonstrated gate rejection behavior; causality was not isolated with a profiler. |
| Python scan reference, 3,005 evidence rows | 200.144 / 206.059 ms | 192.514 / 199.575 ms | 20; a lexical Python scan reference, not a previously shipped search command. |
| New indexed lookup on same synthetic corpus | unavailable | 0.170 / 0.187 ms | 20 warm lookups; compares lookup mechanics only. |
| New index build plus first search | unavailable | 20.335 ms | One cold-index observation; interpreter startup excluded. |

Python peak allocated memory during traced repetitions was approximately 52.5 KB for compatibility, 95.8 KB for the final fixture workflow, 10.1 KB for the Python scan and 9.6 KB for warm indexed search. This excludes SQLite's native allocations, other process memory and the already-built index; it is **not RSS** or an index-memory comparison. Median reported CPU time is 0 ms for short operations because of timer/accounting granularity, not because the operation uses no CPU. The longer final scan reported 187.5 ms median process CPU time.

Five predefined synthetic queries each returned the one relevant canonical record, with precision of returned results, recall and reciprocal rank all 1.0. A generated advisory containing all query terms was excluded. This small, intentionally simple corpus tests lexical plumbing; it does not establish real research retrieval quality, contradiction detection or model accuracy. The scan and index outputs were asserted equal for those queries.

Five fixture workflow repetitions produced one semantic outcome digest after excluding run IDs, timestamps and row IDs. This establishes that narrow outcome reproducibility, not byte-identical logs, cross-host builds or hardware repeatability.

## What remains unmeasured

**UNKNOWN:** physical discovery/transport latency, jailbreak success rate, loader/kernel boot reliability, provider decompilation accuracy/throughput, process-family RSS, whole-machine CPU, real research retrieval precision/recall, model task completion, billed tokens and tool-call cost. No hardware or generic ARM64 QEMU experiment was performed. No speed advantage is claimed for a jailbreak fork, provider, framework or multi-agent topology.

The important local gain is a new independently usable retrieval capability with bounded provenance, alongside demonstrably stronger gate/session rejection behavior. The current bottleneck to physical progress is unavailable identity/firmware/native-host evidence, not the sub-millisecond compatibility service. Prioritize the [roadmap](roadmap.md) instead of optimizing already-small deterministic checks.

## Reproduction

Use Python 3.12+ and the pinned development environment. From the repository root:

```text
python -m pytest -q -W error --junitxml=.aegis/reports/tests.xml
python tools/benchmark.py --label local-review --output .aegis/reports/benchmark.json
python -m aegis --db .aegis/reports/research.sqlite research
python -m aegis --db .aegis/reports/research.sqlite search-evidence "A10 timer"
```

The interpreter should be the isolated environment's Python, not the host's default 3.9. For a baseline, extract `git archive b99da1cb313845392279792d5ce5701cc03eab99` into an ignored directory and pass its `src` with `--source`. Do not reuse old source-tree timings for a changed revision. Public JSON outputs omit private host paths; full local test/discovery reports remain under ignored `.aegis/reports/`.
