# Network Isolation

The platform uses Kubernetes `NetworkPolicy` resources to restrict selected
Pods. The cluster CNI must enforce `networking.k8s.io/v1` policies.

NetworkPolicies are additive and apply only to selected Pods and declared
directions. A namespace is not isolated unless a policy selects every Pod with
`podSelector: {}`. A connection must be allowed by both source egress and
destination ingress when both Pods are isolated.

## Current Coverage

The namespace stage defines ingress-and-egress default-deny policies for:

- `auth-keycloak`;
- `frontend-librechat`;
- `librechat-code-interpreter`;
- `infra-postgres-auth`;
- `infra-postgres-operations`.

The AgentGateway extProc chart applies the same namespace-wide isolation to
`monitor-agentgateway-extproc` when installed.

Every other platform namespace manifest creates a namespace without a
default-deny policy. Some charts isolate specific workloads, but unselected
Pods remain unrestricted in directions not covered by another policy. Important
current gaps include:

- AgentGateway data-plane and controller policies restrict ingress only. Their
  egress is unrestricted.
- cert-manager and Rook/Ceph have no platform-owned NetworkPolicies.
- kube-prometheus-stack has no namespace baseline. The platform adds only an
  Alertmanager egress policy.
- Dify and Studio have workload-specific policies but no namespace baseline or
  general ingress isolation.

Do not describe a namespace as isolated based only on the presence of one
workload policy.

## Common Traffic Rules

- Traefik terminates public HTTP traffic in `kube-system`. External port `80`
  redirects to HTTPS before requests reach application backends.
- Policy ports are destination Pod ports, not Service ports.
- DNS allowances use TCP and UDP port `53`. Some policies select CoreDNS by Pod
  label; others currently allow port `53` to all Pods in `kube-system`.
- Prometheus allowances vary between an exact Prometheus Pod selector and the
  complete monitoring namespace. Check the owning chart.
- Standard NetworkPolicy cannot select an FQDN. An `ipBlock` rule limits IP
  ranges and ports, but it does not verify a hostname.

### Kubernetes API Access

OpenBao allows both Kubernetes API paths because NetworkPolicy enforcement may
occur before or after Service destination NAT:

- the Kubernetes Service IP on TCP `443`;
- the client-configured fixed K3s server address on TCP `6443`.

The chart default Service IP is `10.43.0.1/32`. Override it when the cluster
uses a different Service CIDR. The K3s server address must remain stable, and an
OpenBao init container verifies the Service path before startup. See
[OpenBao Operations](../operations/openbao.md#requirements).

## External Egress

Current workload-specific external allowances are:

| Workload | Allowed destination |
| --- | --- |
| Dify API, worker, and plugin daemon | IPv4 TCP `443`, excluding common private, loopback, link-local, carrier-grade NAT, and multicast ranges |
| LibreChat application | The same IPv4 TCP `443` scope for its OIDC issuer and public RGW endpoint |
| LibreChat RAG API | Optional use of the same IPv4 TCP `443` scope |
| Code Interpreter package initializer | The same IPv4 TCP `443` scope for pinned downloads |
| Keycloak Active Directory federation | Client-declared IPv4 CIDRs on TCP `636`, only when federation is enabled |
| Keycloak SMTP | Public IPv4 destinations on the configured SMTP port, only when SMTP is enabled |
| Keycloak initial-administrator email Job | Public IPv4 destinations on TCP `443` for TLS-verified issuer readiness, only when SMTP and the external Gateway are enabled |
| Alertmanager SMTP | Public IPv4 destinations on the configured SMTP port, only when email is enabled |

These IP rules are not FQDN allowlists. cert-manager and AgentGateway can reach
external destinations without an egress NetworkPolicy restriction under the
current manifests.

## Sensitive Paths

### Keycloak And PostgreSQL

`auth-keycloak` is default-deny. Keycloak ingress permits Traefik, configuration
workloads, Studio, the API-key bridge, and the exact AgentGateway data-plane and
controller identities. Egress permits DNS, verified-TLS access to
`postgres-auth`, and the enabled LDAPS or SMTP destinations described above.

`infra-postgres-auth` is default-deny. Its TLS PostgreSQL listener accepts only
Keycloak and its provisioning Job.

`infra-postgres-operations` is default-deny. The exact AgentGateway data-plane,
Dify, Langfuse, LibreChat RAG, and provisioning identities may use its plaintext
PostgreSQL listener with SCRAM authentication. AgentGateway reaches the
`agentgateway` database through Service port `5432`; ingress is restricted on
the backing destination Pod port `9712`. The DocumentDB gateway uses verified
TLS and accepts only LibreChat and the provisioning Job. See
[Shared PostgreSQL](postgresql.md#transport-and-network-policy).

### AgentGateway, PII Engine, And Studio

All supported model requests and MCP routes pass through fail-closed extProc.
The extProc namespace is default-deny and permits egress only to DNS and the PII
Engine analysis listener. PII Engine permits extProc and Studio API on its mTLS
analysis port. See [Routing](routing.md#agentgateway) and
[PII Policy Engine](pii-policy-engine.md#request-flow).

The Studio API Pod has egress allowances for DNS, PII Engine, Keycloak, the
API-key bridge, OpenSearch, and the AgentGateway data-plane admin port `15000`.
It has no Langfuse usage or model-provider egress allowance. AgentGateway
ingress on `15000` permits only the Studio API Pod identity. The
`frontend-studio` namespace has no default-deny baseline, so this statement
applies only to the selected API Pod.

The AgentGateway admin listener is unauthenticated in the current development
deployment. Port-scoped NetworkPolicies restrict which workload can reach it,
but standard NetworkPolicy cannot restrict HTTP paths. A compromised Studio API
Pod could therefore call other admin routes, including configuration dump and
shutdown routes; the configuration dump may expose the expanded database URL.
This is an accepted development risk, not a production-ready boundary. Add
admin authentication or a path-restricting proxy before production use. Never
expose port `15000` through a public listener or `HTTPRoute`.

### Rook/Ceph And Code Interpreter

Rook/Ceph currently has no NetworkPolicy baseline or RGW destination ingress
policy. Its public Gateway terminates TLS and forwards authenticated S3 requests
to the internal RGW Service.

When Code Interpreter is composed, its namespace is default-deny. The API
accepts only LibreChat, and the sandbox runner can reach only the Code
Interpreter egress gateway. The file server reaches the RGW Service on port
`80`; its egress policy therefore selects the RGW Pod on destination port
`8080`. This consumer egress rule does not provide destination ingress if RGW is
later isolated. See [LibreChat](librechat.md) for the sandbox boundary.

## Validation

Render and validate the platform from `base/`:

```bash
make kustomize-validate
make helm-lint
make helm-validate
```

Local validation does not prove that the CNI enforces policies. After an
authorized deployment, inspect the rendered policies and test both allowed and
denied connections:

```bash
kubectl get networkpolicies -A
kubectl describe networkpolicy <name> -n <namespace>
```

Verify DNS, Traefik backends, controller webhooks, Prometheus scrapes, both
OpenBao API paths, and required storage traffic. Also verify a denied
cross-namespace connection and both sides of every sensitive service path.
