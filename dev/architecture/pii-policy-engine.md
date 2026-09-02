# PII Policy Engine

The PII policy path detects sensitive data in supported model and MCP requests,
applies client policy, and returns a typed decision. It is split across four
components:

- **PII Engine** analyzes structured requests and applies policy.
- **PII model sync** verifies and selects optional transformer model bundles.
- **AgentGateway extProc** adapts Gateway traffic to the PII Engine API and
  processes provider responses.
- **Studio** lets authorized users inspect and test policy.

## Request Flow

```text
caller
-> AgentGateway authentication and authorization
-> trusted destination metadata
-> extProc validation and protocol processing
-> PII Engine analysis over mTLS, when enabled and needed
-> policy decision and request transformation
-> model or MCP backend, or rejection
-> extProc response validation and placeholder reversal
```

Every supported model request and every configured MCP route passes through
extProc. AgentGateway supplies the verified principal and destination policy.
Callers cannot choose or override this metadata.

Each model and MCP destination has independent `piiEnabled` and
`contentTracingEnabled` settings. Both default to `true`, and each client must
set both values explicitly.

- A PII-disabled model still receives strict model dispatch, but extProc does
  not call PII Engine or create PII state.
- A PII-disabled MCP route still receives strict MCP protocol validation, but
  extProc does not transform or report content.
- Content tracing is an AgentGateway setting. It does not change PII policy.

## Supported Traffic

PII Engine supports strict request models for:

- OpenAI Chat Completions;
- OpenAI Responses;
- MCP `tools/call` requests using protocol version `2025-11-25`.

Only schema-defined, model-visible text is analyzed. Protocol fields, object
keys, IDs, tool names, and other control data are not treated as user text. For
MCP, only string values below `tools/call.params.arguments` are analyzed.

Text leaves are independent. Entity spans do not cross messages, content parts,
tool arguments, or other leaves.

## Decisions And Actions

PII Engine returns one of four decisions:

| Decision | Result |
| --- | --- |
| `pass` | Forward the request without a terminal policy action. |
| `apply_actions` | Forward the validated transformed request. |
| `reroute` | Select a policy-approved route. |
| `block` | Reject the request and do not forward it. |

Supported actions, from strictest to least strict, are:

```text
block
> reroute
> redact
> replace
> reversible_replace
> encrypt
> hash
> mask
> pass
```

Attachment and safety rules run before PII scanning. A block is resolved before
any text is transformed. MCP cannot reroute to a model, so an MCP `reroute`
action becomes a block.

### Overlapping Detections

PII Engine handles overlaps deterministically:

1. Connected detections of the same entity become one logical occurrence.
2. Remaining connected overlaps form one region.
3. The strictest action wins and is applied once to the complete region.
4. Equal actions use deterministic span, score, entity, and recognizer
   tie-breakers.

Reports retain aggregate counts for every logical entity. They do not include
matched text, previews, spans, hashes, ciphertext, or reversal plaintext.

## Sessions And Reversal

extProc derives an opaque session key from trusted identity, destination, and
session information. Model conversation headers and MCP session IDs are inputs
only after protocol validation. If no usable session reference exists, extProc
uses a random request nonce. Prompt content is never used as session identity.

PII Engine may store sticky block and reroute decisions in Valkey. Stored state
is bounded and contains only policy state and aggregate report facts. It never
contains request text, conversation IDs, or reversal mappings.

Stable reversible aliases are limited to adapter Chat requests. Their namespace
depends on the trusted session key, active policy version, and runtime hash key.
Direct Studio evaluation and other request types use request-local namespaces.

Reversal mappings remain in one extProc request and are discarded after response
processing. extProc restores only exact, authorized placeholders in supported
response fields. Invalid placeholders fail closed in structured and protocol
data. In ordinary human-readable model text, extProc replaces an invalid token
with a bounded marker and continues the response.

For analyzed model requests, extProc also adds a fixed instruction that tells the
model to preserve PII aliases. PII Engine does not analyze this adapter-owned
instruction. It is not added to MCP or PII-disabled model requests.

Before provider dispatch, extProc omits empty `tool_calls` arrays from analyzed
Chat Completions messages. Non-empty tool calls remain unchanged. This
normalization preserves interoperability with providers that require
`tool_calls` to contain at least one call whenever the field is present.

## Analysis Results

A successful analysis includes:

- the decision, transformed request, route, and applied actions;
- entity names and aggregate counts;
- scan and cache provenance;
- analysis duration when a scan ran;
- overlap count and the `strictest_action` strategy;
- policy version and text-leaf count;
- policy-owned response notices.

The adapter response also contains a bounded report and request-local reversal
mapping. `/v1/studio/analyze-request` returns neither. Policy evaluation returns
an aggregate report and simulation strings, but never the reversal mapping.

For successful analyzed model responses, extProc replaces any upstream
`x-presidio-code` header with one result code:

| Code | Meaning |
| --- | --- |
| `P00` | No sensitive data was detected. |
| `P01` | Sensitive data was detected and passed by policy. |
| `P02` | Sensitive data was transformed or masked. |
| `P03` | Policy rerouted the request. |

This header is result metadata, not authorization input. MCP responses do not
receive it.

## Private APIs

The analysis listener requires mTLS. Routes also check the exact client
certificate identity.

| Route | Client | Purpose |
| --- | --- | --- |
| `GET /v1/adapter/ready` | extProc | Verify the complete analysis path. |
| `POST /v1/adapter/analyze-request` | extProc | Analyze traffic and return adapter-only report and reversal data. |
| `POST /v1/studio/analyze-request` | Studio API | Analyze without returning reversal data. |
| `POST /v1/studio/evaluate-policy` | Studio API | Evaluate a request-local policy candidate. |
| `GET /v1/actions` | Studio API | Read the action registry. |
| `GET /v1/policy` | Studio API | Read safe policy metadata. |

The default Studio client certificate common name is
`frontend-studio-api`. Browser JWTs terminate at Studio API and are never sent
to PII Engine.

## Studio Policy Evaluation

The browser calls `POST /api/policy-engine/evaluate` on Studio API. The route
requires the `studio-user` and `pii-admin` realm roles. Browsers never call PII
Engine directly.

An evaluation may include a request-local `PolicyOverride`. It may change policy
behavior, but not process settings, model configuration, Helm values, or custom
recognizers. PII Engine merges, validates, and compiles the candidate for that
request only. It does not change live policy or session state.

Valid results include aggregate reports and bounded diagnostics with paths,
code-point offsets, normalized entities, confidence scores, recognizer sources,
and configured and resolved actions. Diagnostics never include matched text or
reversal mappings.

The `deterministic_echo` simulation calls no model, provider, or AgentGateway.
It uses request-local reversal data to build simulated model and user views, but
does not return the reversal mapping. Reversible placeholders use a random
request-local namespace, so identical evaluations are not guaranteed to be
byte-identical. The current Studio UI does not display the simulation strings.

## Limits And Timeouts

Current platform limits are:

| Boundary | Limit |
| --- | ---: |
| Serialized request body | `5 MiB` |
| Aggregate model-visible text | `4,000,000` Python characters |
| Model-visible text leaves | `256` |
| Request nesting depth | `32` |
| Adapter response | `10 MiB` |
| Studio evaluation response | `10 MiB` |
| Transformed model request | `10 MiB` |
| Provider response input | `10 MiB` |
| Transformed provider output | `10 MiB` |

Wire-byte, semantic-text, leaf-count, and nesting limits are independent. UTF-8
encoding and JSON escaping can make a request reach the byte limit before it
reaches the character limit.

Studio API also limits supported text fields to `100,000` characters before it
calls PII Engine.

The deployed timeout order for model traffic is:

```text
PII Engine analysis:       up to 600 seconds
extProc to PII Engine:           615 seconds
AgentGateway to extProc:         630 seconds
```

The active policy may set a lower analysis timeout. PII Engine limits direct
Studio analysis and evaluation to 30 seconds. Studio API uses a 45-second outer
request timeout.

A caller timeout does not stop CPU work immediately. Timed-out analysis can
continue to consume capacity until its worker exits.

## Readiness And Listeners

PII Engine separates workload and management traffic:

- Port `8443` serves the mTLS analysis API.
- Port `8001` serves `/live`, `/ready`, and `/metrics` for Kubernetes and
  Prometheus.

Management readiness checks policy, keys, model runtime, and Valkey when sessions
are enabled. extProc `/ready` makes one short, non-retrying mTLS request to
`/v1/adapter/ready` through the PII Engine Service. extProc `/health` checks only
its own process.

NetworkPolicy allows extProc and Studio to reach only the analysis listener.
Management endpoints must remain cluster-internal.

Flux `dependsOn` controls installation order. It does not replace continuous
runtime readiness.

## Model Runtime

The PII Engine image includes small English, German, and Dutch spaCy models for
offline baseline analysis. If the exact desired transformer bundle is already
verified and selected, the engine starts in transformer mode. Otherwise it uses
the baseline while model sync prepares the desired bundle.

The model-sync CronJob runs every 15 minutes. It verifies the pinned version,
manifest digest, checksum index, files, size, and paths before atomically
selecting a bundle. A missing bundle leaves baseline analysis available. An
invalid bundle cannot replace the previous selection.

Never replace a published bundle. Publish a new immutable bundle and keep the
version and manifest digest aligned in:

- `base/charts/pii-engine/values.yaml`;
- `base/charts/pii-engine-model-sync/values.yaml`;
- `base/releases/pii-engine/app.yaml`;
- `base/releases/pii-engine-model-sync/app.yaml`.

## Configuration Ownership

| Configuration | Owner |
| --- | --- |
| Platform policy defaults | `base/releases/shared/default-pii-settings.yaml` |
| Client-wide policy | `client_*/config/client.yaml` |
| PII Engine product values | `client_*/infrastructure/observability/pii-engine/values.yaml` |
| extProc product values | `client_*/infrastructure/observability/agentgateway-extproc/values.yaml` |
| Model destination policy | `client_*/infrastructure/networking/agentgateway/values.yaml` |
| MCP destination policy | `client_*/config/client.yaml` under `mcp.servers` |

Policy and model bundle pins are non-secret. Runtime TLS keys, hash and
encryption keys, and Valkey credentials are secrets supplied through OpenBao.
Rook creates the object-store credentials used by model sync.

## Security Boundaries

- PII Engine workload traffic uses mTLS.
- Studio API performs human authorization and does not forward browser tokens.
- Reversal plaintext is available only to the adapter request that needs it.
- Management endpoints rely on network isolation and have no application
  authentication.
- Normal logs and metrics contain bounded operational and aggregate entity data,
  not request values, spans, or reversal mappings.
- `DEBUG` logging may include exception text and request content. Enable it only
  for a short diagnostic window, then restore `INFO`.

This policy path does not cover direct Code Interpreter traffic or the private
RAG embedding listener. Review those paths separately before sending sensitive
documents.

## Verification

From the workspace root, run the owning repository checks after changing the
engine or adapter:

```bash
cd pii_engine
make check

cd ../agentgateway_extproc
make check
```

For deployment changes, render and validate the `base/` charts and release
contracts. Test the complete contract through AgentGateway, including disabled
destinations, terminal decisions, transformations, streaming responses, and
malformed placeholders.
