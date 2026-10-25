# Changes

## 0.2.0 — 2026-10-25

- Add optional `llm-status` and `summarize-evidence` commands for a local Ollama
  service. No model installation, device access or physical workflow is invoked.
- Keep generated advice and failure records separate from canonical evidence;
  verify cited record IDs and exclude generated text from later summary inputs.
- Preserve bounded source classifications, simulation labels and limitations
  outside truncated excerpts, with explicit unknown/truncation markers.
- Enforce numeric loopback destinations, disabled proxies/redirects, request and
  response budgets, a total HTTP worker deadline and cancellation cleanup.
- Normalize malformed JSON, oversized integers and invalid configuration into
  structured errors and fallback records. Existing observations remain intact.
- Add mocked and real loopback HTTP regression tests, and document a separate
  evaluation procedure for model accuracy. No model-quality benchmark is claimed.

The operator approval, backup and compatibility requirements are unchanged.
Hardware installation and native Linux boot remain unverified. No project
license is selected.
