# GitHub Workflow

GitHub records planning, review, and release intent. It does not replace
repository checks or authorize releases, deployments, credential changes, or
cluster operations.

## Issues

Use an issue form provided by the owning repository. Forms differ by
repository, so do not assume that every repository has the same issue types.
Keep each issue focused on one independently verifiable outcome.

For cross-repository work:

1. Create a parent issue in the repository that owns the shared contract.
2. Create one sub-issue in each repository that must implement or consume the
   contract.
3. Put the integrated acceptance criteria in the parent issue.
4. Close each sub-issue through its implementation pull request.
5. Close the parent only after all required sub-issues are complete.

Link parent issues from pull requests without using `Closes`, `Fixes`, or
`Resolves`. Local todo files are not used for tracked work.

## Labels

Use each repository's exact label names. Preserve spaces after namespace
colons, such as `type: bug`.

### Base Repository

Base issue forms use the native GitHub types `Bug`, `Feature`, and `Task`, and
apply `status: triage`.

Base pull requests use these generated-note categories:

- `breaking`
- `feature`
- `fix`
- `operations`
- `security`
- `documentation`
- `maintenance`

Use `skip-changelog` or `release: none` to exclude a pull request from generated
notes. Reserve `release: platform` for platform release preparation.

### Namespaced Taxonomy

Client, service, and tooling repositories that use namespaced labels use this
taxonomy:

- Type: `type: bug`, `type: task`, `type: architecture`
- Priority: `priority: p0`, `priority: p1`, `priority: p2`, `priority: p3`,
  `priority: p4`
- Area: `area: docs`, `area: platform`, `area: client`, `area: service`,
  `area: operations`, `area: security`
- Release: `release: none`, `release: notes`, `release: platform`,
  `release: client`

Check the repository's issue forms, `.github/label-taxonomy.md`, and
`.github/release.yml` before applying labels.

## Project Fields

Use these values in the organization Project:

| Field | Values or format |
| --- | --- |
| Status | Triage, Backlog, Ready, In progress, In review, Blocked, Done |
| Priority | P0, P1, P2, P3, P4 |
| Repository | Owning workspace repository |
| Target release | Exact `vX.Y.Z`, `Unscheduled`, or `Not applicable` |
| Rollout | Not applicable, Example client, Draft fleet, Approved, In progress, Complete |

If a Project field conflicts with an issue label or description, resolve the
conflict in the issue before implementation.

## Pull Requests

For normal planned work:

1. Use the repository's pull request template.
2. Close the implementation issue and link related issues.
3. Describe affected contracts and operational or security effects.
4. Record the exact validation commands and results.
5. Wait for required checks and resolve every review conversation.
6. Squash-merge the reviewed pull request and delete its branch.

Automated release and client-adoption pull requests use workflow-generated
bodies instead of the normal template. Reviewers must still verify their
classification and evidence before merge.

Use `Required CI` as the stable normal-validation check for `main`. Client
repositories also require `Platform Compatibility` from the configured GitHub
App integration. The compatibility workflow uses trusted default-branch code,
does not execute pull request code, and fails closed. A push to `main` refreshes
the status on each open pull request's current test-merge commit.

`CODEOWNERS` requests review; it does not prove approval. Follow the owning
repository's approval policy and complete any required protected-environment
approval.

Direct pushes to `main` are limited to one-time empty-repository bootstrap or an
explicitly authorized, documented emergency. Merge commits and merge queues are
not part of the normal workflow.

## Release Pull Requests

An ordinary base pull request may affect release notes, but it does not publish
a release. Apply the appropriate generated-note label or deliberately exclude
the pull request.

A platform release starts with the base release-proposal form, which creates a
native `Task`. The preparation workflow opens a draft pull request containing
the version, changelog, migration document, release configuration, and generated
manifest. For a new-format release, review the explicit stable-upgrade policy,
the mandatory `Breaking Changes` section, and any release-specific checkpoint
instructions. Complete its release evidence and pass release checks before
review. Merging the pull request does not authorize or create the signed tag or
GitHub Release.

After a stable platform release is published, automation may open a draft client
adoption pull request. The draft starts in a fail-closed review state. A
maintainer must review and commit the exact target state, satisfy `Platform
Compatibility`, and complete any repository-specific approval before merge.
Automation must not select the target state, merge, deploy, reconcile Flux,
change Secrets, or contact a cluster.

A skipped-version upgrade does not collapse these boundaries: operators review
and apply every crossed release's migration and breaking-change instructions in
ascending order, maintainers authorize the exact client change, and deployment
or reconciliation still requires its separate authorization.

See the [platform release runbook](../operations/platform-releases.md) for release
preparation, signing, publication, compatibility, and client adoption details.

## Agent and Tool Limits

Agents may draft issues, changes, pull requests, reviews, and release text only
within their granted permissions. Tool access, CI success, generated reviews,
and `CODEOWNERS` requests are not human authorization.

Agents must not use those signals as permission to merge, tag, publish, deploy,
reconcile, change credentials, or modify persistent data. If a tool cannot
perform a required GitHub operation, leave it for a maintainer instead of
bypassing the requirement.
