# Coding and Release Conventions

Code is split across independent Git repositories. A change is complete when
the implementation, deployment contract, tests, and documentation agree.

## Development Workflow

1. Open or select an issue with a clear outcome and acceptance criteria.
2. Identify the repository that owns the change and any affected contracts.
3. Create a dedicated Git worktree and branch. Do not work directly on `main` or
   switch branches in a shared checkout.
4. Read applicable `AGENTS.md` files, the repository's Makefile, package
   configuration, and CI workflows before editing.
5. Make the smallest complete change. Update focused tests and documentation.
6. Run the repository's formatting, linting, type checking, tests, and build
   checks.
7. Render affected Helm charts and Kustomizations for deployment changes.
8. Review the final diff for secrets, generated files, stale paths, and
   unintended lockfile changes.
9. Open a pull request using the repository template. Close the implementation
   issue, link related issues, identify affected contracts, and list exact
   validation results.
10. Wait for required CI and resolve every review conversation.
11. Squash-merge the reviewed pull request and delete its branch.

Direct pushes to `main` are limited to one-time empty-repository bootstrap or an
explicitly authorized and documented emergency. See the
[GitHub workflow](github-workflow.md) for issue, label, review, and pull request
rules.

## Validation

Repository-local configuration is the source of truth. Use the commands defined
in the repository's Makefile, `pyproject.toml`, `package.json`, and CI workflows.
Run `make check` when the repository provides it. Do not skip a failing check or
bypass hooks to hide a failure.

## Cross-Repository Changes

Coordinate changes that affect contracts between repositories, including:

- service configuration consumed by a chart;
- API request or response formats;
- Keycloak roles, application authorization, or API-key permissions;
- image tags consumed by chart values;
- shared PostgreSQL databases, roles, credentials, or connections;
- client values consumed by platform release contracts.

For coordinated work, use a parent issue and one implementation sub-issue per
repository. Define a safe merge and deployment order. Do not merge a contract
change that leaves a current consumer incompatible.

## Release Rules

A pull request, merge, or successful CI run does not authorize a release or
deployment. Creating or pushing a release tag and reconciling a cluster each
require separate authorization.

### Images and Helm Charts

Follow the [image release runbook](../operations/image-releases.md) before
changing a version, creating a tag, updating an image pin, or deploying it.
CI-managed images publish from explicit `v*` tags. Pin immutable,
version-specific images in `base/`.

Increment a chart's `version` whenever its packaged content changes, including
templates, defaults, dependencies, or packaged files. Update `appVersion` only
when it represents the released application. Keep dependency locks
reproducible.

### Platform Releases

Follow the [platform release runbook](../operations/platform-releases.md). A
platform release uses a reviewed release proposal and preparation pull request,
followed by a separately authorized signed `vX.Y.Z` tag. The release commit
contains the matching changelog, migration document, and generated manifest.

Clients select one exact signed platform tag. Adoption automation creates draft
pull requests in the fail-closed `review-required` state; it does not merge,
deploy, or reconcile Flux. A maintainer must review and authorize the exact
client transition.

There is no command that releases every workspace service.

## Commit Messages

Use concise, imperative subjects with a useful type, such as `feat:`, `fix:`,
`test:`, `docs:`, or `chore:`. If an intentionally incomplete change is
committed, state that clearly in the commit or pull request.
