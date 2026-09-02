# Repository Layout

The workspace root is not a Git repository. Most top-level directories are
independent Git repositories with distinct ownership. The `docs/` directory is
shared documentation and is not a Git repository.

## Workspace Areas

| Path | Responsibility |
| --- | --- |
| `base/` | Helm charts, platform release contracts, namespaces, platform defaults, and validation |
| `client_example_com/` | Reference client facts, values, ConfigMaps, and Flux cluster composition |
| Private client repositories | Client-specific facts, values, ConfigMaps, and Flux cluster composition |
| `agentgateway_extproc/` | AgentGateway external-processing adapter for the PII Engine |
| `keycloak_api_key_bridge/` | API-key management and authorization decisions |
| `pii_engine/` | PII analysis, policy, and model runtime |
| `studio/` | Studio API and web application |
| `dify_ce_builder/` | Owned overlay and image build for upstream Dify |
| `tooling/` | Kubernetes initialization commands and independently locked workstation tools |
| `docs/` | Cross-repository architecture, conventions, and runbooks |
| `_external_readonly_repos/` | Read-only upstream source references; never edit these files |

Refer to private clients generically outside their own repositories.

## Where a Change Belongs

### Platform

- Helm templates: `base/charts/<product>/`.
- HelmRelease contracts: `base/releases/<product>/`.
- Platform defaults: `base/releases/shared/`.
- Namespace resources: `base/releases/namespaces/`.
- Stage aggregation: `base/releases/infrastructure/` and
  `base/releases/applications/`.

Stage directories contain only aggregation. Keep product HelmReleases under
`base/releases/<product>/`.

### Clients

- Shared non-secret client facts: `client_*/config/client.yaml`.
- Product-specific values and ConfigMaps: the matching directory under
  `client_*/apps/` or `client_*/infrastructure/`.
- Shared PostgreSQL storage values:
  `client_*/infrastructure/storage/postgres/values.yaml`.
- Flux source composition and reconciliation order:
  `client_*/clusters/prod-eu-1/`.

### Services, Tools, and Documentation

- Application behavior and API contracts: the owning service repository.
- OpenBao bootstrap and supported provider updates:
  `tooling/cli_tools/openbao_stack_setup/`.
- Cross-repository contracts and runbooks: `docs/dev/`.

## Boundaries

- Do not place charts, HelmReleases, or platform Namespace resources in a client
  repository.
- Do not place client-specific values, such as hostnames or sizing, in `base/`.
- Do not wrap product paths in technical categories such as `auth/`,
  `frontend/`, `infra/`, or `monitor/`.
- Do not edit `_external_readonly_repos/`.

See [File Structure](file_structure.md) for canonical directory trees and
[Configuration Conventions](configuration.md) for value ownership.
