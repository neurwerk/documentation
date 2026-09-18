# Private Image Attachments

Status: source merged on 2026-09-18 in
[extProc #31](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/31)
(`c55e7d3`), [Tooling #49](https://github.com/neurwerk/k8s_stack_tooling/pull/49)
(`f930907`) and [Base #195](https://github.com/neurwerk/k8s_stack_base/pull/195)
(`3a4a0a6`), tracked by [Base #193](https://github.com/neurwerk/k8s_stack_base/issues/193).
Required CI passed for all three; local Base checks pass on the committed tree.

The chart changes are available in Base `main`, the alpha source, not stable
`v0.3.8`. Published extProc `0.8.0` and Tooling `0.7.0` predate these changes and
their Base pins are unchanged. Image processing therefore still needs separately
published/verified runtimes, pin adoption and explicit v2 activation. Existing
client values and permissions are unchanged. No cluster reconciliation or live
reader verification was performed for this merge. The existing
[document pipeline](docling.md) remains the version-one runtime contract.

## Responsibilities

```text
supported attachment
  -> bounded local validation and image normalization
  -> trusted text extraction
  -> existing text PII analysis, when enabled
  -> text-only output, or explicitly permitted normalized image output
```

Extraction, privacy analysis and forwarding are independent responsibilities.
There is no image redaction, face recognition, identity database or new PII API.
YuNet performs face detection only. Ordinary document formats and text policy
actions remain supported.

## Reader Selection

The preferred shared configuration is:

```yaml
docling:
  enabled: true
  inference:
    mode: internal-standard # internal-standard | private-vlm
    # Existing private URL, model, Secret references, TLS and timeout settings.
```

`internal-standard` uses document parsing and RapidOCR inside the Docling worker.
`private-vlm` calls a separately hosted, trusted vision-language model. The old
`cpu` and `remote` names remain transition aliases. Existing shipped defaults
remain unchanged, and Base translates preferred names to those old values in the
extProc environment so the staged chart alone does not break published consumers.
Tooling accepts both name pairs and preserves the existing managed Secret contract.

PDFs use the selected pipeline. Office and text formats use their format-specific
parsers. There are no GPU, OCR or handwriting switches: the selected reader and
model determine those capabilities. A compatible model and representative
handwriting results must be established; a VLM label is not proof of quality.
Do not repeat operator-confirmed qualification for every client.

The initial processed standalone-image path requires `private-vlm`, including
text-only and local unchecked image output. The standard reader still supports
scanned PDFs. Raw local images without extraction remain an explicit passthrough
use case, not an automatic fallback.

The private Docling preset `images` uses `scale: 1.0` and `max_size: null`.
The existing `default` PDF preset retains scale 2. The image preset and compatible
consumer must both be deployed before image activation. Normalized images have no
DPI metadata, so the private reader receives the same decoded visible pixels
inspected locally and considered for forwarding. PNG re-encoding is allowed;
byte-for-byte identity across service encoders is not required. The inference
server's own model preprocessing is still part of reader qualification.

## Model Policy

These settings belong to each effective model, not to caller input:

```yaml
guardrails:
  llmPolicyEngine:
    # Rollout guard, default 1. Set only after compatible consumers are deployed.
    attachmentPolicyVersion: 2
    models:
      - name: remote/example
        # Existing provider, backend and authorization settings omitted.
        attachmentMode: process
        piiEnabled: true
        faceProtectionEnabled: true
        imageForwarding: if-no-pii-detected
```

| Setting | Meaning |
| --- | --- |
| `attachmentMode: block` | Default; reject attachments |
| `attachmentMode: process` | Locally process attachments before applying the output policy |
| `attachmentMode: extract` | Transition name for the same processing path |
| `attachmentMode: passthrough` | Explicitly preserve original request bytes without attachment normalization, extraction or privacy inspection |
| `imageForwarding: none` | Default; forward extracted text only |
| `imageForwarding: if-no-pii-detected` | Forward normalized images only when all required inspections succeed with no detected PII or faces |
| `imageForwarding: pii-unchecked` | Skip the image privacy gate, only for a proven concrete local destination |

`piiEnabled` retains its ordinary text meaning. Face protection defaults to true
for processed attachments, but does not run for `imageForwarding: none`.
Enabling protection does not grant image-forwarding permission.

Validation rejects conditional forwarding without both protection flags.
Non-`none` processed forwarding requires enabled private-VLM Docling.
`pii-unchecked` requires `faceProtectionEnabled: false` and a concrete configured
local backend with no `piiReroute` branch. It still performs extraction, optional
text PII processing, and normal request checks; it cannot override a policy block.
An actual backend must support images; current catalog metadata cannot prove that.

Passthrough is allowed on local or remote destinations, but requires PII and face
protection disabled and no explicit `imageForwarding`. The absence of a face flag
on legacy passthrough defaults to false. The backend owns URL/reference handling;
extProc does not fetch those references. Normal protocol and request limits apply.
Neither PII disabling nor a processing failure implicitly selects passthrough.

## Image Boundary

The first version accepts inline JPEG and PNG in Chat `image_url` or Responses
`input_image` parts, including history. It rejects external URLs, file IDs, extra
reference fields, MIME mismatches, unsupported formats, animation and multiple
frames on the processed path. PDFs and Office files remain text-only outputs;
original documents, embedded images and rendered PDF pages are not forwarded.

Before any reader submission, bounded preflight checks every attachment. A
resource-limited disposable helper applies orientation, composites transparency
onto white, and rebuilds RGB PNG pixels without source metadata or trailing data.
Only that normalized representation can reach the reader, detector or downstream
model. Caller parameters cannot choose the reader, detector or trusted policy.

| Bound | Limit |
| --- | --- |
| Source image and normalized PNG | 5 MiB each, or the smaller configured file limit |
| Normalized data URIs across the request | 5 MiB total, including base64 |
| Text-only / unchecked normalization | 12 million pixels; at most 4096 per dimension |
| Face-protected image | 2 million pixels; each dimension 64 through 2048 inclusive |
| Native helper | 768 MiB address space, 10 CPU seconds, 15-second parent timeout |

Oversized protected images are rejected with 413, not silently resized only for
the detector. Existing count, aggregate byte, page, text and final-body limits
still apply. Timeout kills and reaps the helper. Cancellation stops subsequent
preflight helpers while retaining admission until the active helper finishes.
Existing native Docling job admission and poisoned-state behavior remain.

The service bundles MIT-licensed OpenCV YuNet `face_detection_yunet_2023mar.onnx`
from revision `47534e27c9851bb1128ccc0102f1145e27f23f98`, with SHA256
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
The model, source record and license ship in the Python distributions and runtime
image. There are no runtime downloads or face-model storage resources. Detection
is CPU-only, with threshold 0.5; model failures block protected images, not ordinary
text readiness. No face crops, embeddings or identities are retained.

## PII Decision

PII Engine receives the complete converted text request through its existing
fresh document-analysis endpoint, not image pixels. Image approval uses original
entity findings and scan provenance, never already-masked text, a `pass` action,
or `remote_allowed` alone.

The initial implementation deliberately uses a request-wide gate: any detected
entity anywhere in the converted request, including ordinary prompt/history text,
withholds all images. This includes entities whose configured text action is
`pass`, masked or replaced. This conservative behavior avoids a new attribution
system; it can reject an otherwise clean image accompanying a sensitive prompt.
Ordinary text-only processing retains the existing text policy.

Any detected face, non-pass policy decision, cached/ambiguous analysis or required
inspection failure prevents image forwarding. A complete, nonempty reader result
is required; images with no extracted text are rejected, not assumed clean.
The affected request receives a content-free rejection and text-only retry
guidance. Images are never silently removed from a successful chat request, and
there is no automatic raw fallback or attempt to undo an existing block/reroute.

`if-no-pii-detected` means the required checks found no PII or faces; it is not a
privacy guarantee. Readers and detectors can miss content. These checks do not
cover every identifying visual detail or decode every barcode. Use `none` when
image pixels must never reach a downstream chat model.

## Trust And Retention

The private extraction VLM sees unprotected images before PII analysis. It is
inside the trusted processing boundary even when `imageForwarding: none` is set;
that setting controls downstream chat output, not internal extraction traffic.
Keep extraction separate from the public chat route to avoid processing loops.

Use approved private egress, verified TLS and separate service credentials. A
private hostname alone does not prove trustworthy operation. The inference
server must not dispatch to public providers or retain/log raw requests contrary
to the agreed processing boundary. Existing short-lived Docling result cleanup
remains; no new persistent image storage is introduced. Native diagnostics and
raw content must remain out of processing logs, including error paths.

`contentTracingEnabled` is unchanged and independent. When enabled it may retain
downstream prompt/completion content; neither local routing nor passthrough
disables tracing. Review it separately during client activation.

## Rollout And Migration

Version-one metadata remains the default. New per-model fields and `process`
require `attachmentPolicyVersion: 2`; invalid v1 combinations fail rendering
rather than silently losing protection. MCP metadata remains version one.

Version two retains `models` and `attachment_modes`, adding trusted
`image_forwarding`, `face_protection` and `local_models` maps. IDs must exist in
`models`, booleans are strict, and unknown fields are rejected. Passthrough models
are omitted from `image_forwarding`. Locality is derived from the same concrete
routing configuration, never caller headers, model names or text classification.
Remote-capable/virtual destinations cannot receive unchecked processed images.

1. Publish and verify compatible extProc and Tooling releases with separate approval.
2. Adopt their verified pins and deploy compatible consumers while keeping metadata v1 and existing permissions.
3. Deploy the compatible private Docling configuration, including `images`, and verify actual reader/backend capabilities under separately authorized access.
4. Explicitly select metadata v2 and migrate `extract` to `process` with `imageForwarding: none`; migrate `cpu`/`remote` to their preferred names only after Tooling support is available.
5. Enable image forwarding only for reviewed model entries. Configure application upload support separately; this implementation does not enable client uploads.

Old values remain accepted during this transition. Do not remove them until all
consumers and client selections have migrated in a reviewed later change. Restore
v1-compatible configuration before rolling a consumer back. Never emit v2 to an
old consumer: strict validation can reject ordinary text requests for the whole
catalog, not only image requests. Publication, pinning, activation and deployment
are separate approvals; no unpublished image pin is added by this implementation.

## Verification

Service checks cover actual model loading, bounded normalization and detection,
text-only extraction, PII masking/pass findings, face rejection, both chat API
formats, history, failure/cancellation and unchanged passthrough. Chart checks
cover versioned metadata, invalid combinations, aliases and private presets.
Tooling checks cover mode aliases and unchanged credential-provider restrictions.

Base provides explicit integration checks in `tests/validation/`: one renders
mixed catalogs through a selected real extProc consumer; the other executes
pinned upstream reader methods to verify visible pixels reach the VLM HTTP
request unchanged. Neither proves live handwriting/detection accuracy or a full
container deployment. Follow the normal repository checks and
[image release procedure](../operations/image-releases.md); do not require a new
staging server or repeated model qualification for every client.
