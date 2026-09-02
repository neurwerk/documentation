# File Structure

Use product-oriented paths. Keep these layers separate:

```text
chart source != platform release contract != client values != cluster composition
```

Do not add technical category directories such as `auth/`, `frontend/`,
`infra/`, or `monitor/` around product paths. Existing Kubernetes namespaces
and resource names may keep their established prefixes.

## Platform Repository

The `base/` repository owns Helm charts, platform release contracts,
namespaces, platform defaults, and release metadata.

```text
base/
├── charts/
│   └── <product>/                     Helm chart source
│       └── <component>/               optional component chart
├── releases/
│   ├── namespaces/                    Namespace manifests
│   ├── infrastructure/                infrastructure stage index
│   ├── applications/                  application stage index
│   ├── shared/                        platform defaults
│   └── <product>/                     HelmRelease contracts and defaults
├── release/
│   ├── config.yaml                    reviewed release inputs
│   ├── manifest.yaml                  generated release manifest
│   ├── manifest.schema.json           release manifest schema
│   ├── migrations/                    release transition requirements
│   └── trust/                         public release verification keys
├── scripts/                           release and validation scripts
├── tests/
├── VERSION
├── CHANGELOG.md
└── Makefile
```

### Release Packages

`releases/infrastructure/` and `releases/applications/` contain only stage
Kustomizations. Product manifests remain under `releases/<product>/`.

Release filenames normally match the chart's leaf component:

| Chart | Release contract |
| --- | --- |
| `charts/dify/web/` | `releases/dify/web.yaml` |
| `charts/studio/api/` | `releases/studio/api.yaml` |
| `charts/keycloak/realm-config/active-directory/` | `releases/keycloak/active-directory.yaml` |

LibreChat release contracts use `core/`, `rag/`, and `code-interpreter/`
subgroups. The default application stage includes only `core/`.

`releases/shared/` contains platform defaults only. Never place client facts in
this directory.

`release/` contains publication metadata. Flux does not reconcile this path.

## Client Repositories

Client repositories own non-secret client facts, product values, generated
ConfigMaps, and cluster composition.

```text
client_*/
├── config/
│   └── client.yaml                    shared non-secret client facts
├── apps/
│   ├── kustomization.yaml             application values index
│   └── <product>/
│       ├── values.yaml                product-specific values
│       └── kustomization.yaml         ConfigMap generator or subgroup index
├── infrastructure/
│   ├── kustomization.yaml             infrastructure values index
│   ├── networking/<product>/
│   ├── observability/<product>/
│   ├── security/<product>/
│   └── storage/<product>/
├── clusters/
│   └── prod-eu-1/
│       ├── flux-system/               generated Flux bootstrap files only
│       ├── applications.yaml
│       ├── client-values.yaml
│       ├── cluster-identity.yaml
│       ├── infrastructure.yaml
│       ├── kustomization.yaml
│       ├── namespaces.yaml
│       └── platform-source.yaml
├── scripts/
├── tests/
└── Makefile
```

Product Kustomizations generate stable, namespace-local ConfigMaps:

- `client-values` from `config/client.yaml`;
- `<product>-product-values` from the product's `values.yaml`.

`config/client.yaml` has no Kustomization. Product Kustomizations read it
directly from the Flux source artifact.

Some products use subgroup Kustomizations. LibreChat stores shared product
values in `apps/librechat/values.yaml` and generates ConfigMaps from `core/` and
`code-interpreter/`. PostgreSQL stores shared values in
`infrastructure/storage/postgres/values.yaml` and generates namespace-local
ConfigMaps from `auth/` and `operations/`.

Client repositories do not contain HelmRelease resources, chart source,
platform Namespace objects, or secret values.

## Application Repositories

Python services use a `src` layout:

```text
<service>/
├── src/<package>/
├── tests/
├── pyproject.toml
├── uv.lock
└── Dockerfile
```

Studio is a mixed Python and TypeScript workspace:

```text
studio/
├── apps/
│   ├── api/                            Python API
│   └── web/                            TypeScript web application
├── package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
└── turbo.json
```

Service behavior, API contracts, Dockerfiles, and service tests belong in the
service repository, not in platform charts.

## Tooling Repository

The `tooling/` repository separates Kubernetes job commands from workstation
utilities:

```text
tooling/
├── src/k8s_stack_tooling/              commands included in the tooling image
├── tests/
├── Dockerfile
└── cli_tools/
    └── <project>/                      independently locked Python project
        ├── src/<package>/
        ├── tests/
        ├── pyproject.toml
        ├── uv.lock
        └── README.md
```

`cli_tools/` is excluded from the tooling package and container image.

## Tests

Keep tests in the owning repository's `tests/` directory. Use product names and
mirror the source or manifest under test. Do not create technical category
wrappers such as `auth/`, `frontend/`, `infra/`, or `monitor/`.
