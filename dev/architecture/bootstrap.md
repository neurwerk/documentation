# Bootstrap and Reconciliation

Each client repository is the Flux entry point for its cluster. The `base/`
repository provides platform release contracts, but it does not bootstrap a
cluster.

## Cluster Entry Point

The cluster root is `clusters/prod-eu-1/kustomization.yaml` in the client
repository. It contains:

| Resource | Purpose |
| --- | --- |
| `flux-system/` | Generated Flux controllers and self-reconciliation |
| `cluster-identity.yaml` | Non-secret client and cluster identity |
| `platform-source.yaml` | Signed platform Git source |
| `namespaces.yaml` | Platform namespace reconciliation |
| `client-values.yaml` | Application and infrastructure ConfigMaps |
| `infrastructure.yaml` | Platform infrastructure reconciliation |
| `applications.yaml` | Platform application reconciliation |

Keep other Flux resources at the cluster root. The `flux-system/` directory is
bootstrap-only and contains `gotk-components.yaml` and `gotk-sync.yaml`.

The root and `flux-system/` Kustomizations must not use name prefixes, labels,
patches, or other transforms.

### Platform Source

The platform `GitRepository`:

- uses anonymous HTTPS;
- selects one exact signed `vX.Y.Z` tag;
- verifies the tag with the namespace-local `k8s-stack-release-trust` Secret;
- sets `platform.neurwerk.com/adoption-target` to the selected tag;
- sets `platform.neurwerk.com/adoption-mode` to `fresh-install` or `upgrade`;
- does not use `include` or other artifact-rewriting fields.

`fresh-install` requires an operator-verified empty or replacement target. A
stable `upgrade` must satisfy the selected release's compatibility contract:
future releases use `stableUpgrade`, while immutable legacy releases retain
their exact `upgradesFrom` allowlists. Skipping stable versions is permitted
when a strictly newer new-format target declares support, but operators must
apply every crossed release's migration and breaking-change instructions in
ascending order. Exact alpha promotion remains a separate allowlist contract.

Provision the private client Git credential and platform release trust Secret
out of band. Never commit either Secret.

## Reconciliation Order

Flux uses explicit `dependsOn` relationships:

```text
namespaces
├── client-infrastructure-values ──> infrastructure ──┐
└── client-app-values ────────────────────────────────┴─> applications
```

All stages wait for readiness before allowing dependent stages to continue.
Directory order does not control reconciliation order.

Platform stage indexes are:

- `base/releases/namespaces/`
- `base/releases/infrastructure/`
- `base/releases/applications/`

The infrastructure and application directories only aggregate packages. Product
manifests remain under `base/releases/<product>/`.

## Prerequisites

Before bootstrapping a cluster:

1. Select and verify the intended Kubernetes context.
2. Provision read-only credentials for the private client repository.
3. Provision `k8s-stack-release-trust` in the `flux-system` namespace.
4. Install the prerequisite APIs and controllers listed in the selected signed
   release's `release/manifest.yaml`.
5. Verify that all images required by enabled workloads are published.
6. Prepare enabled workload dependencies, such as storage devices, DNS records,
   certificates, and dedicated nodes.
7. Prepare secure external storage for the OpenBao custody and recovery files.

Install prerequisite CRDs before Flux applies resources that use them. Current
platform prerequisites include Gateway API, cert-manager, Prometheus Operator,
AgentGateway, and External Secrets APIs. Use the versions declared by the
selected release.

## OpenBao Initialization

Flux creates the OpenBao release, but an operator must initialize it from a
trusted workstation. The release remains pending until `stack-setup` creates
the static-seal Secret.

Run from `tooling/cli_tools/openbao_stack_setup/`:

```bash
uv sync --dev
uv run stack-setup preflight \
  --context <kube-context> \
  --client <client-name>
uv run stack-setup bootstrap \
  --context <kube-context> \
  --client <client-name>
```

Always pass the context and client explicitly. Keep custody files and custodian
packages outside the workspace and all Git repositories.

`stack-setup bootstrap` initializes OpenBao, applies its approved secret catalog,
revokes root access, refreshes the cataloged External Secrets, and reconciles
infrastructure releases that were waiting for generated credentials. Flux can
then complete the infrastructure and application stages.

For an initialized cluster, use `stack-setup reconcile` with two distinct,
cluster-bound custodian packages. The command applies only the catalog compiled
into the tool. It does not accept arbitrary secret paths or policy rules, migrate
application databases, or authorize a platform version change.

See [OpenBao Operations](../operations/openbao.md) for custody requirements,
recovery verification, provider updates, and failure handling.

## Local Validation

Run from a client repository:

```bash
make check
```

To render individual composition layers:

```bash
kustomize build --load-restrictor LoadRestrictionsNone apps >/dev/null
kustomize build --load-restrictor LoadRestrictionsNone infrastructure >/dev/null
kustomize build clusters/prod-eu-1 >/dev/null
```

The relaxed load restriction is required because product generators read
`config/client.yaml` from a parent directory.

## Reconciliation Checks

Use read-only inspection first:

```bash
flux get sources git -n flux-system
flux get kustomizations -n flux-system
flux get helmreleases -A
flux tree kustomization applications -n flux-system
kubectl -n flux-system get configmap neurwerk-stack-identity -o yaml
kubectl get events -A --field-selector=type!=Normal --sort-by='.lastTimestamp'
```

A successful empty-cluster run has:

- every Flux source at the intended revision;
- every Kustomization and enabled HelmRelease Ready;
- no manual resource edits;
- retrying hooks that converge after partial success;
- no persistent errors in affected workload logs.

Do not use a manual HelmRelease reset as a rollout fix. Preserve the failure
evidence, correct the owning chart, values, dependency, or tooling contract, and
repeat the acceptance run.

## Live Model Acceptance

The live acceptance target tests AgentGateway, model access, and PII enforcement.
It is not part of `make check` and does not test Dify initialization.

Run it from `base/` only after the required images are published and pinned:

```bash
LIVE_ACCEPTANCE_CONFIRM=I_CONFIRM_LIVE_AGENTGATEWAY_ACCEPTANCE \
LIVE_ACCEPTANCE_EXPECTED_CONTEXT=<context> \
LIVE_ACCEPTANCE_EXPECTED_CLIENT=<client> \
LIVE_ACCEPTANCE_AGENTGATEWAY_URL=https://<agentgateway-host> \
LIVE_ACCEPTANCE_MODEL_ID=<model-id> \
LIVE_ACCEPTANCE_API_KEY=<environment-injected-key> \
make live-acceptance
```

The runner reads the current Kubernetes context, stack identity ConfigMap, and
AgentGateway `client-values` ConfigMap. It does not read Kubernetes Secrets and
redacts credentials and response bodies from failures.
