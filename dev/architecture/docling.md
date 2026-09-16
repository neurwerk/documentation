# Docling Attachments (Planned)

Status: agreed design, not an implemented or deployed platform capability.
Upstream API behavior was checked against Docling `2.127.0`; the final Docling,
model and runtime pins remain implementation work. No server address or port is
needed to begin implementation.

## Implementation Tracking

[Base #170](https://github.com/neurwerk/k8s_stack_base/issues/170) tracks the
cross-repository work. The first implementation is
[extProc PR #28](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/28):
typed Chat/Responses attachments, including history, follow a per-model mode
independently of PII. Missing modes default to `block`; explicit `passthrough`
requires PII disabled. `extract` fails closed with HTTP 503 for file parts until
conversion is implemented; other attachment types return 403 in that mode.
This preserves ordinary text-only bypass, arbitrary tool JSON and MCP behavior.
It is a review-stage change, not a published image or deployed platform feature.

The remaining bounded tasks are:

- [Gateway conversion #27](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/issues/27).
- [Document PII contract #14](https://github.com/neurwerk/k8s_stack_pii_engine/issues/14).
- [CPU service and client-overridable defaults #171](https://github.com/neurwerk/k8s_stack_base/issues/171).
- [Per-model chart PR #174](https://github.com/neurwerk/k8s_stack_base/pull/174), implementing [#173](https://github.com/neurwerk/k8s_stack_base/issues/173).

## Deployment Boundary

**Docling runs in its own CPU Pod inside Kubernetes. The document-reading vision
model runs on the internal GPU VM and is called by Docling over an API.** Do not
deploy the whole Docling service on that VM or require a GPU on the Docling Pod
for this design.

The following flow applies to `extract` mode. `passthrough` instead forwards the
original request directly to the selected chat backend, without Docling or PII.

```text
LibreChat
  -> AgentGateway / extProc: authenticate, authorize, validate attachments
  -> Docling service (Kubernetes CPU Pod)
       -> parse document / render PDF pages
       -> private GPU inference endpoint (internal VM)
       <- extracted page content
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
| Docling -> GPU inference server | Read rendered pages using a compatible vision-language model (VLM) | Client-owned URL, model settings and trust/auth references |

The client can set the GPU server IP/hostname and port later. "External" means
outside the Docling Pod, not a public processing provider. The model server can
be an OpenAI-compatible deployment such as vLLM or Ollama. Its actual model must
support image inputs and the selected Docling output format.

The operator owns the external server, targeting Granite-Docling-258M served by
llama.cpp. The in-cluster worker can use upstream `docling-serve-cpu`, avoiding a
new first-party service repository. The researched candidate is
[docling-serve v1.33.0](https://github.com/docling-project/docling-serve/releases/tag/v1.33.0),
whose lockfile selects `docling-slim 2.127.0` and `docling-core 2.96.1`; the image
digest is not yet verified or adopted. Use the local execution engine with no UI
or persistent queue, and a fixed administrator-owned remote VLM preset.

The gateway constructs conversion options rather than forwarding caller options:
one uploaded file, in-body JSON output, no URL sources or callbacks. Upstream
returns the document under `document.json_content` in a status/error envelope.
Its synchronous wait timeout does not cancel the underlying job; worker deadlines,
bounded admission and cleanup must account for that, without blind retries.

PDFs use the remote VLM conversion pipeline. Formats such as DOCX, XLSX, PPTX,
plain text, Markdown and CSV use their format-specific parsing paths; they are
not automatically sent as whole files to the vision endpoint. This is not a
generic URL override for every traditional OCR backend.

## Why Chat Completions

`POST /v1/chat/completions` is a request/response protocol, not a text-only model
or a specific server. Its multimodal message format can carry text and images.
Docling's API engine uses this protocol for document reading, rather than for a
conversation with the end user.

An illustrative request body, with image bytes omitted, is:

```json
{
  "model": "ibm-granite/granite-docling-258M",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {"url": "data:image/png;base64,<page-bytes>"}
        },
        {"type": "text", "text": "Convert this page to docling."}
      ]
    }
  ]
}
```

The GPU server returns generated content in the Chat Completions response. A
matching Docling preset defines the extraction instruction and expected format,
for example DocTags for Granite-Docling. Docling parses that content and builds
the `DoclingDocument`; the GPU server need not return that JSON schema directly.

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
Neither PR publishes or pins a new extProc image.

Selected catalog rows may carry an explicit mode, but keep their PII-enabled
default. Clients should use the existing direct-model values/whole-list override
mechanism rather than manually edit generated catalogs. A same-name direct model
replacement can explicitly disable PII and opt into passthrough; it does not
inherit a catalog attachment mode. These settings never grant model permissions.

The initial extraction allowlist is PDF, DOCX, XLSX, PPTX, plain text, Markdown
and CSV. In `extract` mode, standalone images/audio/video remain unsupported; a
scanned PDF may produce internal page images. The extraction path strips image
payloads, embedded objects,
source-file URLs and hidden raw copies before preparing the chat-model request.
With PII disabled, extracted text may contain personal information and must not be
described as PII-sanitized. With PII enabled, preserve the existing policy's
allow/transform/reroute/block behavior, rather than inventing mandatory redaction.

The GPU extraction model necessarily receives unredacted page images before PII
analysis. It is part of the trusted internal processing boundary. "Blocked jobs
never reach models" means no downstream chat-model or embedding dispatch after a
block; it cannot mean no prior internal extraction-model inference. No RAG or
embedding service is part of this feature.

Keep page images, extraction output, prompts and filenames out of logs and traces
on both service hops, including error paths. The researched Docling API helper
can log response bodies on errors and a request payload at debug level. Normal
log levels alone are insufficient; suppress/filter content-bearing library logs.
Its non-streaming error path can return empty output instead of raising, so a
completed HTTP call alone must not be treated as successful extraction.

## Client Defaults And UX

Base supplies validated defaults; client repositories may override them without
code changes. Planned extraction limits are 20 MiB per file, five files and 40 MiB
total per request, and 200 pages total for paged documents. Client settings also
control the remote inference endpoint/model and operational time/resource limits.
Keep upload, decoded-byte and extracted-content limits distinct. These new
extraction limits are not yet implemented and do not expand the current transport
limits for passthrough.

LibreChat should send raw documents where its existing provider-delivery settings
allow it. Local text extraction is acceptable. Keep its stored originals and GUI
deletion behavior. Delete only this feature's temporary gateway/Docling data;
account for transient data on the inference server as well.

Use LibreChat's normal waiting behavior. Do not add a custom upload API, progress
display, durable document store or LibreChat fork upfront. Keep new tests focused
on configuration and blocked/Docling/PII dispatch, including failure without raw
fallback. Run existing repository checks; no separate acceptance-test campaign
or GPU test environment is required. Reduced tests do not establish OCR quality
or comprehensive PII leak resistance.

## Sources And Related Docs

- [Docling remote vision models](https://github.com/docling-project/docling/blob/v2.127.0/docs/usage/vision_models.md#remote-models)
- [Docling API engine options](https://github.com/docling-project/docling/blob/v2.127.0/docling/datamodel/vlm_engine_options.py)
- [Docling API inference engine](https://github.com/docling-project/docling/blob/v2.127.0/docling/models/inference_engines/vlm/api_openai_compatible_engine.py)
- [Docling image request implementation](https://github.com/docling-project/docling/blob/v2.127.0/docling/utils/api_image_request.py)
- [LibreChat](librechat.md)
- [PII policy engine](pii-policy-engine.md)
- [Network isolation](networking.md)
