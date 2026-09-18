# Docling Attachments

Status: [Base PR #185](https://github.com/neurwerk/k8s_stack_base/pull/185) merged
wiring and image pins at `5c9e0c8c3e9a39cca8b9405c716d43bf805f80f4`.
PII Engine `0.9.0` and extProc `0.8.0` have been observed live and Ready through
the Base alpha source. The CPU Docling backend is deployed, and synthetic TXT and
PDF conversions followed by PII analysis passed with fresh request-local aliases.
Final model/upload activation remains disabled while an environment storage-health
check blocks dependent releases; end-to-end chat dispatch is not yet verified.

The staged [private image extension](image-attachments.md) adds preferred reader
names, version-two attachment policies and local face detection. It is not part
of published extProc `0.8.0` and does not enable existing clients automatically.
The document behavior below remains the published version-one baseline.

## Implementation Tracking

[Base #170](https://github.com/neurwerk/k8s_stack_base/issues/170) tracks the
cross-repository work. [extProc PR #29](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/29)
and [PII PR #15](https://github.com/neurwerk/k8s_stack_pii_engine/pull/15) are merged
and published as extProc `0.8.0` and PII Engine `0.9.0` (CPU and CUDA).
See [publication verification](../operations/image-releases.md#document-extraction-images)
for exact sources, digests and successful release workflows.

[Base #184](https://github.com/neurwerk/k8s_stack_base/issues/184) tracks the merged
integration above; alpha service readiness does not establish stable publication.
The remaining client adoption targets end-to-end CPU extraction; remote vision
inference has not been tested end to end.

The CPU service in [Base PR #175](https://github.com/neurwerk/k8s_stack_base/pull/175)
is merged, closing [#171](https://github.com/neurwerk/k8s_stack_base/issues/171).
Credential delivery is merged in [Base PR #177](https://github.com/neurwerk/k8s_stack_base/pull/177),
with the operator CLI in [Tooling PR #42](https://github.com/neurwerk/k8s_stack_tooling/pull/42).
Explicit standard CPU selection is merged in [Base PR #179](https://github.com/neurwerk/k8s_stack_base/pull/179),
with the CPU-aware CLI in [Tooling PR #44](https://github.com/neurwerk/k8s_stack_tooling/pull/44).

The initial mode consumer [extProc PR #28](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/28)
and chart producer [Base PR #174](https://github.com/neurwerk/k8s_stack_base/pull/174)
were merged on 2026-09-16; they did not enable extraction by themselves.

## Deployment Boundary

**Docling runs in its own CPU Pod inside Kubernetes.** Clients explicitly select
`docling.inference.mode: remote` (the default) or `cpu`. Remote mode calls the
operator's vision-model server; CPU mode runs standard OCR, layout and table
extraction inside the existing Pod. Neither mode needs a GPU on that Pod, and
there is no automatic failover or retry on the other mode.

The following flow applies to `extract` mode. `passthrough` instead forwards the
original request directly to the selected chat backend, without Docling or PII.

```text
LibreChat
  -> AgentGateway / extProc: authenticate, authorize, validate attachments
  -> Docling service (Kubernetes CPU Pod)
       -> parse document / render PDF pages
       -> remote: private vision-model endpoint
          OR cpu: local OCR, layout and table models
       -> assemble DoclingDocument JSON
  <- validated document result
  -> PII Engine only when enabled for the destination
  -> model-readable content
  -> selected chat model
```

The two service addresses have different purposes:

| Connection | Purpose | Configuration ownership |
| --- | --- | --- |
| Gateway processing -> Docling Kubernetes Service | Convert an allowed document into structured data | Platform service wiring |
| Docling -> GPU inference server (remote mode only) | Read rendered pages using a compatible vision-language model (VLM) | Client-owned URL, model settings and trust/auth references |

The client can set the GPU server IP/hostname and port later. "External" means
outside the Docling Pod, not a public processing provider. The model server can
be an OpenAI-compatible deployment such as vLLM or Ollama. Its actual model must
support image inputs and the selected Docling output format.

The operator owns the external server, targeting Granite-Docling-258M served by
llama.cpp, with matching model/projector files and `--special` so DocTags are not
stripped from its output. The in-cluster worker uses upstream `docling-serve-cpu`,
avoiding a new first-party service repository. The disabled chart pins
[docling-serve v1.33.0](https://github.com/docling-project/docling-serve/releases/tag/v1.33.0),
whose lockfile selects `docling-slim 2.127.0`, `docling-core 2.96.1` and
`docling-jobkit 3.6.0`. The verified CPU index digest is
`sha256:546cf392145a0a578f23e4250663a37a5fb727fe6b57fd163e301584ad8bc18c`.
It includes amd64 and arm64; the amd64 manifest is
`sha256:e034edf2914d56503b6c968891e8c8cffb0b749708c42740052b8aab383e1bfa`,
and its revision label matches source `27fa2aa9638e449d7fcd4364ffcde8d9a47bc4eb`.
The earlier worker verification inspected registry metadata and pinned upstream
build/runtime source, without live extraction. Use the local task engine with no
UI or persistent queue. Remote mode keeps the fixed administrator-owned VLM preset.

### CPU Selection

```yaml
docling:
  inference:
    mode: cpu
```

Chart `0.2.0` uses the same pinned image and its baked Heron layout, TableFormer v1
accurate and RapidOCR ONNX models. `DOCLING_DEVICE=cpu` forces CPU execution;
runtime downloads stay off and no model volume or second server is added.
Remote services, configured VLM engines, inference-token/CA mounts and inference
egress are absent in CPU mode, even if unused remote settings remain in values.
The internal API key and HTTPS Service remain required.

Trusted gateway CPU requests select `pipeline=standard`, `ocr_preset=rapidocr`,
`do_ocr=true` and `do_table_structure=true`, with enrichment flags false and
`ocr_lang` unset. This uses the baked default OCR checkpoint; other language or
model selections may need artifacts not in the image. Native legacy VLM options
still exist, so these settings are not a universal standard-only API filter.
Only trusted gateway code may choose conversion options.

CPU results can differ from vision-model results and large documents may take
longer. Existing CPU, memory and time limits remain client-configurable. Selecting
CPU alone does not enable uploads or complete client activation.

## Document Conversion

`extract` accepts PDF, DOCX, XLSX, PPTX, UTF-8 text, Markdown and CSV, including
attachments in history. Chat Completions uses `type: file` with `file.filename`
and `file.file_data`; Responses uses `type: input_file` with `filename` and
`file_data`. Data must be an exact MIME/extension-matched
`data:<mime>;base64,<bytes>` URI with strict base64, not a URL, file ID, raw base64
or extra reference. All files pass preflight checks before any submission.
Standalone images, audio and video are unsupported and return HTTP 403.

The verified-HTTPS client submits one multipart file at a time using native
`POST /v1/convert/file/async`, polls `GET /v1/status/poll/{task_id}`, then fetches
`GET /v1/result/{task_id}`. This is internal job handling, not a new UI or durable
queue. Submissions are never retried. Only the service API key is sent, never
caller credentials, options, URL sources or callbacks. Output is in-body JSON;
image exports and enrichments are off. Plain text uses the Markdown backend.

Only successful, error-free, nonempty `document.json_content` results with
`DoclingDocument` schema `1.10.0` are accepted. A strict reference walk collects
body/furniture text, table rows and picture captions. Broken references, cycles,
orphaned content, unsupported structures and incomplete PDF page sets reject the
whole request. Checkbox labels keep `[x]` or `[ ]`; formulas without nonempty
canonical text are rejected, never recovered from `orig`.

Each document becomes one complete text part (`text` for Chat, `input_text` for
Responses). Only its display filename survives as source metadata; Docling receives
a constant `upload.ext` name. Images, embedded objects, `orig`, source URLs and
other metadata are not forwarded. There is no truncation, partial-result dispatch,
raw fallback, line/cell reconstruction, RAG or embedding path.

Each extProc process admits one active batch with no waiting queue. Cancellation
or the batch deadline stops later files but holds admission until the in-flight
native job or preflight work finishes. If submission/status replies are lost,
conversion stays locked in that process: an operator must check native jobs before
restarting it. This does not fail health/readiness or trigger automatic restarts.
extProc shutdown drains for at most five seconds; crashes, restarts and overlapping
rollouts can leave native jobs running. This is not a global or persistent limit.

## Disabled Service Package

Base owns `charts/docling/` and these optional, excluded packages:

- `releases/namespaces/docling`: namespace and default-deny policy.
- `releases/docling/secret-sync`: remote-mode credential delivery, including the inference token.
- `releases/docling/secret-sync/internal`: CPU-mode delivery of only the internal API key and its extProc copy; select this or the remote package, not both.
- `releases/docling/reloader`: opt-in values extending the existing Reloader's
  watch list and scoped RBAC to `docling`; no second controller.
- `releases/docling/app`: HelmRelease, local defaults and shared attachment limits.

None is part of normal stage composition. `docling.enabled` defaults to false.
For later client composition, create the namespace first, project the enabled
flag into certificate approval and extProc values, and reconcile the optional
Reloader values and controller before starting Docling. An already-Ready Reloader
does not prove it has consumed newly created values; verify that reconciliation.

The service uses native HTTPS on Pod port 5001 through ClusterIP port 443. Its
rotating `docling-tls` certificate uses the exact internal approval profile in
namespace `docling`. Ingress admits only extProc and the cleanup job. Remote
inference egress uses explicitly configured RFC1918 IPv4 CIDRs and the matching HTTPS port;
DNS names alone are not a network allowlist. The optional inference CA ConfigMap
contains `ca.crt` and sets `REQUESTS_CA_BUNDLE`, replacing Requests' root bundle.

`docling.apiKeySecretRef` supplies the private service's `X-Api-Key` credential.
In remote mode, `docling.inference.tokenSecretRef` supplies a separate upstream
Bearer credential. The remote secret-sync package delivers `docling-api:api-key` and
`docling-inference:token` in the Docling namespace. extProc receives only a copy of
the service API key in `monitor-agentgateway-extproc-docling-secret:api-key`.
Its OpenBao role cannot read the Docling namespace's upstream token.

The CPU-aware operator CLI is `openbao-stack-setup` `0.2.16` from Tooling revision
`269b8c09190df8bd7b775ff7ef202964d3fe2703`. Its canonical selector is
`docling.enabled: true` in `docling/docling-product-values`, with the exact Secret
references above. This permits credential-only staging: compose the namespace,
values and secret-sync resources, but leave the application package unselected.
Other namespaces' shared enable flags and attachment modes stay unchanged.
Secret-sync can remain NotReady until the operator completes setup; normal
applications must not depend on its readiness at this stage.
See [Docling credential setup](../operations/openbao.md#optional-docling-credentials)
for the reconciliation and hidden-prompt commands. No manual Secret manifests
belong in client repositories, and credential staging does not enable extraction.

A small mounted startup script injects the remote-mode upstream token into the custom
`default` preset before importing Docling. Upstream has no native config-file
environment substitution. The script disables Python logging through CRITICAL,
including error-response bodies, and runs Uvicorn with no access log. Only fixed
startup failure text is emitted. This trades library diagnostics for content
privacy; direct native-library stderr and the external server's logging remain
separate concerns. Offline model settings prevent downloads, not arbitrary local
pipeline execution by an authenticated caller: trusted extProc must supply fixed
options, and no browser receives the service API key.

The Pod has one worker and converter cache, UID 1001, no Kubernetes API token,
no GPU resources, read-only root and bounded disposable `/scratch` and `/tmp`
volumes. Its probes check the local lifecycle, not remote model availability.
Uvicorn has no server-wide concurrency cap: that cap also rejects health probes
when conversions occupy the listener. Conversion admission belongs in the gateway,
before calling Docling, and is implemented in extProc `0.8.0`. Adopt the compatible
consumer before enabling this disabled service. One native worker alone does not
bound waiting requests or the task queue.
Defaults request a 300-second document budget, 90-second model calls and a
360-second wait setting, also used for extProc's whole batch deadline. Native
retries and page-batch checks can exceed worker budgets; these are not hard
job-cancellation guarantees. extProc uses async polling, not synchronous conversion.

On normal shutdown, Uvicorn stops accepting connections and drains in-flight HTTP
requests for up to `syncWaitSeconds`. Pod termination grace is derived from that
value plus 30 seconds for cleanup (390 seconds by default). The HelmRelease uses
a 70-minute ceiling to cover the largest permitted override (3660 seconds), cleanup
and the five-minute startup probe budget. This is a maximum wait, not a fixed
rollout delay. Native jobs can outlive an HTTP timeout; force deletion, crashes and
work exceeding these budgets are not guaranteed to finish during shutdown.

Fetched results have a 60-second removal delay. A scoped, nonconcurrent CronJob
every five minutes clears completed results older than 600 seconds using the
native authenticated cleanup API and verified TLS. It never deletes LibreChat
files or cancels active jobs. Certificate and credential changes require the
configured Reloader watch; failed cleanup must remain visible as Job failure.

PDFs use either the selected remote VLM or standard CPU pipeline. Formats such as
DOCX, XLSX, PPTX, plain text, Markdown and CSV use their format-specific parsing paths; they are
not automatically sent as whole files to the vision endpoint. This is not a
generic URL override for every traditional OCR backend.

## Why Chat Completions

In remote mode, Docling uses `POST /v1/chat/completions` to send rendered page
images and an extraction instruction to the vision server. This protocol supports
images as well as text. The preset defines the expected response, such as DocTags
for Granite-Docling; Docling turns it into `DoclingDocument` JSON.

Using the same URL path does not mean using the same hostname, credentials or
model as normal chat. Docling calls the private GPU endpoint directly, not the
public AgentGateway chat route. Do not loop extraction back through the gateway's
attachment handler or change user attachment modes to allow these internal calls.

## Remote Pipeline Configuration

The researched version provides:

- `VlmPipeline` with `VlmPipelineOptions` for page-based VLM conversion.
- `VlmConvertOptions.from_preset(...)` for the model instruction/output contract.
- `ApiVlmEngineOptions` for `engine_type`, full endpoint `url`, `params` including
  the served model name, authentication `headers`, `timeout` and `concurrency`.
- `enable_remote_services=True`, required to permit the API engine's calls.

The endpoint normally ends in `/v1/chat/completions`. This is a GPU inference
endpoint, not the base URL of a remote Docling conversion server. Use the explicit
API engine; do not silently fall back to loading the vision model in the CPU Pod.

Enabling remote services is not an endpoint allowlist. Limit network access to
the approved internal destination, verify TLS and authenticate both service hops.
Keep credentials in Secrets and only non-secret values/references in client
configuration. Do not let uploaded documents or browser parameters choose the
inference URL, model or authentication headers.

## PII And Attachment Rules

Each model has an independent `attachmentMode`. Model routing, attachment handling,
PII processing and content tracing remain separate controls:

| Mode | PII enabled | PII disabled |
| --- | --- | --- |
| `block` (default) | Reject typed attachments with HTTP 403 | Reject typed attachments with HTTP 403 |
| `extract` | Validate/extract allowed documents, then apply PII policy | Validate/extract allowed documents without PII |
| `passthrough` | Invalid configuration | Forward original request and provider response unchanged, without extraction or PII |

Ordinary or LibreChat-extracted text follows the existing PII setting regardless
of attachment mode. Passthrough is an explicit grant, never implied by disabling
PII and never selected after extraction or PII fails. It does not imply local
hosting, disable tracing, or guarantee native attachment support in the backend.
Existing request-size and protocol limits still apply; extProc does not fetch
file/image URLs on the passthrough path. Downstream handling remains the backend's
responsibility. A failed or incomplete extraction, or required PII failure/block,
stops the entire request without forwarding the original as a fallback.

For PII-enabled extraction, extProc sends the whole canonical converted Chat or
Responses request once to `POST /v1/adapter/analyze-document-request` over the
existing adapter mTLS connection. PII Engine uses a fresh request scope, with no
session-cache reuse or persistence; the existing request and reply contracts and
policy allow/transform/reroute/block behavior remain. Mutation and reversal checks
use the converted request. There is no separate PII call per line or table cell,
and PII split across those boundaries may be missed. Ordinary text-only bypass,
tool JSON and MCP behavior are unchanged.

### Configuration And Compatibility

The chart setting is `guardrails.llmPolicyEngine.models[].attachmentMode`, keyed
by the model's public `name`. The version-1 trusted metadata retains the existing
`models` ID-to-PII-boolean map and adds an optional sparse `attachment_modes` map.
Unknown modes/IDs and passthrough combined with enabled PII fail closed at the
consumer. Chart validation rejects invalid modes and the same PII combination.

Chart `1.3.0` source omits the new map when no effective model explicitly configures
a mode, preserving default renders for shipped extProc. **Deploy the new extProc
consumer before configuring any explicit mode, including `block`.** Older strict
consumers reject the new metadata field rather than ignore it. Omitted modes default
to block in the new consumer; this does not retroactively change older runtimes.
Extraction needs both service versions, the merged Base wiring and client activation.
Phase gateway model settings and the LibreChat upload flag only after compatible
consumers and the private Docling service are ready.

Selected catalog rows may carry an explicit mode, but keep their PII-enabled
default. Clients should use the existing direct-model values/whole-list override
mechanism rather than manually edit generated catalogs. A same-name direct model
replacement can explicitly disable PII and opt into passthrough; it does not
inherit a catalog attachment mode. These settings never grant model permissions.

With PII disabled, the model receives the converted body without PII state or guard
injection. Extracted text may contain personal information and is not PII-sanitized.
`contentTracingEnabled` remains a separate, unchanged model setting: when enabled,
model traces may retain prompts and completions, including extracted text.

In remote mode, the extraction model receives unredacted page images before PII
analysis. It is part of the trusted internal processing boundary. "Blocked jobs
never reach models" means no downstream chat-model or embedding dispatch after a
block; it cannot mean no prior internal extraction-model inference. No RAG or
embedding service is part of this feature.

The extraction and document-PII hops keep raw content and filenames out of logs
and traces, including errors. Keep Docling's content-bearing library logs suppressed
and backend resource fetching disabled. PDF resource isolation is not a full
security sandbox, and schema checks cannot prove OCR completeness or PII detection
quality; worker resources and network restrictions remain necessary.

## Bounds And Deadlines

`releases/shared/document-attachments.yaml` defines `documentAttachments.fileBytes`
(20 MiB), `totalBytes` (40 MiB), `count` (5) and `pages` (200). Client-wide overrides
belong in canonical client values projected into the consuming namespaces. Count,
total bytes, pages and the conversion deadline apply to the whole batch, including
history. Raising upload limits does not raise converted-output limits.

| Boundary | Limit or check |
| --- | --- |
| Uploads | 20 MiB per file; 40 MiB, 5 files and 200 pages per batch by default |
| Filename | At most 256 characters, no controls; retain only the display basename |
| PDF inspection | Valid, unencrypted PDF; isolated helper with 256 MiB address space, 5-second CPU and 10-second parent deadline; kill/reap on timeout, no temporary files or parser output |
| Office ZIP | 100 MiB expanded total, 25 MiB per entry, 10,000 entries; safe paths, no encryption, required OOXML parts; never unpack to disk |
| XLSX / CSV | 100,000 positions, including sparse cells and ranges; XLSX streaming XML rejects DTDs and caps depth at 32 and elements at 200,000; CSV delimiter/quote counts and row/column product are bounded |
| Docling output | 16 MiB JSON response; schema `1.10.0`, 20,000 graph nodes, depth 32 and 100,000 table positions/reference visits |
| JSON parsing | Incoming request, Docling result and PII reply: depth 64, 200,000 lexical tokens before tree allocation; reject duplicate keys and non-finite numbers |
| Converted request | 5 MiB serialized and 4,000,000 text characters across the whole request, even with PII off; no truncation |
| Upload transport (Docling enabled) | Gateway `maxBufferSize: 67108864` as integer bytes, **not** `64Mi`; extProc request 64 MiB and gRPC envelope 68,222,976 bytes |
| extProc resources (Docling enabled) | Two fixed Pods, no HPA; one batch per process, four concurrent gRPC RPCs per Pod; memory request 1 GiB, limit 2 GiB |

Each Docling HTTP call has a fixed 30-second deadline; status replies are capped
at 64 KiB. extProc enforces the whole conversion-batch deadline (360 seconds by
default) and the whole PII call, including response reading (615 seconds in the
platform). Foreground waits are therefore bounded by 360 + 615 = 975 seconds.
AgentGateway 1.5's backend `requestTimeout` (1005 seconds by default with Docling enabled)
covers only initial gRPC response headers, **not** end-to-end processing. Native
jobs can outlive these waits; admission stays held as described above.

## Client Defaults And UX

Client product values supply `docling.inference.url`, `model`, `cidrs`, `port`,
optional `caConfigMap`, Secret references and service resources/time budgets.
Keep the full `/v1/chat/completions` URL separate from the internal Docling Service.

LibreChat sends raw documents where its existing provider-delivery settings allow
it; the file-provider fallback works without a legacy flag. Keep its stored
originals and GUI deletion behavior. Cleanup covers only temporary gateway/Docling
data; account for transient data on the inference server as well.

`frontendLibrechat.documentAttachments.enabled` defaults to false. When selected,
the shared chart emits native `fileConfig.endpoints.AgentGateway` provider-delivery
settings and the document MIME allowlist, converting shared byte caps to numeric
MiB. It does not select model attachment modes or activate Docling, and does not
change the app image, stored originals, GUI deletion or normal waiting behavior.

The pinned upstream LibreChat skips DOCX, XLSX and PPTX for `claude`-named models
before the request reaches the gateway. Use PDF or text for those models. Do not
add a fork or a `nativeText` override: upstream local extraction does not support
PPTX and can truncate text, so it cannot guarantee complete document delivery.

Use LibreChat's normal waiting behavior, with no custom upload API, progress UI or
durable document store. Run existing repository checks; no separate acceptance-test
campaign or GPU test environment is required. These checks do not establish OCR
quality, remote-vision behavior or comprehensive PII leak resistance.

## Sources And Related Docs

- [Docling remote vision models](https://github.com/docling-project/docling/blob/v2.127.0/docs/usage/vision_models.md#remote-models)
- [Docling API engine options](https://github.com/docling-project/docling/blob/v2.127.0/docling/datamodel/vlm_engine_options.py)
- [Docling API inference engine](https://github.com/docling-project/docling/blob/v2.127.0/docling/models/inference_engines/vlm/api_openai_compatible_engine.py)
- [Docling image request implementation](https://github.com/docling-project/docling/blob/v2.127.0/docling/utils/api_image_request.py)
- [llama.cpp special-token output option](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
- [LibreChat](librechat.md)
- [PII policy engine](pii-policy-engine.md)
- [Network isolation](networking.md)
