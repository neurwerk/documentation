# Supported Upgrades

Platform compatibility is explicit. Semantic Versioning (SemVer) alone does not
make an upgrade safe.

A Git or Helm rollback changes the declared configuration. It does not reverse
database migrations, CRD storage changes, persistent data, storage changes, or
Kubernetes control-plane changes.

## Current Support

The latest published platform release is `v0.1.1`.

| Target | Contract | Stable upgrade sources | Alpha promotion | Downgrade |
| --- | --- | --- | --- | --- |
| `v0.1.0` | Legacy allowlist | None | None | Unsupported |
| `v0.1.1` | Legacy allowlist | None | Exact revision declared by `v0.1.1` | Unsupported |

The published contracts are immutable. Neither permits an in-place upgrade from
a stable release. `v0.1.1` permits promotion only from its exact declared alpha
revision.

The selected target tag is authoritative. Check:

- `release/manifest.yaml` for `spec.compatibility` and prerequisites;
- `release/migrations/vX.Y.Z.md` for operator actions, checks, exclusions, and
  recovery limits.

The files must agree. Published `v0.1.0` and `v0.1.1` use immutable legacy
`upgradesFrom` allowlists. Beginning with a future release, compatibility uses
`stableUpgrade`:

- `supported` is the default and permits an upgrade from any exact stable tag
  with a strictly lower SemVer, including a skipped-version upgrade;
- `fresh-install-only` prohibits an in-place stable upgrade.

Every release supports installation into a verified empty or replacement
environment. Downgrades are unsupported.

## Stable Adoption

A client selects one exact signed release tag in
`clusters/prod-eu-1/platform-source.yaml`.

Use `platform.neurwerk.com/adoption-mode` as follows:

- `upgrade`: a legacy target must list the current exact tag in `upgradesFrom`;
  a new-format target must set `stableUpgrade: supported`, and its exact SemVer
  must be strictly newer than the current exact stable tag;
- `fresh-install`: the operator must verify that the target is empty or is a
  replacement environment.

The compatibility check verifies the signed tag, published GitHub Release,
manifest, migration document, adoption mode, and source version. It does not
verify backups, restore data, or prove data integrity. The current schema and
check reject all downgrades.

## Alpha Transitions

Alpha may select `base` `main` or one full commit SHA using the separate alpha
trust root. It is not a published release contract.

Before selecting stable, freeze a changing alpha branch to the observed commit
and reconcile it. A forward upgrade requires that exact commit in the target
manifest's `upgradesFromAlphaRevisions` and migration document. This exact alpha
upgrade contract is unchanged by `stableUpgrade`. Fresh installation instead
requires a verified empty or replacement environment.

## Before a Supported Upgrade

1. Verify the current and target exact signed tags, target manifest,
   prerequisites, packages, exclusions, and supported transition.
2. Review and apply the migration and `Breaking Changes` instructions for every
   crossed release in ascending SemVer order, including the target release.
   Complete any checkpoint only where those instructions require one.
3. Create application-consistent backups outside the production storage failure
   domain. Restore them in a replacement environment and verify integrity.
4. Test the exact transition and recovery action on a disposable cluster.
5. Define application-level readiness checks. A Ready controller or
   `HelmRelease` does not prove that stored data is usable.

Stop if any required evidence or procedure is missing. Do not invent an
intermediate checkpoint or infer support from an upstream compatibility
statement.

Fresh installation does not require per-release upgrade evidence. Before a fresh
installation, verify that the target is empty or is a replacement environment,
then verify the release prerequisites, client values, storage, DNS, certificates,
and external credentials.

## Recovery Actions

Each release declares one of these recovery classifications:

| Action | Meaning | Limit |
| --- | --- | --- |
| Configuration revert | Reconcile an earlier Git or Helm declaration. | Does not restore or downgrade persistent state. |
| Forward-fix | Apply a tested, compatible declaration that repairs the transition. | May not be available after every failure. |
| Component-native restore | Restore an independently verified backup with the component's supported tooling. | Requires a tested restore and integrity check. |
| Replacement restore | Build a separate environment and restore state into it in the documented order. | Use when in-place recovery is unsafe or unproven. |

Retained PVCs and in-cluster snapshots are not independent backups.

## Persistent State

Treat every persistent component as forward-sensitive unless the target release
documents and tests an exact transition.

| Component | Current persistent state | Recovery concern |
| --- | --- | --- |
| Kubernetes and K3s | Control-plane datastore, API objects, and encrypted Secrets | K3s is outside the platform release contract. Back it up and test it separately. |
| Rook/Ceph | OSD device, monitor host data, RBD volumes, RGW objects, and snapshots | The single-node stack is one failure domain. Retention is not disaster recovery. |
| OpenBao and internal CA | Raft volume, static-seal and recovery material, and the cert-manager CA Secret | Snapshot upload is disabled. Verify OpenBao unsealing, certificate issuance, and workload trust. |
| PostgreSQL | Separate authentication and operations claims; operations includes durable AgentGateway request logs | AgentGateway usage records, Dify, Langfuse, LibreChat, and LibreChat RAG share one operations process, volume, maintenance window, and recovery point. Restore each affected instance completely. |
| API-key bridge | SQLite API-key database | Verify restored data and Keycloak authorization. |
| Dify | Operations PostgreSQL, Redis, application files, and plugin files | The sandbox dependency cache is disposable. Classify Redis and file recovery explicitly. |
| LibreChat core | Operations PostgreSQL, Valkey, Meilisearch, compatibility image PVC, and optional RGW objects | Verify conversations, search, cache recovery, and files. `v0.1.0` excludes RAG and Code Interpreter. |
| Langfuse | Operations PostgreSQL, ClickHouse, Redis or Valkey, and RGW objects | Restore and verify traces across all stores. |
| Observability | OpenSearch indices and snapshots, Prometheus metrics, and Alertmanager state | OpenSearch snapshots share the Ceph failure domain. Decide which history requires independent recovery. |
| PII Engine | Valkey state, model cache, and authoritative RGW model objects | Rebuild the cache only from verified model objects. |

## AgentGateway Usage Prerequisite

A target that enables AgentGateway PostgreSQL request logging must declare an
exact `openbao-stack-setup` package version and immutable tooling commit with
reconciliation schema `4`. Before selecting that platform source, run the exact
declared tool and verify successful schema-4 reconciliation. If the target
manifest does not yet contain those exact identifiers, the transition is not
ready; do not invent a release ID, tool version, or commit.

The target release must order operations PostgreSQL before AgentGateway and
AgentGateway before Studio. Treat the new `agentgateway` role, database, and
indefinitely retained metadata-only request logs as persistent forward-sensitive
state covered by the complete operations PostgreSQL backup and restore plan.

## CRD Changes

Upgrade a CRD and its controller as one tested transition. Never use a Git or
Helm rollback to downgrade a CRD storage version.

Current installation paths are:

| Installation path | API families |
| --- | --- |
| Client bootstrap | Flux Source, Kustomize, Helm, and Notification Toolkit CRDs and controllers |
| Out-of-band release prerequisites | Gateway API, cert-manager core, Prometheus Operator, AgentGateway, and External Secrets CRDs |
| Platform charts | cert-manager approver-policy, External Secrets, trust-manager, Rook and ObjectBucket, Ceph CSI Operator, and Kubernetes snapshot CRDs |
| Cluster-provided APIs | K3s `HelmChartConfig` and Traefik `TLSOption` |

The target release manifest declares exact prerequisite versions. An
installation path identifies ownership; it does not guarantee an upgrade path.

## Post-Deployment Checks

After an authorized rollout, inspect reconciliation and warnings:

```bash
flux get sources git -n flux-system
flux get kustomizations -n flux-system
flux get helmreleases -A
kubectl get events -A --field-selector=type!=Normal --sort-by='.lastTimestamp'
```

Then verify the affected applications and persistent data. Review logs without
exposing Secret values or sensitive request content.

If a Kustomization remains in a health-check cycle for an older source revision
after a newer verified revision is available, first inspect its attempted and
applied revisions and the referenced HelmReleases. Do not patch application
resources or HelmRelease values around the failed reconciliation.

For an explicitly authorized recovery of an already-stale in-flight cycle,
restart only the stateless Kustomize controller, wait for it to become
available, and request reconciliation of the affected Kustomization:

```bash
kubectl delete pod -n flux-system -l app=kustomize-controller --wait=true
kubectl rollout status deployment/kustomize-controller -n flux-system --timeout=5m
kubectl annotate kustomization applications -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
```

Recheck the exact source and applied revisions, all Kustomizations and
HelmReleases, warning events, affected workloads, and persistent data. A
controller restart does not authorize a source change or application mutation.
