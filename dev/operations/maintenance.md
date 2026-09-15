# On-Demand Maintenance

Maintenance overlays approved application HTTPS hosts; normal requests never
traverse its server. After the last scope is off and cleanup succeeds, there is
no maintenance Deployment or Pod. Failed startup or cleanup can retain one.

## Status And Adoption

The operator confirmed testing complete on 2026-09-15. Stable availability is
being added in `v0.3.8`; completed testing is not repeated for each client.

Tooling [0.6.2](https://github.com/neurwerk/k8s_stack_tooling/releases/tag/v0.6.2)
is published from `03f5767f6716da1838b8d248317ae4d7b96a3953`. Its verified image is
`ghcr.io/neurwerk/k8s-stack-tooling:0.6.2@sha256:299ded44d76d5a73e3c1045af09b02649b08a3b5f00d07a993e3be7c61a490fd`.
Base `22e834c9161050756cca6bddb50d066359518e97` supplies this pin in maintenance
chart `0.1.1`; existing initialization-job image pins are unchanged.

The authorized alpha rollout on 2026-09-15 enabled the contract and all three
stages in the existing namespace, client-values and application composition files.
Flux sources, Kustomizations and HelmReleases were Ready, with no active maintenance
routes, Deployment, Pod or operation lock remaining after acceptance.

A temporary random-header-only route verified 503 pages for every approved host,
including specific API paths and POST requests, while ordinary requests retained
their original responses. Certificates were unchanged, the company PNG loaded,
and operator resources survived Flux reconciliation. With the temporary server
scaled to zero, test traffic received 503 rather than falling through to apps.
Startup took 39 seconds in this test, with transient connection-refused health
probes before readiness. All temporary resources were removed; no normal product
maintenance switch was activated. CLI scope-overlap tests remain offline tests.

For another client, follow [Image Releases](image-releases.md), review Base and
client values, and obtain rollout approval. Enable the contract and reconcile
namespace -> client values -> maintenance release, then verify readiness and
the client's configured hosts. Installing the setup does not activate maintenance.

## Ownership And Contract

Tooling owns `src/k8s_stack_tooling/maintenance/` (server and bundled assets) and
the independent `cli_tools/maintenance/` workstation project. Base owns
`charts/maintenance/`, `releases/maintenance/`, and the separate namespace package.
Clients own non-secret values, branding projections and Flux composition.

Base owns the permanent `maintenance:8080` Service and NetworkPolicy. When enabled,
it also renders inert version-1 templates in `maintenance-runtime` ConfigMap key
`contract.json`. The operator, not Flux/Helm, owns the runtime Deployment, scope
IngressRoutes and operation lock. This exception does not cover CRD installation
or ordinary application routes. Exact schema, labels and values are documented in
`base/charts/maintenance/README.md`; do not hand-maintain another manifest set.

Base owns image approval and must pin a verified
`ghcr.io/neurwerk/k8s-stack-tooling:X.Y.Z@sha256:<64 lowercase hex digits>`.
The CLI checks contract version, identities, scopes and image format, not full
Kubernetes schemas or live manifest equality. Review the Base contract and static
prerequisites before operation; the CLI does not verify Traefik configuration.

## Routing Limits

Scopes are `studio`, `dify`, `librechat` (including Admin Panel), `langfuse`, and
`global`, the union of approved product hosts. Approval in values is not activation.
Identity, model and storage endpoints remain excluded and unchanged. Global and
product routes persist independently; turning off global leaves product scopes on.

Original application Gateways and HTTPRoutes remain intact. Overlays use exact
hosts, all paths, `websecure`, and `tls: {}` to reuse certificates already loaded
by those Gateways. Global priority is `2000000000`; product priority is `1900000000`.
Both Traefik providers and CRD `allowEmptyServices` must be enabled. With the
Service and route intact, empty endpoints must not fall through to applications.
A missing Service or deleted overlay can instead reopen applications.

Reuse accepted testing of TLS reuse, 503 responses, empty-backend behavior,
NetworkPolicy enforcement and scope removal. No separate test server or repeat
qualification is required. Preserve
the static Service and original Gateway/certificate dependencies during the window.
Maintenance does not drain existing connections, stop workers, block internal
Service calls or establish database quiescence. Follow [Supported Upgrades](upgrades.md)
for application-consistent backups and component-specific maintenance procedures.

## Branding And Cost

Project the canonical `authKeycloak.realmDisplayName`,
`authKeycloak.branding.logoConfigMapName`, and `authKeycloak.branding.logoFormat`
from the same client sources used by Keycloak, with the same logo bytes in the
maintenance namespace. Do not duplicate literals or query Keycloak at runtime.
Clients control only name and PNG/SVG logo; palette, templates and bundled Inter
typography are fixed. Assets and branding load at startup.

The server returns HTML `503`, `Retry-After: 300`, `Cache-Control: no-store`, and
`X-Platform-Maintenance: true`. Bundled asset GET/HEAD requests and
`/_maintenance/healthz` return `200`; health is process-local, not app readiness.
It has no upstream, Kubernetes or identity-server dependency.

CPU/memory requests default to `10m`/`64Mi`, limits to `100m`/`128Mi`, through
`maintenance.resources`. The Pod is non-root, has no API token or egress, uses a
read-only root/logo mount and bounded `32Mi` `/tmp`; ingress is Traefik-only.
Zero warm replicas means image-pull, scheduling and startup costs on activation.
Allow for cold start; offline tests do not establish latency or capacity.

## Operator Commands

Install with `uv tool install .` from `tooling/cli_tools/maintenance/` on a trusted
workstation. These are future authorized commands, not operations run here:

```bash
kubectl maintenance status --context "$CONTEXT"
kubectl maintenance on studio --context "$CONTEXT"
kubectl maintenance on global --context "$CONTEXT"
kubectl maintenance off global --context "$CONTEXT"
kubectl maintenance off studio --context "$CONTEXT"
```

The equivalent alias is `maintenance`. Context is mandatory, namespace is fixed
to `maintenance`, and omitted scope defaults to `global`. Only `on`, `off`, and
`status` exist. Image approval is in Base, not an additional CLI argument.
`status` reports route references, Deployment presence and lock UID as read-only
JSON; it is not an HTTPS readiness check. Gates use fixed 120-second timeouts.

`on` checks ownership, creates or reuses the backend without updating settings,
and requires an existing Deployment's image to match Base. It waits for rollout
and a ready endpoint before creating the selected route. Each selected host must
then return trusted HTTPS `503` with the marker; no redirects or TLS bypass are
used. A failed check does not automatically undo routes or delete the backend.

`off` deletes only the selected owned route, with UID/resourceVersion guards.
Remaining scopes retain the backend. After the last route, it checks all approved
hosts for marker absence, waits five seconds, rechecks HTTPS and all-namespace
references, then deletes the owned Deployment. Unknown/indirect references or
listing/verification failures retain it. Normal responses need not be `200`;
check application readiness separately before reopening. `off` permits an older
image. Inspect status after failures; repeat `off global` to clean an orphaned
Deployment when no scopes remain. It never deletes the Service or Base ConfigMap.

## Recovery And Changes

Every on/off atomically creates `maintenance-operation-lock`; locks never expire
or get stolen. Only after independently confirming the owning operator process
has stopped may an authorized operator inspect and manually delete its lock:

```bash
kubectl --context "$CONTEXT" -n maintenance get configmap maintenance-operation-lock
kubectl --context "$CONTEXT" -n maintenance delete configmap maintenance-operation-lock
```

Never remove a running operator's lock. Other manual writers must honor the same
lock and safe order: backend readiness before routes, routes removed and reference/
HTTPS checks complete before backend deletion. Kubernetes cannot make that
multi-resource sequence atomic. Prefer retrying the CLI after inspecting status.

Turn off every scope and finish cleanup before removing static dependencies,
disabling the contract, or changing hosts/product approvals. Use the old host
contract for deactivation so no affected hostname escapes verification. For image,
branding or resource changes, also deactivate and recreate: `on` never updates
an existing Deployment. Unlike `on`, `off` can clean an older-image Deployment;
there is no full manifest-comparison gate. Flux pruning or Git rollback does not
remove operator-owned routes or restore application data.
