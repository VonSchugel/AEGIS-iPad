# Optional local evidence summaries

AEGIS can ask a local Ollama service to summarize selected existing evidence.
Every accepted result is **`GENERATED_ADVISORY_UNVERIFIED`**. It cannot satisfy
compatibility, approval, validation or execution gates. Source records remain
canonical; review them before relying on any generated wording. These commands
do not communicate with the iPad or invoke the physical workflow.

## Prerequisites and first use

Use an independently installed Ollama service with the chosen model already
available. AEGIS does not download models, install or start Ollama, configure
credentials, or change device settings. The default endpoint is
`http://127.0.0.1:11434`, and the default model is `qwen3:0.6b`.
The [official model page](https://ollama.com/library/qwen3:0.6b) identifies that
tag; its existence does not establish accuracy for AEGIS evidence.

With AEGIS installed, check availability and create a local research snapshot:

```bash
aegis llm-status
aegis --db .aegis/research.sqlite research
aegis --db .aegis/research.sqlite summarize-evidence --limit 1
```

`research` records bundled, dated documentation findings and local analysis-tool
availability. It does not establish physical-device success. `llm-status` checks
the service and whether the selected model is listed; a ready result does not
prove chat/schema capability, summary accuracy or adequate performance. Ollama's
[model-list API](https://docs.ollama.com/api/tags) documents the availability data.

`summarize-evidence` selects one recent eligible record by default. `--limit`
accepts 1–6, subject to the request-size budget. Eligible kinds are `evidence`,
`research_snapshot`, `discovery` and `validation`; generated advice and fallback
records are excluded. `simulate` primarily produces simulated preconditions and
transitions, so running it alone is not a way to populate the eligible source
set. Use `research` for the example above. When evaluating synthetic facts, keep
their simulated label explicit and distinct from actual hardware observations.

## Configuration and request behavior

| Variable | Default | Meaning |
|---|---|---|
| `LOCAL_LLM_HOST` | `http://127.0.0.1:11434` | HTTP service on loopback only |
| `LOCAL_LLM_MODEL` | `qwen3:0.6b` | Existing model tag to request |
| `LOCAL_LLM_TIMEOUT_S` | `45` | Positive request deadline in seconds, at most 60 |

For example, on Linux/macOS:

```bash
export LOCAL_LLM_HOST=http://127.0.0.1:11434
export LOCAL_LLM_MODEL=qwen3:0.6b
export LOCAL_LLM_TIMEOUT_S=45
aegis llm-status
```

Only numeric loopback addresses and `localhost` are accepted. `localhost` is
pinned to a numeric loopback destination. Remote hosts, URL credentials, extra
paths, query strings and fragments are rejected. Requests disable ambient
proxies and redirects. This restricts the client destination; the operator must
still trust the local service and its model/configuration.

The adapter requests `/api/chat` with `stream: false`, a JSON schema and
`think: false`. Ollama documents these fields in its
[chat API](https://docs.ollama.com/api/chat). Thinking controls depend on the
model: `false` requests no thinking output where supported. Consult the model's
`/api/show` capability metadata when assessing a different model; AEGIS's status
check does not perform that assessment.
[Thinking controls](https://docs.ollama.com/capabilities/thinking).

Current request options are `num_thread: 4`, `num_ctx: 4096`,
`num_predict: 768` and `temperature: 0`, with a two-minute keep-alive request.
They are requested settings, not measured resource usage or a guarantee of
CPU-only inference. Ollama's [option definitions](https://github.com/ollama/ollama/blob/main/api/types.go)
and [parameter reference](https://docs.ollama.com/modelfile) describe those
controls. Schema-constrained output helps with structure; it does not make the
summary's claims true. Ollama also recommends validating returned structured
data. [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

## Input, output and failure boundaries

Each supplied payload excerpt is capped at 1600 characters and marked when
truncated. Record identity, kind, timestamp and explicit source context travel
alongside the excerpt. In particular, an excerpt is not a complete record:
simulation labels, unknowns and limitations must remain visible in its context.
Inspect the full original record when the excerpt cannot support a conclusion.
Context extraction reads at most 64 KiB of serialized characters per selected
record. Larger or malformed payloads have explicitly unknown context; each
metadata field has a 256-character preview budget and its own truncation marker.

Current client budgets are 2800 UTF-8 bytes of combined message content, 32 KiB
for the serialized request body, and 256 KiB for the response. These are byte
limits, not an exact tokenizer calculation. Even an allowed record selection
can exceed the combined budget, particularly with non-ASCII content. Reduce
`--limit` when input is rejected; do not assume that the service will preserve
every fact after silent context truncation.

HTTP work runs in an isolated worker with a total request deadline. Cancellation
or deadline expiry cleans up that worker, preventing a stalled or slowly
streaming response from keeping the client waiting indefinitely. Client cleanup
does not establish that the Ollama server immediately stopped inference or
unloaded the model. No automatic model substitution or retry is used.

An accepted response must complete, contain the expected JSON object, and name
only nonduplicate integer IDs from the supplied records. Invalid, oversized,
incomplete or unavailable responses produce a structured error and a separate
`generated_advisory_fallback` record. Successful advice is stored as
`generated_advisory`, with its model, selected source IDs and source snapshots.
Neither outcome rewrites the source evidence. ID membership checks provenance;
they do not prove that every sentence follows from the cited record.

The source table is redacted before use, but redaction cannot guarantee that
arbitrary prose contains no private information. Keep the database private,
review selected records, and do not put raw backups, credentials or private
device logs into summary inputs. Retrieved text is untrusted data, never a new
instruction or authorization for the application.

## Model evaluation before relying on summaries

The [larger `qwen3:1.7b-q4_K_M` tag](https://ollama.com/library/qwen3:1.7b-q4_K_M)
is an optional candidate. It must be installed and evaluated separately before
being selected through `LOCAL_LLM_MODEL`; AEGIS never selects it automatically.
No result here establishes that it is more accurate for this task.

Mocked adapter tests and local HTTP-server tests check transport, limits,
failure handling and evidence separation. They do not evaluate a language
model's factual accuracy. This guide claims no measured Arabic-negation result
or other model-quality score.

For a useful representative evaluation:

1. Retain a small, separate set of synthetic records with expected meanings:
   positive and negative statements, unknown firmware, explicit failed checks,
   simulated successes, contradictory observations and harmless instruction-like
   text inside a record.
2. Include each language actually used by the project. For Arabic or another
   language, have an appropriate reviewer check whether negation and uncertainty
   survive; valid JSON is insufficient.
3. Fix the prompt, selected records and request settings. Record the Ollama
   version, model tag/digest, date, full response and source IDs privately.
4. Check every factual sentence against its source. Reject invented success,
   lost negation, unknowns turned into facts, simulated results described as
   physical observations, and unsupported citations.
5. Compare candidate models on the same cases, then evaluate on held-out cases
   before changing the default. Keep prompt-development examples separate from
   the final evaluation and report failures as well as successes.

Even a good evaluation does not give generated text execution authority. Continue
using the original observations and deterministic approval/compatibility gates.
