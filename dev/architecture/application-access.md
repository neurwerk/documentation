# Application Access Planning

The platform is introducing consistent human-client access profiles without
changing canonical application identities or the existing network boundaries.
The first implementation is an offline plan validator in Base, not a deployment
control. No chart, Flux input, firewall, DNS service, or device enrollment consumes
the plan format yet.

The offline checker was merged in
[Base PR #124](https://github.com/neurwerk/k8s_stack_base/pull/124). It is available
from Base `main`, not yet from an adopted stable platform release.

Track implementation and approvals in
[Base parent issue](https://github.com/neurwerk/k8s_stack_base/issues/121).
The workspace companion checklist is
`docs/todos/application-access-and-private-dns.md`; `docs/todos/` is intentionally
Git-ignored and is not part of the published documentation.

## Profiles and Boundaries

| Profile | Human-client reachability |
| --- | --- |
| `public` | Direct internet access, subject to normal application authorization. |
| `internal` | Approved client LAN or corporate VPN, without an extra device gate. |
| `restricted` | The permitted client boundary AND an approved WireGuard device grant for this application. |

The client-wide `access.boundary` is `internet` or `client-network`. An internet
boundary permits, but does not automatically create, internet access. Under a
client-network boundary, public profiles and an internet-reachable WireGuard
entry point are prohibited. This boundary must eventually be enforced before
WireGuard decapsulation, including for roaming devices and alternate IP paths.

`access.default` supplies omitted endpoint levels; it never selects an endpoint
or enables a product. It accepts the three profiles. The recommended default for
both current clients is `internal`. A `public` default is rejected under
`client-network`, even if every explicit endpoint overrides it.

An explicit profile replaces the default rather than accumulating its rules.
Thus an internet-boundary restricted endpoint does not also require LAN access.
An additional per-endpoint LAN restriction in that case is not yet supported.

Network access does not establish a person's identity or application rights.
Keep Keycloak admission, native sessions/tokens/keys, repository permissions,
and offboarding independent. Workload consumers remain explicitly approved
separately; they do not inherit human-client exposure.

## Existing Clients

| Client | Boundary | Pod canonical routing | Initial certificate profile |
| --- | --- | --- | --- |
| Internet-connected client | `internet` | `public-dns` | `public-production` |
| Private-network client | `client-network` | `internal-traefik` | `public-production` |

The following inventory records intended classifications for review, not proof of
live reachability. Existing ordinary routes use Traefik in both clients. An enabled
Gateway is not itself proof of public access or a network firewall.

| Endpoint | Internet-client intent | Private-client intent | Client-facing surfaces |
| --- | --- | --- | --- |
| Keycloak | Public | Internal | Login, account, and currently same-origin administration |
| LibreChat | Public | Internal | Chat UI, API, login callbacks |
| LibreChat Admin Panel | Public pending narrower policy review | Internal pending narrower policy review | Separate UI; authentication callback on main chat origin |
| LibreChat files | Public reachability, not anonymous buckets | Internal | Effective signed file, image, avatar, and download endpoint |
| Studio | Public | Internal | UI, API, authentication callback |
| Dify | Public | Internal | Console/apps, API, files, authentication callback |
| Langfuse | Public | Internal | Web and API |
| AgentGateway | Public | Internal | Authenticated native/API data plane, not administration |
| Forgejo | Restricted target; private operator tunnel currently documented | Restricted target; product not adopted | HTTPS UI, Git, API, LFS, authentication callback |

Canonical names remain in each client's `config/client.yaml`; do not copy them
into a second deployment inventory. Operator-only dashboards, databases,
OpenBao, the API-key bridge, RAG, and Code Interpreter are not automatically
selected by these profiles. Their existing private access remains unchanged.

## Dependency Validation

Every enabled browser/native-client workflow needs compatible reachability at
each endpoint it contacts. Base owns the fixed dependency catalog, rather than
requiring every client to reproduce it.

| Source | Required client-facing dependencies |
| --- | --- |
| LibreChat | Keycloak; effective file endpoint when S3-backed file workflows are selected |
| LibreChat Admin Panel | Main LibreChat origin and Keycloak |
| Studio | Keycloak |
| Dify | Keycloak when console SSO is selected |
| Forgejo | Keycloak for human login |

The same-origin UI/API/callback paths are one endpoint in the first model.
Forgejo Git-over-HTTPS and LFS share its HTTPS surface; SSH is outside this slice.
Do not infer a Langfuse login dependency from its administrator role or tracing
identity. Server-side database, model, search, and other service calls do not
inherit a browser's network audience.

Public sources require public dependencies. Internal sources require internal
or public dependencies, not device-restricted ones. Restricted sources can use
public dependencies, or restricted dependencies that admit every source device.
Under `client-network`, they can also use internal dependencies. Under `internet`,
internal dependency reachability is unproven because a device may be off-network.

Compare exact expanded device IDs, not group names or list lengths. Empty grants
mean deny-all and produce explicit warnings. A missing required endpoint fails
even for a deny-all source. Dependency failures never broaden exposure or publish
anything automatically. The relation is directional: public Keycloak does not
make its private applications public.

## Offline Checker

Base provides `scripts/check_application_access.py`, a synthetic example at
`tests/platform/application-access.example.yaml`, and the exact input contract
in its README. Run from the Base checkout with pinned tools:

```bash
mise exec -- uv run --offline --frozen python scripts/check_application_access.py tests/platform/application-access.example.yaml
```

The required top-level mappings are `access`, `certificates`,
`canonicalEndpointRouting`, and `endpoints`. Endpoint presence selects a plan
entry. `level` can inherit the default; restricted entries require an explicit
`devices` list. LibreChat requires `features.files` and Dify requires
`features.consoleSSO` as explicit booleans.

The initial certificate profile accepts only `public-production`. It checks the
declared selection, not issuance or trust. Both existing canonical routing modes
are accepted independently of access. Unknown keys, unsupported values, incorrect
types, duplicate YAML keys, aliases/merge keys, and explicit tags are rejected.
Diagnostics do not print supplied values or YAML excerpts.

This input is a normalized planning document, not Helm values or a Kubernetes
resource. A human currently supplies reviewed endpoint, feature, and grant facts.
The [effective-values adapter](https://github.com/neurwerk/k8s_stack_base/issues/123)
must later derive these from selected client/platform composition, respect value
precedence, and detect unclassified endpoints and effective file-storage overrides.
The checker does not authenticate device IDs or establish whether logical endpoints
share a physical origin.

A successful result says `Access plan valid; planning only. Runtime enforcement/DNS
not verified.` It cannot establish that a real client is fully classified or secure.
Do not add these planning fields to reconciled values before supported enforcement
and migration validation exist.

## DNS and Certificates

Keep [canonical Pod routing](split-horizon-dns.md) independent from workstation
resolution. `internal-traefik` configures neither a workstation nor its router.
Private Forgejo's exact Pod DNS exception remains separate from its Keycloak
issuer path. Never replace the whole client domain with a catch-all VPN resolver
merely to reach a restricted application.

The operator reports temporary public Route53 application A records for the private client because
internal DNS administration is not yet available. This is an exception to the
documented final internal-only address-publication policy, not evidence of public
server reachability. Exact records and DNS ownership have not been independently
verified. Leave them intact until the reviewed internal DNS cutover and complete
browser workflow tests succeed; preserve mail and ACME validation records.

[Public DNS-01 certificates](certificates.md) do not require public application
A/AAAA records or public inbound application traffic. They still require public
validation and disclose certificate names through public transparency logs.
Private-CA support is deferred and requires trust distribution, custody, rotation,
and removal of unconditional public-issuer/Route53 bootstrap dependencies.

## Enforcement Gates

DNS and hostnames are not access controls. Separate serving paths and reviewed
firewall policies must implement private/restricted reachability. A route on a
shared public listener is not made private by removing its DNS record.

Gateway placement, approved network ranges, CNI/NAT behavior, device enrollment,
and internal resolver integration remain open prerequisites. Node-origin traffic
and administrative forwarding require particular review; client-side WireGuard
routes alone are not server-side authorization.

No deployment follows from checker success or a merge. An alpha client follows
Base `main`, so this slice changes no reconciled inputs. A stable client stays on its
selected signed platform release, with no Forgejo adoption. Follow
[upgrade gates](../operations/upgrades.md) and obtain separate authorization for
network changes, deployments, signed publication, and adoption.
