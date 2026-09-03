# Configuration Conventions

Configuration is organized by owner and sensitivity. Keep each value in the
narrowest layer that owns it.

## Configuration Layers

| Source | Purpose |
| --- | --- |
| `base/charts/<product>/**/values.yaml` | Safe, environment-independent chart defaults |
| `base/releases/shared/*.yaml` | Platform-wide defaults |
| `base/releases/<product>/**/app-defaults.yaml` | Product or component release defaults |
| OpenBao-backed Kubernetes Secrets | Confidential runtime values |
| `client_*/config/client.yaml` | Shared, non-secret client facts |
| `client_*/.../<product>/values.yaml` | Product-specific client values |

For each HelmRelease, later `valuesFrom` entries override earlier entries.
Inline `spec.values` override `valuesFrom`. Always review the complete
HelmRelease before adding or moving a value.

## Client Values

Each client product package generates namespace-local ConfigMaps:

- `client-values` contains `config/client.yaml`.
- `<product>-product-values` contains the product's `values.yaml`.

Both use the key `values.yaml` and set `disableNameSuffixHash: true` because
HelmRelease references require stable names.

`config/client.yaml` does not have its own Kustomization. Product
Kustomizations load it from the same Flux source artifact.

`infrastructure/storage/postgres/values.yaml` is the single non-secret client
configuration for shared PostgreSQL. Its `auth` and `operations` packages each
generate a namespace-local `postgres-product-values` ConfigMap.

Every ConfigMap or Secret in `valuesFrom` must be in the HelmRelease namespace.
The same name may be reused in different namespaces, but cross-namespace values
references are invalid.

Use Kustomize's relaxed load restriction for local client builds:

```bash
kustomize build --load-restrictor LoadRestrictionsNone apps >/dev/null
kustomize build --load-restrictor LoadRestrictionsNone infrastructure >/dev/null
```

## Destination Controls

The platform supplies a reviewed OpenRouter model snapshot by default. Clients
inherit its serving entries, pricing, AgentGateway roles, access-group grants,
and LibreChat groups when they adopt the platform release containing that
snapshot. A client can opt out globally or exclude exact upstream model IDs in
`config/client.yaml`:

```yaml
openrouterCatalog:
  enabled: false
  excludedModels:
    - publisher/model
  grantToAccessGroups: false
```

All fields are optional. The defaults enable the catalog, exclude nothing, and
grant inherited model roles to each declared AgentGateway access group.

Clients configure direct, local, and other custom model destinations in
`infrastructure/networking/agentgateway/values.yaml`. They configure MCP
destinations in `config/client.yaml` under `mcp.servers`. Do not copy inherited
OpenRouter models or roles into client values. The LibreChat core composition
projects the canonical AgentGateway product values into its own namespace so
those direct and local models use the same definitions in both products.

The platform sets `piiEnabled` and `contentTracingEnabled` to `true` on
inherited OpenRouter destinations. Clients must set both explicitly on every
direct, local, or other custom model and MCP destination. `contentTracingEnabled: true`
allows traces to retain model prompts and completions or MCP tool arguments and
results.

The settings are independent and apply only to the selected destination:

- `piiEnabled: false` keeps fail-closed extProc processing. On MCP routes, it
  uses protocol-only processing without contacting PII Engine or changing
  content.
- `contentTracingEnabled: false` omits destination content attributes while
  retaining the root trace and bounded non-content metadata.

AgentGateway derives trusted metadata from the reviewed catalog, selected route,
and verified identity. Callers cannot override it. See
[Routing](../architecture/routing.md) and
[Observability](../architecture/observability.md).

## Secrets

Never commit these values in client or platform configuration:

- passwords or API keys;
- OIDC client secrets;
- private keys or recovery material;
- cloud-provider credentials;
- Secret manifests containing real data.

Store confidential values in OpenBao. External Secrets creates namespace-local
Kubernetes Secrets. See [Secret Architecture](../architecture/secrets.md).

## Feature-Gated Settings

A disabled chart feature may use validation placeholders only when guarded by
`enabled: false`. Disabled features must not create runtime trust or secret
resources.

When Active Directory federation is enabled, the client repository provides the
real LDAPS URL, DNs, approved groups, IPv4 egress CIDRs, and public CA PEM. The
bind DN and credential remain in OpenBao at `auth-keycloak/external`. A disabled
client must not generate the `auth-keycloak-active-directory-ca` ConfigMap.

## Add a Setting

1. Choose the narrowest owner: chart, platform, client-wide, or product.
2. Add a chart default only when a safe default exists.
3. Update the correct ConfigMap generator and HelmRelease `valuesFrom` list.
4. Keep one canonical client value; do not duplicate facts across products.
5. Render the platform package and a representative client configuration.

See [OpenRouter Catalog](../operations/openrouter-catalog.md) for snapshot
generation and review.
