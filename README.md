# AEGIS-iPad

An evidence-based Python application for owner-authorized iPad 7 research. It implements six cooperating agents, read-only discovery, a version-aware compatibility engine, a persistent evidence database, fixture simulations, and a guarded adapter for **palera1n v2.4 rootless**.

**Current result:** software verification passes on Windows and in Debian 13/Python 3.13 CI. The iPad's identity and firmware could not be established on the observed host because Apple communication utilities are absent. The physical installation gate has not been crossed. No device was modified, no jailbreak was verified, and Linux was not booted. See [verification results](docs/testing.md).

## Start

For a new Debian installation, follow [Install on Debian 13](docs/debian.md).
It covers GitHub cloning, system packages, an isolated Python environment,
tests and read-only discovery. Debian 12's default Python is too old for this
project. See [publication notices](NOTICE.md) for current limitations and license status.

Python 3.12 or newer is required. Create a local environment and install the pinned development dependencies:

```powershell
git clone https://github.com/VonSchugel/AEGIS-iPad.git
cd AEGIS-iPad
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.lock
.\.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\aegis doctor
.\.venv\Scripts\aegis simulate
.\.venv\Scripts\python -m pytest -q
```

On Linux/macOS, use `python3`, `.venv/bin/python`, and `.venv/bin/aegis`. Core installation without test dependencies is `python -m pip install .`. Optional USB and binary-analysis packages are declared in `pyproject.toml`; their presence does not establish working drivers or analysis engines.

The historical Windows build used Python 3.12.14 in an isolated environment. See [the environment summary](docs/environment.md) for the original observations; private machine paths and reports are excluded from this public source.

## Commands

All command results are JSON. Standard diagnostic commands do not pair, change USB mode, reset, restore or jailbreak a device.

| Command | Purpose |
|---|---|
| `aegis doctor` | Host architecture, CPU, installed tools and dependency candidates |
| `aegis discover` | Read-only normal/recovery/DFU observations; unknowns remain unknown |
| `aegis compatibility` | Evaluate the freshly observed hardware, firmware and host |
| `aegis research` | Dated citation snapshots and REA capability observations |
| `aegis inspect --artifact PATH` | Offline header/hash admission of a supplied artifact |
| `aegis plan --backup DIR --binary FILE` | Build a live plan and stop at approval |
| `aegis simulate` | Complete fixture-only state-machine run |
| `aegis simulate --scenario timeout` | Simulate a failure; also `disconnect`, `partial`, `unsupported` |
| `aegis validate` | Three bounded connectivity samples; never infers jailbreak from connectivity |
| `aegis validate --identity KEY --ssh-port 44` | Additional device-bound, USB-only SSH probes using an existing key and host-key pin |
| `aegis linux-status` | Independent Linux subsystem and milestone assessment |
| `aegis export-evidence --output report.jsonl` | Export the persistent, redacted evidence history |

The global database option precedes the command: `aegis --db research.sqlite simulate`. The default is `.aegis/evidence.sqlite`; each invocation gets its own run identity. Do not point this at a public/shared directory.

A packaged demonstration profile is available at `src/aegis/data/simulation.json`. `discover --fixture PATH` and `compatibility --fixture PATH` accept explicitly labeled data. Fixture input is never accepted by the physical execution command. `simulate` bypasses every physical adapter and records simulated evidence separately.

## Physical installation path

The execution command is implemented and fixture-tested, but **has not been exercised on hardware**. It requires native Linux/macOS, exactly one identifiable iPad7,11 or iPad7,12, a successful singleton Apple USB inventory, known release firmware/build, a completed matching backup, and a local binary matching an official pinned SHA-256 digest. Windows and WSL are blocked. Current local firmware policy is **15.0 through 18.4.0**; this is a conservative evidence policy, not a claim that newer firmware is unsupported upstream. Dopamine and historical checkra1n paths are researched alternatives, not automatic fallbacks.

1. Read [compatibility](docs/compatibility.md), [recovery](docs/recovery.md) and [threat model](docs/threat-model.md).
2. Use supported, independently verified upstream Apple/USB tools and the stable release listed in `src/aegis/data/palera1n.json`. This project does not download or install a jailbreak executable. It rejects mismatching binary bytes before executing even `--version`.
3. Establish a normal-mode read-only profile and resolve every unknown. Disconnect other Apple devices. Keep the same device attached throughout the approved experiment.
4. Review an existing completed backup. The verifier checks target/model/firmware, age within seven days, finished status, SQLite manifest integrity, and referenced regular-file payload presence. **It cannot prove restoreability or content integrity. Encrypted backups currently block this verifier; keep protected backups and use a separately reviewed verification path instead of weakening them.**
5. Run `aegis plan --backup DIR --binary FILE`. No device write is authorized by a saved plan or exported evidence.
6. In an interactive terminal, run `aegis execute --backup DIR --binary FILE`. It rebuilds the live plan, presents the briefing and requires `APPROVE <plan-specific phrase>`. Approval expires after five minutes, is bound to the target/backup/artifact/command, and is single-use. No `--yes` or piped approval is supported.
7. After fresh rechecks, the only physical command is the verified upstream **`palera1n -l`**. Its recovery/DFU instructions require operator participation. The adapter allows one invocation with a 15-minute host timeout and no automatic retry. It excludes passcode-bypass and loader-injection environment variables.
8. After the upstream tool exits, the operator completes the documented on-device loader/bootstrap prompts and confirms completion. Optional `--identity KEY --ssh-port 44` enables independent USB-only SSH validation with a preconfigured host key. Without those interfaces, the result remains partial/unverified.

Cancellation kills the ordinary POSIX subprocess group and stops bounded log collection; it cannot undo device changes or guarantee termination of a process that deliberately detached. Inspect device state before any new experiment. No recovery command, erase, restore, downgrade or experimental payload is automatically invoked.

Validation checks USB identity binding, hardware identity, filesystem access, bootstrap, `dpkg` and local root command execution where interfaces permit. `CORE_VALIDATED` describes only these checks. Reboot persistence, graphical package-manager operation and stability remain unknown. See [validation](docs/validation.md) for key pinning and the limits of the result.

## Evidence and native Linux

Historical private reports are excluded from the public source. Generate new reports locally under `.aegis/reports/` using the Debian guide. Bundled research snapshots retain source URLs, revisions/dates, observations, classifications, confidence, limitations, reproduction and next investigations. External content and device logs are data, never executable instructions or approval.

The Linux report confirms pinned mainline J171/J172 device trees, downstream Hoolock implementations, and an author-reported J172 touch/NVMe experiment. Those findings do not establish a reproducible native Linux installation on this device. All five local milestones—payload, early kernel, shell, root filesystem and graphical environment—remain **NOT_TESTED**. Read the [Linux feasibility report](docs/linux-feasibility.md) and [roadmap](docs/roadmap.md).

## Project map and verification

`src/aegis/agents` contains the six agents; `adapters` isolates upstream tools; `orchestration` enforces transitions; `safety` implements backup/approval checks; `evidence` stores redacted events; and `data` contains dated research and artifact manifests. REA is independent of physical command construction. Its [integration guide](docs/rea.md) distinguishes the implemented capability/parser seam from the unavailable live MCP/provider connection.

See [architecture](docs/architecture.md), [toolchain evaluation](docs/toolchain.md), and [test results](docs/testing.md). Tests cover compatibility boundaries, unknowns, privacy, malformed metadata, expired/replayed approvals, device changes, subprocess timeout/cancellation, simulated failures and independent validation. They never exploit or modify physical hardware. Target-host diagnostics and an approved hardware experiment remain necessary before relying on physical execution; macOS remains untested.
