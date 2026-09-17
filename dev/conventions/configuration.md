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

Each client owns its reviewed OpenRouter selection and pricing policy in
`config/openrouter-catalog-policy.json`. The trusted-workstation sync tool
generates `config/openrouter-catalog.yaml` and
`infrastructure/networking/agentgateway/model-pricing.json`; do not edit those
outputs manually. Base contains no concrete model or pricing catalog. It
consumes the namespace-local client ConfigMaps when present and derives serving,
policy metadata, role definitions, and LibreChat groups from the same selected
model list. Selection does not authorize callers. Keep the global safe default
and both client policies at `grantToAccessGroups: false`; rendering rejects
`true`. Explicit `authKeycloak.agentgatewayAccessGroups` grants accept only
`/access/neurwerk-llm-all-users` for model roles and
`/access/neurwerk-mcp-all-users` for MCP roles, with `llm:invoke` as required.
Rendering rejects other groups and cross-resource grants.
Application or administrator membership grants neither, and MCP access must not
generate model access.

Clients inherit the platform's canonical `/access` groups and application role
mappings from the immutable chart file
`base/charts/keycloak/realm-config/realm-roles/files/standard-access.yaml`.
Rendering rejects `authKeycloak.accessGroups`, `authKeycloak.realmRoles`, and
`authKeycloak.realmRoleComposites` overrides; omit those keys entirely.
Memberships, directory settings, and explicit resource grants remain
client-owned.

With realm-roles chart `2.2.0` or later, the one supported application-administration exception is
`authKeycloak.platformAdminRoleExclusions`, default `[]`, in client Keycloak
values. It subtracts approved direct application roles from Base's
`platform-admin` composite; it does not override the immutable catalog or group
mappings and cannot add authorization. Allowed entries are `keycloak-admin`,
`api-key-admin`, `opensearch-admin`, `langfuse-admin`, `pii-admin`, `studio-user`,
`librechat-admin`, `dify-admin`, and `forgejo-admin` only. For example:

```yaml
authKeycloak:
  platformAdminRoleExclusions: ['forgejo-admin']
```

Each override replaces the entire list, not individual entries; `[]` restores
all default application grants, including Forgejo only when enabled.
`forgejo-admin` is a valid exclusion even while Forgejo is disabled. Rendering
rejects non-lists, non-string entries, duplicates, unknown roles, group names,
and model/MCP permissions (including `llm:invoke`). Arbitrary role, group, and
catalog overrides remain prohibited. This setting changes neither resource
groups nor existing explicit model/MCP baseline grants or catalog policy. It
does not revoke direct application-group memberships or native credentials.
See
[Keycloak](../authentication/keycloak.md#roles-and-access-groups).

Clients configure direct, local, and other custom model destinations in
`infrastructure/networking/agentgateway/values.yaml`. They configure MCP
destinations in `config/client.yaml` under `mcp.servers`. Direct and local model
pricing belongs in the policy's `customPricing` field, including disjoint
`customPricing.openrouter` entries for direct OpenRouter routes. The LibreChat core
composition projects the canonical AgentGateway product values into its own
namespace so those direct and local models use the same definitions in both
products.

The chart defaults `piiEnabled` and `contentTracingEnabled` to `true` on selected
OpenRouter destinations and routes their PII fallback through the client-owned
`guardrails.llmPolicyEngine.localTarget`. Clients map that fallback in
`monitorPiiEngine.policy.routing` and must set both booleans explicitly on every
direct, local, or other custom model and MCP destination.
`contentTracingEnabled: true` allows traces to retain model prompts and
completions or MCP tool arguments and results.

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

### Attachment Modes

Model `attachmentMode` is `block` (default), `extract` or `passthrough`, separately
from `piiEnabled`. Passthrough requires PII disabled and deliberately sends raw
attachments to the selected backend; it neither implies local routing nor disables
content tracing. Extract performs document conversion before optional PII and
must never fall back to passthrough. extProc `0.8.0` implements conversion and uses
PII Engine `0.9.0` for request-local document analysis when PII is enabled.

The chart produces an optional sparse `attachment_modes` map next to the existing
trusted model-to-PII map. Configure direct/local models in the existing AgentGateway
product values; normal Helm whole-list override rules still apply. Install the
compatible extProc consumer before setting any explicit mode: older consumers reject
unknown metadata fields. See [Docling attachment modes](../architecture/docling.md#configuration-and-compatibility)
for configuration and rollout order; service publication is not client adoption.

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
real directory URL, user/group DNs, group selection and IPv4 `egressCidrs` in
`apps/keycloak/values.yaml`. Under `authKeycloak.activeDirectory`, exactly one of
`groupNames` or `groupMappings` must be non-empty; both default to `[]`. Legacy
`groupNames` uses same-name lowercase `neurwerk-` groups. Each mapping contains
only `sourceName` and `targetParent`, for example
`{sourceName: CORP_STUDIO, targetParent: /access/neurwerk-studio-users}`. Sources
must be unique ignoring case and targets must be unique existing canonical
paths; mappings do not override platform groups or role definitions.

`allowInsecureLdap: false` is the default. Verified `ldaps://ad.example.com:636`
requires the client public CA PEM and its ConfigMap. Plain
`ldap://ad.example.com:389` requires `allowInsecureLdap: true`; it sends credentials
and directory data without TLS, not through StartTLS. Only enabled LDAPS uses
`caConfigMapName` and `caKey`. A disabled or plaintext client must not generate
the `auth-keycloak-active-directory-ca` ConfigMap. Egress is enabled only for the
selected directory port and configured CIDRs.

The bind principal and credential remain in OpenBao at `auth-keycloak/external`
and use the same Secret for both transports and group modes. Mappings and
plaintext require the staged charts `1.1.0` and compatible Tooling `>=0.7.0`
image contract; `0.7.0` source is not publication or adoption. Do not change pins
as part of a group-only values edit before the image is published and verified.
See [Keycloak federation](../authentication/keycloak.md#active-directory-federation)
for source-name validation, actual child paths and the exact runtime gate.

## Add a Setting

1. Choose the narrowest owner: chart, platform, client-wide, or product.
2. Add a chart default only when a safe default exists.
3. Update the correct ConfigMap generator and HelmRelease `valuesFrom` list.
4. Keep one canonical client value; do not duplicate facts across products.
5. Render the platform package and a representative client configuration.

See [OpenRouter Catalog](../operations/openrouter-catalog.md) for client catalog
generation, review, and rollout.
