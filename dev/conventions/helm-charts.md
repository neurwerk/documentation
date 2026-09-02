# Helm Chart Conventions

Helm charts define Kubernetes resources and chart-safe defaults. Platform
release packages define how Flux installs those charts.

## Chart Location

Store charts in `base/charts/` under a product-oriented path:

```text
charts/<product>/
charts/<product>/<component>/
```

Use lowercase letters, numbers, and hyphens in chart metadata names. New chart
names must be unambiguous across the platform.

Treat existing chart metadata and Kubernetes resource names as deployed
identities. Do not rename them as unrelated cleanup.

## Chart Contents

- Put safe, environment-independent defaults in `values.yaml`.
- Document each public value near its declaration.
- Group related values in maps and keep override paths predictable.
- Use helper templates for repeated names and labels.
- Do not create `Namespace` resources in charts. The platform namespace stage
  owns them.
- For charts with dependencies, commit `Chart.lock` and the archives in the
  chart's `charts/` directory.
- Do not hardcode customer domains, credentials, storage devices, or sizing.
  Receive non-secret customer settings through values and secrets through
  Kubernetes Secrets.

See [Configuration Conventions](configuration.md) for the value layers and
secret boundary.

## Platform Releases

Define deployable charts with platform-owned `HelmRelease` resources under
`base/releases/<product>/`. A product package may also contain:

- a `kustomization.yaml` file;
- product release defaults;
- related non-chart resources;
- multiple component `HelmRelease` resources.

Release filenames normally match the leaf chart component. Product subgroups
may be flattened when the current release package does so. Examples:

```text
charts/keycloak/realm-config/realm-roles/ -> releases/keycloak/realm-roles.yaml
charts/postgres/auth/                     -> releases/postgres/auth.yaml
```

`releases/infrastructure/` and `releases/applications/` only aggregate product
packages. Keep product manifests in `releases/<product>/`.

## Kubernetes Metadata

Follow the [Kubernetes name and label contract](kubernetes.md#namespaces-and-resource-identity).
Reuse helpers for repeated query labels. Keep selector labels minimal and
stable. Use annotations for controller behavior, hooks, checksums, and
operational metadata.

## Validation

Run these commands from `base/`:

```bash
make helm-lint
make helm-validate
make kustomize-validate
```

These targets verify committed chart dependencies without changing them. Run
`make helm-deps` only when intentionally rebuilding dependency archives.

Also follow Helm's official
[chart best practices](https://helm.sh/docs/chart_best_practices/) unless a
platform convention is stricter.
