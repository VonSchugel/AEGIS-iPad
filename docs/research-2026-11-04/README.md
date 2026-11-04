# AEGIS research and engineering package

Checked **2026-11-04**. Initial source: `b99da1cb313845392279792d5ce5701cc03eab99`. This package contains the requested audit, current primary-source landscape, architecture decisions, working core changes and empirical software results. The separate full original specification was not found; reconstruction uses the supplied directive and existing repository. No new release has been published.

**Decision:** retain the six existing deterministic service modules and one optional research reasoning layer. Use temporary independent researchers for uncertain subjects. Strengthen execution contracts and source retrieval before adding frameworks, providers or device operations. The audit found no actual six-LLM architecture to remove.

**Implemented:** typed gate-specific receipts, rejection of wrong evidence kind/run/mode/target, cooperative process-level hardware exclusion, bounded canonical evidence search, backward-compatible DOCUMENTED evidence labels, updated Dopamine comparison and independent Linux L0–L5 contracts. The core remains model-free, and RE/research remains independent of physical execution.

**VERIFIED software:** baseline **234 passed / 2 skipped**; reviewed Windows source **269 passed / 3 skipped**, warnings treated as errors. Published source subsequently passed **272 tests** in [Debian CI](https://github.com/VonSchugel/AEGIS-iPad/actions/runs/41936088473), including the POSIX checks. Compatibility remains about 0.39 ms median; the fixture workflow rose from 4.84 to 6.44 ms with stronger gates. On a simple 3,005-row synthetic corpus, warm indexed retrieval took 0.17 ms versus a 192.51 ms Python scan reference. These are software results, not hardware, real research accuracy or token-cost results. See [the full benchmark report](benchmark-report.md).

**UNKNOWN hardware:** fresh Windows discovery could not identify the iPad or firmware. Windows remains outside the reviewed physical adapter policy; no device was modified. Encrypted-backup verification, exact release/build catalog admission, native USB validation and a working deep RE provider remain unresolved. The next useful physical step is supported native-host read-only discovery.

The most material research corrections are current [Dopamine 3.0.13](https://github.com/opa334/Dopamine/releases/tag/3.0.13), exact-board [J172 derivative work](https://github.com/Pauli1Go/HoolockLinux/tree/7b3e4e8b0156e190d9175c6fcf396ae384419f14) with author-reported experimental functionality, and the [REA 6.8.0](https://github.com/morluto/rea/releases/tag/rea-agents-6.8.0) / [Ghidra 12.2](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.2_build) provider-version mismatch. None justifies automatically replacing the pinned palera1n adapter, widening firmware admission or claiming Linux success. Consult the detailed reports for exact scope and source limitations.

## Deliverable map

| Requested deliverable | Artifact |
|---|---|
| 1. Design audit, assumptions and ranked hypotheses | [Architecture audit](architecture-audit.md) |
| 2. Current projects, forks, patches and research | [Jailbreak landscape](jailbreak-landscape.md), [RE tools](reverse-engineering.md), [Linux research](linux-feasibility.md) |
| 3. Hardware / firmware / host compatibility matrix | [Compatibility and integration matrix](jailbreak-landscape.md#compatibility-and-integration-matrix), [current execution policy](../compatibility.md) |
| 4. RE integration analysis | [Interfaces, provider matrix, forks and validation corpus](reverse-engineering.md) |
| 5. Accepted/rejected alternatives | [ADR-001 through ADR-007](architecture-decisions.md) |
| 6. Optimized architecture | [Component/data-flow diagram and typed contracts](architecture-decisions.md) |
| 7. Agentic configuration / context / budgets / host | [Engineering configuration](agentic-configuration.md) |
| 8. Prioritized implementation and experiment roadmap | [Dependencies, acceptance criteria and blockers](roadmap.md) |
| 9. Working code and tests | [Core source](../../src/aegis), [tests](../../tests), [benchmark harness](../../tools/benchmark.py), [installed-package verifier](../../tools/verify_package.py) |
| 10. Native Linux feasibility | [Exact-board subsystem matrix and L0–L5](linux-feasibility.md), [machine-readable milestones](../../src/aegis/data/linux.json) |
| 11. Benchmarks and validation limits | [Report](benchmark-report.md), [baseline JSON](benchmark-baseline.json), [final JSON](benchmark-final.json), [installed-package check](package-verification.json) |
| 12. Research provenance | [Jailbreak sources](jailbreak-sources.json), [RE sources](re-sources.json), [Linux sources and file digests](linux-sources.json), [engineering sources](engineering-sources.json) |

The four research ledgers contain 99 source entries; related claims and repeated URLs are not independent confirmation. Checked dates, refs, observed/source-claimed distinctions, confidence and access gaps accompany findings. GitHub API rate limits and inaccessible Apple/postmarketOS pages prevented complete coverage. Mutable pages are identified rather than given invented commits.

## Evidence vocabulary

**VERIFIED** means the particular local software/source/metadata observation was actually made. It does not imply hardware success. **DOCUMENTED** is an upstream capability/support statement. **EXPERIMENTAL** includes author-reported prototypes/results not reproduced here. **HYPOTHESIS** is a proposed inference/benefit/test. **UNKNOWN** is insufficient evidence. Historical `SUPPORTED BY DOCUMENTATION` labels remain accepted and map to DOCUMENTED in typed evidence. Simulation and physical status are tracked separately; all local Linux stages remain NOT_TESTED.

## Use the result

Use the repository's isolated Python 3.12+ environment. The following commands require no model or physical device:

```text
python -m aegis --db .aegis/research.sqlite research
python -m aegis --db .aegis/research.sqlite search-evidence "PongoOS handoff"
python -m aegis simulate
python -m aegis linux-status
python -m pytest -q -W error
```

Keep local databases, backups, logs and discovery reports private. No saved plan, search result, source text or model summary authorizes a device change. Each modifying experiment still needs a concrete compatible plan and explicit operator approval. Read the [roadmap](roadmap.md) before hardware work.
