# Implemented architecture

AEGIS is a local Python 3.12+ application with six cooperating, testable agent
modules. The agents are explicit software components coordinated by the CLI and
state machine; they are not six independently running language-model processes.
Read-only discovery, offline research and fixture simulation work independently
of physical installation. No physical jailbreak or native Linux boot has been
verified in this project run.

## Module boundaries

| Agent | Implementation | Responsibility and current boundary |
|---|---|---|
| A: hardware discovery | `agents/discovery.py`, `adapters/libimobiledevice.py`, `adapters/libirecovery.py` | Host diagnostics, normal/recovery observations and numeric USB inventory; unknown properties stay unknown |
| B: compatibility | `agents/compatibility.py`, `data/compatibility.json` | Offline comparison with cited, dated policy; eligibility permits further checks, not execution approval |
| C: reverse engineering | `agents/reverse_engineering.py`, `adapters/rea.py` | Regular-file admission, hashing and bounded header identification; deep REA analysis remains blocked without a verified provider |
| D: jailbreak workflow | `agents/jailbreak.py`, `adapters/palera1n.py` | Live preconditions, plan, exact approval and one pinned upstream invocation |
| E: validation/recovery | `agents/validation.py`, `docs/recovery.md` | Independent connectivity, identity and optional authenticated bootstrap checks; documented manual recovery |
| F: Linux feasibility | `agents/linux_research.py`, `data/linux.json` | Dated subsystem/milestone assessment; no boot or firmware modification |

`models/core.py` supplies typed evidence, states, transitions and structured
errors. `adapters/process.py` isolates external programs using argument arrays,
deadlines, bounded retained output and cancellation handling. `evidence/store.py`
records redacted run-scoped observations and transitions in SQLite and exports
JSONL. `safety/backup.py` checks a completed local backup; `safety/approval.py`
binds human approval to the exact prepared plan. `orchestration/simulation.py`
uses explicitly labeled fixtures and never constructs a physical approval.

Raw upstream output is retained only under the database directory's ignored
`private/<run-id>/` tree. Exportable records contain status, truncation state and
stream hashes. Heuristic redaction alone is not used to make raw device logs
safe for publication. Review private files before deliberately sharing them.

The reverse-engineering layer does not construct jailbreak arguments. Available
source is inspected directly; REA is reserved for supplied binary-specific
questions. The REA MCP seam checks advertised operation names and Evidence
responses. It is an availability/schema boundary, **not a live MCP transport**.
Per-tool live schema validation remains the connecting client's responsibility.
No registered REA MCP tools or verified native provider were available here.
See [REA integration](rea.md).

## Workflow and evidence

```text
DISCOVER → IDENTIFY_DEVICE → VERIFY_COMPATIBILITY → VERIFY_BACKUP
 → PREPARE_ENVIRONMENT → SIMULATE → AWAIT_OPERATOR_APPROVAL
 → GUIDED_DEVICE_PREPARATION → EXECUTE_SUPPORTED_JAILBREAK → VALIDATE
 → POST_JAILBREAK_RESEARCH → LINUX_FEASIBILITY_ASSESSMENT
```

Execution or validation failures can branch to `RECOVERY_GUIDANCE`. The state
machine rejects skipped edges, false preconditions, empty evidence references
and references outside the current run. Each owning agent evaluates the actual
gate and stores its observation before requesting a transition. Referenced
records establish traceability; the generic state machine does not independently
prove the semantics of arbitrary evidence supplied by another Python caller.

The live path requires one identified target and one observed Apple USB
descriptor, reviewed model/firmware/host compatibility, a matching recent
completed backup and a verified upstream artifact. `SIMULATE` in this path means
the prepared dry-run plan and invocation; the separate fixture simulator tests
success, disconnect, timeout, partial-installation and unsupported paths.

An operator-controlled terminal displays the plan and briefing. The exact
`APPROVE <12-character plan digest>` response creates a local approval bound to
the complete plan, valid for five minutes after entry and consumed once. Saved
plans and simulated approvals cannot authorize execution. Before invoking the
tool, AEGIS rechecks target identity/firmware, singleton inventory, host,
eligibility, backup and artifact. Disconnecting or changing the target requires
fresh planning.

## Narrow installation adapter

The adapter accepts only the platform-specific standalone **palera1n v2.4** asset
whose SHA-256 matches `data/palera1n.json`; even the version probe follows hash
verification. The reviewed physical command is exactly `palera1n -l`. The plan
records the resolved path and artifact identity. Environment filtering excludes
loader injection and bypass variables. Upstream owns interactive DFU guidance
after approval. There is one invocation and no automatic physical retry.

The local firmware policy is **15.0 through 18.4.0**, inclusive. This is a
conservative AEGIS evidence boundary, not upstream's maximum. Unknown,
prerelease, malformed or unreviewed properties block. Windows/WSL execution is
blocked; native reviewed Linux/macOS hosts and architectures are required.
See [compatibility policy and sources](compatibility.md).

A zero upstream exit advances only to validation. Manual on-device loader and
bootstrap completion may still be necessary. Optional authorized SSH validation
requires an existing identity and pinned host key. Connectivity and bootstrap
predicates can establish a limited `CORE_VALIDATED` result; graphical package
management, reboot behavior and long-term stability remain independent unknowns.
See [validation](validation.md). Reaching the Linux assessment state merely
loads research; it never boots Linux.

## Evidence and process limits

Research uses `VERIFIED`, `SUPPORTED BY DOCUMENTATION`, `EXPERIMENTAL`,
`HYPOTHESIS` and `UNKNOWN`, with source/revision, confidence, limitations,
reproduction and next investigation. Fixture observations are explicitly
simulated; a passing software test is not a hardware result. Mutable citations
and inaccessible revisions are disclosed in the bundled ledgers.

On POSIX, subprocesses start in a new session and timeout/cancellation terminates
their process group. Processes that deliberately leave that group can escape
cleanup. Windows terminates the direct process; physical execution is disabled
there. Output-reader shutdown is bounded. None of these controls can undo a
change already made to the iPad. See [threat model](threat-model.md).
