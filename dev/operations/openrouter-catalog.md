# OpenRouter Catalog

The platform publishes a reviewed snapshot of compatible OpenRouter models. It
does not discover or authorize new upstream models at runtime.

## Contract

The snapshot is generated from OpenRouter's public paginated endpoint:

```text
https://openrouter.ai/api/v1/models
```

The `openrouter-catalog-sync` trusted-workstation CLI owns retrieval,
compatibility filtering, name validation, and pricing conversion. The generated
files are committed to `base`:

| File | Purpose |
| --- | --- |
| `releases/shared/openrouter-catalog-policy.json` | Reviewed public-name compatibility and source exclusions |
| `releases/shared/openrouter-catalog.yaml` | Shared serving names, upstream IDs, labels, and LibreChat groups |
| `charts/agentgateway/files/catalog-overrides.json` | OpenRouter cost rates in USD per million tokens |

Do not commit the raw OpenRouter response. The generated snapshot contains no
credential and the public endpoint requires none.

The generator excludes floating aliases, batch variants, expired models,
non-text and parameterless entries, policy exclusions, and routing pseudo-models
that advertise negative sentinel pricing. Public names are stable release
contract identifiers. Preserve an existing name through
`publicNameOverrides`; do not rename it merely because an upstream display name
changes.

## Refresh

Run the CLI from its independently locked project and target a dedicated `base`
worktree:

```bash
cd tooling/cli_tools/openrouter_catalog_sync
uv sync --frozen --dev
uv run --frozen openrouter-catalog-sync \
  --catalog-output <base-worktree>/releases/shared/openrouter-catalog.yaml \
  --pricing-output <base-worktree>/charts/agentgateway/files/catalog-overrides.json \
  --policy <base-worktree>/releases/shared/openrouter-catalog-policy.json \
  --write
```

Then verify exact reproducibility:

```bash
uv run --frozen openrouter-catalog-sync \
  --catalog-output <base-worktree>/releases/shared/openrouter-catalog.yaml \
  --pricing-output <base-worktree>/charts/agentgateway/files/catalog-overrides.json \
  --policy <base-worktree>/releases/shared/openrouter-catalog-policy.json \
  --check
```

Review additions, removals, changed public names, provider groups, pricing, and
the total destination count. The effective AgentGateway catalog must not exceed
512 entries. Unsupported time- or day-conditioned pricing overrides are omitted
while the ordinary base rate is retained; context-threshold overrides become
ordered AgentGateway tiers.

Run the tooling project's complete quality gates and `make check` in `base`.
Tests use fixtures and must not depend on the live provider endpoint.

## Client Inheritance

Clients receive the snapshot only when they adopt its signed platform release.
An OpenRouter API change alone never alters a cluster.

Inheritance defaults to enabled. A client can disable the complete inherited
catalog, exclude exact upstream IDs, or stop automatic grants to its declared
AgentGateway access groups:

```yaml
openrouterCatalog:
  enabled: true
  excludedModels:
    - publisher/model
  grantToAccessGroups: true
```

Unknown and duplicate exclusions fail rendering. Exclusions apply consistently
to AgentGateway models, extProc policy metadata, Keycloak roles, normal access
groups, and LibreChat model specifications. Pricing may remain in the global
snapshot, but an excluded model is not callable.

Dify model permissions remain explicit. Excluding a model still referenced by
Dify fails validation instead of silently expanding or changing Dify access.

## Rollout

Merge and release the backward-compatible platform contract first. Each client
must then adopt that exact platform release and wait for successful Flux and
application reconciliation before merging the cleanup that removes manually
duplicated OpenRouter entries. Publishing the platform release alone is not
sufficient because platform and client sources reconcile independently.

The default client policy grants every inherited model to every declared
AgentGateway access group. Adoption therefore expands authorization and
potential spend beyond a previously curated client catalog unless the client
uses `excludedModels` or disables `grantToAccessGroups`. Review that policy as
part of each client adoption.

Keycloak client-role definitions are additive. Exclusions remove serving,
normal access-group grants, and generated managed-key grants, but they do not
delete an existing directly assigned client role. Audit direct and service
account role assignments before reusing an excluded public model name.

Refreshing and merging the snapshot does not authorize a platform release,
client adoption, Flux reconciliation, credential change, or deployment. Follow
[Platform Releases](platform-releases.md) for those separate actions.
