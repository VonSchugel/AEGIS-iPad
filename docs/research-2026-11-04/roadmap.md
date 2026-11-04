# Implementation and experiment roadmap

Checked **2026-11-04**. Ordering reflects consequence and dependencies. Completed software work is subject to the [verification report](benchmark-report.md); proposed benefits are **HYPOTHESIS**, and unavailable physical results remain **UNKNOWN / NOT_TESTED**.

| Priority / milestone | Dependencies and work | Measurable acceptance | Current result |
|---|---|---|---|
| P0 baseline and host | Inspect original source, build isolated runtime, run unmodified tests, fresh read-only discovery | Reproducible test report; interpreter/dependency identity; unknowns remain unknown | VERIFIED local software baseline; device/firmware unresolved. |
| P0 gate contracts | Reuse state graph; type receipts and bind target/run/mode | Reject wrong edge, wrong kind/target/mode, failed/nonboolean/duplicate/foreign evidence; pass normal/simulated flow | Implemented; regression and full-suite results in report. |
| P0 hardware ownership | OS lock independent of database; no lease stealing/retry | Two independent processes cannot own session; busy path accesses no USB; owner error/death releases host lock | VERIFIED ordinary-process tests on Windows and Debian CI; physical USB remains untested. |
| P1 source retrieval | Typed evidence, literal FTS5, incremental index, cancellation handling | Preserve original source rows; exclude generated advice; bounded input/output; migrate existing DB; missing-FTS error; five-query synthetic judgments | Implemented and measured; real research precision UNKNOWN. |
| P1 research refresh | Exact releases/refs, source comparisons, source ledgers | Versioned claims, dates, limitations and access gaps; no unsupported policy expansion | Completed prioritized review; Dopamine 3.0.13 refreshed; palera1n physical policy unchanged. |
| P1 Linux milestone contracts | Independent L0–L5, source references, subsystem report | All reference IDs resolve; documented/simulated/physical distinct; legacy A–E remains compatible | Implemented; all local Linux stages NOT_TESTED. |
| P2 native host and target L0 | Operator-provided supported Linux/macOS host and authorized unit; verified Apple tools/permissions | Exactly one device and Apple descriptor; observed ProductType, firmware/build, normal mode and binding; no pairing/mode change by discovery | Blocked by actual Windows host and unavailable identification tooling. |
| P2 exact firmware admission | L0 observations; original Apple metadata/BuildManifest from legitimate artifact | Match product, release and build to a pinned provenance record; reject inconsistent or unreviewed combinations | Planned. Current engine checks syntax/train and conservative range only. |
| P2 encrypted backup evidence | Existing protected completed backup; separately reviewed verification design | Private target/age/completion binding plus explicit encryption/verification limits; no password extraction or weakening encryption | Planned; current verifier blocks encrypted backups and cannot prove restoreability. |
| P2 metadata adapter corpus | Redistributable known-source ARM64 ELF/Mach-O samples, malformed/fat fixtures; selected provider executable | Digest unchanged; formats/architecture/sections/symbols agree with ground truth/LLVM; bounded timeout and unsupported features unknown | Planned; existing header/hash admission remains operational. |
| P3 optional deep RE provider | Metadata corpus; provider/version/host matrix; active advertised schemas | Known-function boundaries/calls checked against truth; full parent Evidence retained; cancellation/resource outcome recorded | Planned. No active REA provider or transport established. |
| P3 approved jailbreak experiment | L0 + exact compatibility + backup + pinned artifact + dry run + exact operator approval | One invocation; retained stage logs; same target reidentified; independent bootstrap/root checks; failures/partial outcomes reported | NOT_TESTED. No permission or physical action inferred from this roadmap. |
| P3 Linux offline build/QEMU | Native build host; pinned kernel/DT sources/toolchain/initramfs; licenses and configs | Kernel/DTB binding checks, source/config/tool digests; generic init/shutdown passes QEMU `virt` deadline; output explicitly simulated | Planned; tools/build not exercised here. |
| P4 Linux L1–L4 RAM-only experiment | Board/firmware-specific loader review, logs/recovery plan, offline artifacts, separate explicit operator approval | Fresh board-bound interface/payload banners; kernel AIC/timer/RAM log; interactive RAM-root shell; bounded stopping conditions | NOT_TESTED; Hoolock and J172 derivative are candidates only. |
| P5 Linux L5 usability | Repeated approved earlier stages; peripheral-specific plans | Recorded repeat boots, display/touch, bounded thermal/power, stability and recovery results; storage/radio/suspend separately scoped | NOT_TESTED; no native Linux success is claimed. |

## Minimal next hardware step

Use the existing native Linux guide to collect **read-only** `doctor` and `discover` results from the actual target environment. Do not assume 17.0.3, board identity or USB readiness from an example file. Retain reports privately and resolve identification before considering an execution plan. Windows remains a supported development/research host, with physical execution blocked by the current adapter.

An operator-approved physical attempt must name device/model/release/build, host/USB transport, source/artifact hashes, backup receipt and limits, allowed operation, deadline/attempt count, expected observations, independent validation and manual stopping/recovery guidance. Approval must be bound to the concrete plan and consumed once. Interruption does not imply no device effect; fresh inspection precedes a new plan. No autonomous erase, restore, downgrade, internal-storage rewrite or Activation Lock/credential operation belongs in these experiments.

## Experiment manifest contract

The existing evidence database supplies run IDs, timestamps, receipts and event history. Extend it incrementally with a typed experiment manifest when real artifact/build experiments are available. Required fields should include:

- Question/hypothesis, exact target applicability and acceptance/failure criteria declared before the trial.
- Inputs: artifact/source/commit/submodule/configuration/toolchain hashes, host identity without private machine names, and provenance.
- Evidence mode: DOCUMENTED, simulated, physical or generated interpretation; preserve explicit NOT_TESTED/UNKNOWN.
- Actions: read-only versus modifying, authorization scope, hardware owner, deadline and maximum attempts.
- Results: full log/artifact digests, bounded projections/truncation, independent validation, failures, limitations and reviewed conclusion.

This manifest extension is **planned**, not a new CLI feature claimed in this package. Current run records do not resume physical commands. No result is promoted from simulation or another board. Source/build reproducibility, semantic outcome reproducibility and byte-for-byte log identity are separate properties.

## Optimization evaluation order

First eliminate incorrect transitions and overlapping hardware sessions. Then measure deterministic retrieval and provider work. Evaluate context/model specialization only after source-grounded held-out tasks exist. Source-token estimates, billed model tokens, wall latency, process-family RSS and real device reliability are separate measures; missing measurements remain missing.

Change the architecture only when a representative controlled comparison shows a benefit. A faster fork with weaker board support is inadmissible. A heavy provider that recovers needed facts accurately may justify startup cost. A durable research orchestrator becomes useful only when long-running nonphysical tasks and recovery requirements exceed the local SQLite/process model. None of those future choices is precommitted.
