# Face Policy And Phone Photos

Status: source merged on 2026-09-18, with green Required CI:

- [PII Engine #17](https://github.com/neurwerk/k8s_stack_pii_engine/pull/17), `bf98781`.
- [extProc #35](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/35), `2e3fbda`.
- [Base #205](https://github.com/neurwerk/k8s_stack_base/pull/205), `6d06a97`.

Parent [Base #203](https://github.com/neurwerk/k8s_stack_base/issues/203) and both
service issues are closed. AgentGateway chart `1.6.0` and LibreChat shared chart
`1.5.0` are on Base `main` (alpha source), not stable `v0.3.8`.
This is not a service release, deployment, or client activation. Base still pins
PII Engine and extProc `0.9.0`; those images cannot use this contract.

The [published image baseline](image-attachments.md) remains unchanged until
operators explicitly select attachment policy version three. This page defines
the new behavior alongside the existing [Docling](docling.md) and
[PII Engine](pii-policy-engine.md) contracts.

## Processing

1. Validate and normalize each supported image locally.
2. Run CPU YuNet when face protection is enabled, even for text-only forwarding.
3. Extract text through the configured CPU OCR or qualified private reader.
4. Send converted text and trusted face counts to PII Engine, never pixels.
5. Enforce the central action and the destination's existing forwarding permission.

The supported standalone formats are JPEG, PNG and HEIC/HEIF still photos.
Inline Chat `image_url` and Responses `input_image` parts are supported,
including history; the optional standard `detail` hint is validated and ignored.
URLs, file IDs, animations, multiple independent photos and other image formats
are rejected on the processed API path. Explicit passthrough keeps its separate,
byte-preserving contract and does not gain any privacy inspection.

CPU extraction uses the existing standard/RapidOCR pipeline, not another service.
Handwriting quality is not promised. Native Docling submissions use
`from_formats=image`; this source also corrects the erroneous `img` value in the
published v2 client. The private reader's image preset remains `scale: 1.0` and
`max_size: null`; it must not resize the canonical image again.

## Phone Images

V3 accepts at most 20 MiB source bytes, 50 million source pixels and 10,000 pixels
per dimension, subject to smaller configured limits. One bounded normalization
reduces large images to at most 2 million pixels and 2048 pixels per dimension.
Protected images must remain at least 64 pixels in each dimension. OCR, face
detection and permitted forwarding all receive this same RGB PNG, not a separate
low-resolution detector view.

Orientation is applied, transparency uses white, and metadata is discarded.
HEIF decoding uses pinned, offline `pi-heif` wheels and their decoder-only native
libraries. Higher-bit-depth HEIF becomes 8-bit; gain-map HDR, depth information
and auxiliary payloads are not forwarded. Independent photos and timed tracks
are rejected rather than selecting a frame. Package licenses are recorded in
extProc's `THIRD_PARTY_NOTICES.md`; its test encoder is not installed at runtime.

The existing 5 MiB canonical PNG and aggregate base64-URI limits still apply,
as do request, batch, text and final-body limits. A busy or oversized request can
still be rejected. The helper retains its 768 MiB address-space, 10 CPU-second
and 15-second parent limits, with kill/reap on timeout and no persistent images.

Resizing can make small faces and text harder to detect. A completed scan with
zero detections is not proof that an image contains no personal information.
No face recognition, identity storage, embeddings, face blurring or image
redaction is introduced.

## Central Policy

After compatible services are deployed, the optional setting is:

```yaml
monitorPiiEngine:
  policy:
    attachments:
      faces:
        action: block # block | text-only | reroute
        # routeClass: local/vision # only with reroute
```

The new Engine defaults to `block` when this setting is absent. Base deliberately
does not emit `faces` in shipped defaults because the old Engine rejects it.

| Action | Result |
| --- | --- |
| `block` | Reject the whole request with HTTP 403. |
| `text-only` | Withhold all request images and send the checked extracted text. |
| `reroute` | Send images only through an explicitly approved local vision route. |

Text blocks always win. Different text and face reroute classes block rather
than choosing a destination. Required inspection failures block without a raw,
public-provider or alternate-reader fallback. An omitted face route uses
`routing.defaultTarget`; route classes are bounded to 128 safe characters.

A complete valid image conversion with no text uses the fixed adapter marker
`[Image: no text extracted]`, not a fabricated PII finding. Such images cannot
complete text-only handling or conditional remote forwarding. They can reach an
approved local image reroute or an explicitly permitted unchecked local model.
Empty ordinary documents and failed or incomplete conversions still reject.

## Trusted Contract

Only the adapter mTLS identity can submit the new document envelope:

```json
{
  "api_version": "v1",
  "request": {"model": "example", "input": "Converted attachment text"},
  "text_pii_enabled": true,
  "visual_findings": {"faces": {"scan_status": "complete", "count": 2}}
}
```

ExtProc constructs these fields from trusted settings and its detector, not
caller findings. `complete` requires a bounded integer count; `not_scanned` and
`failed` require null. The Engine echoes the findings and extProc verifies the
echo. Missing, failed and zero-count scans are not interchangeable. Counts are
detections across images, not unique people. Findings use fresh request-scoped
analysis and are never cached.

Turning text PII off does not turn face protection off. Text scan metadata stays
honest, and no clean-text PII header is emitted for a skipped text scan. The
legacy bare document request and reply shapes remain accepted without the new
field. Studio, MCP and ordinary analysis endpoints do not accept this envelope.

## Local Routing

Opt-in `guardrails.llmPolicyEngine.attachmentPolicyVersion: 3` retains the v2 maps
and adds `image_models` and `image_reroutes`. The first requires explicit
`supportsImages: true` and a concrete local backend. The second binds the source
model and exact route class to the actual approved local image destination.
Each map is bounded to 16 KiB. V1/v2 reject these new fields and capability options.

The producer follows the same ordered exact/prefix rules as actual gateway
routing. It cannot skip an earlier matching text-only local target in favor of
a later vision target. Fallback bindings identify the generated local backend,
not a guessed model name. Named targets retain their own permission checks;
dedicated fallbacks retain the source permission. These maps grant no access.

Missing approval or image capability blocks image forwarding. `imageForwarding:
none` never gains pixels through rerouting. Conditional external forwarding
still rejects original text PII findings, even if extracted text was masked.
V3 unchecked forwarding additionally requires explicit local image capability.

`Qwen3-VL-8B-Instruct` is the recommended simple local chat candidate for a 32 GB
VRAM budget with bounded context and concurrency. No model is deployed or
selected by default. The private Docling extraction model remains separate and
must satisfy its own output contract.

## Reports And Chat

Face findings use the existing `PII Engine Notice` and Entity/Request/Response
table. The row names the actual action and detected count, with zero face
transformations. Text-only reports withheld images; approved reroutes report
unmasked local delivery. Blocks never claim that images were forwarded.
Zero counts do not create an invented entity row; scan status remains visible.
Successful JSON/SSE placement and structured-output/MCP suppression are retained.

Blocked image requests remain real HTTP 403 errors, with a standard safe
`error.message` and structured `pii_report`. The pinned LibreChat renders errors
as plain text, can shorten them, and can replace protected provider errors.
The API report is available, but a formatted blocked-error table in the chat UI
is not promised. There is no UI fork or fabricated successful assistant answer.

The separate, disabled `frontendLibrechat.documentAttachments.imagesEnabled`
setting requires document uploads and v3. It permits JPEG/PNG/HEIC selection and
chooses PNG storage output. Pinned LibreChat converts HEIC to JPEG in the browser,
then resizes and converts stored images on the server; animation may be flattened
before the gateway. Gateway findings describe the delivered still pixels, not
every frame or original container. Original-container rejection applies only
when the API receives the original bytes. Live browser/storage delivery remains
unverified; enabling the chart option does not itself establish end-to-end use.

## Adoption

Merge compatible source, then separately authorize publication and verify both
service images before pinning them in Base. Deploy compatible Engine and extProc
before adding face configuration or emitting v3 metadata. Keep existing defaults,
permissions, private-reader selection and client values unchanged until explicitly
enabled. Restore v1/v2-compatible configuration before rolling back a consumer.
Source merges alone do not make this available in the pinned alpha runtime or
in an existing stable platform tag.

Validation uses the normal repository checks and focused regression cases.
Local Engine-to-extProc integration and rendered-metadata consumer checks verify
contracts, not live OCR accuracy, face-detection quality or cluster health.

At merge, both service `make check` commands passed: extProc had 900 passing cases;
Engine had 454 passing cases and three existing opt-in model skips. Base passed
`mise exec -- make check` and `mise exec -- make release-check`, including 121
chart tests, 10 offline safety tests and 87 platform cases with two standard tag
skips. Its rendered v1/v2/v3 catalogs passed the real extProc consumer check.
A local in-process Engine/extProc probe passed 76 boundary, dispatch and invalid
reply checks; pinned Docling source verification also confirmed the native image
format and CPU pipeline. No cluster, live model or browser test was performed.
