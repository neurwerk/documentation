# Canonical Endpoint DNS Routing

Canonical public endpoint names can resolve to different addresses for Pod and
non-Pod callers without changing their HTTPS identity. This is DNS routing, not
an HTTP redirect: URLs, TLS SNI, OIDC issuer identity, redirect URIs, browser
origins, and S3 request signatures continue to use the canonical public names.

## Routing Modes

Clients select one `canonicalEndpointRouting.mode` value:

| Mode | DNS expectation | Workload egress |
| --- | --- | --- |
| `internal-traefik` | Exact CoreDNS rewrites send selected canonical names to the cluster Traefik Service | Affected workloads receive exact Traefik Pod egress on TCP `443` |
| `public-dns` | Canonical names resolve through normal public DNS | Affected workloads do not receive the additional Traefik allowance |

`internal-traefik` is the fail-closed chart default. A client whose canonical
endpoints resolve publicly must select `public-dns` explicitly. Unknown values
fail Helm rendering.

Dify API and LibreChat retain their general public HTTPS allowances in both
modes because they have other external HTTPS dependencies. The Keycloak
initial-administrator action-email Job uses Traefik-only HTTPS egress in
`internal-traefik` mode and public HTTPS-only egress in `public-dns` mode.

## Resolver Boundaries

Dify web makes server-side HTTPS calls to its own canonical origin. Include that
exact application hostname in the reviewed rewrite list for internal-routing
clients, alongside required issuer and object-store names. Workstation resolution
does not make these Pod-side self-calls work. Preserve the canonical URL and TLS
verification; do not substitute a backend Service URL or a parent-zone rewrite.

Check the web Pod's actual NetworkPolicy selectors before adding egress rules.
The current platform does not isolate Dify web egress, so adding its exact DNS
rewrite does not require a new policy. Dify API's policy is a separate boundary.

These mechanisms have separate owners and scopes:

| Mechanism | Scope | Responsibility |
| --- | --- | --- |
| Workstation `/etc/hosts` | One operator workstation | Temporary browser and operator resolution only; it never configures Pod DNS |
| Active Directory DNS | Approved internal clients | Final browser-facing internal records; it does not configure CoreDNS or issue Gateway certificates |
| CoreDNS exact rewrites | Every Pod query for an exact matching name | Pod-side routing to the Traefik Service; NetworkPolicy separately controls reachability |
| Route53 public DNS | Public authoritative zone | Public records, mail records, and cert-manager DNS-01 challenge records |
| cert-manager | Gateway listener namespaces | ACME issuance and renewal plus the same-namespace TLS Secrets consumed by Gateways |

A CoreDNS `rewrite name exact` rule is cluster-wide for the matching query. It
does not target only Dify, LibreChat, or Keycloak Pods. Keep the rewrite list
minimal and exact; never replace it with a wildcard, suffix, regex, or parent-zone
override. NetworkPolicy is the workload boundary.

Route53 DNS-01 validation does not require an application A or AAAA record.
CoreDNS and Active Directory DNS therefore may route application names
internally while Route53 remains authoritative for ACME challenges and other
public records. Active Directory Certificate Services is not part of the public
Gateway certificate path.

### Private Forgejo Exception

The [staged optional Forgejo integration](forgejo.md#canonical-address-and-transport)
uses native HTTPS when its public Gateway is disabled. Approved Pod consumers
must resolve its exact canonical hostname to `forgejo.forgejo.svc.cluster.local`,
not to Traefik. The Forgejo Pod's local callbacks use a separate loopback host
alias. Workstation tunnel resolution remains independent of both mechanisms.
Keycloak issuer resolution and trust must be checked separately; do not change
the shared routing mode or issuer route merely to route Forgejo. Public-DNS
Keycloak egress needs reviewed exact IP CIDRs before authorized rollout.

## Rollout Contract

Use this order for an internal-routing client:

1. Publish a platform release containing the routing-mode NetworkPolicies.
2. Adopt that exact signed release and select `internal-traefik` in client values.
3. Verify the affected NetworkPolicies and workloads after reconciliation.
4. Add only the reviewed exact CoreDNS rewrites.
5. Verify rewritten and unrelated DNS answers, strict HTTPS, Gateway routing,
   OIDC issuer identity, and S3 requests.

For rollback, revert the client DNS composition through Git and let Flux remove
the custom CoreDNS ConfigMap. Do not imperatively delete a resource that remains
declared by Git. Confirm CoreDNS remains Ready and that the rewritten names no
longer return the Traefik Service address.

Workstation overrides and an eventual Active Directory DNS transition are
independent of Pod-side CoreDNS activation. A production-certificate switch is
also independent and occurs only after DNS, Gateway, and staging-certificate
verification.
