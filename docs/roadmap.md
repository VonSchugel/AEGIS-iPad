# Evidence-based roadmap

Status date: **2026-10-21**. The implementation and fixture tests are software
achievements. **Zero physical jailbreak installation steps and zero Linux boot
experiments were performed.** Exact target firmware is still unknown. Test
results and the observed environment are reported separately; this roadmap does
not substitute a fixture profile for the owner's iPad.

## Delivered phases and their limits

| Phase | Delivered software/evidence | Remaining external validation |
|---|---|---|
| 0: toolchain discovery | Host/package/library/PATH diagnostics; environment observations and explicit missing-tool reports | Verify suitable native Linux/macOS tooling, USB drivers and actual transport; PATH presence is insufficient |
| 1: research and requirements | Dated compatibility comparison, pinned palera1n manifest, boot-chain and Linux subsystem evidence | Refresh mutable sources, resolve disclosed revision gaps and detect the real firmware |
| 2: read-only prototype | Typed discovery adapters, numeric USB inventory, firmware parsing, redacted evidence and offline artifact inspection | Run supported read-only utilities against the owner's normal/recovery target; do not guess inaccessible fields |
| 3: orchestration | Explicit state machine, same-run evidence references, backup verifier, local approval, structured errors and simulation scenarios | Confirm representative host/device transport behavior under an approved experiment |
| 4: jailbreak integration | Minimal rootless palera1n v2.4 adapter, official per-platform hashes, exact `-l`, filtered environment, one attempt and independent validation path | No upstream jailbreak binary or physical installation was executed here; manual bootstrap/loader completion may be required |
| 5: controlled experiment | Reviewable plan, guarded command, log/evidence collection and recovery guidance are implemented | Physical phase has not started; requires explicit operator approval and all gates |
| 6: native Linux | Independent source-backed report, readiness matrix and A–E criteria | Cross-build, QEMU userspace checks and every physical Linux milestone remain unperformed |

The Windows fixture suite covers normal/recovery/DFU parsing, ambiguity and
missing dependencies, compatibility rejection, backup/approval/artifact gates,
timeouts, cancellation, malformed outputs, partial validation and simulated
recovery. Physical transports are mocked. POSIX-only process-group tests are
skipped on Windows and require a supported POSIX host; no cross-platform result
is implied by the Windows run.

Public Debian 13/Python 3.13 CI subsequently passed all 172 software tests,
including the POSIX process-group checks, and fixture-only simulation.
See [verification evidence](testing.md). Actual target USB transport, DFU,
jailbreak installation and every Linux boot milestone remain untested.

## Next smallest useful steps

1. **Complete read-only identification.** Attach only the authorized target and
   inspect host/USB/device reports. Success requires an observed exact model,
   release firmware/build, mode, singleton inventory and local identity binding.
   Missing Apple utilities, USB access or firmware fields remain blockers.
2. **Prepare a supported host and reviewed backup.** Physical execution requires
   native reviewed Linux/macOS, not Windows/WSL. Verify installed dependency
   provenance and the local completed matching backup. The verifier's manifest
   and payload-presence checks do not prove restoreability; the operator must
   review that limitation.
3. **Produce a live plan.** Supply the correct standalone palera1n v2.4 artifact
   matching the packaged SHA-256. The conservative firmware policy permits
   15.0–18.4.0 only; newer releases need exact-version evidence and a reviewed
   policy change. Do not weaken the policy because a boot-ROM primitive exists.
4. **Request approval for that concrete experiment.** Display the target, backup,
   artifact, exact command and failure/recovery limits. The local digest-bound
   approval lasts five minutes after entry and permits one invocation. A saved
   fixture or old plan cannot authorize a physical action.
5. **Record the physical outcome independently.** Follow upstream preparation
   after approval, retain bounded redacted logs, and stop on failure. A zero exit
   is not installation success. Complete documented on-device bootstrap steps
   manually when necessary, then use existing authorized SSH credentials and a
   pinned host key for the limited core checks. Report unsupported, partial or
   unstable results without retry loops or automatic restore.

## Native Linux milestones

| Milestone | Current local status | First acceptable evidence |
|---|---|---|
| A: custom payload | NOT TESTED | Exact payload hash and fresh loader banner on the detected board |
| B: early Linux initialization | NOT TESTED | Kernel/DTB identity, usable RAM, AIC and timer boot logs |
| C: Linux shell | NOT TESTED | Interactive initramfs console with retained command results |
| D: usable root filesystem | NOT TESTED | RAM root first; storage experiments separately reviewed and approved |
| E: stable graphical Linux | NOT TESTED | Repeatable boot/input/thermal/power/recovery results; desktop appearance alone is insufficient |

Begin host-side Linux work by pinning kernel, board DTB, PongoOS/m1n1 and minimal
userspace source/configuration. Build with a suitable ARM64 toolchain, retain
artifact hashes and validate init/userspace on QEMU `virt`. QEMU does not emulate
the iPad's A10 peripherals and cannot establish their driver readiness. A
RAM-only physical handoff then requires its own approval; ordinary jailbreak
validation never loads a Linux payload.

Mainline J171 support and Hoolock's downstream work make a small bring-up
experiment credible. The exact-board J172 touch/NVMe desktop lead is
author-reported and experimental until pinned source and independent logs are
reviewed. J171 portability, internal storage, suspend and full power behavior
remain separate questions. See [Linux evidence and access gaps](linux-feasibility.md).

## Decisions requiring new evidence

Expand firmware eligibility only after reviewing exact-version upstream support,
release regressions and representative tests. Enable a new tool/host only after
its actual interface, provenance and failure behavior are verified. Advance a
Linux milestone only with that milestone's captured physical evidence. Treat
reviewed corrections as versioned project knowledge with separate evaluation
examples; changing instructions or evidence does not train model weights.

The implementation currently provides an MCP availability/schema seam, not a
live REA connection. Deep native analysis needs a legitimately supplied artifact
and verified provider. Inspect available source directly; investigate binaries
only for questions that source cannot establish. No firmware extraction, exploit
reimplementation, automatic restore or unrestricted agent loop is needed to
complete the next useful experiment.
