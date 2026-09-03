# OpenBao Operations

`stack-setup` initializes and operates OpenBao from a trusted workstation. It
handles bootstrap, catalog reconciliation, status checks, recovery verification,
and supported provider credential updates. It is not a Kubernetes Job.

The current platform release contract requires `stack-setup` `0.2.10` from
tooling commit `fbf91a133e755e5f5b3a79e0e73c2506fc09021f`.

The AgentGateway usage migration requires reconciliation schema `4`. Its target
platform release must pin `openbao-stack-setup` `0.2.11` from tooling commit
`5d1a33a938e22e9034581aebecf33485adc88a29`. Do not substitute a branch or
moving reference. The existing requirement above remains authoritative for the
currently published platform release.

## Requirements

Before running `stack-setup`:

- Use a trusted, encrypted workstation.
- Install `uv`, `kubectl`, and `gpg`.
- Configure access to the target Kubernetes context.
- Apply the client identity, product values, and OpenBao release contract.
- Assign the K3s server a stable IPv4 address. If it uses DHCP, reserve its
  persistent NIC MAC and configure K3s `--node-ip` and `--advertise-address`.
- Enable Kubernetes Secret encryption on every K3s server.
- Prepare separate, secure storage for the static-seal kit and three custodian
  packages. See [Recovery Custody](recovery-custody.md).

## Safety Rules

- Pass `--context` and `--client` explicitly on every `stack-setup` command.
- Confirm that `flux-system/neurwerk-stack-identity` identifies the expected
  client and cluster before making changes.
- Keep custody material outside the workspace, Git repositories, tickets, logs,
  and chat.
- Never pass credentials or recovery material as command arguments.
- Keep the static-seal kit separate from the custodian packages.
- Treat recovery verification and reconciliation as privileged root operations.
- Do not delete OpenBao storage, the `infra-openbao` namespace, the static-seal
  Secret, or local custody checkpoints to recover from an error.

## Prepare The CLI

Run all commands from the tool directory:

```bash
cd tooling/cli_tools/openbao_stack_setup
uv sync --dev
```

The default custody root is:

```text
~/.local/share/neurwerk/openbao/<client>/
```

`bootstrap`, `reconcile`, `status`, and `recovery verify` accept
`--custody-root <path>`. The override replaces the complete client-specific
path. The CLI rejects custody roots inside Git repositories or a recognized
multi-repository workspace.

## Run Preflight

```bash
uv run stack-setup preflight \
  --context <kube-context> \
  --client <client-name>
```

Preflight verifies:

- the requested client matches `neurwerk-stack-identity`;
- the `infra-openbao` namespace and OpenBao HelmRelease exist;
- the External Secrets, Rook/Ceph, and trust-manager HelmReleases are Ready;
- the OpenBao server Certificate is Ready;
- Keycloak and monitoring values are valid and indicate whether SMTP
  credentials are required;
- Keycloak values indicate whether Active Directory credentials are required;
- the endpoint in `infra-openbao/openbao-product-values` matches a Ready Node
  InternalIP and the ready `default/kubernetes` EndpointSlice.

Preflight does not verify control-plane Secret encryption. Check the K3s
configuration manually before bootstrap.

## Bootstrap OpenBao

```bash
uv run stack-setup bootstrap \
  --context <kube-context> \
  --client <client-name>
```

The command requires you to type the client name. It then:

1. Creates or resumes the private custody checkpoint.
2. Collects three distinct custodian names and creates three passwordless
   RSA-4096 OpenPGP key pairs.
3. Creates the immutable static-seal Secret and reconciles the OpenBao release.
4. Initializes OpenBao with three encrypted recovery shares and a 2-of-3
   threshold.
5. Creates three custodian ZIP packages and verifies that every package can
   decrypt its share.
6. Prompts for OpenRouter, DeepSeek, Brave, and Route 53 credentials. It also
   prompts for SMTP and Active Directory credentials when client values enable
   those features.
7. Displays newly generated Keycloak, Dify, Langfuse, and Grafana administrator
   passwords through the controlling terminal. Save them securely before
   acknowledging the prompt.
8. Configures KV storage, Kubernetes authentication, namespace-scoped roles and
   policies, provider records, and generated internal credentials.
9. Verifies the restricted secret-operator login and revokes root tokens.
10. Refreshes cataloged SecretStores and ExternalSecrets, reconciles blocked
    infrastructure HelmReleases, and reconciles the Flux `infrastructure`
    Kustomization.

The tool verifies Kubernetes Secret metadata and readiness without reading the
materialized Secret values.

### Resume A Failed Bootstrap

Rerun the same `bootstrap` command with the same custody root. The checkpoint
allows safe continuation after most failures.

Do not delete an incomplete `operator-custody/openbao-seal.json`. Before
bootstrap completes, it can contain custodian private keys, the one-time
initialization response, a root token, and unacknowledged administrator
passwords. Protect it as privileged recovery material.

OpenBao can commit initialization before the workstation saves the one-time
response. If the CLI reports this condition, stop and escalate. OpenBao cannot
return those recovery shares again.

### Empty-Cluster Initialization Reset

There is no CLI reset operation. Reset is destructive and requires explicit
authorization. Use it only for a pre-production cluster that contains no
OpenBao data.

Retain the immutable static-seal Secret and local custody checkpoint. Then:

1. Suspend the OpenBao HelmRelease.
2. Scale `StatefulSet/infra-openbao` to zero.
3. Identify the PV bound to `PersistentVolumeClaim/data-infra-openbao-0`.
4. Change only that PV's reclaim policy from `Retain` to `Delete`.
5. Delete the PVC and wait for the old PV and Ceph RBD image to disappear.
6. Scale the StatefulSet to one and resume the HelmRelease.
7. Confirm that the replacement PVC uses a different bound PV and that
   `/v1/sys/init` reports `initialized=false` before retrying bootstrap.

Never use this procedure for an installation that contains data.

## Check Status

```bash
uv run stack-setup status \
  --context <kube-context> \
  --client <client-name>
```

`status` reports whether OpenBao is initialized and shows the local custody
checkpoint. It does not verify leadership, policies, External Secrets, or
workload health.

## Verify Recovery

```bash
uv run stack-setup recovery verify \
  --context <kube-context> \
  --client <client-name> \
  --custodian-package /secure/custodian-1.zip \
  --custodian-package /secure/custodian-2.zip
```

Use exactly two distinct packages from the same recovery ceremony. The command
validates their client, cluster, namespace, static-seal, and ceremony bindings.
It decrypts the shares in isolated temporary GnuPG homes, creates a temporary
root token, performs a privileged verification call, and revokes the token.

The operation uses a TLS-verified port-forward to the loopback-only recovery
listener on `Pod/infra-openbao-0`. It verifies recovery custody; it does not
restore data.

## Reconcile The Catalog

Run reconciliation after a platform update changes the approved OpenBao catalog:

```bash
uv run stack-setup reconcile \
  --context <kube-context> \
  --client <client-name> \
  --custodian-package /secure/custodian-1.zip \
  --custodian-package /secure/custodian-2.zip
```

`reconcile` accepts no arbitrary paths, fields, roles, or policies. It applies
only the catalog compiled into `stack-setup`. It requires a complete custody kit
and exactly two matching custodian packages.

Schema `4` adds
`infra-agentgateway/internal:postgresqlPassword` and copies its exact value to
`infra-postgres-operations/internal:agentgatewayPassword`. It stops adding
Langfuse project credentials to new `frontend-studio/internal` reconciliation,
while additive upsert behavior preserves fields already present there. Canonical
Langfuse project credentials remain in `monitor-langfuse/internal` for tracing.
Copy conflicts prevent schema advancement, and retrying reconciliation is safe.

Before selecting a platform source that enables AgentGateway database logging,
install the exact schema-4 tooling prerequisite declared by that release and
successfully reconcile the target to schema `4`. PostgreSQL provisioning and
AgentGateway startup depend on the resulting namespace-owned credential copies.

The command creates a temporary recovery root, applies the catalog, verifies the
restricted secret operator, and revokes root access before reconciling
Kubernetes consumers. Failed runs are safe to retry. Record the custodians,
purpose, schema transition, time, and result in the external access log. Do not
record package paths, shares, or tokens.

## Update Provider Credentials

```bash
uv run stack-setup secret set <provider> \
  --context <kube-context> \
  --client <client-name>
```

Supported providers are:

- `openrouter`
- `deepseek`
- `brave`
- `route53`
- `smtp`
- `active-directory`

The CLI collects values through hidden terminal prompts, updates approved
OpenBao records with compare-and-set writes, refreshes the relevant
ExternalSecrets, and reconciles affected HelmReleases.

SMTP credentials are copied to isolated Keycloak and monitoring records.
Active Directory updates are allowed only when federation is enabled in the
selected client's rendered values. Its bind DN and credential remain only in
`auth-keycloak/external`.

## Verify Kubernetes State

After an operation, inspect resource conditions without reading Secret values:

```bash
kubectl --context <kube-context> get helmrelease openbao -n infra-openbao
kubectl --context <kube-context> get secretstores,externalsecrets -A
kubectl --context <kube-context> get pods -n infra-openbao
```

Stop if the client identity, namespace UID, recovery ceremony, or static-seal
binding does not match. Do not attempt manual repair.
