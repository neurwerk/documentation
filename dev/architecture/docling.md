# Docling Attachments (Planned)

Status: agreed design, not an implemented or deployed platform capability.
Upstream API behavior was checked against Docling `2.127.0`; the final Docling,
model and runtime pins remain implementation work. No server address or port is
needed to begin implementation.

## Deployment Boundary

**Docling runs in its own CPU Pod inside Kubernetes. The document-reading vision
model runs on the internal GPU VM and is called by Docling over an API.** Do not
deploy the whole Docling service on that VM or require a GPU on the Docling Pod
for this design.

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
attachment handler or relax its user-image block to allow these internal calls.

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

Document handling is independent of the destination's `piiEnabled` setting:

| Input | PII enabled | PII disabled |
| --- | --- | --- |
| Allowed raw document | Validate, extract, apply PII policy, dispatch if allowed | Validate, extract, dispatch without PII Engine calls |
| Ordinary or LibreChat-extracted text | Apply existing PII policy | Existing text-only bypass |
| Image, audio, video or unsupported file | Reject | Reject |
| Failed, timed-out or incomplete conversion | Reject; no raw fallback | Reject; no raw fallback |
| PII failure or block | Reject | No PII dependency |

The initial raw-document allowlist is PDF, DOCX, XLSX, PPTX, plain text, Markdown
and CSV. A scanned PDF may produce internal page images for extraction; a user
image attachment remains unsupported. Strip image payloads, embedded objects,
source-file URLs and hidden raw copies before preparing the chat-model request.
With PII disabled, retained text may contain personal information and must not be
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
code changes. Agreed starting limits are 20 MiB per file, five files and 40 MiB
total per request, and 200 pages total for paged documents. Client settings also
control the remote inference endpoint/model and operational time/resource limits.
Keep upload, decoded-byte and extracted-content limits distinct.

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
