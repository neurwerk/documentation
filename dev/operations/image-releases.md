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
lists the immutable tags that may be pinned in `base/`.

| Repository | Version source | Immutable image tags | Platform consumers |
| --- | --- | --- | --- |
| `pii_engine/` | `pyproject.toml`, `uv.lock` | `k8s-stack-pii-engine:<version>-cpu`, `k8s-stack-pii-engine:<version>-cu124` | `charts/pii-engine/`, `charts/pii-engine-model-sync/` |
| `agentgateway_extproc/` | `pyproject.toml`, `uv.lock` | `k8s-stack-agentgateway-extproc:<version>` | `charts/agentgateway-extproc/` |
| `keycloak_api_key_bridge/` | `pyproject.toml`, `uv.lock` | `k8s-stack-keycloak-api-key-bridge:<version>` | `charts/keycloak-api-key-bridge/` |
| `studio/` | `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/web/package.json` | `k8s-stack-studio-api:<version>`, `k8s-stack-studio-web:<version>` | `charts/studio/api/`, `charts/studio/web/` |
| `tooling/` | `pyproject.toml`, `uv.lock` | `k8s-stack-tooling:<version>` | Every matching value under `base/charts/` |

PII Engine publishes CPU and CUDA variants from one release tag. Studio
publishes API and Web images from one release tag, so its API and Web versions
must match.

The Tooling image is an auxiliary image in its consuming charts. Bump each
affected chart's `version`, but keep the product's existing `appVersion`.

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

- source commit: `cdfe54c3498818b21b33fb609fee02f2742b37ea`;
- image: `ghcr.io/danny-avila/librechat-dev@sha256:f309d33a0f0b22fe5d3a804c5d197f40d58e69f74d49b68f250cbc502da7e6b2`.

This temporary exception expires on `2026-09-30`, as defined in
`base/release/config.yaml`. It permits only that digest and source commit. It
does not permit a moving development tag, `latest`, another commit, or a release
candidate. Replace it with a reviewed immutable upstream release before expiry.

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
