# Software verification — 2026-10-20

Historical Windows Python 3.12.14 run: **166 passed, 2 skipped**, exit 0. All warnings were treated as errors. The two skipped tests require POSIX process-group behavior, which Windows cannot establish. Historical machine-readable reports are excluded from the public source; reproduce the run locally.

The sanitized publication copy was retested on 21 October 2026 against its own
source with the same runtime: **166 passed, 2 skipped**, warnings treated as
errors. That local report is kept in the ignored `.aegis/reports/` directory.
Debian/Python 3.13 has not yet been exercised; the prepared CI job and Debian
guide describe how to obtain that evidence.

Reproduction from an installed checkout:

```text
python -m pytest -q -W error --junitxml=.aegis/reports/tests.xml
```

Coverage is by behavior rather than a line-percentage claim:

| Area | Verified software behavior |
|---|---|
| Discovery | Normal/recovery parsing; non-pairing queries; bounded numeric USB worker; unknowns, multiple devices, private-ID exclusion |
| Compatibility | Target models, firmware range/build train, prerelease rejection, unsupported/unknown hosts, WSL, manual alternatives |
| Approval/state machine | Legal edges, current-run evidence, false preconditions, exact phrase, expiry, plan binding, single use |
| Backup | Completed metadata, target/model/version, age, SQLite integrity, payload presence, malformed plist roots, missing/encrypted data |
| Execution adapter | Pinned hash rejection, supported host, exact version/arguments, sanitized environment, terminal requirement, fixture rejection |
| Workflow | Full mocked plan/approval/validation sequence; changed target/firmware/backup/inventory; timeout and partial result; no automatic retries |
| Subprocesses | Shell metacharacters remain arguments, status/streams, output cap, timeout, cancellation, detached-child pipe cleanup |
| Validation | USB-only explicit target transport, SSH key/host-key restrictions, hardware response, bootstrap probes, failure/unknown results |
| REA/artifacts | Header/hash admission, malformed/oversized artifacts, strict MCP evidence/error/projection handling and advertised-tool checks |
| Evidence/CLI | Privacy filtering, private log separation, SQLite/JSONL history, fixture labeling, CLI command integration |

Tests use synthetic device outputs, temporary backup manifests and ordinary local Python subprocesses. They do not invoke a jailbreak executable, send an exploit, pair, change device mode, install packages on an iPad, boot Linux or test firmware recovery.

Review found and corrected structured-error failures for malformed metadata, approval-state ordering, incomplete singleton inventory, unbounded descendant-pipe cleanup and SSH endpoint binding. Windows pytest-asyncio's policy lookup also allocated an unused event loop. The session test fixture explicitly owns its event-loop policy; no resource warning is suppressed and production asyncio behavior is unchanged.

Host diagnostics and blocked planning were exercised separately through the installed CLI; those historical reports remain private. Simulated success does not satisfy a hardware precondition. The physical Linux/macOS adapter, actual DFU progression, bootstrap completion, independent hardware validation, reboot behavior and all Linux milestones remain untested. The CI workflow is a prepared verification procedure; no remote CI result is claimed.

The distributable wheel was also installed into a separate target directory.
Isolated interpreter checks asserted that the imported module came from that
target rather than the source checkout, then successfully ran `simulate`,
`research` and `linux-status`. All four bundled data files were present and no
private logs/database were packaged. That historical package report remains private.
