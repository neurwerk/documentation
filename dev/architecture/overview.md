# Stack Architecture

This workspace contains separate repositories for platform configuration,
client configuration, application code, tooling, and documentation. Put each
change in the repository that owns it.

Keep these layers separate:

```text
chart source != platform release contract != client values != cluster composition
```

## Repository Responsibilities

| Repository | Responsibility |
| --- | --- |
| `base/` | Charts in `charts/`, platform contracts and defaults in `releases/`, publication metadata in `release/`, and platform validation |
| `client_*/` | Client facts in `config/`, values and ConfigMaps in `apps/` and `infrastructure/`, and the Flux graph in `clusters/` |
| Service repositories | Application behavior, APIs, tests, Dockerfiles, and images |
| `dify_ce_builder/` | Owned Dify overlay and image build |
| `tooling/` | Kubernetes initialization commands and trusted-workstation tools |
| `docs/` | Cross-repository architecture, conventions, and runbooks |

`base/releases/infrastructure/` and `base/releases/applications/` are stage
indexes only. Product releases stay under `base/releases/<product>/`, while
platform-wide defaults stay under `base/releases/shared/`. The `base/release/`
directory contains publication metadata and is not reconciled by Flux.

Client repositories do not contain charts, platform `HelmRelease` resources,
platform namespace objects, or secret values.

## Platform Release

Production clients select one exact, signed platform tag in
`clusters/prod-eu-1/platform-source.yaml`. That tag determines the effective
platform contract.

The selected tag's `release/manifest.yaml` records compatibility,
prerequisites, included and excluded packages, and artifact versions. A chart or
release file existing in `base/` does not mean that the selected platform release
includes it.

## Flux Reconciliation

Each cluster combines two Git sources:

```text
client source   -> cluster graph, identity, and client values
platform source -> namespaces and platform releases
```

The client source self-syncs over SSH using a Kubernetes Secret. The stable
platform source uses anonymous HTTPS and verifies the selected tag with the
operator-provisioned `k8s-stack-release-trust` Secret. The Git credential and
cluster trust Secret are provisioned outside Git.

Kustomize groups manifests. Flux `Kustomization.spec.dependsOn`, readiness
checks, and `HelmRelease.spec.dependsOn` define reconciliation order. Directory
order does not.

See [Bootstrap and Reconciliation](bootstrap.md) for the dependency graph,
prerequisites, and operator actions.

## Configuration and Secrets

A `HelmRelease` can use the following value sources. Each release uses only the
sources it needs:

```text
chart defaults
-> platform shared defaults
-> product release defaults
-> OpenBao-backed Secret values
-> client-values
-> <product>-product-values
-> inline HelmRelease values
```

Later `valuesFrom` entries override earlier entries. Inline values override all
`valuesFrom` entries. Referenced ConfigMaps and Secrets must be in the same
namespace as the `HelmRelease`.

Customer-specific domains, identity policy, sizing overrides, physical storage
topology, and feature selections belong in the client repository. Credentials
and other confidential values belong in OpenBao. External Secrets creates the
namespace-local Kubernetes Secrets used at runtime.

## Subsystems

- [Bootstrap and reconciliation](bootstrap.md)
- [Secrets](secrets.md)
- [Certificates and trust](certificates.md)
- [Routing](routing.md)
- [Network isolation](networking.md)
- [Shared PostgreSQL](postgresql.md)
- [Rook/Ceph storage](rook-ceph.md)
- [LibreChat](librechat.md)
- [Observability](observability.md)
- [PII policy engine](pii-policy-engine.md)
- [Authentication](../authentication/overview.md)
- [Supported upgrades](../operations/upgrades.md)

See [File Structure](../conventions/file_structure.md) for the canonical paths.
