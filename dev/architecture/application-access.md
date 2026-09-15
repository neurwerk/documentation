# Application Access Planning

The platform is introducing consistent human-client access profiles without
changing canonical application identities or the existing network boundaries.
The planning implementation consists of an offline plan validator and a bounded
local composition adapter in Base. The separate optional static WireGuard chart
uses explicit operator values, not that planning format; no automatic device
enrollment or policy controller consumes the plan.

The offline checker was merged in
[Base PR #124](https://github.com/neurwerk/k8s_stack_base/pull/124); the composition
adapter was merged in [Base PR #127](https://github.com/neurwerk/k8s_stack_base/pull/127).
They are available from Base `main`. Clients can pin this validation tooling
independently without changing their selected stable runtime platform.

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
resource. A human can supply reviewed endpoint, feature, and grant facts, or use
the adapter below. The standalone checker does not authenticate device IDs or
establish whether logical endpoints share a physical origin.

A successful result says `Access plan valid; planning only. Runtime enforcement/DNS
not verified.` It cannot establish that a real client is fully classified or secure.
Do not add these planning fields to reconciled values before supported enforcement
and migration validation exist.

## Selected Client Values

`scripts/check_client_application_access.py` reads local client and selected Base
checkouts. It derives endpoint selection, optional browser workflows, canonical
origins, callback paths and realms, certificate selection, and Pod routing from
the supported Kustomize/Flux composition and ordered HelmRelease value sources.
It then calls the normalized validator. The full supported subset is documented
in Base's README; this is not a general Helm or Kustomize interpreter.

The client owns `config/application-access.yaml`, containing only `access` and
`endpoints`. Endpoint entries contain optional `level` and `devices` fields.
Every derived endpoint must be classified, and stale/unselected entries fail.
Do not duplicate hostnames, feature flags, certificates, or routing in this file.
It must remain outside ConfigMap generators and all reconciled runtime inputs.

Run from the checker checkout:

```bash
mise exec -- uv run --offline --frozen python scripts/check_client_application_access.py \
  --client-root /path/to/client --platform-root /path/to/selected-platform \
  --cluster prod-eu-1
```

Supported clients integrate this into ordinary `make check` and `Required CI`:

- `config/application-access-checker-revision` pins the checker to one full merged
  Base commit. The initial integration used `70bf2955dbd5d52b9ce2d74a5e52a557e4610eec`;
  the alpha integration uses `90d6ce6342375520ee1bd644aa24d8013ee1d96f` for quoted Forgejo values.
- `.ci/application-access-checker` holds that disposable tooling checkout.
- `.ci/application-access-platform` independently holds the selected runtime
  platform, derived from the client's existing source selector.
- Explicit `APPLICATION_ACCESS_CHECKER_WORKTREE` and
  `APPLICATION_ACCESS_PLATFORM_WORKTREE` paths support local candidate work.
  A checker override is reported as a candidate, not as pinned validation.
- Do not reuse `BASE_WORKTREE`: existing tests reserve it for candidate platform
  authorization checks. Protected Platform Compatibility workflows are unchanged.

Checkout preparation may access GitHub; the adapter never fetches or contacts a
cluster. It reports checker, platform, and client revisions separately. Consumed
platform files must match regular committed blobs at the selected local ref;
modified or uncommitted consumed client inputs are reported as candidates.
Git inspection avoids filters, external helpers, and lazy fetching. Source
identity and local commit matching are not release-signature verification or
proof of the revision currently running in a cluster.

Missing or unsupported value sources remain unknown. A selected, uniquely owned
ExternalSecret can establish a finite declared write scope only through the
supported strict quoted-YAML producer form; all its values remain opaque.
Static sibling output keys may contain only whole raw-field expressions for
direct workload consumers; they do not contribute to the referenced Helm values.
The adapter never reads Secret values and does not verify actual synchronization
or tampering. Apply-suppressed declarations, unclassified alternate routes,
callback mismatches, and unsupported composition fail rather than imply safety.

### Forgejo Quoted Values

[Base PR #133](https://github.com/neurwerk/k8s_stack_base/pull/133) replaces the
opaque Secret `targetPath` with quoted `values.yaml`. The registration Job still
uses the raw `oidcClientSecret` key; both outputs come from the same existing
source. The adapter continues to reject opaque `targetPath` inputs rather than
assuming they cannot affect sibling settings.

The operator authorized a single coordinated early-alpha rollout, accepting a
brief reconciliation retry while the new key arrived. Alpha convergence and
non-mutating HTTPS/authentication-path checks passed; see
[Forgejo rollout evidence](../operations/forgejo.md#quoted-oidc-values).
Stable runtime adoption remains deferred to a later reviewed release bump.

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

No deployment permission follows from checker success or a merge alone. The
initial checker/client integration changed no reconciled inputs; the later
quoted-values change had explicit alpha rollout authorization. A stable client
stays on its selected signed platform release, with no Forgejo adoption. Follow
[upgrade gates](../operations/upgrades.md) and obtain separate authorization for
network changes, deployments, signed publication, and adoption.

### Private HTTPS Prerequisite

Base [PR #137](https://github.com/neurwerk/k8s_stack_base/pull/137), closing issue
[#136](https://github.com/neurwerk/k8s_stack_base/issues/136), adds the
destination-side `forgejo.networkPolicy.httpsClients` allowance, default `[]`.
It selects an exact namespace and nonempty Pod-label map together and admits only
native HTTPS on Pod TCP `3000` behind Service TCP `443`, not SSH `2222`.
Nonempty selection with the public Forgejo Gateway fails rendering. Existing
web-and-SSH `clients` remain separate and unchanged; overlapping rules are
additive, so this is not a subtractive restriction on existing consumers.

This is a bounded prerequisite, not the reusable WireGuard gateway implementation
or proof of restricted access. No platform or client peers are selected. The
separate static gateway now provides default-deny inner traffic, device checks
before SNAT and exact Forgejo egress. Permission changes use manual stop/update/start,
not automatic expiry or bounded revocation. Operators stop before Service
recreation and recover with no peers if the approved list is untrusted. Live
acceptance must verify the CNI-visible gateway Pod identity and absence of
alternate entrances; never compensate for node-source translation with broad
node allowances. Gateway activation, DNS, enrollment and outer-network forwarding
remain gated on reviewed facts and explicit operational scope.

Merged on 2026-09-15 as `dc59d300bf79b6fb0e82c3df27a2d3c45bab262f`, this
prerequisite is available in Base `main` for alpha source consumption, not in the
selected stable release. Required CI, full local checks and independent review
passed; default disabled, private and public renders were byte-for-byte unchanged.
No gateway deployment or live-policy verification was performed.

### Static Gateway

Base [PR #141](https://github.com/neurwerk/k8s_stack_base/pull/141) merged as
`763c55e0079a5ee24b9eaed0f92a2ff946c96ef5`. The optional `wireguard` chart defaults
disabled, with zero replicas and
an empty peer list. It implements the one-Mac, Forgejo-HTTPS pilot with a pinned
WireGuard image, static nftables rules installed before tunnel startup, no
management UI or Kubernetes API access, and no automatic Service discovery.
It preserves end-to-end native Forgejo TLS and canonical identity. The gateway
references a namespace-local server-key Secret; persistent delivery through
OpenBao/ESO and real network values remain activation prerequisites.

Both gateway packages are outside default stages and excluded from stable
eligibility. Source availability does not imply client adoption or packet-path
acceptance. See [Static WireGuard Pilot](../operations/wireguard.md) for the
implemented runtime, manual stop/update/start, empty-list recovery and live gates.
