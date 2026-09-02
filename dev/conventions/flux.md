# Flux Conventions

Client repositories own Flux cluster composition. They consume platform
namespaces and release contracts from a separate Git source.

## Git Sources

Each cluster has:

- `GitRepository/flux-system`: the private client repository, cluster
  composition, and non-secret client values.
- `GitRepository/k8s-stack`: the public platform repository, namespaces, and
  `HelmRelease` packages.

The private source uses its own Git credential. The public source uses anonymous
HTTPS. Keep the Git credential separate from the platform release trust key.

### Stable Platform Source

A production platform source must:

- select one exact signed `vX.Y.Z` tag;
- use Flux tag verification with the operator-provisioned
  `k8s-stack-release-trust` Secret;
- set `platform.neurwerk.com/adoption-target` to the selected tag;
- set `platform.neurwerk.com/adoption-mode` to `fresh-install` or `upgrade`;
- keep the canonical `interval`, public URL, `ref`, and `verify` fields.

Do not use a branch, SemVer range, `include`, or another field that changes the
verified source artifact. Change the adoption mode only when changing the tag.

Do not commit the release trust Secret, Git credentials, or `.sourceignore`
files. Keep the cluster root and `flux-system` Kustomizations transform-free.
The client compatibility check protects their resource lists, generated Flux
bootstrap files, and controller bundle.

## Cluster Kustomizations

Flux `Kustomization` objects live directly in `clusters/prod-eu-1/`.
`clusters/prod-eu-1/flux-system/` contains only generated controller and
self-sync manifests.

The required dependency graph is:

```text
namespaces -> client-infrastructure-values -> infrastructure -> applications
namespaces -> client-app-values -----------------------------> applications
```

For each Kustomization:

- use `spec.dependsOn` for ordering;
- use `wait: true` or explicit health checks for readiness;
- set a timeout that covers the slowest expected resource;
- set `prune: true` for Git-owned resources;
- use one source and one path.

Keep the graph acyclic. Do not use overlapping paths: each resource must have
one Flux inventory owner.

### Readiness

When `wait: false`, list every required HelmRelease and Gateway in
`healthChecks`. Include enabled optional releases so their failures make the
stage fail.

Gateway health expressions ignore stale conditions by matching
`observedGeneration` to the current generation. Treat `InvalidCertificateRef`
as in progress while cert-manager creates the first TLS Secret. Treat
`RefNotPermitted` as failed. The stage timeout handles other unresolved errors.

## Helm Releases

Use Flux Kustomization dependencies for stage ordering. Use
`HelmRelease.spec.dependsOn` when one release requires another release to be
ready.

ConfigMaps and Secrets in `valuesFrom` must be in the HelmRelease namespace.
Later references override earlier references.

Use `RetryOnFailure` for both installation and upgrade. The standard retry
interval is one minute. A component with slower recovery may use a documented
two-minute interval. Persistent failures remain visible in release conditions
and alerts.

## Naming

- Use the stage names `namespaces`, `client-infrastructure-values`,
  `infrastructure`, `client-app-values`, and `applications`.
- Name releases after their product or component.
- Use product names in paths.

## Validation and Inspection

Run local validation from the client repository:

```bash
make yaml-lint
kustomize build --load-restrictor LoadRestrictionsNone apps >/dev/null
kustomize build --load-restrictor LoadRestrictionsNone infrastructure >/dev/null
kustomize build clusters/prod-eu-1 >/dev/null
```

Inspect a cluster with read-only Flux commands:

```bash
flux get sources git -n flux-system
flux get kustomizations -n flux-system
flux tree kustomization applications -n flux-system
```

See the Flux documentation for
[repository structure](https://fluxcd.io/flux/guides/repository-structure/),
[Kustomizations](https://fluxcd.io/flux/components/kustomize/kustomizations/),
and [HelmReleases](https://fluxcd.io/flux/components/helm/helmreleases/).
