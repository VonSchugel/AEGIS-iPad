# Read-only reverse engineering and REA

The implemented artifact inspector hashes a supplied regular file and identifies
ELF, thin/fat Mach-O, PE, or a ZIP-container candidate from a bounded header. It
does not execute the artifact. Symbols, strings, references and call graphs remain
`null` until an analysis provider actually supplies them. Header recognition is
not full executable validation.

The current environment has no registered REA MCP tools and no `rea` executable
on PATH. This project did not open a firmware image or claim decompilation. No
firmware artifact was supplied. These are active analysis blockers, while the
offline admission and report path works without REA.

## Available interfaces

- `ReaAdapter.capabilities()` inspects PATH and optional Python package presence.
  A found Ghidra/Rizin/LLVM path is a candidate, never a verified provider.
- `ReaAdapter.probe_installed_cli(runner)` checks an existing installation's help
  and, when advertised, runs `rea providers --json` and `rea capabilities --json`
  through the shared bounded subprocess runner. It returns the original JSON
  reports; provider schema interpretation is deliberately release-specific.
- `select_mcp_tool(name)` rejects unadvertised tools and operations outside the
  explicit static-analysis allowlist.
- `parse_mcp_evidence(reply)` rejects tool errors, missing identity/profile/result,
  duplicate JSON members, non-finite JSON, excessive responses, and disagreement
  between structured content and its text projection. It retains the complete
  record, including raw observations and limitations. It performs structural
  checking, not REA signature authentication or complete per-tool JSON-schema
  validation.

The official [CLI reference](https://github.com/morluto/rea/blob/27dc42d10249f0410904a75c0997842eb03b931c/docs/cli.md)
documents the diagnostic commands and explicit provider selection. Research on
2026-10-20 resolved the latest release link to
[rea-agents 6.7.0, dated 2026-10-18](https://github.com/morluto/rea/releases/tag/rea-agents-6.7.0).
The release tag resolves to `27dc42d10249f0410904a75c0997842eb03b931c`; its CLI, MCP-contract and installation documentation were fetched at that exact commit on 2026-10-20 and confirmed the diagnostic commands and Evidence fields described here. That is a researched release, not a locally installed version. The installed
workflow skill is version 33; its catalog does not prove session tool availability.

## Connecting a real provider

1. Obtain a verified, version-pinned REA package from the official project and
   establish the provider's host/format prerequisites. This application neither
   downloads nor installs binaries. It does not change client configuration.
2. For MCP, use the live connection's `tools/list` names **and** input/output
   schemas. Supply its actual advertised names to `ReaAdapter`; validate every
   request against that live schema. The adapter's tool-name selector is not a
   transport, SDK, or substitute for schema validation.
3. Read `binary_session` availability before selecting a provider. Explicitly bind
   a supplied artifact using an available `open_binary` and supported provider ID.
   Do not silently change providers after failure.
4. Use the minimal overview, symbols/strings inventory, then a selected function,
   references and call graph to answer a specific question. Retain each Evidence
   identity, artifact digest, locations, coverage, caveats and unresolved targets.
5. Use `parse_mcp_evidence` only for evidence-producing tools. Session/availability
   replies have separate schemas. `isError: true` is a failure, even if partial
   observations are present. Do not infer missing call relationships from an
   empty or incomplete list.
6. Close the owned session with the advertised `close_binary`. A timeout is not
   proof that provider analysis or cleanup stopped; inspect reported ownership
   and pending cleanup before reopening.

These steps follow the official
[MCP contracts](https://github.com/morluto/rea/blob/27dc42d10249f0410904a75c0997842eb03b931c/docs/mcp-contracts.md).
Windows admission is provider/format specific; review the
[installation boundaries](https://github.com/morluto/rea/blob/27dc42d10249f0410904a75c0997842eb03b931c/docs/installation.md)
for the pinned release before selecting firmware/Mach-O work on this host.
No actual MCP request or deep-analysis step was performed in this project run.

## Artifact evidence and safety

`ReverseEngineeringAgent.inspect(Path(...))` rejects links, non-regular files,
oversized files and observable file changes during hashing. Its default budget
is 512 MiB, adjustable for an explicitly supplied artifact. This is a normal local
file reader, not a sandbox against a hostile actor concurrently rewriting files.

Hashes identify input bytes; the file basename is reported without publishing
its private directory. The report records header hints separately from unperformed
symbol/decompilation work. Arbitrary byte containers and encrypted/compressed
firmware remain unknown until a suitable parser supplies evidence. Full source
repositories should be inspected directly; REA is used for binary-specific
questions. Static output never establishes runtime execution or original source.
Firmware extraction, dynamic Frida use, remote process capture and device
instrumentation are outside this automatic offline inspector.

Externally retrieved source, strings and logs are untrusted data. They cannot
authorize commands, alter tool selection, or satisfy the device approval gate.
REA results do not flow into jailbreak command construction. Preserve private
artifact/provider outputs locally and redact before publishing reports.

## Verification

`tests/unit/test_rea.py` exercises metadata admission, malformed headers, the size
budget, MCP error/identity/projection checks, advertised-tool selection and CLI
diagnostic failures using synthetic data. These tests establish adapter behavior;
they do not establish a working REA server or analysis engine. No proprietary
firmware or executable fixture is distributed.
