# Forgejo

Forgejo is an optional native Git service. `forgejo.enabled` defaults to `false`.
Human sign-in uses Keycloak; Git and API access use Forgejo's own authorization
and credentials. It is not an AgentGateway-protected application.

## Status And Scope

As of 2026-09-14, the implementation is merged in Base
[PR #113](https://github.com/neurwerk/k8s_stack_base/pull/113), at commit
`d2ebc87361ec575d38d0b803f9a182fc626ddedd`, and Tooling
[PR #30](https://github.com/neurwerk/k8s_stack_tooling/pull/30).
The source is available on alpha `main`, but the platform manifest still
excludes the Forgejo packages and image from stable release eligibility.
The prepared client has the selector disabled and all four optional Flux stages
suspended. This is not a deployed service.

Adoption requires selection-gated `openbao-stack-setup` `0.2.12`, still using
reconciliation schema `4`, from immutable tooling commit
`7a00c0d7a725a500ca251d699ce3f00dff57e660`. This optional prerequisite does not
replace the baseline tool requirement for clients without Forgejo.
The implementation includes role selection, restricted OIDC scopes,
and optional issuer CA trust. Check the reviewed implementation and release
contract against the [rollout gates](../operations/forgejo.md#before-adoption).

Local Base validation passed 76 chart tests, 10 security tests, 16 platform tests,
and four embedded JavaScript tests; two tag-only tests were skipped. Tooling's
credential suite passed 241 tests, and the cross-repository client rendering
checks passed. Required PR CI was green before merging. Actual-image, database,
SSO, Git, and recovery acceptance still require an authorized environment.

There is no existing-repository migration, runner deployment, or runner
credential provisioning in this integration. Do not infer support for importing
another installation or running CI jobs from Forgejo's upstream features.

## Ownership And Stages

Base owns the chart, namespace, release resources, secret synchronization,
database provisioning, Keycloak registration, and certificate approval. Clients
own non-secret selection, hostname, product values, and Flux composition.

| Stage | Source path | Purpose |
| --- | --- | --- |
| `forgejo-namespaces` | Base `releases/namespaces/forgejo` | Create namespace `forgejo` and its platform boundaries. |
| `client-forgejo-values` | Client `apps/forgejo` | Generate namespace-local `client-values` and `forgejo-product-values`. |
| `forgejo-secret-sync` | Base `releases/forgejo/secret-sync` | Create the runtime and cross-namespace credential delivery resources without starting Forgejo. |
| `forgejo` | Base `releases/forgejo/app` | Reconcile `keycloak-forgejo-oidc` and the Forgejo HelmRelease. |

Namespace and secret synchronization must stay separate from application startup.
The Forgejo HelmRelease waits for operations PostgreSQL, its OIDC registration,
and certificate issuers. A secret stage that waits for the application or for a
database release blocked on the same new password creates a dependency cycle.
See the [staged activation procedure](../operations/forgejo.md#staged-activation).

## Canonical Address And Transport

`forgejo.hostname` is the one canonical browser, TLS, callback, and HTTPS clone
hostname, for example `forgejo.example.com`. Keep the URL
`https://forgejo.example.com` in both modes; a tunnel does not introduce a second
origin or a localhost callback.

| Mode | Web path | SSH |
| --- | --- | --- |
| Private, default `externalGateway.enabled: false` | Approved private tunnel to Service `forgejo:443`, native HTTPS on Pod port `3000` | Built-in server on private Service/Pod port `2222` for approved consumers only. |
| Optional public `externalGateway.enabled: true` | Traefik terminates HTTPS and sends HTTP to Service port `80`, Pod port `3000` | Remains private; Traefik is not admitted to SSH. |

There is no public SSH listener, TCPRoute, NodePort, or LoadBalancer for Forgejo.
Internal consumers need explicit namespace and Pod selectors in
`forgejo.networkPolicy.clients`; the default list is empty. Switch internal web
consumers consistently when changing transport mode.

For private browser access, an approved workstation tunnel must actually bind
local port `443`, and workstation resolution must direct the canonical hostname
to that listener. Establish this prerequisite before login. A port-forward on
`8443` alone does not satisfy the canonical callback. Do not assume a VPN exists,
run SSH as root, or use `sudo` to access a private key to work around binding.

Pod resolution is separate from workstation resolution. In private mode,
approved Pod consumers resolve the exact Forgejo hostname to
`forgejo.forgejo.svc.cluster.local`, not Traefik. The Forgejo Pod itself uses a
loopback host alias for its native local callbacks. Neither rule changes the
Keycloak issuer's resolution.

For Keycloak, `canonicalEndpointRouting.mode: internal-traefik` permits the
reviewed Traefik HTTPS path. `public-dns` instead requires reviewed individual
Keycloak destination `/32` or `/128` addresses in
`forgejo.networkPolicy.keycloakPublicCidrs`. These addresses remain unresolved
rollout inputs; do not substitute general internet egress or blindly change the
shared routing mode. NetworkPolicy enforces peers and ports, not hostnames on a
shared IP. Cluster DNS or reachability checks require separate authorization.

## Certificates And Trust

Whenever Forgejo is enabled, its chart creates exactly one explicit Certificate
`forgejo-tls` and same-named Secret in `forgejo`, independently of the public
Gateway. It requests the exact canonical hostname, RSA 2048, `2160h` duration,
and `Always` key rotation from the existing shared issuer selected by
`publicCertificates.useProduction`:

- `false`: `letsencrypt-staging-cluster-issuer`;
- `true`: `letsencrypt-production-cluster-issuer`.

The exact Forgejo approval profile must be present even in private mode. The
optional Gateway reuses this Secret and has no cert-manager issuance annotation;
do not create a second issuer or listener-owned Certificate. DNS-01 issuance
does not require a public application A or AAAA record.

Browser trust of Forgejo's staging certificate and Forgejo's trust of the
Keycloak issuer are separate requirements. System CA trust is the default for
Keycloak. `forgejo.oidc.caConfigMap` defaults to an empty string, meaning system
roots only. For a staging or private-CA issuer, the client creates the selected
non-secret ConfigMap in namespace `forgejo`, with the independently verified
public CA bundle in key `ca.crt`. The chart does not create this ConfigMap.

Initialization adds that bundle to system roots in the process trust store;
only approved CA certificates belong there. A missing ConfigMap/key blocks the
mount, and an empty bundle blocks initialization. The selected ConfigMap is a
Reloader input so a change rebuilds trust on Pod replacement. Hostname and issuer
verification stay enabled. Forgejo's own serving certificate is not added to
this trust bundle and cannot establish trust in Keycloak's separate certificate.

Staging browser trust must be explicitly prepared on the workstation. Do not
disable TLS verification to make OIDC work. The upstream 15.0.8 internal API
client has its own verification limitation noted in the chart README; that is
not permission to bypass verification for browsers, Git clients, or OIDC.

## Runtime And State

The chart fixes the rootless image for both initialization and serving:

```text
code.forgejo.org/forgejo/forgejo:15.0.8-rootless@sha256:8f97b55ca162ef3b538c6c78a2a077df9f2143c41d80b2bc6b6920f8d430df34
```

The chart records registry verification of this OCI index on 2026-09-14. This is
not actual-image runtime acceptance. Clients cannot override the image.

One UID/GID `1000` Pod uses a Recreate Deployment and retained `forgejo-data`
RWO PVC, default `20Gi` on `infra-rook-ceph-rbd`. Repositories, LFS, attachments,
indexes, queues, and Git state live under `/data`. The built-in SSH host key at
`/data/ssh/forgejo.ed25519` is created only when absent.

The native PostgreSQL database and role are both `forgejo`, reached at
`postgres-operations.infra-postgres-operations.svc.cluster.local:5432`. Service
port `5432` targets Pod port `9712`; NetworkPolicies must allow the latter on the
exact database Pods. This uses the existing operations-only plaintext/SCRAM
exception, not DocumentDB's Mongo-compatible gateway and not `postgres-auth`.

The initializer validates credentials, regenerates configuration, runs native
database migrations, reconciles the exact `keycloak` auth source, and creates
the recovery account only if absent. Unexpected sources or malformed account
state block startup rather than being deleted. Attempts are bounded but may be
retried by Kubernetes. Migrations are forward-sensitive; application startup
does not imply that an older image can read the resulting database.

The database shares the operations instance's process, PVC, maintenance window,
and recovery point with its other consumers. Recovery must coordinate a backup
of the complete shared instance, the Forgejo PVC, and durable secrets. PVC
retention is not a backup, and neither a Helm rollback nor a Forgejo-only database
restore is promised as a safe recovery path.

## Related Documentation

- [Forgejo authentication](../authentication/forgejo.md)
- [Forgejo operations and acceptance checks](../operations/forgejo.md)
- [Shared PostgreSQL](postgresql.md)
- [Certificates and trust](certificates.md)
