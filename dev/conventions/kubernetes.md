# Kubernetes Conventions

Kubernetes manifests must make ownership, security, and readiness clear. Apply
these rules to platform-owned resources. Do not change generated upstream
resources only to make their metadata look consistent.

## Namespaces and Resource Identity

- Use lowercase, DNS-compatible resource names. Use `<product>-<component>` when
  a namespace contains several components.
- Use the established product namespaces. Do not deploy workloads to `default`.
- For new or changed first-party workloads, use `app.kubernetes.io/name`,
  `app.kubernetes.io/instance`, and `app.kubernetes.io/part-of`. Add
  `app.kubernetes.io/component` only for an operational role.
- Keep selectors minimal and stable. Every workload selector must match its Pod
  template. Treat selector changes as identity migrations because Deployment
  and StatefulSet selectors are immutable.
- Flux resources and client-generated values ConfigMaps use stable names and
  namespaces as their identity. They do not need application labels.
- Namespace labels enable a controller or policy. Add them only when a documented
  consumer requires them.

## Workloads

### Security

- Run as a non-root user, disable privilege escalation, drop unnecessary
  capabilities, and use `RuntimeDefault` seccomp when the image supports them.
- Mount writable paths explicitly when using a read-only root filesystem.
- Set `automountServiceAccountToken: false` when a Pod does not call the
  Kubernetes API.
- Give Kubernetes API clients dedicated ServiceAccounts and least-privilege
  RBAC. Use exact resources and verbs, and use `resourceNames` when the required
  operation supports it.
- Avoid wildcard RBAC and cluster-wide bindings for application workloads.

Some workloads have explicit runtime exceptions. For example, DocumentDB allows
privilege escalation, while the Code Interpreter sandbox uses a reviewed UID,
capability, and seccomp configuration. Keep exceptions narrow and documented in
the owning chart.

### Resources and Health Checks

- Read resource requests and limits from values so release or client values can
  set workload sizing.
- Use startup probes for slow initialization and readiness probes to decide when
  a Pod can receive Service traffic.
- Keep liveness process-local. A failure in DNS, an identity provider, or another
  workload must not restart a healthy process.
- Separate readiness and liveness when a dependency outage should remove traffic
  without restarting the process.

## Lifecycle Gates

Use each gate for the state it controls:

- **Flux `dependsOn`** orders releases or stages. It does not prove that
  application-level configuration has completed.
- **Init containers** check prerequisites that must exist before the application
  starts. Remote checks must use normal trust verification, fail clearly, and
  have a deadline.
- **Helm hook Jobs** perform one-time release reconciliation. New hook Jobs must
  have `activeDeadlineSeconds`, verify the resulting state, and fail when work is
  incomplete. Set the HelmRelease timeout above the Job's maximum runtime.

A Ready Pod does not prove that a separate configuration Job succeeded unless
that state is part of a declared readiness or release gate.

## Networking

- Use ClusterIP Services for internal traffic and Gateway API for external HTTP
  routes.
- Keep cross-namespace references explicit and use `ReferenceGrant` only when
  required.
- Put workload NetworkPolicies in the chart that owns the workload.
- Select both the peer namespace and Pod when possible. Use destination container
  ports, not Service ports.
- Scope public-IP, API-server, node, and dynamic-workload exceptions to the
  narrowest possible ports and CIDRs.
- Verify TLS identities. Do not disable certificate verification.

Default-deny is not platform-wide. It currently applies to `auth-keycloak`,
`frontend-librechat`, `librechat-code-interpreter`, `infra-postgres-auth`, and
`infra-postgres-operations`. Check the namespace and owning charts before
assuming a workload is isolated.

Traefik owns public port 80 and redirects HTTP to HTTPS. Application Pods receive
only Traefik's internal backend connection.

The only accepted database transport exception is plaintext PostgreSQL to
`postgres-operations`. Exact consumer NetworkPolicies and default-deny isolate
this path. `postgres-auth` and the operations DocumentDB gateway require verified
TLS. See [Shared PostgreSQL](../architecture/postgresql.md#transport-and-network-policy).

## Storage and Secrets

- Use PVCs for durable state. Check each workload's reclaim and StatefulSet claim
  retention settings; there is no platform-wide PVC retention policy.
- Keep environment-specific topology in client values. This includes Rook
  node/device selection and the PostgreSQL StorageClass. Some charts provide
  platform StorageClass names as defaults.
- Use ConfigMaps for non-secret configuration and Kubernetes Secrets for
  confidential values.
- Never commit real Secret values or generated Secret manifests.
- OpenBao and External Secrets provide most namespace-local runtime Secrets.
  ObjectBucketClaim controllers generate scoped RGW credentials for their
  buckets.
- Helm `valuesFrom` references must use ConfigMaps or Secrets in the HelmRelease
  namespace.

See [Secret Architecture](../architecture/secrets.md) for the complete secret
flow.

## Review Checklist

Before review, check:

- namespace, names, labels, and selectors;
- ServiceAccount, token automount, RBAC, and security contexts;
- resources, probes, lifecycle gates, and cleanup behavior;
- Services, routes, NetworkPolicies, and TLS verification;
- PVC retention, ConfigMaps, and Secret references.

Validate rendered manifests, not only Helm templates.

See the Kubernetes guidance for [security contexts](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
and [Secret handling](https://kubernetes.io/docs/concepts/security/secrets-good-practices/).
