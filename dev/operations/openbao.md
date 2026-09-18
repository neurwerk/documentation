# OpenBao Operations

`stack-setup` initializes and operates OpenBao from a trusted workstation. It
handles bootstrap, catalog reconciliation, status checks, recovery verification,
and supported provider credential updates. It is not a Kubernetes Job.

The published `v0.3.3` platform release contract requires `stack-setup` `0.2.11`
from tooling commit `5d1a33a938e22e9034581aebecf33485adc88a29`.

The AgentGateway usage migration requires reconciliation schema `4`. Its target
platform release must pin `openbao-stack-setup` `0.2.11` from tooling commit
`5d1a33a938e22e9034581aebecf33485adc88a29`. Do not substitute a branch or
moving reference. This matches the currently published platform prerequisite.

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

### Staged Optional Forgejo Catalog

Forgejo requires the selection-gated `openbao-stack-setup` `0.2.12` catalog,
still at schema `4`, from tooling commit
`7a00c0d7a725a500ca251d699ce3f00dff57e660`; the baseline prerequisite above must
not be assumed to contain it. The optional packages remain excluded until the target release
contract is updated and adoption is authorized.

Selection is read from `auth-keycloak/client-values` on each run. Stage namespace
and secret-sync resources first, then reconcile `forgejo.enabled: true` into
that ConfigMap while keeping the application stage suspended. Run the approved
new tool before starting the application. The exact namespace store is
`forgejo-openbao-secret-store`. See
[Forgejo operations](forgejo.md#staged-activation) for sequencing, credential
copies, and checks that avoid a database/password dependency cycle.

## Optional WireGuard Catalog

`openbao-stack-setup` `0.2.13` adds the static gateway's server-key catalog at
schema `4`; use the exact Tooling revision in the selected optional Base
package's prerequisites. `wireguard.enabled` in namespace-local
`wireguard/wireguard-product-values` selects it, with the fixed
`serverKeySecret: wireguard-server-key`. Missing/disabled selection does not add
the optional role or key. This does not expand secret-operator provider access.

Bootstrap/reconcile persist a missing raw-base64 X25519 key at
`wireguard/internal:privateKey`, preserving valid existing values. After temporary
root revocation, they converge `wireguard-openbao-secret-store` and the
`wireguard-server-key` ExternalSecret. The Secret receives only `privateKey`.
There is no new key-update command, device enrollment, permission controller or
gateway activation. Follow [WireGuard setup](wireguard.md#server-key-setup) for
staging and the separate Mac-public-key approval and stop/update/start procedure.

## Optional Speech Credentials

[Tooling PR #38](https://github.com/neurwerk/k8s_stack_tooling/pull/38) merged
optional `librechat-stt` and `librechat-tts` managed credentials in package
`0.2.14`, still at catalog schema `4`, at Tooling revision
`0c2e02ddf18776530c1b7cd735327bf27570721b`. No package publication is implied by
the merge. It requires compatible charts and separately authorized adoption;
see [LibreChat voice support](../architecture/librechat.md#optional-voice-support).

The record is `frontend-librechat/external`, with separate `sttApiKey`
and `ttsApiKey` fields. Both the selected direction and its authentication switch
must be enabled in `librechat-product-values` before the tool prompts for a key.
Bootstrap adds no speech prompts or records. Existing installations need an
approved reconciliation to grant creation of this exact external record.

Each update preserves sibling fields and refreshes only the selected
`frontend-librechat-stt-secret` or `frontend-librechat-tts-secret` consumer.
It does not wait for the whole LibreChat application, allowing both keys to be
supplied in sequence. Reloader handles rollout; check application readiness after
all required keys are provisioned during the authorized deployment. No live key
provisioning or reconciliation has been performed as part of this implementation.

## Optional Docling Credentials

[Tooling PR #44](https://github.com/neurwerk/k8s_stack_tooling/pull/44) adds CPU selection
in `openbao-stack-setup` `0.2.16` at revision
`269b8c09190df8bd7b775ff7ef202964d3fe2703`, still at catalog schema `4`.
Use that exact source revision for the optional Docling package; the global
`0.2.11` prerequisite does not contain this catalog. The operator runs these
commands on the trusted workstation, not through an agent or Kubernetes Job.

Stage `releases/namespaces/docling`, client product values and one credential package
first, without composing the Docling application. Use
`releases/docling/secret-sync/internal` for CPU, or `releases/docling/secret-sync`
for remote. In `docling/docling-product-values`, the `values.yaml` data for CPU is:

```yaml
docling:
  enabled: true
  apiKeySecretRef: {name: docling-api, key: api-key}
  inference:
    mode: cpu
```

Remote mode is the default when `mode` is omitted. It additionally requires
`docling.inference.tokenSecretRef: {name: docling-inference, key: token}`.

This selector enables credential preparation only while the application package
is unselected. Missing/disabled selection adds no internal records, roles or
consumer refreshes. Invalid selection or mismatched references stops the CLI
before confirmation or secret interaction. Deselection does not delete credentials.
Changing modes does not rotate or delete stored OpenBao values. Existing `0.2.15`
credential provisioning remains valid; no new keys or repeated token entry are
required merely to use CPU mode. Switching a Flux stage from the remote package
to the internal package may prune the unused inference ExternalSecret and its
owned Kubernetes Secret, but retains the token in OpenBao for later remote use.
Update that stage's health checks to match its selected consumers.

For an existing installation, from `tooling/cli_tools/openbao_stack_setup` at the
revision above, follow the normal two-custodian procedure:

```bash
uv run --frozen stack-setup reconcile \
  --context <kube-context> --client <client-name> \
  --custodian-package <first-secure-package> \
  --custodian-package <second-secure-package>

# Remote mode only; skip this command for CPU mode.
uv run --frozen stack-setup secret set docling-inference \
  --context <kube-context> --client <client-name>
```

Reconciliation generates the missing service API key and copies it to extProc's
isolated record. It preserves existing values and rejects invalid keys or copy
conflicts without rotation. It performs normal catalog/infrastructure convergence,
but does not wait for the inference token or start Docling.
The second command is rejected in CPU mode before any secret interaction. In remote
mode it collects the upstream token in a hidden prompt and refreshes
only `docling-inference`; it does not force application reconciliation.
Do not put tokens or custody material in arguments, Git, logs or chat.

The two SecretStores and the selected ExternalSecrets (two for CPU, three for remote)
can remain NotReady until these steps complete. Verify their conditions and target
Secret metadata, never values. This prepares credentials only; gateway conversion,
remote-mode server settings and application activation remain separate prerequisites.
See [Docling architecture](../architecture/docling.md).

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
- `docling-inference` (selected remote Docling only; CPU-aware selection from `0.2.16`)

The CLI collects values through hidden terminal prompts, updates approved
OpenBao records with compare-and-set writes, refreshes the relevant
ExternalSecrets, and reconciles affected HelmReleases.

SMTP credentials are copied to isolated Keycloak and monitoring records.
Active Directory updates are allowed only when federation is enabled in the
selected client's rendered `auth-keycloak/keycloak-product-values` ConfigMap.
The boolean `authKeycloak.activeDirectory.enabled` remains the selector; changing
`groupMappings` or `allowInsecureLdap` neither enables federation nor changes this
command. Disabled selection is rejected before prompting or opening OpenBao.

For both group modes and both transports, the bind principal (DN or UPN) and
credential use the existing `activeDirectoryBindDn` and
`activeDirectoryBindCredential` fields in `auth-keycloak/external`, preserving
SMTP sibling fields. External Secrets delivers the same
`auth-keycloak-active-directory-secret`. No new provider record or credential
rotation is required for a mapping-only change. Missing or failed enabled
ExternalSecret and `keycloak-active-directory` HelmRelease consumers remain fatal.

Before credential provisioning, apply the reviewed enabled product values and
required server trust/egress and secret-sync resources. For mappings or plaintext
LDAP, first satisfy the separate compatible-image publication and adoption gate;
the secret command cannot bypass it. Follow the
[federation operator sequence](../authentication/keycloak.md#enable-federation),
then verify reconciliation without printing Secret values. Tooling runtime
`0.7.0` is a separate package from this workstation CLI; its image is published
and verified, but Base pin adoption is pending. No new OpenBao schema or
bootstrap ceremony is implied.

## Verify Kubernetes State

After an operation, inspect resource conditions without reading Secret values:

```bash
kubectl --context <kube-context> get helmrelease openbao -n infra-openbao
kubectl --context <kube-context> get secretstores,externalsecrets -A
kubectl --context <kube-context> get pods -n infra-openbao
```

Stop if the client identity, namespace UID, recovery ceremony, or static-seal
binding does not match. Do not attempt manual repair.
