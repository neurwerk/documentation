# Image Releases

Publishing an image, updating its platform pin, and deploying it are separate
operations. Complete and verify each operation before starting the next.

## Release Rules

- Treat Git tag creation and publication as release actions. Do not create or
  push a release tag without explicit authorization.
- CI-managed images publish from an exact `vX.Y.Z` tag that matches the
  repository's declared version.
- CI-managed images target `linux/amd64` and do not publish `latest`.
- Some workflows publish a moving `<major>.<minor>` alias. Never use that alias,
  `latest`, or another moving tag in `base/`.
- Verify the full versioned image tag and digest before updating `base/`.
- Bump every affected chart's `version` when an image pin changes. A patch bump
  is normally appropriate.
- Update `appVersion` only when it represents the released application. Do not
  set it to the version of an auxiliary image.
- A published image or merged platform change does not authorize deployment.
  Contact or modify a cluster only when the user explicitly requests it.

## CI-Managed Images

All image names in this table use the `ghcr.io/neurwerk/` prefix. The tag column
lists immutable tag formats, not proof of publication or verified CI. Only
published, verified images may be pinned in `base/`.

| Repository | Version source | Immutable image tags | Platform consumers |
| --- | --- | --- | --- |
| `pii_engine/` | `pyproject.toml`, `uv.lock` | `k8s-stack-pii-engine:<version>-cpu`, `k8s-stack-pii-engine:<version>-cu124` | `charts/pii-engine/`, `charts/pii-engine-model-sync/` |
| `agentgateway_extproc/` | `pyproject.toml`, `uv.lock` | `k8s-stack-agentgateway-extproc:<version>` | `charts/agentgateway-extproc/` |
| `keycloak_api_key_bridge/` | `pyproject.toml`, `uv.lock` | `k8s-stack-keycloak-api-key-bridge:<version>` | `charts/keycloak-api-key-bridge/` |
| `keycloak_theme/` | `VERSION` | `k8s-stack-keycloak-theme:<version>` | `charts/keycloak/server/` on alpha `main`; existing stable tags unchanged |
| `studio/` | `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/web/package.json` | `k8s-stack-studio-api:<version>`, `k8s-stack-studio-web:<version>` | `charts/studio/api/`, `charts/studio/web/` |
| `tooling/` | `pyproject.toml`, `uv.lock` | `k8s-stack-tooling:<version>` | Every matching value under `base/charts/` |

PII Engine publishes CPU and CUDA variants from one release tag. Studio
publishes API and Web images from one release tag, so its API and Web versions
must match.

### PII Engine 0.8.0 CPU-Only Adoption Exception

On 2026-09-15, the user explicitly authorized Base adoption of the published
`ghcr.io/neurwerk/k8s-stack-pii-engine:0.8.0-cpu` image without waiting for CUDA
or the combined GitHub Release. This is a scoped exception to the GitHub Release
verification prerequisite below, not a waiver of image verification:

- Tag `v0.8.0` resolves to source `d3bf3595f94e3fee0e33c6eae89ac4377474ee6e`.
- [CPU publication job 104361602237](https://github.com/neurwerk/k8s_stack_pii_engine/actions/runs/34963163582/job/104361602237)
  succeeded, including registry digest, `linux/amd64`, and source-revision checks.
- Its `pii-engine-cpu-digest` artifact records
  `sha256:2cfb28997c8063938c96bd414093f5395da2c102015b7269a84157d3cfdb0fc9`.

The adoption updates all CPU image defaults in both Engine and model-sync
charts, with chart versions `1.0.3` and `1.0.2` respectively and application
version `0.8.0`. Model bundle pins remain unchanged. CUDA publication is not an
adoption gate for these CPU consumers and no CUDA pin is added. This exception
does not establish merge, deployment, client adoption, or Base `0.3.7` publication.

### PII Engine 0.8.1 CPU-Only Publication Verification

On 2026-09-15, the user explicitly authorized merging PII Engine
[PR #13](https://github.com/neurwerk/k8s_stack_pii_engine/pull/13), publishing
`v0.8.1`, and completing CPU verification without waiting for CUDA or the combined
GitHub Release. This publication-only exception does not extend the `0.8.0`
Base adoption exception above or authorize image pin changes or deployment.

- PR #13 was squash-merged and tag `v0.8.1` resolves to
  `a0883dee93333f05af5ba19034c34dcc87dbe230`.
- [CPU publication job 104388944955](https://github.com/neurwerk/k8s_stack_pii_engine/actions/runs/34971499708/job/104388944955)
  succeeded, including registry digest, `linux/amd64`, and source-revision checks.
- Its `pii-engine-cpu-digest` artifact records
  `sha256:a829987654971c87d802f6ba3059d19caf69bc3e969a95bebee62986355cd76a`
  for `ghcr.io/neurwerk/k8s-stack-pii-engine:0.8.1-cpu`.

CUDA was still building when CPU verification completed. The unchanged workflow
publishes the combined GitHub Release only after both variants succeed; this
record does not assert CUDA or combined Release completion.

The user subsequently authorized updating Base [PR #152](https://github.com/neurwerk/k8s_stack_base/pull/152)
to adopt this verified `0.8.1-cpu` image in Engine and model-sync, superseding
the unmerged `0.8.0-cpu` pins without waiting for CUDA or the combined Release.
This extends the CPU-only adoption exception to the exact artifact above.
The cumulative chart versions remain `1.0.3` and `1.0.2`, with both appVersions
set to `0.8.1`. The same PR adopts published extProc
[`0.7.1`](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/releases/tag/v0.7.1)
from `e50450d50849d9254fb9d87d6090d9cd92f3947e`, pinned to
`sha256:59bb5a51192dbbb01ba5cb30c4d4b182c5fde2c3ae8c3193b3eda1cb6de3fbe6`,
in chart `1.0.5`. Together these images accept 20,000-character tool descriptions.
Base merge, platform publication, client adoption, and deployment remain separate
actions; none is established by this pin update.

### Document Extraction Images

- PII [PR #15](https://github.com/neurwerk/k8s_stack_pii_engine/pull/15) merged at
  `a2a6dea4a8d81eb9083e8439689fa6ba8a95a03f` and published `v0.9.0`;
  [workflow 35275538359](https://github.com/neurwerk/k8s_stack_pii_engine/actions/runs/35275538359)
  passed both CPU/CUDA jobs and the GitHub Release job.
- extProc [PR #29](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/pull/29)
  merged at `fc87d020637fd20f740a4ae75b268cef8ad80a38` and published `v0.8.0`;
  [workflow 35278793398](https://github.com/neurwerk/k8s_stack_agentgateway_extproc/actions/runs/35278793398)
  passed all jobs, including the GitHub Release.

Registry tag digests, `linux/amd64` platform and source-revision labels were also
independently verified for all three images under `ghcr.io/neurwerk/`:

| Image | Verified Digest |
| --- | --- |
| `k8s-stack-pii-engine:0.9.0-cpu` | `sha256:1f0025caf4d39ddfd4b12d0d70c9718ae14a42400c2342f1d553831472bc3779` |
| `k8s-stack-pii-engine:0.9.0-cu124` | `sha256:09577898fad3de6380cc4b497470d97024a120a8e5f02a61e928dd4df588a261` |
| `k8s-stack-agentgateway-extproc:0.8.0` | `sha256:908d088a10014f0f868f2d04a9bbf3521f1659966af7c2583c4746fa660d74f5` |

[Base PR #185](https://github.com/neurwerk/k8s_stack_base/pull/185) merged wiring
and the PII CPU/extProc pins above at `5c9e0c8c3e9a39cca8b9405c716d43bf805f80f4`.
Those service versions were observed live and Ready through the Base alpha source,
not a stable publication. CPU Docling is deployed and synthetic TXT/PDF conversion
followed by PII analysis passed. The final client upload switch remains off while
storage health blocks dependent releases; end-to-end chat dispatch is not yet
verified. See [document extraction](../architecture/docling.md).

### Auxiliary Tooling Image

The Tooling image is an auxiliary image in its consuming charts. Bump each
affected chart's `version`, but keep the product's existing `appVersion`.

Tooling [v0.6.2](https://github.com/neurwerk/k8s_stack_tooling/releases/tag/v0.6.2)
is published from `03f5767f6716da1838b8d248317ae4d7b96a3953`, with verified manifest
digest `sha256:299ded44d76d5a73e3c1045af09b02649b08a3b5f00d07a993e3be7c61a490fd`
and a `linux/amd64` image. Maintenance chart `0.1.1` is its new consumer; this
additive rollout does not update existing initialization-job consumers. See
[On-Demand Maintenance](maintenance.md) for alpha acceptance and idle state.

### Keycloak Theme Image

`keycloak_theme/` (`neurwerk/k8s_stack_keycloak_theme` on GitHub) owns the native
`neurwerk` login/email theme and a Dockerfile image extending Keycloak `26.7.2`.
The upstream Keycloak base image is digest-pinned in the Dockerfile. Published
artifacts for the name/logo-only integration are:

| Image (under `ghcr.io/neurwerk/`) | Digest | Source |
| --- | --- | --- |
| `k8s-stack-keycloak-theme:0.1.1` | `sha256:4b94ab5b56f7784c487c1716d6229f82de3a67246640221792709192e885de5d` | `54d037ac60653358d574e0ae46fcad4b51b65f1e` |
| `k8s-stack-tooling:0.6.1` | `sha256:60829618924ae8121817a2039faecff2dbf881debef852f84bec7c1ceb03a805` | `f15bc5b51b12db8e9c138057f78c3ac7150bc44d` |

Theme `0.1.1` adds PNG/SVG logo selection through `companyLogoFormat`, retaining
fixed shared styles and templates. Local disposable PNG and SVG login/email
previews passed; no new test framework was added. Tooling
[v0.6.1](https://github.com/neurwerk/k8s_stack_tooling/releases/tag/v0.6.1) is
unchanged and provides explicit realm theme handling with omitted settings left
unchanged.

The earlier Base commit `0cb8931` pins theme `0.1.0` and Tooling `0.6.1` and bumps
all 11 Tooling-consuming chart versions without changing their product
`appVersion`. The authorized alpha
rollout verified signed source reconciliation, healthy Helm releases, live
desktop/mobile login and reset pages, the selected login/email themes, and
unchanged realm user/client/role counts. Production reset emails were not sent;
email rendering and reset completion were checked in the disposable preview.
PNG/SVG support and the `0.1.1` pin are merged at `94c69da`; existing PNG login/reset
pages were verified live on alpha. Signed Base
[v0.3.5](https://github.com/neurwerk/k8s_stack_base/releases/tag/v0.3.5) is published
at `b016489`, with its `published-platform-release` identity artifact verified.
An authorized stable client's public desktop/mobile login and reset pages were
verified with the supplied SVG; internal cluster health was not inspected. See
[Native Theme](../authentication/keycloak.md#native-theme) for the fixed shared
templates, child-theme values, and two-step removal contract.

### Publish A Service Image

1. Update every declared version source and lockfile in the service repository.
2. Run the formatting, linting, type checking, tests, and build checks defined by
   that repository.
3. Merge the reviewed release-ready change into `main`.
4. With explicit release authorization, create and push `v<version>` from the
   release commit.
5. Verify the GitHub Actions run, GitHub Release, full image tag, and digest.

The package checker reports published package and workflow state. It does not
report what is deployed in Kubernetes.

```bash
cd tooling/cli_tools/package_checker
uv run package-checker --json
```

### Update Platform Pins

1. In `base/`, search all charts for the old image tag.
2. Update every consumer to the full versioned tag.
3. Bump each affected chart's `version`.
4. Update `appVersion` where it represents the released application.
5. Regenerate the platform release manifest and validate the change:

   ```bash
   make release-manifest
   make kustomize-validate
   make helm-lint
   make helm-validate
   make release-check
   ```

6. Review and merge the coordinated `base/` pull request.

## Dify Images

Dify image builds are user-operated because they are too large for the current
GitHub-hosted build path. An agent must not run a Dify build, execute
`dify_ce_builder/deploy.sh`, or push a Dify image.

Give the user this command and wait for them to run it:

```bash
cd dify_ce_builder
./deploy.sh <immutable-overlay-version>
```

The overlay version must begin with the value in `DIFY_VERSION`, followed by
`-`, such as `1.15.0-kc-v15`. The script requires a clean checkout at the current
canonical `origin/main`. Its prompts default to both images, `linux/amd64`, and a
registry push.

The script publishes only the requested immutable tag. It rejects `latest` and
existing final tags. API and Web publication is sequential, so a failure can
leave a partial release.

Wait for the user to confirm the exact tags and digests before updating `base/`:

| Image | Platform consumers |
| --- | --- |
| `addon-dify-ce-builder-api:<overlay-version>` | `charts/dify/api/`, `charts/dify/beat/`, `charts/dify/worker/` |
| `addon-dify-ce-builder-web:<overlay-version>` | `charts/dify/web/` |

For an upstream Dify update, update and verify `DIFY_VERSION`, the API image
digest, the source revision, the source archive checksum, and the related
provenance and overlay files. Then publish new API and Web tags, update all four
chart pins, versions, and `appVersion` values.

For an overlay-only update, publish a new overlay tag and bump the affected
chart versions. Keep the upstream Dify `appVersion` unchanged.

## LibreChat Images

LibreChat components use third-party images rather than images from a workspace
service repository.

### Core Image Exception

The core chart currently uses this reviewed source and exact multi-architecture
digest:

- source commit: `eaed216994b2604e050966cd6eaf3c2bdd359233`;
- image: `ghcr.io/danny-avila/librechat-dev@sha256:d05623decc48482bd83560248eb6efbdb5e60ea844298ab2fbaa70b462feb611`;
- publication: upstream [Docker Dev Images Build run 34323899158](https://github.com/danny-avila/LibreChat/actions/runs/34323899158), successful for that exact source; its manifest merge records the digest above.

This temporary exception expires on `2026-09-30`, as defined in
`base/release/config.yaml`. It permits only that digest and source commit. It
does not permit a moving development tag, `latest`, another commit, or a release
candidate. Replace it with a reviewed immutable upstream release before expiry.

This deliberately replaces the previous `cdfe54c3498818b21b33fb609fee02f2742b37ea`
exception; it does not extend the expiry. The app's permission provisioning hook
uses the same pinned image and upstream model/cache APIs. Before another pin
change, verify the packaged `createModels`, `createMethods`, `updateRoleByName`,
`getRoleByName`, `standardCache`, Redis readiness, and tenant/cache-key behavior
against the target image. Run the executable adapter tests and verify the hook
against the actual target image. Confirm startup preserves both role permission
blocks when global agent/marketplace interface overrides are absent. A swallowed
database failure, stale cache, missing module, or deadline must not report success.

The current main-branch contract is an alpha change, not a modification of the
published `v0.3.3` tag or authorization to adopt it on stable clients. Operations
PostgreSQL must reconcile the provisioning identity's ingress before the LibreChat
app hook runs. Verify the Job result, effective endpoints, database/cache policy,
application readiness, and persistent application data after authorized adoption.

The Admin Panel uses a reviewed upstream version tag. The RAG API also uses an
upstream version tag, but its package remains excluded in
`base/release/config.yaml` because deployment readiness is incomplete.

### Code Interpreter Images

The Code Interpreter package is excluded in `base/release/config.yaml` because
its first-party versioned runtime images have not been published. Current GHCR
references under `charts/librechat/code-interpreter/` are placeholders. Do not
deploy or mirror them.

Before enabling this package:

1. Add an owned, reproducible build for every required component.
2. Publish all images from an explicit version tag with source provenance.
3. Verify every image and required architecture.
4. Replace all placeholders with immutable versioned tags.
5. Bump every affected chart's `version` and update the release manifest.

## Deployment Verification

Confirm the Kubernetes context before contacting a cluster. After an explicitly
authorized GitOps deployment, inspect reconciliation and warning events:

```bash
flux get sources git -n flux-system
flux get kustomizations -n flux-system
flux get helmreleases -A
kubectl get events -A --field-selector=type!=Normal --sort-by='.lastTimestamp'
```

Review affected workload logs without exposing Secret values or sensitive
request content. Do not use mutable tags or direct workload restarts as a
deployment shortcut.
