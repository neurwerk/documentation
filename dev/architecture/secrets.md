# Secrets Architecture

Git stores secret references and non-secret configuration. It must not contain
credentials, private keys, recovery material, or generated Secret manifests.

OpenBao stores operator-supplied and platform-generated application secrets.
External Secrets copies approved fields into namespace-local Kubernetes
Secrets. Other controllers manage their own scoped Secrets:

- cert-manager creates certificate and private-key Secrets;
- Rook creates S3 credential Secrets for `ObjectBucketClaim` and
  `CephObjectStoreUser` resources.

See [Certificates and Trust](certificates.md) for certificate ownership.

## Secret Flow

```text
operator input or generated credential
-> stack-setup
-> OpenBao KV
-> namespace-local SecretStore
-> ExternalSecret
-> Kubernetes Secret
-> HelmRelease or workload
```

Client repositories do not contain secret values or secret-management
resources. `config/client.yaml` and product `values.yaml` are non-secret by
contract.

## OpenBao Bootstrap and Recovery

Run `stack-setup` from a trusted workstation. It:

- creates the immutable static-seal Secret in the OpenBao namespace;
- initializes OpenBao;
- configures Kubernetes authentication and namespace policies;
- stores provider credentials and generated credentials;
- writes the recovery kit outside Git and the workspace.

OpenBao uses three encrypted recovery shares with a 2-of-3 threshold. Keep the
custodian packages separate from the static-seal kit and audit access as
described in [Recovery Custody](../operations/recovery-custody.md).

During an incomplete bootstrap, the local static-seal kit can temporarily hold
custodian private keys, the initialization response, the initial root token,
and generated administrator passwords. Treat it as privileged recovery
material. `stack-setup` removes temporary values as checkpoints complete.

Recovery-root operations use the TLS listener on `127.0.0.1:8203` inside the
OpenBao Pod. The port is absent from Services, declared container ports, and
NetworkPolicy rules. `stack-setup` reaches it through an authorized Pod
port-forward and handles the temporary token in workstation memory.

See [OpenBao Operations](../operations/openbao.md) for bootstrap, recovery,
reconciliation, and provider-update commands.

## Namespace Isolation

Each namespace that reads OpenBao has:

- a dedicated ServiceAccount;
- a namespace-local `SecretStore`;
- an OpenBao role bound to that ServiceAccount and the `openbao` audience;
- a read-only policy limited to that namespace's KV data and metadata prefix;
- `ExternalSecret` resources that request explicit properties.

There is no `ClusterSecretStore`. Trust Manager copies the OpenBao CA into only
the namespaces labeled `secrets.neurwerk.com/openbao-trust: "true"`.

`ExternalSecret` resources refresh hourly and own their target Secret.
`deletionPolicy: Retain` preserves the target when its provider record disappears;
deleting the owning `ExternalSecret` can still garbage-collect the target Secret.

Existing installations receive approved roles, policies, records, and consumers
through the versioned `stack-setup reconcile` catalog. Reconciliation requires
two recovery shares, uses a temporary root token, and revokes it before
Kubernetes resources converge. Conflicting copied values fail closed.

## Runtime Delivery

An `ExternalSecret` produces one of two outputs:

- a Secret containing `values.yaml` for a same-namespace `HelmRelease`;
- a Secret mounted or referenced directly by a workload.

The platform release contract selects the pattern. Flux `valuesFrom` references
must be in the same namespace as the `HelmRelease`. ConfigMaps used by
`valuesFrom` must remain non-secret.

## Shared Credential Contracts

### SMTP

`stack-setup` stores the send-only SMTP credential in these records:

- canonical operator record: `stack-setup/providers/smtp`;
- Keycloak runtime copy: `auth-keycloak/external`;
- monitoring runtime copy: `monitor-kube-prometheus-stack/external`.

Runtime roles cannot read the canonical record or another namespace's copy.
`stack-setup` updates all three records as one operator action. The update is
retry-safe, but it is not an atomic transaction across the records.

The monitoring `ExternalSecret` creates only the SMTP values consumed by its
`HelmRelease`. Non-secret routing settings remain in client values. The chart
renders the final Alertmanager configuration as a Kubernetes Secret.

### Active Directory

When Active Directory federation is enabled, `auth-keycloak/external` contains:

- `activeDirectoryBindDn`;
- `activeDirectoryBindCredential`.

`auth-keycloak-active-directory-secret` copies only these fields into the
`auth-keycloak` namespace. Disabled federation does not render or read this
`ExternalSecret`. There is no separate canonical Active Directory credential
record.

The Active Directory CA is public trust data, not a secret. See
[Certificates and Trust](certificates.md#microsoft-active-directory-ca-trust).

### LibreChat

LibreChat uses separate OpenBao records for `frontend-librechat/internal` and
`librechat-code-interpreter/internal`.

- The LibreChat namespace keeps the Code Interpreter JWT private signer.
- The Code Interpreter API receives only the public JWT verifier.
- The service worker keeps the execution-manifest private signer.
- The sandbox receives only the public execution-manifest verifier.
- Admin Panel session and metrics values use a dedicated workload Secret.

### PostgreSQL

Shared PostgreSQL uses two namespace-isolated records:

| Record | Fields |
| --- | --- |
| `infra-postgres-auth/internal` | `adminPassword`, `keycloakPassword` |
| `infra-postgres-operations/internal` | `adminPassword`, `agentgatewayPassword`, `documentdbPassword`, `difyPassword`, `langfusePassword`, `librechatRagPassword` |

Each PostgreSQL administrator password is generated independently. Application
passwords are exact copies of the corresponding application credentials, so the
application and database use the same value without cross-namespace access.
See [Shared PostgreSQL](postgresql.md#credentials) for the field mapping.

AgentGateway's canonical PostgreSQL password is generated at
`infra-agentgateway/internal:postgresqlPassword`. Reconciliation copies that
exact value to
`infra-postgres-operations/internal:agentgatewayPassword`; a conflicting copy
fails closed. External Secrets delivers the source value to a dedicated
AgentGateway runtime Secret and the copy to the PostgreSQL provisioning values.

AgentGateway receives the runtime password through `secretKeyRef` and expands
it into the database URL at process startup. The literal password must not be
rendered into AgentGateway configuration or a ConfigMap. Studio calls the
private AgentGateway analytics API and receives neither this database credential
nor direct database access. Studio also receives no Langfuse project credential
for usage analytics; Langfuse retains its own tracing credentials and storage.

## Optional WireGuard

The static gateway's selected catalog uses only `wireguard/internal:privateKey`.
`stack-setup` `0.2.13` generates a missing key on the trusted workstation during
authorized bootstrap/reconciliation and preserves it on retry; it does not enroll
devices or restore their historical permissions. The optional namespace-local
ESO package delivers that one property to `wireguard-server-key`. The device
private key stays in the Mac WireGuard app. See
[WireGuard setup](../operations/wireguard.md#server-key-setup) for exact selection
and readiness gates; no runtime selection follows from source availability.

## Optional Docling

The selected `stack-setup` `0.2.16` catalog generates a missing service API key at
`docling/internal:apiKey` and copies it exactly to
`monitor-agentgateway-extproc/internal:doclingApiKey`. Conflicting copies and
invalid existing keys stop reconciliation without rotating them.
In remote mode, the operator separately supplies `docling/external:inferenceToken`
through the hidden `docling-inference` provider prompt, which preserves sibling
fields. CPU mode needs no inference token and rejects that provider command;
existing OpenBao credentials are retained when changing modes.

The optional Base secret-sync package delivers only the approved fields:

- `docling/docling-api`, key `api-key`;
- `docling/docling-inference`, key `token` (remote package only);
- `monitor-agentgateway-extproc/monitor-agentgateway-extproc-docling-secret`, key `api-key`.

Each namespace has its own read-only OpenBao role and store. extProc cannot read
the upstream inference token. Routine secret-operator updates permit the exact
Docling external record, not either internal API-key record.
CPU clients select `releases/docling/secret-sync/internal`; the existing root
package still renders the same resources for remote clients.
See [Docling setup](../operations/openbao.md#optional-docling-credentials) for
selection, custody and credential-only staging without application startup.

## Safety Rules

- Never commit secret values, credentials, private keys, recovery material, or
  generated Secret manifests.
- Never print Secret values while troubleshooting.
- Grant Secret `get`, `list`, and `watch` permissions only when required.
- Use explicit OpenBao properties instead of importing complete records.
- Verify `ExternalSecret` conditions and target metadata without reading target
  values.

```bash
kubectl get secretstores,externalsecrets -A
kubectl describe externalsecret <name> -n <namespace>
```

See the Kubernetes documentation for additional
[Secret handling guidance](https://kubernetes.io/docs/concepts/security/secrets-good-practices/).
