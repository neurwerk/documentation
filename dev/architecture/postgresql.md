# Shared PostgreSQL

The platform runs two singleton database releases. Authentication data is kept
separate from application and observability data.

## Topology and ownership

| Release | Namespace | Runtime | Consumers |
| --- | --- | --- | --- |
| `postgres-auth` | `infra-postgres-auth` | `docker.io/postgres:18.6-alpine3.24` | Keycloak |
| `postgres-operations` | `infra-postgres-operations` | `ghcr.io/documentdb/documentdb/documentdb-local:pg18-0.116.0` | AgentGateway, Dify, Langfuse, LibreChat, and LibreChat RAG |

The platform owns the charts and release contracts:

```text
base/charts/postgres/auth/
base/charts/postgres/operations/
base/releases/postgres/
```

Both releases depend on Rook/Ceph, the internal cert-manager issuer, and
trust-manager.

Clients select the RBD StorageClass in
`infrastructure/storage/postgres/values.yaml`. The nested `auth/` and
`operations/` Kustomizations generate a namespace-local
`postgres-product-values` ConfigMap for each release. Credentials come from
OpenBao, not client values.

## Database contracts

### Authentication

`postgres-auth` creates the `keycloak` role and a database of the same name.
Keycloak connects to:

```text
postgres-auth.infra-postgres-auth.svc.cluster.local:5432/keycloak
```

The server requires SCRAM-SHA-256 authentication over TLS 1.3 or later for all
TCP connections. Keycloak and the provisioning Job use `verify-full` with the
platform internal CA and the exact service DNS name.

### Operations

`postgres-operations` runs PostgreSQL 18, pgvector, the DocumentDB extension,
and a MongoDB-compatible DocumentDB gateway in one StatefulSet.

| Consumer | Role | Database | Additional contract |
| --- | --- | --- | --- |
| AgentGateway | `agentgateway` | `agentgateway` | Durable metadata-only request logs used by Studio usage analytics. |
| Dify | `dify` | `dify`, `dify_plugin`, `dify_vector` | The `vector` extension is installed in `dify_vector`. |
| Langfuse | `langfuse` | `postgres_langfuse` | The chart's PostgreSQL dependency is disabled. |
| LibreChat RAG | `librechat_rag` | `librechat_rag` | The `vector` extension is installed. |
| LibreChat | `librechat` | DocumentDB database `LibreChat` | The user authenticates against `admin` with `readWriteAnyDatabase` and `clusterAdmin`. |

The PostgreSQL `postgres` database hosts the DocumentDB extension. The image's
PostgreSQL owner is `documentdb`. The `operations_admin` gateway administrator
provisions and verifies the `librechat` user.

DocumentDB currently requires broad database roles for secondary write users.
LibreChat must remain the only MongoDB-compatible consumer of this instance. A
second consumer requires a separate DocumentDB instance because `librechat`
could access its databases.

This limitation does not grant LibreChat access to the AgentGateway, Dify,
Langfuse, or LibreChat RAG PostgreSQL databases. Those databases use separate
roles, grants, and port-scoped NetworkPolicies. Provisioning also verifies that
`librechat` cannot connect to them.

## Provisioning

Finite post-install and post-upgrade Jobs reconcile roles, databases, grants,
and required extensions. They verify the complete database contract and fail
the Helm release when it is incomplete.

For DocumentDB user management, provisioning temporarily gives
`operations_admin` PostgreSQL `CREATEROLE` and delegated
`documentdb_admin_role` authority. The Job revokes and verifies both privileges
before it succeeds.

## Transport and network policy

| Connection | Transport |
| --- | --- |
| Keycloak to `postgres-auth:5432` | TLS with exact service identity verification |
| AgentGateway, Dify, Langfuse, and LibreChat RAG to `postgres-operations:5432` | SCRAM authentication over plaintext PostgreSQL |
| LibreChat to `postgres-operations:10260` | TLS with the platform internal CA |

Plaintext PostgreSQL is an accepted exception for `postgres-operations` only.
It does not apply to `postgres-auth` or the DocumentDB gateway.

Both PostgreSQL namespaces are default-deny. Ingress policies allow only the
approved consumer Pods and provisioning Jobs on the required container port.
The operations PostgreSQL policy permits the exact AgentGateway data-plane Pod
identity on destination Pod port `9712`, which backs Service port `5432`.
Consumer egress policies select the destination namespace, Pod identity, and
port. Database grants provide a separate authorization boundary.

The DocumentDB certificate covers the exact `postgres-operations` service names.
LibreChat and the provisioning Job verify it with
`infra-openbao-ca-bundle`.

## Credentials

`stack-setup` manages two OpenBao records:

| Record | Fields |
| --- | --- |
| `infra-postgres-auth/internal` | `adminPassword`, `keycloakPassword` |
| `infra-postgres-operations/internal` | `adminPassword`, `agentgatewayPassword`, `documentdbPassword`, `difyPassword`, `langfusePassword`, `librechatRagPassword` |

Each `adminPassword` is generated independently. Application passwords are
copied from their existing namespace-owned records:

| Destination | Source |
| --- | --- |
| `infra-postgres-auth/internal:keycloakPassword` | `auth-keycloak/internal:dbPassword` |
| `infra-postgres-operations/internal:agentgatewayPassword` | `infra-agentgateway/internal:postgresqlPassword` |
| `infra-postgres-operations/internal:documentdbPassword` | `frontend-librechat/internal:documentdbPassword` |
| `infra-postgres-operations/internal:difyPassword` | `frontend-dify/internal:postgresPassword` |
| `infra-postgres-operations/internal:langfusePassword` | `monitor-langfuse/internal:postgresqlPassword` |
| `infra-postgres-operations/internal:librechatRagPassword` | `frontend-librechat/internal:ragPostgresqlPassword` |

Conflicting copies fail reconciliation. Namespace-local ExternalSecrets create
`postgres-auth-values` and `postgres-operations-values` for the corresponding
Helm releases.

## Persistence and recovery

Each StatefulSet has one retained RBD claim:

| Release | Claim | Default size |
| --- | --- | --- |
| `postgres-auth` | `data-postgres-auth-0` | `5Gi` |
| `postgres-operations` | `data-postgres-operations-0` | `50Gi` |

Both StatefulSets retain their claims when deleted or scaled down. The
DocumentDB data directory is `/data/postgresql` on the operations claim mounted
at `/data`.

All operations databases share one process, data directory, PVC, maintenance
window, and recovery point. A failure or restore affects AgentGateway request
logs, Dify, Langfuse, LibreChat, and LibreChat RAG together. The authentication
release is a separate logical recovery domain, but both claims use the same
single-node Rook/Ceph physical failure domain.

PVC retention is not a backup. Recovery requires an application-consistent,
independently stored backup of the complete affected instance.
