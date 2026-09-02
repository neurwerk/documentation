# LibreChat

The platform deploys upstream LibreChat components through first-party Helm
charts and Flux release contracts. The application source remains upstream.

## Release Packages

LibreChat is split into three packages:

| Package | Namespace | Components | Default stage |
| --- | --- | --- | --- |
| Core | `frontend-librechat` | Shared configuration, Valkey, Meilisearch, LibreChat, Admin Panel | Included |
| RAG | `frontend-librechat` | RAG API | Excluded |
| Code Interpreter | `librechat-code-interpreter` | Valkey, package initializer, file server, tool-call server, egress gateway, worker, sandbox runner, API | Excluded |

The default application stage includes only
`base/releases/librechat/core/`. The current platform release manifest excludes
RAG because its deployment contract is incomplete. It excludes Code Interpreter
because its first-party runtime images have not been published.

`base/releases/librechat/kustomization.yaml` aggregates all three packages. Do
not compose that path unless all optional-package requirements are satisfied.

### Current Upstream Pins

| Component | Current chart pin |
| --- | --- |
| LibreChat | Source commit `cdfe54c3498818b21b33fb609fee02f2742b37ea`; image digest `sha256:f309d33a0f0b22fe5d3a804c5d197f40d58e69f74d49b68f250cbc502da7e6b2` |
| Admin Panel | `1.0.0` |
| RAG API | `v0.9.0` |
| Code Interpreter | Source commit `fea707467600f3802d65596a6875c7822f25cfd8`; runtime images are not published |

Change source, image, and chart pins together. Use exact versions or digests,
not moving tags.

## Core Architecture

LibreChat is one Node.js workload. It serves the browser application and API on
port `3080`. The Admin Panel is a separate workload with a separate public
hostname.

```text
user browser
-> Traefik
-> LibreChat UI and API
   -> AgentGateway
   -> DocumentDB TLS gateway
   -> Valkey
   -> Meilisearch
   -> optional Rook RGW bucket

admin browser
-> Traefik
-> Admin Panel
-> internal LibreChat API
```

The generated LibreChat configuration uses schema `1.3.14`. It:

- exposes only the configured AgentGateway endpoint;
- fetches the available model list from AgentGateway;
- generates conversation titles after the final response;
- maps provider reasoning through custom endpoint parameters to
  `reasoning_content` and retains reasoning in chat history;
- enables Redis-backed resumable streams;
- sets `STREAM_DELTA_COALESCE_MS` to `0` by default.

The DocumentDB client defaults to 20 pooled connections and two concurrent
connection attempts. Clients may change these limits through
`frontendLibrechat.documentdb.maxPoolSize` and `maxConnecting` after reviewing
the shared PostgreSQL capacity.

## Authentication And Traffic

### Human Access

LibreChat and the Admin Panel share one confidential Keycloak OIDC client.
Local email login and registration are disabled.

- `librechat-user` grants access to LibreChat.
- `librechat-admin` grants administrative access and includes
  `librechat-user`.
- The Admin Panel is SSO-only and has no local administrator password.

Client configuration supplies exact redirect URIs and web origins. The Admin
Panel callback is handled by the main LibreChat API:

```text
https://<main-host>/oauth/openid/callback
https://<main-host>/api/admin/oauth/openid/callback
```

The registered web origins are the main LibreChat hostname and the Admin Panel
hostname. When MCP is enabled, the same OIDC client receives one exact callback
for each configured server:

```text
https://<main-host>/api/mcp/<server-id>/oauth/callback
```

Before LibreChat starts, an init container validates the issuer's OpenID
discovery document over HTTPS. It requires an exact issuer match and HTTPS
authorization, token, and JWKS endpoints. Failure keeps the Pod from starting.

The application uses separate probes:

| Probe | Path | Purpose |
| --- | --- | --- |
| Startup | `/api/admin/oauth/openid/check` | Confirms OIDC initialization |
| Readiness | `/readyz` | Controls Service traffic |
| Liveness | `/livez` | Checks the local process |

### Models And MCP

LibreChat sends model and MCP requests through AgentGateway. AgentGateway
authenticates the caller and enforces focused permissions:

```text
llm:invoke
model:<model-id>:invoke
mcp:<server-id>:invoke
```

The generated agent capability allowlist includes `tools` only when MCP is
enabled. RAG and Code Interpreter capabilities remain independently gated by
their feature selections.

Every configured destination has independent `piiEnabled` and
`contentTracingEnabled` settings. Both chart defaults are `true`; clients should
state both values explicitly. Requests use fail-closed external processing.
AgentGateway removes caller credentials before forwarding requests to a model or
MCP backend.

RAG and Code Interpreter use private Services. Code Interpreter traffic does
not pass through AgentGateway or the PII Engine.

See [Routing](routing.md), [PII Policy Engine](pii-policy-engine.md), and
[OIDC Clients](../authentication/oidc.md) for the shared traffic contracts.

## Configuration And Secrets

Configuration follows the workspace ownership model:

| Configuration | Owner |
| --- | --- |
| Charts | `base/charts/librechat/` |
| Release contracts | `base/releases/librechat/` |
| Shared client facts | `client_*/config/client.yaml` |
| LibreChat product values | `client_*/apps/librechat/values.yaml` |
| Client package composition | `client_*/apps/librechat/kustomization.yaml` |

Client Kustomizations generate `client-values` and
`librechat-product-values` in the namespace of each consuming HelmRelease. The
example client composes only core and explicitly disables RAG and Code
Interpreter.

Only the core `shared` HelmRelease imports the broad OpenBao-backed runtime
Secret. It creates narrower Secrets for the workloads. The LibreChat namespace
keeps the Code Interpreter JWT private signer; the Code Interpreter API receives
only the public verifier.

Never put OIDC secrets, database credentials, S3 credentials, or signing keys in
client values. See [Secrets Architecture](secrets.md).

## Storage And Recovery

Core uses these durable stores:

- the `LibreChat` database through the shared operations PostgreSQL DocumentDB
  TLS gateway;
- Valkey append-only state;
- Meilisearch data;
- the LibreChat compatibility image PVC;
- an optional retained Rook RGW bucket for files, avatars, images, and
  documents.

When object storage is enabled, LibreChat requires the client-owned public HTTPS
RGW hostname for server-side S3 access and browser-facing presigned URLs. The
route does not enable anonymous bucket access.

Shared operations PostgreSQL also provisions the `librechat_rag` database and
pgvector extension. RAG keeps uploads in temporary Pod storage and stores
vectors in that database.

Code Interpreter uses a separate retained RGW bucket, a Valkey store, and a
retained package PVC. Its file server uses the internal RGW Service.

PostgreSQL and these Rook stores share a single-node physical failure domain.
Retention is not backup. The current release contract supports fresh installs;
it does not declare a supported upgrade or downgrade path. See
[Shared PostgreSQL](postgresql.md#persistence-and-recovery) and
[Rook/Ceph Storage](rook-ceph.md).

## Optional Packages

### RAG

The RAG API is private and accepts traffic only from the LibreChat Pod. It uses
native PostgreSQL with pgvector.

Do not enable RAG until all of these are configured together:

- an internal OpenAI-compatible embedding backend;
- a dedicated AgentGateway embedding listener;
- `llm:invoke` and the exact embedding-model permission;
- NetworkPolicies for both the RAG API and AgentGateway sides of the path.

The embedding listener disables access logging and content tracing because an
embedding request may contain a complete uploaded document.

### Code Interpreter

Code Interpreter uses direct NsJail without KVM. The sandbox runs as UID `0`
with an explicit capability set that includes `SYS_ADMIN`. It is not a
privileged Kubernetes container, drops all default capabilities first, and has
no KVM device or host path.

This shared-kernel mode is not approved for general-purpose nodes. Before
composing the package:

1. Publish and verify every first-party runtime image.
2. Select nodes dedicated to untrusted execution and configure matching taints
   and tolerations.
3. Install and verify the chart-provided Localhost seccomp and AppArmor profiles
   on every selected node.
4. Use a CNI that enforces NetworkPolicy.
5. Accept the remaining shared-kernel risk explicitly.

The profile ConfigMaps contain source material only. Flux does not install host
security profiles or change node labels and taints.

The package initializer is a finite Helm hook that prepares the retained package
PVC before the worker starts. Failed hooks remain available for logs and are
replaced on retry. Successful hooks are deleted.

## Validation

Run the owning repository checks:

```bash
cd base
make check
kustomize build --load-restrictor LoadRestrictionsNone releases/librechat/rag >/dev/null
kustomize build --load-restrictor LoadRestrictionsNone releases/librechat/code-interpreter >/dev/null

cd ../client_example_com
make check
```

`base` root Kustomize validation covers the default core package. Build each
optional release package explicitly when changing it.

After an authorized deployment, inspect reconciliation, routing, warnings, and
logs without reading Secret values:

```bash
flux get helmreleases -A
kubectl get gateways,httproutes -A
kubectl get externalsecrets -A
kubectl get events -A --field-selector=type!=Normal --sort-by='.lastTimestamp'
```
