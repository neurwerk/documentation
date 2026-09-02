# Certificates and Trust

cert-manager issues certificates, approver-policy authorizes requests,
trust-manager distributes public CA certificates, and product charts declare
the certificates they consume. Client values provide public hostnames and ACME
configuration.

## Certificate Request Approval

cert-manager's built-in automatic approver is disabled. The approver-policy
controller is the approval authority for the platform's cert-manager Issuer and
ClusterIssuer requests.

The platform defines approval profiles for:

- the internal CA bootstrap;
- each internal workload identity;
- the trust-manager webhook;
- each configured public Gateway hostname under both public ClusterIssuers.

Profiles require the expected issuer, namespace, identity, duration, and private
key settings. They constrain any requested usages and CA capability. A catch-all
policy denies unmatched requests. Only the cert-manager controller
ServiceAccount can use these policies, and certificate permissions are not added
to the standard Kubernetes `edit` or `admin` roles.

The release order is:

```text
cert-manager controller
-> approver-policy controller and CRD
-> approval profiles and use RBAC
-> internal and public issuers
-> workload and Gateway certificates
```

Issuers and certificate-producing workloads must not bypass this order.

## Internal PKI

The internal CA chain is:

```text
infra-cert-manager-self-signed-issuer
-> infra-cert-manager-internal-ca Certificate
-> infra-cert-manager-internal-ca-secret
-> infra-cert-manager-internal-ca-issuer
-> workload certificates
```

The internal CA certificate is valid for 10 years. Its private key remains in
the generated Secret in `infra-cert-manager`; it is not stored in Git or
OpenBao.

### Workload Certificates

The chart that owns a service also declares its internal certificate. Current
certificates cover:

- OpenBao server TLS;
- OpenSearch HTTP, transport, and administrator identities;
- PII Engine server TLS;
- AgentGateway extProc and Studio API client identities for PII Engine;
- `postgres-auth` server TLS;
- the `postgres-operations` DocumentDB gateway.

These workload certificates request a 90-day (`2160h`) lifetime and use
cert-manager rotation. Reloader annotations restart PII Engine, AgentGateway
extProc, Studio API, `postgres-auth`, and `postgres-operations` when their
certificate Secrets change.

OpenBao and OpenSearch do not have certificate Reloader annotations. After any
rotation, verify that every consumer has loaded the current certificate. The
PostgreSQL listener in `postgres-operations` remains the documented
[plaintext exception](postgresql.md#transport-and-network-policy); its
DocumentDB gateway uses TLS.

## Trust Distribution

### OpenBao CA Bundle

trust-manager copies `tls.crt` from the internal CA Secret into ConfigMap
`infra-openbao-ca-bundle`. It creates this ConfigMap only in namespaces labeled:

```yaml
secrets.neurwerk.com/openbao-trust: "true"
```

The bundle distributes trust only. OpenBao roles, ServiceAccounts, RBAC, and
NetworkPolicy still control authentication and access.

trust-manager's webhook uses a separate namespace-local self-signed Issuer and
a 90-day certificate. cert-manager's cainjector supplies the webhook CA bundle.
The webhook certificate is not signed by the shared internal CA.

### OpenSearch CA Copies

trust-manager publishes the internal CA certificate as ConfigMap
`monitor-opensearch-ca-bundle` in `infra-cert-manager`. OpenSearch
synchronization jobs can read this public ConfigMap but cannot read the internal
CA Secret.

The jobs copy the CA into trust ConfigMaps for OpenSearch, Fluent Bit, and
Studio. A periodic recovery job repeats the synchronization and restarts Fluent
Bit or Studio when its copy changes. It does not restart OpenSearch.

## Public TLS

Product charts create public HTTPS Gateways only when enabled by client values.
cert-manager's Gateway API integration then creates each listener certificate
and its same-namespace TLS Secret. Every public HTTPS Gateway requests a 90-day
certificate.

The public ClusterIssuers use Let's Encrypt with Route53 DNS-01 validation. The
client provides the public hostnames, DNS zones, and ACME contact email. The
shared setting below selects one issuer for all enabled public Gateways:

```text
publicCertificates.useProduction: false -> letsencrypt-staging-cluster-issuer
publicCertificates.useProduction: true  -> letsencrypt-production-cluster-issuer
```

Use staging to validate DNS and issuance. Switch to production once validation
succeeds, and avoid repeated toggles that can consume ACME issuance limits.

Route53 credentials flow from OpenBao through External Secrets. The public
issuer release cannot become ready until OpenBao is initialized and those
credentials have converged. Never put provider credentials in chart defaults or
client Git repositories.

LibreChat requires distinct certificates for its main application and Admin
Panel hostnames in `frontend-librechat`. The Rook-owned public RGW hostname in
`infra-rook-ceph` also requires its own certificate.

## Microsoft Active Directory CA Trust

When Active Directory federation is enabled, the client repository provides the
public CA certificate at `apps/keycloak/active-directory-ca.pem`. Its
Kustomization publishes ConfigMap `auth-keycloak-active-directory-ca` with key
`ca.crt` in `auth-keycloak`. Disabled federation must not create this ConfigMap.

Only the Keycloak server mounts this ConfigMap. `KC_TRUSTSTORE_PATHS` adds the
mounted CA to Keycloak's system truststore; it does not replace the Java default
roots. The CA is not added to the internal CA, OpenBao bundle, host trust store,
other workloads, or a trust-manager bundle. The Active Directory CA private key
must never enter Git, OpenBao, Kubernetes, or platform certificate controllers.

Before enabling federation or accepting a CA rotation:

1. Verify the expected CA fingerprint through an independent, client-approved
   channel.
2. Verify that the LDAPS hostname matches the directory server certificate.
3. Keep hostname validation enabled for every LDAPS connection.
4. Restrict Keycloak egress to the configured Active Directory IPv4 CIDRs on TCP
   `636`.

## Operator Checks

Confirm the Kubernetes context before inspecting a cluster:

```bash
kubectl config current-context
kubectl get clusterissuers
kubectl get certificates -A
kubectl get certificaterequests -A
kubectl get certificaterequestpolicies.policy.cert-manager.io
kubectl get orders.acme.cert-manager.io,challenges.acme.cert-manager.io -A
kubectl get bundles.trust.cert-manager.io
kubectl get gateways.gateway.networking.k8s.io -A
```

A `Ready` Certificate is not sufficient. Verify that its consumer loaded the
current Secret. For public TLS, also require Gateway `Programmed=True` and
`ResolvedRefs=True` conditions for the current generation.

Never manually approve a denied CertificateRequest. Fix the request to match an
intended profile, or deliberately review and add a new profile.

Before accepting a new cluster, test one intended request and one unmatched
synthetic request in a disposable environment. The intended request must be
approved by its profile. The unmatched request must be denied without creating
a Secret.

See [Routing](routing.md) for Gateway ownership, [Secrets](secrets.md) for
credential flow, and [Keycloak](../authentication/keycloak.md) for Active
Directory federation.
