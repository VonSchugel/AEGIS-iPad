# Threat model and operational boundaries

AEGIS assumes an owner-authorized research iPad and an operator-controlled local
host. Its safeguards reduce accidental target selection, unsupported invocation,
false success claims and disclosure of identifiers. They are not a security
sandbox against a malicious local administrator, a compromised operating system
or a hostile upstream executable. No physical installation has been tested here.

## Assets and trust boundaries

The protected assets are the owner's device data and bootability, local backups,
private identifiers and pairing material, SSH credentials/host-key trust, and
the integrity of experiment evidence. Distinct boundaries exist between the
operator and approval prompt; observed device properties and compatibility
policy; external tools and parsed results; public research and executable plans;
and local evidence and material intended for publication.

| Threat | Implemented control | Remaining limitation |
|---|---|---|
| Wrong or swapped device | Singleton device/USB checks, local identity binding, fresh pre-execution comparison and matching backup | Keep other Apple devices disconnected; there is no physical lock preventing a swap after the final observation |
| Unsupported firmware or host | Exact target scope, release/build validation, conservative 15.0–18.4.0 policy, native Linux/macOS requirement | Version/build syntax is not proof that an exact firmware release exists; documented eligibility is not a successful experiment |
| Altered upstream binary or arguments | Platform-specific palera1n v2.4 SHA-256 manifest, version check, rehash before invocation, exact `-l` argument, filtered environment | Release metadata is not an independent audit; a hostile local actor can exploit the path-to-execution race |
| Reused or mismatched approval | Exact plan-digest phrase, interactive terminal, five-minute local lifetime and single-use consumption | Approval records the operator's consent, not independent proof of ownership or operator identity |
| Incomplete backup | Matching identity/model/firmware, recent finished snapshot, manifest integrity and payload-presence checks | Payload contents and restoreability are not verified; encrypted backups are unsupported by this verifier |
| False installation success | Independent connectivity/identity/SSH/bootstrap predicates; zero tool exit is insufficient | `CORE_VALIDATED` does not prove stable graphics, reboot behavior or long-term reliability |
| Runaway tool or hung USB backend | Timeouts, bounded output, cancellation, isolated query processes and no physical retry loop | Stopping the host process cannot reverse device changes; escaped descendants may survive cleanup |
| Malicious research or logs | Fixed operation selection, parsed allowlisted properties, no evaluation of retrieved text | Upstream tools/parsers still process untrusted files and device responses under local host permissions |
| Identifier disclosure | Property allowlists, transient raw identifiers, pseudonymous local binding and redaction before storage/export | Redaction is best effort; review exports and retained free-form tool logs before publication |

## Device modification boundary

Initial diagnostics and discovery do not pair, enter DFU, reset USB, install a
bootstrap or write firmware. PyUSB inventory reads numeric descriptors without
claiming interfaces or changing configuration. Missing access means unknown.
Only the guarded execution path can invoke the pinned jailbreak tool, after
explicit approval and a live recheck. Approval covers the displayed plan and its
upstream guided preparation, not unrelated tools, restore actions or Linux boots.

The application exposes no automatic erase, restore, downgrade, repartition,
rootful/fakefs, experimental kernel argument or custom-payload path. Activation
Lock/Apple ID circumvention, credential extraction and unauthorized access are
outside scope. Recovery guidance does not authorize device restoration. A
separate, concrete operator-reviewed experiment is required for any later
device-modifying research.

## Evidence and privacy

Raw UDID/ECID/serial values are excluded from public discovery reports. A digest
of the normal-mode identifier can bind local backup, planning and validation;
that digest remains potentially linkable and is also redacted from persisted
records and public output. Transient identifiers may appear in arguments passed
to trusted local transport tools. The subprocess layer does not automatically
log those arguments or raw discovery streams. Do not enable independent shell
or process tracing that publishes them.

The SQLite API adds records with a run ID and timestamp; transitions reference
records from that same run. This is an application append-only convention, not
a tamper-evident or immutable database. A local actor who can edit files can
change the database, code, fixtures and manifests. Hashes identify byte content;
they do not independently authenticate ownership, runtime behavior or source
provenance. Preserve source URLs/revisions and distinguish documentation claims,
author-reported experiments and locally observed outcomes.

External pages, repositories, strings, firmware and device logs are **data**.
They cannot instruct an agent, authorize a tool, supply operator consent or
override compatibility rules. REA's static-operation selector rejects absent or
runtime operations, and its Evidence boundary rejects structural errors and
text/structured-result disagreement. The seam does not authenticate REA
signatures or implement a live MCP transport; connecting clients must also
validate actual advertised schemas. See [REA boundaries](rea.md).

## Cancellation, recovery and authenticated validation

POSIX execution uses a separate process group, terminated on timeout or
cancellation. A descendant that deliberately starts another session/group can
escape it. Windows cleanup targets the direct process, and physical jailbreak
execution is blocked on Windows/WSL. Output-reader shutdown has its own bound.
These controls constrain host work; they cannot guarantee the device's final
state or undo a partially completed write. After failure, stop and inspect
read-only state using [recovery guidance](recovery.md); do not retry blindly.

Optional SSH validation uses an operator-supplied key, existing independently
pinned device host key, explicit USB target selection and fixed read-only
commands. It does not accept host keys, install credentials, change passwords,
open a network fallback or reboot the device. Missing prerequisites leave the
installation unverified. Manual bootstrap preparation and long-term stability
assessment remain distinct from these checks.
