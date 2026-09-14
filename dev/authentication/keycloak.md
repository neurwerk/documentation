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
| `base/charts/keycloak/realm-config/realm-roles/files/standard-access.yaml` | Immutable platform catalog of standard groups, realm roles, composites, and application mappings; not a values override. |
| `base/releases/shared/` | Shared platform defaults. |
| `base/releases/keycloak/app-defaults.yaml` | Keycloak release defaults. |
| `client_*/config/client.yaml` | Shared client facts such as realm, hostname, OIDC settings, and AgentGateway roles. |
| `client_*/apps/keycloak/values.yaml` | Realm display name, theme selection, name/logo branding, initial administrator, SMTP, and optional Active Directory settings. |
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

## Native Theme

The product repository `keycloak_theme/`
([neurwerk/k8s_stack_keycloak_theme](https://github.com/neurwerk/k8s_stack_keycloak_theme))
owns the native `neurwerk` login and email theme and its Dockerfile image,
which extends Keycloak `26.7.2`. Shared overrides include the authentication
layout, login and forgot-password forms, footer, and HTML email wrapper, using
native Keycloak field and button macros. Authentication behavior remains
upstream; account, admin, and welcome themes are unchanged. Branding does not
change language or SMTP policy.

Login theme selection is realm-scoped, not a separate login theme per user's
privilege. Administrators can therefore see the branded login when authenticating
through a realm that selects it, without changing the Admin Console itself.

Theme image `0.1.1` is published; Tooling remains at `0.6.1`. PNG/SVG support is
merged at `94c69da`, with existing PNG branding verified on alpha. Signed Base
`v0.3.5` is published at `b016489` (release PR #100), with its publication identity
verified; an authorized stable client's public login/reset pages also serve SVG branding.
See [Image Releases](../operations/image-releases.md#keycloak-theme-image).

The platform contract keeps shared styles and templates fixed in the
public `neurwerk` theme. Clients supply only a company name and logo through the
`client-brand` child theme; no client CSS or template overrides are supported:

- `authKeycloak.branding.enabled` defaults to `false`. Enabling it mounts assets
  but does not select a realm theme.
- The existing `authKeycloak.realmDisplayName` supplies `companyName` in both
  generated login and email `theme.properties`, each with `parent=neurwerk`.
- `authKeycloak.branding.logoConfigMapName` selects a client-owned ConfigMap in
  `auth-keycloak`, containing fixed key `company-logo.<format>`.
  `authKeycloak.branding.logoFormat` accepts `png` (default) or `svg` and supplies
  the shared theme property `companyLogoFormat` for login only. A read-only
  projected volume at `/opt/keycloak/themes/client-brand` combines the properties with the
  logo at `login/resources/img/company-logo.<format>`.
- Flux excludes `.png` source files by default. Store the PNG bytes as
  `apps/keycloak/company-logo.bin` and use generator entry
  `company-logo.png=company-logo.bin`; the mounted file remains a PNG. This keeps
  the logo in the source artifact without prohibited `.sourceignore` overrides.
  SVG sources can remain `source.svg`, with generator entry
  `company-logo.svg=source.svg`: Flux does not exclude `.svg` by default, so only
  PNG sources need the `.bin` workaround.
- `authKeycloak.loginTheme` and `authKeycloak.emailTheme` default to empty strings
  and are omitted from realm updates when empty. Omission neither selects nor
  clears a theme. Explicitly set both to `client-brand` to select the child;
  that selection requires branding to be enabled.
- Reloader watches the logo ConfigMap while preserving the Active Directory CA
  reload annotation. A Pod-template `checksum/branding` rolls out generated
  property changes.

To remove branding, first explicitly select upstream `keycloak.v2` for login
and `keycloak` for email while keeping the custom image and child mount available.
Verify realm reconciliation before disabling branding and removing its assets in
a later change. Manual Admin Console selection is only for disposable previews,
not managed production configuration.

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

The platform defines these 13 canonical groups as flat children of `/access`:

- `neurwerk-api-key-admins`
- `neurwerk-dify-admins`
- `neurwerk-dify-users`
- `neurwerk-keycloak-admins`
- `neurwerk-langfuse-admins`
- `neurwerk-librechat-admins`
- `neurwerk-librechat-users`
- `neurwerk-opensearch-admins`
- `neurwerk-pii-admins`
- `neurwerk-platform-admins`
- `neurwerk-studio-users`
- `neurwerk-llm-all-users`
- `neurwerk-mcp-all-users`

The staged optional Forgejo contract preserves these 13 groups when unselected
and adds `neurwerk-forgejo-users` and `neurwerk-forgejo-admins` only when selected.
It does not add automatic Forgejo inheritance to platform administrators. These
selection changes are pending adoption, not part of the published group contract
below. See [Forgejo authentication](forgejo.md#roles-and-admission) for the native
role boundary, restricted OIDC claim, and mandatory manual offboarding.

The `neurwerk-` prefix is intentional: it is the supported Active Directory
namespace and satisfies federation prefix validation. Existing application
realm roles and composites are unchanged. Clients inherit the platform group
definitions and application mappings rather than copying them. Clients own
local or directory memberships, directory settings, and explicit model and MCP
grants.

The chart loads the shared catalog from `files/standard-access.yaml`, not from
overridable values. Rendering rejects any supplied `authKeycloak.accessGroups`,
`authKeycloak.realmRoles`, or `authKeycloak.realmRoleComposites` key, even an empty
one. Omit those keys from client values.

Application and administrator groups do not implicitly grant resource access.
`neurwerk-llm-all-users` receives only explicitly granted model permissions;
`neurwerk-mcp-all-users` receives only explicitly granted MCP permissions. The
word `all` is not a wildcard for catalog additions, and MCP grants never generate
model grants. Both require `llm:invoke` alongside each resource permission.
The global safe default and both client catalog policies use
`grantToAccessGroups: false`; the template rejects
`openrouterCatalog.grantToAccessGroups: true` rather than expanding model roles.

Configure explicit grants under `authKeycloak.agentgatewayAccessGroups`, keyed
by full group path. Only `/access/neurwerk-llm-all-users` and
`/access/neurwerk-mcp-all-users` are accepted. Rendering rejects grants to any
other group, MCP roles in the LLM group, and model roles in the MCP group. Each
grant must be a list of roles from the effective catalog.

Before overlaying those explicit grants, the template sets
`clientRoles.agentgateway: []` on all 13 standard groups. These explicit empty
mappings clear stale managed AgentGateway grants during reconciliation; omitted
mappings would not. This does not delete obsolete groups or remove user
memberships, and it does not revoke unrelated direct user or service grants.

Every AgentGateway grant must exist in the effective client-role catalog
(including selected OpenRouter model roles and explicit
`authKeycloak.agentgatewayClientRoles`) and match one of these forms:

```text
llm:invoke
model:<model-id>:invoke
mcp:<server-id>:invoke
```

Do not hand-edit managed roles or group mappings in Keycloak. Reconcile changes
from Git. Role and group creation is additive, so removing a value does not
automatically delete every previously created role or group.

See [OIDC Clients](oidc.md) for client registration and token validation.

These group and grant rules are published in `v0.3.3`. Its tagged migration
requires aligned client values and group references before cleanup. Publication
does not establish live adoption; release verification covers rendered/static
tests and contract checks, not live installation, migration, cleanup, or recovery.

### Studio Event Access

For Studio `0.9.0`, Base's realm-roles chart `2.0.2` adds
`realm-management/view-events` to the `keycloak-admin` composite alongside its
existing user, client, and realm read permissions. Base owns provisioning;
Studio forwards the administrator's bearer token and does not provision roles
or use a service account for these reads.

This expands upstream event-read permission, not merely permission to read
Studio's recent-sign-in summary. Holders can read Keycloak user and admin events
directly, including event details; Studio's successful-`LOGIN`, seven-day,
timestamp-only filtering does not restrict that upstream authority.

Realm provisioning enables event storage with default retention of `604800`
seconds (seven days). Keycloak captures `LOGIN` by default, but a customized
realm can disable that event type; provisioning does not set an explicit
`enabledEventTypes` list. Missing records therefore cannot establish that a
user never signed in. Missing event-read permission or failed lookups are
reported as unavailable, not as an empty history.

The existing post-install/post-upgrade Job applies this to both new and existing
realms. Administrators need a newly issued token to use the added permission.
The authorized alpha rollout completed the Job and confirmed the grant addition;
stable adoption remains separate. See
[Studio](../architecture/studio.md#admin-users-and-recent-sign-ins) for the API
and UI contract and the limits of the recorded live verification.

### Existing-Realm Cleanup

For an unused development client, use a one-time manual cleanup after the base
and client configuration is aligned; no membership migration tooling is needed.
Fresh installations into verified empty or replacement environments use the
canonical defaults without group cleanup. Preserve intended explicit model/MCP
grants and administrator memberships when aligning existing clients.

1. Confirm an independent administrative login that does not rely on a group
   being removed. Align default groups, initial-admin memberships, directory
   allowlists, and explicit grants with the canonical set, then verify successful
   reconciliation before deleting anything.
2. In the intended realm's Keycloak Admin Console, inspect the exact superseded
   unprefixed groups and their memberships and role mappings. Delete only those
   obsolete groups after confirming their access is no longer needed. Do not delete the
   realm, `/access`, canonical groups, unrelated groups, users, application realm
   roles, composites, or OIDC clients.
3. Verify the canonical groups, intended administrator membership, and effective
   application and resource permissions. Confirm unrelated identities and
   configuration remain intact.

Removing YAML does not delete existing groups. Existing-user provisioning adds
missing memberships but does not remove old ones. Group deletion removes that
group's memberships and inherited access; it does not delete the users. If the
client has active users whose access must be preserved, stop and review their
intended memberships rather than treating them as unused development state.

## Initial Administrator

Configure the initial administrator in `client_*/apps/keycloak/values.yaml`.
The Job looks up the user by username. Fresh-bootstrap defaults and configured
initial-admin memberships must use the canonical groups above, including
`/access/neurwerk-platform-admins` for platform administration. Administrative
membership alone must not supply model or MCP grants.

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
