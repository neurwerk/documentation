# Platform Releases

The `base` repository publishes the complete platform contract. A release binds
charts, HelmRelease resources, runtime pins, prerequisites, compatibility, and
operator instructions to one signed Git tag.

Platform versions are separate from chart, application, and image versions.

## Release Contract

Platform tags use strict SemVer in the form `vX.Y.Z`. Each new version must be
newer than the previous signed release.

Compatibility is explicit. Published `v0.1.0` and `v0.1.1` retain their
immutable legacy stable-source allowlists. Current-format releases use
`compatibility.stableUpgrade`, explicitly `supported` or
`fresh-install-only`. `supported` is the default and permits any strictly
forward transition between exact stable SemVer tags, including skipped
versions. Alpha promotion remains limited to exact commits listed by the target
release.

The latest published release is `v0.3.6` (2026-09-14). It declares
`stableUpgrade: supported`, no alpha source revisions, unsupported downgrades,
and forward-fix recovery. Publication does not establish live client adoption.
See [Current Support](upgrades.md#current-support); published contracts remain
immutable.

[Platform v0.3.6](https://github.com/neurwerk/k8s_stack_base/releases/tag/v0.3.6)
is published at `da27cd98e09874c3d3f89fc074e964e226d6773e`, prepared by
[Base PR #110](https://github.com/neurwerk/k8s_stack_base/pull/110). It includes
streaming/MCP fixes, Studio `0.9.0`, and Keycloak theme `0.1.2`. The approved SSH
signature and publication identity artifact were verified. Client adoption uses
a separate reviewed PR; live checks remain operator-owned.

Every platform release supports installation into a verified empty or
replacement environment; fresh installation is not a release-specific
compatibility field. Downgrades are unsupported.

Each release commit contains:

| File | Purpose |
| --- | --- |
| `VERSION` | Version without the leading `v` |
| `CHANGELOG.md` | Curated changes and compatibility summary |
| `release/config.yaml` | Reviewed release, compatibility, package, prerequisite, exception, trust, and provenance inputs |
| `release/manifest.yaml` | Generated platform artifact inventory |
| `release/migrations/vX.Y.Z.md` | Operator actions, checks, and recovery limits |

The manifest records charts, chart application versions, Helm dependencies,
HelmRelease resources, runtime images, packages, prerequisites, exceptions,
compatibility, trust, and provenance. `make release-check` compares the committed
manifest with generated output and rejects drift.

The signed tag and its exact commit are the release source of truth. The GitHub
Release presents the reviewed changelog, migration instructions, and generated
pull request notes. It does not replace the manifest.

## Trust Contract

The platform release signer has this identity:

| Field | Value |
| --- | --- |
| Principal | `platform-release` |
| Namespace | `git` |
| Algorithm | `ssh-ed25519` |
| Fingerprint | `SHA256:+rDcofrsfRE3ElJJxnUVoB3gmoEzZJUrisDqLZMHimw` |
| Public key | `release/trust/platform-release.sshpub` |

Configure `PLATFORM_RELEASE_ALLOWED_SIGNER` with this exact OpenSSH
allowed-signers line:

```text
platform-release namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOaoKMNPBk8+i23jqEmS7rwXso1HjEoe+8iDIXiJkLeD
```

Authenticate the fingerprint through an operator-controlled channel before
configuring CI or a client. Do not establish trust from the repository or tag
that the key will verify.

The private key stays outside GitHub, repositories, CI, and Kubernetes. The
operator signs through an SSH agent by giving Git the public key path. Repository
rules must prevent updates and deletion of `refs/tags/v*`. Never move or reuse a
release tag.

Flux clients select one exact tag and verify it with public key material:

```yaml
ref:
  tag: vX.Y.Z
verify:
  mode: Tag
  secretRef:
    name: k8s-stack-release-trust
```

`k8s-stack-release-trust` contains only trusted public key material and must not
be committed.

## Prepare a Release

Publish and verify required images through the
[image release process](image-releases.md) before preparing the platform release.

1. Open a release proposal with the `base` release issue form. It creates a
   native `Task` classified as `release: platform`.
2. Merge the reviewed implementation work included in the release. Update chart
   metadata whenever packaged chart content changed.
3. Run the manual `Prepare Release PR` workflow in `base` using `successor` mode.
   Provide the new version, current signed tag, release date, summary, stable
   upgrade policy, supported alpha commits, and recovery classification. The
   workflow defaults the stable policy to `supported`.
4. The workflow verifies the signed predecessor and opens a draft branch named
   `release/vX.Y.Z`. It changes only the five release evidence files listed
   above.
5. Review `release/config.yaml`, the compact migration declarations, and the
   authored release entry in `CHANGELOG.md`. Preparation preserves an existing
   release entry or uses the `Unreleased` text, falling back to the reviewed
   summary when empty. Add any required operator actions; empty release notes
   and unresolved `TODO` markers fail validation.
6. Regenerate the manifest and run all release checks.
7. Resolve review comments and merge the release pull request to `main` through
   the normal reviewed workflow.

The preparation workflow needs a `release-preparation` environment containing
`RELEASE_AUTOMATION_APP_ID` and `RELEASE_AUTOMATION_APP_PRIVATE_KEY`. The GitHub
App is scoped to `base` with contents and pull request write permissions. Its
token allows the draft pull request to run normal `Required CI`.

### Migration Document

The current successor scaffold and validator use exactly one of each required
level-two section:

- `Support`
- `Breaking Changes`
- `Recovery`

No additional boilerplate headings are mandatory. Published documents remain
authoritative and immutable; `v0.3.2` already uses this compact format.

For every new-format release, the `Support` section uses exactly one of these
lines:

```text
- Stable upgrades: Supported.
- Stable upgrades: Fresh installation only.
```

It also declares exact full alpha source commits and unsupported downgrade
behavior. The `Breaking Changes` section must be nonempty. The scaffold uses:

```text
See the release notes in CHANGELOG.md for breaking changes and required actions.
```

Keep the actual changes and required operator actions in the authored release
entry in `CHANGELOG.md`; concise reviewed bullets are sufficient. Add specific
migration details only when needed, not empty sections or generated TODO lists.
A checkpoint is documented only when that release needs one; it is not a
machine-readable compatibility field.

The immutable `v0.1.0` and `v0.1.1` migration documents retain their legacy
exact stable-source declarations. Write `None.` when there are no supported
alpha commits or legacy stable sources.

The `Recovery` section contains a `Recovery classification: <label>.`
declaration using one classification:

- `Configuration revert`
- `Forward fix`
- `Component native restore`
- `Replacement restore`

Keep the migration document consistent with both `release/config.yaml` and the
generated manifest. When client values must change, document a safe staged
order. The client and platform Git sources do not reconcile atomically.

### Validation

Run these commands from `base/`:

```bash
make release-manifest
make check
make release-check TAG="v$(cat VERSION)"
make release-notes OUTPUT=/tmp/platform-release-notes.md
```

`make check` is the normal repository validation suite. It does not replace
`make release-check`, which validates release prose, version consistency,
compatibility, provenance, and generated manifest drift.

## Sign and Publish

Merging the release pull request does not authorize a tag or publication. After
explicit release authorization, use the supported trusted-workstation CLI from
`tooling/cli_tools/platform_release/`, not from `base/`. Select the trusted
primary Base checkout with `--base-repo`; the CLI prepares its own clean linked
release checkout without switching or cleaning the original checkout.

```bash
mise exec -- uv run --frozen platform-release --base-repo /path/to/trusted/base \
  publish --tag vX.Y.Z
```

The CLI asks permission to fetch and prepare the isolated checkout. It requires
the exact merged release PR commit at the remote default-branch tip, successful
required CI, and passing full local checks. Signing uses only ssh-agent and the
public file `~/.ssh/neurwerk_base_release_ed25519.pub`; both must match the
approved fingerprint above. Stop if the approved identity is unavailable.
Never read or pass a private key through arguments, environment variables, CI
secrets, or repository files.

After preflight, review and type the exact displayed confirmation:

```text
PUBLISH OWNER/REPOSITORY vX.Y.Z FULL_RELEASE_MERGE_COMMIT
```

This authorizes signing, staging, and the publication chain together. The CLI
creates and verifies the local signed annotated tag, pushes only its object to
`refs/tags/release-staging/vX.Y.Z`, and dispatches `Create Platform Release Tag`
with the exact tag, tag-object SHA, and target commit. The protected workflow
creates the final tag; do not push it directly or create a GitHub Release by hand.

The CLI then waits for the exact final object and correlated workflow evidence:

1. `Verify Platform Release` verifies the signer, default-branch ancestry,
   release contract, full repository checks, and tag/version consistency.
2. `Release Platform` repeats the trust and provenance checks, verifies the
   signed predecessor, builds the release notes, and publishes the GitHub
   Release through the `platform-release` environment.

Protected environment approvals remain manual. The CLI verifies the non-draft
stable GitHub Release and correlates publication through the
`published-platform-release` identity artifact, not merely a successful run.

If waiting times out or publication is interrupted, inspect the same exact tag
from the same CLI directory and primary Base path:

```bash
mise exec -- uv run --frozen platform-release --base-repo /path/to/trusted/base \
  status --tag vX.Y.Z
mise exec -- uv run --frozen platform-release --base-repo /path/to/trusted/base \
  continue --tag vX.Y.Z
```

`status` inspects without waiting. `continue` waits/rechecks publication only when
the final ref matches the locally verified signed tag; it never redispatches.
Local-only or staged-only states require inspection and separately authorized
recovery using the CLI README's partial-operation guidance. Do not rerun
`publish` automatically, overwrite refs, or bypass the protected workflow.
Missing or expired identity artifacts fail closed rather than proving success.

If release evidence is defective, prepare a new version. Do not repair it by
moving the existing tag.

## Client Adoption

Publication does not authorize client adoption or cluster reconciliation.

### Draft Automation

`Prepare Client Adoption PRs` runs after successful publication or by manual
dispatch with an exact published tag. It is disabled unless these settings
exist in `base`:

| Setting | Purpose |
| --- | --- |
| `CLIENT_ADOPTION_ENABLED=true` | Enables draft creation |
| `CLIENT_ADOPTION_REPOSITORIES` | JSON matrix of approved client repositories |
| `PLATFORM_RELEASE_ALLOWED_SIGNER` | Verifies the platform tag |
| `client-adoption` environment | Restricts adoption credentials to the default branch |
| `CLIENT_ADOPTION_APP_ID` | GitHub App identity stored in the environment |
| `CLIENT_ADOPTION_APP_PRIVATE_KEY` | GitHub App key stored in the environment |

Use this matrix shape without placing confidential client names in public
documentation:

```json
[{"repository":"OWNER/REPOSITORY","name":"REPOSITORY"}]
```

For each configured client, the workflow verifies the signed tag and published
GitHub Release. The existing client source must be a canonical signed stable
source with a reviewed `upgrade` or `fresh-install` mode. The workflow then
changes only `clusters/prod-eu-1/platform-source.yaml` and opens or updates draft
branch `platform-adoption/vX.Y.Z`.

The draft sets the exact tag and matching
`platform.neurwerk.com/adoption-target`. It also sets
`platform.neurwerk.com/adoption-mode: review-required`, which deliberately fails
compatibility until a reviewer records the target state.

The workflow does not change client values or Secrets, mark the pull request
ready, merge it, contact a cluster, or reconcile Flux.

### Review and Rollout

Client repositories require:

- `PLATFORM_RELEASE_SIGNER_FINGERPRINT` with the independently authenticated
  fingerprint;
- `PLATFORM_STATUS_APP_CLIENT_ID` for the status-only GitHub App;
- `PLATFORM_STATUS_APP_PRIVATE_KEY` in the `platform-status` environment;
- a `platform-adoption` environment for changed-source verification;
- a repository rule requiring `Platform Compatibility` from the exact status
  App integration.

The environments protect credentials and verification. They are not human
adoption approval.

For each draft:

1. Review the release manifest, migration document, client values, required
   Secrets, and target state.
2. Use `upgrade` for a stable source only when the target's applicable legacy
   allowlist permits it or its new-format policy is `stableUpgrade: supported`
   and the target is strictly newer. Review every crossed release's migration
   and breaking-change instructions in ascending order. Use `upgrade` for alpha
   promotion only when the target lists the exact reconciled alpha commit.
3. Use `fresh-install` only when a maintainer has verified that the target is
   empty or is a replacement environment.
4. Confirm that `adoption-target` exactly matches the selected tag and that
   `Platform Compatibility` passes.
5. Merge the exact reviewed commit. This merge is the adoption authorization
   and may allow Flux to reconcile.

Roll out one designated, deployed canary client first. A repository-only example
does not provide rollout evidence. After an authorized deployment, inspect the
source, Kustomizations, HelmReleases, warning events, and affected logs before
advancing another client:

```bash
flux get sources git -n flux-system
flux get kustomizations -n flux-system
flux get helmreleases -A
kubectl get events -A --field-selector=type!=Normal --sort-by='.lastTimestamp'
```

A Git or configuration revert is not a state rollback. Follow the recovery
action in the release migration document.
