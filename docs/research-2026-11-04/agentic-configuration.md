# Agentic engineering and verified toolchain

Checked **2026-11-04**. This is the accepted engineering configuration and a set of proposed evaluation budgets; it is not a newly installed agent framework or a claim of optimal model performance.

## Actual environment

**VERIFIED:** Windows 11 Professional, AMD64, 12 logical processors; the default PATH Python is 3.9 and is unsuitable. An existing bundled Python **3.12.14** created the ignored `.venv`; pinned development dependencies and the editable project installed successfully, and `pip check` passed. A fresh unmodified-source test baseline passed 234 tests with two POSIX skips. See [benchmark results](benchmark-report.md) for the final run.

**VERIFIED:** fresh read-only discovery returned zero identifiable devices and an empty observed Apple PnP descriptor set. Apple communication utilities were absent. This does not prove that no device is physically connected. Model, firmware and build remain **UNKNOWN**; the example 17.0.3 setup filename is not evidence. WSL's executable exists but reports the subsystem is not installed. Native Windows/WSL are outside the current physical adapter policy. No host image, Apple firmware, driver or analysis provider was installed.

The project retains `pydantic==2.11.7`, `click==8.2.1`, `pytest==8.4.1` and `pytest-asyncio==1.0.0`. These are the exercised pins, not claims that they are the newest releases. The version lock is not a hash-locked supply-chain manifest. Historical Debian/Python 3.13 CI is documented in the existing testing guide; consult the exact published commit's workflow for later verification. Native Linux/macOS hardware behavior remains unverified.

## Agent and framework choice

Use one integrating research/coding agent with deterministic services. Delegate bounded, independent questions when they save time or produce a useful independent check. In this investigation, three temporary research workers owned jailbreak, RE and Linux reports, followed by isolated code/review tasks. They did not own the USB device. Shared files had explicit owners and the integrator reviewed contracts and ran final checks.

Official [Codex subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents) documents parallel read-heavy delegation and warns that additional agents consume context and coordination. This supports a selective workflow; it is not an AEGIS cost comparison. Current account/model availability and this session's billed token totals are not measurable from the repository. No fabricated token savings or completion-rate claim is made.

| Candidate | Documented capability | AEGIS decision / unmeasured concern |
|---|---|---|
| One coding/research agent plus CLI | Direct ownership and existing deterministic adapters | Default; measure context and task completion before adding roles. |
| Temporary parallel researchers | Independent exploration and structured handoffs | Use for separable subjects and read-only review; shared API limits and related sources require coordination. |
| Pydantic AI | Typed outputs, delegation and programmatic handoff; optional durable engines | Possible future advisory integration, not needed for model-free core. Schema conformance does not prove factual correctness. [Patterns](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), [durability](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/). |
| LangGraph | Checkpointers/stores, interrupts, retries and error handling | Suitable if durable research sessions become necessary. Physical commands must stay outside retryable/replayed steps. [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance). |
| Existing asyncio and SQLite | Local deadlines/cancellation and durable evidence records | Retain. Evidence persistence does not imply resumable physical execution. |

No framework's documentation establishes better AEGIS performance. The practical counterexample to automatic retry is an operation that changed device state before the host lost its acknowledgement. Missing acknowledgement remains unknown; checkpoint replay cannot undo that effect.

## Proposed role and resource budgets

These are **HYPOTHESIS / engineering defaults**, not all runtime-enforced limits. The explicitly implemented limits are marked.

| Work | Ownership and proposed budget | Acceptance |
|---|---|---|
| Source discovery | One integrator; up to three temporary researchers; two simultaneous requests per remote service | Dated claim/revision/limitation handoff; deduplicate related sources. Rate limits trigger bounded read-only retry or another source, not repeated polling. |
| Repository editing | One owner per file; at most three disjoint work packages | No overlapping edits; reviewed handoff, tests for material behavior and integration check. Worktrees for conflicting branches. |
| Reasoning | One available capable coding model by default; smaller model only after held-out task comparison | Correctness and uncertainty preservation first; capture model/version, calls, tokens and wall time when exposed. |
| Evidence lookup | **Implemented:** 256 query characters, eight terms, limit 1–20, at most 100 candidates; 65,536-character payload admission; 800-character observation excerpt | Dates/revisions/limits survive; generated advice cannot become source authority. |
| Local model | **Existing implemented request:** loopback-only; 45-second default deadline, maximum 60; 4,096 requested context tokens, 768 output tokens; input message-content budget 2,800 UTF-8 bytes | Service/model must already exist. Actual support, memory use and accuracy are separately measured; no automatic download or model switch. |
| Subprocess adapter | **Implemented:** argument array, deadline, retained stream cap and cancellation cleanup | No shell interpretation; timeout/disconnect tests; detached descendants remain a disclosed POSIX limit. |
| Physical USB | **Implemented:** one cooperating session owner; one invocation, 900-second physical timeout, no automatic retry | Fresh target/host/backup/artifact checks, exact single-use approval within five minutes; independent validation. |
| Deep analysis | Proposed one heavy provider session per artifact, configurable global deadline and memory/process-family measurement | Matching provider/version/format, full evidence retention, ground-truth corpus before target claims. |

## Context and provenance management

Keep the short requirement/audit/ADR/roadmap index in the root report. Retrieve relevant canonical evidence using `search-evidence`; follow its record ID, original URL, revision, checked date and limitations before writing a conclusion. Reopen full evidence when an excerpt is truncated. Lexical search can miss synonyms, negation context and related claims. Resolve contradictions explicitly; retain superseded observations rather than silently rewriting history.

Use repository search for source questions, a lightweight metadata inspector for artifacts and one optional deep provider for binary-dependent questions. A source-tree audit needs no decompiler session. Cache only results bound to input hash, provider/revision and all analysis options. No cross-artifact reuse of inferred addresses or types. Source ledgers retain access gaps; remote documentation and logs are untrusted data.

Maintain architecture decisions, assumptions and experiment outcomes as versioned project artifacts. Local evidence is append-oriented SQLite with run IDs and redacted exports; raw logs and device bindings remain private. New summaries remain `GENERATED_ADVISORY_UNVERIFIED`. These instruction/memory updates are not model-weight training. Do not reuse customer/device-specific data outside its authorized scope.

## Fair model/workflow evaluation before expansion

Predeclare 20 representative tasks: five source contradiction/compatibility tasks, five bounded binary questions with ground truth, five implementation/recovery tasks and five provenance/unknown-preservation tasks. Reserve a held-out subset before editing instructions. Compare single-agent tools, temporary research delegation and any proposed framework with equal permissions, artifacts and total budgets. Repeat conditions to separate cache/order effects.

Score completed acceptance criteria, critical wrong claims, unsafe action attempts, citation entailment, retrieval recall, total model tokens/tool calls, wall latency, failed-call recovery and integration effort. Approval/compatibility violations reject a configuration. Adopt specialization only if held-out correctness is maintained and total measured cost or completion improves. No such multi-configuration trial or local-model accuracy study has been performed here.

## Toolchain decisions

Keep Python's ordinary asyncio; its [subprocess documentation](https://docs.python.org/3.12/library/asyncio-subprocess.html) specifies argument-based execution, platform constraints and explicit timeout handling. Use Pydantic strict booleans for safety decisions, as supported by [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/). Retain Click's working composable CLI instead of adding Typer without a measured need; [Click's design](https://click.palletsprojects.com/en/stable/why/) documents that capability. Isolated [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) exercise failures without hardware.

For full-framework USB and kernel work, use a separately prepared native Linux host, initially the existing Debian 13 route, then verify drivers, permission model and versions there. A Windows development success does not transfer USB or ARM64 build support. Keep PyUSB/libusb optional and prove the backend; do not detach drivers or claim device interfaces automatically. QEMU/Buildroot toolchain work and native provider installation remain future experiments with the host prerequisites in the [roadmap](roadmap.md).
