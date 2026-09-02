# Keycloak

Keycloak runs in the `auth-keycloak` namespace. It issues OIDC tokens and owns
the client realm, local users, groups, realm roles, and OIDC clients.

Keycloak can also federate human identities from Microsoft Active Directory.
Active Directory then supplies credentials, account state, profile attributes,
and approved group membership. Keycloak still owns roles and group-to-role
mappings.

## Components

The platform separates the server from the jobs that configure it:

| HelmRelease | Purpose |
| --- | --- |
| `keycloak` | Runs the Keycloak server and configures the realm. |
| `keycloak-realm-roles` | Creates realm roles, access groups, composites, and group-role mappings. |
| `keycloak-active-directory` | Configures or disables Active Directory federation. |
| `keycloak-initial-admin` | Creates or updates the initial client administrator. |
| `keycloak-<product>-oidc` | Configures an OIDC client for a supported product. |

The charts and release contracts are in:

```text
base/charts/keycloak/
base/releases/keycloak/
```

Configuration charts use finite post-install and post-upgrade Jobs that call the
Keycloak Admin API. Flux dependencies ensure that required server, realm, role,
and client resources are reconciled in order. A failed Job fails its
HelmRelease.

## Configuration Ownership

| Source | Content |
| --- | --- |
| `base/charts/keycloak/**/values.yaml` | Chart defaults and supported value shapes. |
| `base/releases/shared/` | Shared platform defaults. |
| `base/releases/keycloak/app-defaults.yaml` | Keycloak release defaults. |
| `client_*/config/client.yaml` | Shared client facts such as realm, hostname, OIDC settings, and AgentGateway roles. |
| `client_*/apps/keycloak/values.yaml` | Realm display name, initial administrator, SMTP, and optional Active Directory settings. |
| OpenBao-backed Secrets | Passwords, confidential OIDC client secrets, SMTP credentials, and Active Directory bind credentials. |

The client Keycloak Kustomization generates `client-values` and
`keycloak-product-values` ConfigMaps in `auth-keycloak`. Never put credentials
in either file.

OpenBao and External Secrets provide these runtime Secrets:

- `auth-keycloak-secrets`: bootstrap administrator and database values;
- `auth-keycloak-openbao-secret`: confidential OIDC client secrets;
- `auth-keycloak-smtp-secret`: SMTP credentials;
- `auth-keycloak-active-directory-secret`: Active Directory bind credentials;
  its ExternalSecret is rendered only when federation is enabled.

## Server And Issuer

Keycloak uses the external `postgres-auth` service. The `keycloak` role owns the
`keycloak` database, and the JDBC connection uses `verify-full` TLS against the
exact service DNS name. See
[Shared PostgreSQL](../architecture/postgresql.md#authentication).

The configured HTTPS hostname is the fixed public issuer. Strict hostname mode
and a non-dynamic backchannel keep the issuer unchanged when internal Jobs call
the ClusterIP service directly. Tokens for the client realm use:

```text
https://<auth-hostname>/realms/<realm>
```

When the external Gateway is enabled, Traefik terminates TLS and sends
`X-Forwarded-*` headers. Keycloak accepts those headers through its `xforwarded`
proxy setting, but they do not select the issuer.

## Roles And Access Groups

Human access is assigned through groups below `/access`. The realm-role Job maps
those groups to realm roles and, when configured, AgentGateway client roles.
Do not assign stack roles directly to human users.

The platform defines the standard application and administrator groups. Client
values may add approved federation groups and AgentGateway grants. Every
AgentGateway grant must exist in `authKeycloak.agentgatewayClientRoles` and match
one of these forms:

```text
llm:invoke
model:<model-id>:invoke
mcp:<server-id>:invoke
```

Do not hand-edit managed roles or group mappings in Keycloak. Reconcile changes
from Git. Role and group creation is additive, so removing a value does not
automatically delete every previously created role or group.

See [OIDC Clients](oidc.md) for client registration and token validation.

## Initial Administrator

Configure the initial administrator in `client_*/apps/keycloak/values.yaml`.
The Job looks up the user by username.

For a new user, it:

- creates an enabled user without a password;
- marks the email as unverified;
- sets the configured required actions;
- adds the configured access groups.

On a fresh initial-administrator chart installation, a second Helm hook runs
after user provisioning when SMTP and the external Gateway are enabled. It
waits for Keycloak's internal health endpoint and the public realm OIDC
discovery endpoint, requiring valid public TLS and the exact configured issuer,
then asks Keycloak to email all remaining required actions. Failure to verify
the issuer or request the email fails the Helm installation.

The administrator action link defaults to a 30-minute (`1800` second) lifetime.
`authKeycloak.adminActionTokenLifespan` may set it from 300 to 3600 seconds.

For an existing user, it updates only the email, first name, and last name. It
keeps credentials, verification state, enabled state, and completed actions. It
adds missing configured group memberships but does not remove old memberships.

The email hook is post-install only. Upgrades do not resend or backfill an
email, including for an existing initial administrator. Changing the configured
username creates a different user and leaves the previous user in place.

## Active Directory Federation

Federation is disabled by default. When enabled, Keycloak configures a managed
provider named `microsoft-active-directory` with these rules:

- connections use LDAPS on port `636` with the client-provided CA;
- the provider is read-only and never writes users or groups to Active
  Directory;
- the cache policy is `NO_CACHE`, and periodic full and changed-user syncs are
  disabled;
- eligible users must have a direct `memberOf` value for at least one approved
  group;
- approved groups are synchronized as flat children of `/access`;
- first name, last name, and `mail` are always read from Active Directory;
- `mail` is mapped to a verified Keycloak email;
- the standard Active Directory account-control mapper reads the current
  enabled state.

Approved group names must be unique, lowercase, start with `neurwerk-`, and
already exist below `/access`. The reconciliation Job tests the LDAP connection
and bind, configures the provider and mappers, synchronizes the approved groups,
and verifies each group's LDAP distinguished name.

### Enable Federation

1. Set `authKeycloak.activeDirectory.enabled: true` in
   `client_*/apps/keycloak/values.yaml`.
2. Configure the LDAPS URL, user and group DNs, username attribute, approved
   groups, and exact IPv4 egress CIDRs.
3. Add the public CA certificate as
   `client_*/apps/keycloak/active-directory-ca.pem`. The client Kustomization
   must publish it as ConfigMap `auth-keycloak-active-directory-ca`, key
   `ca.crt`, in `auth-keycloak`.
4. Store the bind DN and credential with `stack-setup`; never add them to Git or
   command arguments.

```bash
cd tooling/cli_tools/openbao_stack_setup
uv run stack-setup secret set active-directory \
  --context <kube-context> \
  --client <client-name>
```

The command is accepted only after the rendered client values enable
federation. It updates OpenBao, refreshes the ExternalSecret, and reconciles the
Active Directory HelmRelease.

Disabling federation disables an existing managed provider. It also removes the
CA mount and LDAPS egress from the Keycloak Pod, and the configuration Job does
not read Active Directory credentials.

See [Certificates And Trust](../architecture/certificates.md#microsoft-active-directory-ca-trust)
and [OpenBao Operations](../operations/openbao.md#update-provider-credentials).

## Inspect Reconciliation

Use read-only checks and do not print Secret values:

```bash
flux get helmreleases -n auth-keycloak
kubectl get statefulset,service,job,externalsecret -n auth-keycloak
kubectl describe helmrelease keycloak -n auth-keycloak
kubectl describe helmrelease keycloak-active-directory -n auth-keycloak
```

Configuration Jobs are Helm hooks and expire after one day, so a completed Job
may no longer exist. Inspect the relevant HelmRelease condition when a Job is
absent.
