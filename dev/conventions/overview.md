# Development Conventions

Use these conventions for every change in the workspace. For exact commands and
enforced settings, follow local configuration and guidance. `docs/` is pre-Git.

## Core Rules

1. Make changes in the workspace area that owns the behavior.
2. Keep Helm charts, platform release contracts, client values, and cluster
   composition separate.
3. Use product-oriented names and paths.
4. Never commit secrets or recovery material.
5. For deployments, define runtime order with `dependsOn`, readiness checks, and
   health checks.
6. Make the smallest complete change and update tests and documentation with it.
7. Run the relevant local validation commands before review.

## Change Workflow

1. Identify the workspace area that owns the change.
2. Read its local configuration and guidance.
3. For Git repositories, create a dedicated worktree and branch.
4. Review the relevant convention guides below.
5. Update code, tests, and documentation together.
6. Run the required local checks.

## Convention Guides

| Guide | Use it for |
| --- | --- |
| [Repository layout](repository-layout.md) | Choosing the repository that owns a change |
| [File structure](file_structure.md) | Finding canonical directories and filenames |
| [Configuration](configuration.md) | Placing defaults, client values, and secrets |
| [Flux](flux.md) | Defining sources, reconciliation, dependencies, and readiness |
| [Helm charts](helm-charts.md) | Creating charts and platform release packages |
| [Kubernetes](kubernetes.md) | Naming, security, workloads, networking, and storage |
| [Coding and releases](coding-and-release.md) | Implementing, validating, and releasing changes |
| [GitHub workflow](github-workflow.md) | Managing issues, pull requests, labels, and review gates |
| [Python](python.md) | Writing and testing Python projects |
| [TypeScript](typescript.md) | Working in Studio and the Dify web overlay |

Existing code is not automatically the correct pattern. Confirm that it follows
the current product-oriented structure and executable configuration before
copying it.
