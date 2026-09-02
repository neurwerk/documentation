# Routing

The stack uses Gateway API resources for HTTP routing. Product charts own their
`Gateway` and `HTTPRoute` resources.

## Gateway Controllers

The platform uses two Gateway classes:

- `traefik` handles public HTTP and HTTPS traffic.
- `agentgateway` handles authenticated model and MCP traffic.

The Traefik chart configures the Traefik installation provided by k3s. It does
not install another controller. A catch-all Traefik route redirects HTTP traffic
to HTTPS with status `301`.

## Public HTTPS Routes

Public routes are disabled by default. A client enables each route and supplies
its exact hostname through client-owned values.

Each public Gateway:

- uses an exact hostname;
- terminates TLS through cert-manager;
- allows routes only from its own namespace;
- uses an `HTTPRoute` in the same namespace.

Inspect the cluster for the current route inventory:

```bash
kubectl get gateways,httproutes -A
```

The client-wide `publicCertificates.useProduction` value selects the issuer for
all enabled public Gateways:

```text
false -> letsencrypt-staging-cluster-issuer
true  -> letsencrypt-production-cluster-issuer
```

LibreChat uses the public RGW hostname for browser-accessible presigned URLs.
The route does not grant anonymous bucket access. LibreChat RAG and Code
Interpreter remain private and have no Gateway or Ingress resources.

See [Certificates And Trust](certificates.md#public-tls) for certificate
ownership and approval.

## AgentGateway

AgentGateway is the controlled entry point for model and MCP traffic.

```text
caller
-> optional public Traefik Gateway
-> internal AgentGateway listener
-> JWT or API-key authentication
-> llm:invoke capability check
-> route-specific authorization and fail-closed processing
-> model provider or MCP backend
```

### Authorization

AgentGateway accepts a verified Keycloak JWT or an API key validated by the
API-key bridge. The trusted principal comes from the JWT `sub` claim or the
bridge's validated `principal_id`. Caller headers cannot set this identity or a
destination policy, and caller credentials are removed before forwarding.

All traffic requires `llm:invoke`. A model also requires
`model:<model-id>:invoke`; an MCP route requires `mcp:<server-id>:invoke`. The
broad capability alone never grants destination access.

### Processing

Supported Chat Completions and Responses requests on the shared listener pass
through fail-closed extProc before model routing. The request selects one entry
from the reviewed model catalog; it cannot create or override catalog policy.

Each MCP server has an exact `/mcp/<server-id>` route. Fail-closed extProc
enforces MCP `2025-11-25` and processes PII where enabled.

- Models are configured in
  `client_*/infrastructure/networking/agentgateway/values.yaml`.
- MCP servers are configured in `client_*/config/client.yaml`.
- Static MCP IDs may be dotted DNS subdomains. Workload-backed IDs must be one
  DNS label because they become Service and container names.

Every destination has explicit `piiEnabled` and `contentTracingEnabled` values;
both chart defaults are `true`.

- `piiEnabled: false` keeps strict dispatch and protocol validation but skips
  PII Engine state, analysis, and content changes.
- `contentTracingEnabled: false` omits model prompt and completion content, or
  MCP input and output content, from trace attributes.

Provider and MCP credentials come from OpenBao-backed Secrets, never ConfigMaps
or client values. See [API Keys](../authentication/api-keys.md),
[PII Policy Engine](pii-policy-engine.md), and [Secrets](secrets.md).

### Private RAG Embedding Listener

The chart contains a disabled RAG embedding listener. It is excluded from the
public `HTTPRoute`, extProc, access logging, and tracing. The platform does not
provide the complete RAG authentication and egress NetworkPolicy contract, so do
not enable it as a standalone values change.

## Internal Routes

Most service-to-service traffic uses private Kubernetes Services. Sensitive
paths, including PII Engine and OpenSearch, use verified internal TLS.

Studio API authorizes browser requests and proxies policy evaluation to PII
Engine over mTLS. It also proxies authorized operations to Keycloak, the API-key
bridge, Langfuse, and OpenSearch. Browsers do not call those services directly.
Studio has no AgentGateway model-discovery or live model-test route.

When enabled, LibreChat calls its RAG and Code Interpreter services directly
over private HTTP. Application authentication and NetworkPolicy protect those
paths.

## Development Rules

- Keep each `Gateway` and `HTTPRoute` in the chart that owns the route.
- Use explicit hostnames on public HTTPS listeners and routes.
- Keep parent and backend references in the same namespace. Add a
  `ReferenceGrant` only for a reviewed cross-namespace requirement.
- Prefer private `ClusterIP` Services for internal traffic.
- Never expose LibreChat RAG or Code Interpreter through a public route.
- Strip caller credentials and untrusted identity headers before backend
  forwarding.

## Verification

After changing a route, inspect both the Gateway and its HTTPRoute:

```bash
kubectl describe gateway <gateway> -n <namespace>
kubectl describe httproute <route> -n <namespace>
kubectl get certificates -A
```

Confirm that Gateway listeners are programmed and references are resolved.
Confirm that each HTTPRoute parent reports `Accepted=True` and
`ResolvedRefs=True`.

See the Gateway API [security model](https://gateway-api.sigs.k8s.io/docs/concepts/security/)
for hostname delegation and cross-namespace reference rules.
