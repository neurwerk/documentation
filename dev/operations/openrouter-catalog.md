# OpenRouter Catalog

Each client publishes a reviewed allowlist of compatible OpenRouter models. Base
provides rendering and validation but contains no model or pricing catalog. The
platform does not discover or authorize new upstream models at runtime.

## Ownership

The `openrouter-catalog-sync` trusted-workstation CLI reads OpenRouter's public
paginated endpoint and maintains three client files. Pricing is complete for the
platform's strict text request contract:

| File | Purpose |
| --- | --- |
| `config/openrouter-catalog-policy.json` | Reviewed model selection, public-name compatibility, grants, and pricing policy |
| `config/openrouter-catalog.yaml` | Generated Helm values for serving names, upstream IDs, labels, and LibreChat groups |
| `infrastructure/networking/agentgateway/model-pricing.json` | Generated complete pricing for selected OpenRouter and client-owned direct or local models |

The client composes `openrouter-catalog.yaml` into namespace-local
`client-openrouter-catalog-values` ConfigMaps for AgentGateway, Keycloak, the
API-key bridge, and LibreChat. It composes `model-pricing.json` into the
AgentGateway namespace as `client-model-cost-catalog`. Base consumes the values
ConfigMap only when it exists and mounts only the pricing sources declared by
the client values.

Do not edit the generated files or commit the raw OpenRouter response. The
generated files contain no credential, and the public endpoint requires none.

## Policy

The policy contains five required fields:

- `selectedModels`: unique exact upstream model IDs. New upstream models are not
  selected automatically.
- `grantToAccessGroups`: whether selected model roles are added to each declared
  AgentGateway access group.
- `publicNameOverrides`: reviewed serving names that must survive an upstream
  display-name change.
- `negotiatedPricing`: complete replacement pricing for selected OpenRouter
  models with a negotiated contract.
- `customPricing`: complete pricing for direct and local models. An `openrouter`
  provider may price direct OpenRouter routes but must not overlap
  `selectedModels`.

The CLI rejects stale or incompatible selections, duplicate IDs, serving-name
collisions, malformed pricing, and unknown fields. It excludes temporary,
batch, expired, non-text, parameterless, and routing pseudo-models from the
selection list. Pricing is emitted in USD per million tokens with at most six
fractional places.

Selected models default to PII processing, content tracing, and local PII
rerouting. Each participating client must configure the llama.cpp endpoint and
`guardrails.llmPolicyEngine.localTarget` in its AgentGateway product values, and
must map the matching fallback under `monitorPiiEngine.policy.routing` in
`config/client.yaml`. Direct, local, and other custom models remain client
product values and must have matching `customPricing` entries.

Dify's default model and model role are client-owned explicit settings;
`grantToAccessGroups` does not grant Dify access. The Base chart owns the fixed
provider adapter and Secret-reference wiring. Stage the selection and role in
the client before adopting a Base revision that has no Dify model default.

## Refresh

Run the independently locked CLI from a tooling worktree and target a dedicated
client worktree:

```bash
cd <tooling-worktree>/cli_tools/openrouter_catalog_sync
uv sync --frozen --dev
uv run --frozen openrouter-catalog-sync \
  --catalog-output <client-worktree>/config/openrouter-catalog.yaml \
  --pricing-output <client-worktree>/infrastructure/networking/agentgateway/model-pricing.json \
  --policy <client-worktree>/config/openrouter-catalog-policy.json \
  --select
```

Type to search, press Space to toggle a model, and press Enter to confirm. Use
`--write` instead of `--select` to regenerate non-interactively. Then verify the
canonical policy and both outputs against the current public data:

```bash
uv run --frozen openrouter-catalog-sync \
  --catalog-output <client-worktree>/config/openrouter-catalog.yaml \
  --pricing-output <client-worktree>/infrastructure/networking/agentgateway/model-pricing.json \
  --policy <client-worktree>/config/openrouter-catalog-policy.json \
  --check
```

Review selected additions and removals, serving names, groups, access grants,
pricing, Dify references, and direct model coverage. The CLI permits at most 256
selected OpenRouter models, limits each generated file to 900,000 bytes, and
enforces the 16,384-byte compact PII metadata limit. Base separately rejects
more than 256 effective model destinations or compact PII destination metadata
larger than 16,384 UTF-8 bytes. Keycloak's composed access-group JSON has a
120,000-byte limit, so broad grants can impose a lower practical model limit.

Run the tooling project's complete quality gates and `make check` in the client
repository. Tests use fixtures and must not depend on the live provider
endpoint.

## Rollout

A normal catalog refresh changes only the client repository after its current
Base source supports the client-owned inputs. Keep the policy and both generated
files in one reviewed client commit.

For an ownership or schema transition, stage compatibility across independently
reconciled Git sources:

1. Merge client ConfigMaps, complete pricing, fallback routing, and
   `frontendDify.defaultModel` values while the current Base remains active.
   Price retained direct OpenRouter routes under `customPricing.openrouter` so
   the verification window does not lose cost attribution.
2. Wait until every namespace-local ConfigMap is observed in the target cluster.
3. Merge and validate the Base contract. Pinned clients do not adopt it yet.
4. For alpha adoption, freeze and verify the exact Base commit. For stable
   adoption, prepare, sign, publish, and verify a release whose compatibility
   contract permits the transition.
5. Update each client to that reviewed exact Base release or alpha commit
   without removing its previous priced model entries.
6. Wait for Flux and application reconciliation. Confirm the selected models,
   pricing source, roles, Dify default, and both streaming and non-streaming
   requests.
7. Remove obsolete duplicate models, roles, and their matching
   `customPricing.openrouter` entries in a later client change, then repeat
   reconciliation and request verification.

Keycloak client-role definitions are additive. Removing a selected model stops
serving and generated group grants, but it does not delete a role directly
assigned to a user or service account. Audit those assignments before reusing a
public model name.

Refreshing or merging a catalog does not authorize a platform release, Flux
reconciliation, credential change, or deployment. Follow
[Platform Releases](platform-releases.md) and [Upgrades](upgrades.md) for those
separate actions.
