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
| `client_*/apps/keycloak/values.yaml` | Realm display name, theme selection, name/logo branding, initial administrator, application-admin role exclusions, SMTP, and optional Active Directory settings. |
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
Under the implemented uniform application-admin policy, enabled Forgejo also
adds `forgejo-admin` to `platform-admin` by default. Adoption and live cleanup
remain separate from implementation and the published baseline described below.
See [Forgejo authentication](forgejo.md#roles-and-admission) for the native
role boundary, restricted OIDC claim, and mandatory manual offboarding.

The `neurwerk-` prefix is intentional for canonical Keycloak groups and legacy
same-name Active Directory federation. The staged `groupMappings` mode accepts
other AD source names without renaming these canonical parents. Existing
application roles retain their supported permissions; the platform-admin
composition is described below. Clients inherit the platform group
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

The baseline canonical group and explicit resource-grant rules were published
in `v0.3.3`, not the later Forgejo inheritance and exclusion policy below. Its
tagged migration requires aligned client values and group references before cleanup. Publication
does not establish live adoption; release verification covers rendered/static
tests and contract checks, not live installation, migration, cleanup, or recovery.

### Uniform Application Administration

This policy is introduced in Base realm-roles chart `2.2.0`; it is not part of
the published `v0.3.6` baseline.

Base's `/access/neurwerk-platform-admins` group maps to `platform-admin`, which
inherits the existing supported application roles by default. The eight core
direct grants are `keycloak-admin`, `api-key-admin`, `opensearch-admin`,
`langfuse-admin`, `pii-admin`, `studio-user`, `librechat-admin`, and `dify-admin`.
When `forgejo.enabled: true`, Base adds `forgejo-admin`, which inherits
`forgejo-user`. LibreChat and Dify administrator roles likewise retain their
existing user-role composites.

This unifies existing supported roles, not unrestricted rights in every product.
For example, `studio-user` supplies admission and `keycloak-admin` retains its
existing scoped realm-management permissions. No missing product permissions,
root access, Kubernetes administrator authority, or OpenBao administrator
authority are introduced.

Clients may subtract only those nine direct grants with
`authKeycloak.platformAdminRoleExclusions`, default `[]`:

```yaml
authKeycloak:
  platformAdminRoleExclusions: ['forgejo-admin']
```

The list replaces the entire inherited exclusion list; `[]` restores the eight
core grants plus Forgejo when enabled. `forgejo-admin` remains a known valid
exclusion while Forgejo is disabled, without enabling its roles or groups.
Non-lists, non-string entries, duplicates, unknown roles, group names, and
indirect user roles such as `forgejo-user` are rejected. Model/MCP roles and
`llm:invoke` are never valid exclusions. This is a subtract-only exception to
the immutable catalog contract, not permission to override role definitions,
group mappings, or catalogs or to add authorization.

Exclusions change only the direct children of `platform-admin`, not the
application roles themselves or their other composites. Reconciliation removes
stale direct composite grants, including when the resulting list is empty.
Other grants remain effective: an exclusion does not revoke direct user roles,
application-group memberships, or native application sessions and tokens.
Initial-user membership provisioning is add-only and requires explicit cleanup
after verification when a membership is no longer intended.

Model and MCP access remain separate. Keep their existing groups, explicit
baseline grants, and resource catalog policy unchanged; platform administration
does not imply either resource grant. See the
[Forgejo transition procedure](../operations/forgejo.md#platform-admin-transition)
for readiness, membership cleanup, and the recorded alpha verification.

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
The Job looks up the user by username. Base's `authKeycloak.initialAdminGroups`
default remains `'["/access/neurwerk-platform-admins"]'` only. This inherits the
supported application roles, including enabled Forgejo unless excluded; no
separate application-admin membership is needed for that inheritance. Client
membership lists must use the canonical groups above. Preserve separately
declared model/MCP memberships and baseline grants: administrative membership
alone must not supply model or MCP grants.

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

- connections default to verified LDAPS on port `636` with the client-provided
  CA; plaintext LDAP on port `389` needs the explicit opt-in described below;
- the provider is read-only and never writes users or groups to Active
  Directory;
- the cache policy is `NO_CACHE`, and periodic full and changed-user syncs are
  disabled;
- eligible users must have a direct `memberOf` value for at least one approved
  source group; nested AD membership does not grant access;
- built-in `READ_ONLY` group mappers resolve directory membership, without a
  plugin or copying that membership into local Keycloak memberships;
- first name, last name, and `mail` are always read from Active Directory;
- `mail` is mapped to a verified Keycloak email;
- the standard Active Directory account-control mapper reads the current
  enabled state.

### Staged Runtime Gate

Server and Active Directory configuration charts `1.1.0` add `groupMappings`
and `allowInsecureLdap`. Tooling `0.7.0` implements both and its image is
[published and verified](../operations/image-releases.md#auxiliary-tooling-image).
Base pin adoption is still pending. Existing chart pins remain unchanged;
image publication is not evidence of platform adoption or deployment.

Selecting mappings or plaintext LDAP requires both charts to receive
`k8sTools.image` as `ghcr.io/neurwerk/k8s-stack-tooling:X.Y.Z`, version
`>=0.7.0`, optionally followed by `@sha256:<64 lowercase hex>`. Moving tags,
prereleases, digest-only references and other repositories are rejected. This
render-time gate checks the declared version, not whether the image is published.
Disabled federation and legacy LDAPS remain renderable with the existing pins.
Image publication, platform release, client adoption and live verification are
separate authorized steps; only Tooling image publication is established here.

### Group Selection

When enabled, set exactly one non-empty list under `authKeycloak.activeDirectory`:

- `groupNames`: legacy same-name mode. Names are unique, lowercase, at most 64
  characters and match `^neurwerk-[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$`. Each group
  must already exist as a flat child of `/access`. Legacy verification requires
  one case-insensitively exact expected DN in `attributes.LDAP_ENTRY_DN`.
- `groupMappings`: each entry contains only `sourceName` and `targetParent`.
  Sources are AD CNs of 1-64 characters; case, underscores, internal spaces and
  LDAP punctuation are preserved. Controls, outer whitespace, placeholders and
  case-insensitive duplicate sources are rejected. Target paths must be unique,
  exact existing canonical groups from the 13-group catalog, or the two optional
  Forgejo groups when present. The other list must be omitted or `[]`.

For example, this non-secret selection maps `CORP_STUDIO` to Studio access:

```yaml
authKeycloak:
  activeDirectory:
    groupNames: []
    groupMappings:
      - sourceName: CORP_STUDIO
        targetParent: /access/neurwerk-studio-users
```

This is only the group selection, not a complete enablement configuration. It
produces `/access/neurwerk-studio-users/CORP_STUDIO`. Members inherit the
canonical parent's existing roles; the parent and its role mappings are not
renamed or rewritten. Full-path group claims report the actual child membership,
not a copied membership in `/access/neurwerk-studio-users`. Policies that compare
group paths must use the actual child path rather than infer parent membership
from inherited roles.

Mapping mode uses one built-in `READ_ONLY` mapper per source. Each mapping
selects exactly one source at
`CN=<escaped sourceName>,<groupsDn>`. For `groupsDn: OU=Groups,DC=example,DC=com`,
the example source is `CN=CORP_STUDIO,OU=Groups,DC=example,DC=com`. A source in a
different OU is not selected merely because it has the same CN. Tooling escapes
DNs and LDAP filters separately and uses both exact `cn` and `distinguishedName`
filters. Eligibility uses direct `memberOf`; each mapper uses direct `member`
lookup (`LOAD_GROUPS_BY_MEMBER_ATTRIBUTE`), not nested AD group expansion.

Reconciliation tests the connection and bind, verifies the existing canonical
parents, and requires each mapper sync to process exactly one source with no
failed or removed groups. It reads back mapper settings and the real parent and
child IDs, names and paths, including unchanged parent IDs. A missing source or
wrong child fails reconciliation. Keycloak `26.7.2` binds these mapped groups by
parent and name; mapping mode neither requires nor fabricates `LDAP_ID` or
`LDAP_ENTRY_DN` attributes as proof of that binding.

### Transport And Credentials

`allowInsecureLdap` defaults to `false`. Use `ldaps://ad.example.com:636` with
verified CA and hostname trust. Plain `ldap://ad.example.com:389` is accepted
only with `allowInsecureLdap: true` and sends bind credentials, user passwords and
directory data without TLS. There is no StartTLS, automatic downgrade or
certificate-verification bypass. Other ports, URL credentials, paths, queries
and fragments are rejected. Setting the opt-in alone does not change an LDAPS URL.

Both transports use the same `auth-keycloak-active-directory-secret` and
OpenBao fields. The Keycloak server's directory egress allows only the selected
port to `egressCidrs`, and only while enabled. Only enabled LDAPS mounts the AD
CA and configures its truststore and CA reload watch; plaintext LDAP does not.

### Reconciliation And Retry

During every mapping reconciliation and transitions to or from legacy mode,
Tooling temporarily disables the provider until all checks succeed. Plan for an
interruption to federated sign-ins and keep an independent local break-glass
administrator available. Run only one reconciler for a realm at a time.

Ownership and retry state use native component `subType`, not custom config
keys: mapped mappers use `k8s-stack-tooling.group-mapping.v1`, and the provider
uses `k8s-stack-tooling.group-reconciliation-pending.v1` while disabled, then
`k8s-stack-tooling.active-directory.v1` when ready. Unrelated subtypes, a manual
mapper overlapping `/access`, or a legacy mapper changed to `IMPORT` require
operator review rather than takeover.

Preflight failures leave the previous state intact. Partial failures after the
provider is disabled leave it disabled for retry; fix the reported problem and
rerun reconciliation rather than manually enabling a partial mapping set. If
final activation cannot be verified, Tooling attempts to disable it again and
reports when even that cannot be verified; this requires operator review.

Group-mapper cleanup removes only reserved, owned mappers under this provider.
It never deletes canonical groups, source-named children, unrelated local groups,
roles or local memberships. Removing a mapping removes its dynamic directory
grants on reevaluation, not existing local grants or already-issued tokens and
application sessions. `NO_CACHE` is not immediate session revocation or permission
for indefinite use during a directory outage: tokens retain their expiry and
application session rules still apply.

### Enable Federation

Use this sequence only for an authorized deployment:

1. For mappings or plaintext LDAP, first publish and verify a compatible Tooling
   image through the separate release process, then adopt its reviewed pin in
   both charts. Review the selected platform release and migration notes; do not
   treat a source version or a successful render as publication.
2. Confirm the canonical target groups and roles exist, each AD source is
   directly under `groupsDn`, and a local break-glass login works. Review local
   memberships and conflicting mappers before changing an existing provider.
3. In `client_*/apps/keycloak/values.yaml`, configure the URL, user and group DNs,
   `usernameAttribute` (`sAMAccountName` or `userPrincipalName`), one group list,
   `emailVerified: true` and exact IPv4 `egressCidrs`. Keep
   `allowInsecureLdap: false` unless plaintext has been explicitly approved.
4. For LDAPS only, add the public CA certificate as
   `client_*/apps/keycloak/active-directory-ca.pem`. The client Kustomization
   must publish it as ConfigMap `auth-keycloak-active-directory-ca`, key
   `ca.crt`, in `auth-keycloak`; verify its fingerprint and hostname trust.
5. Apply the reviewed `enabled: true` product values, server trust/egress and
   enabled secret-sync resources. The credential command must see that enabled
   selection in `auth-keycloak/keycloak-product-values`; a local file change
   alone is insufficient. A first configuration Job may wait for its bind Secret.
6. If credentials are missing or need rotation, store the bind principal (DN or
   UPN) and credential with the following operator command. Reuse an existing
   valid pair when only changing mappings; never add credentials to Git or
   command arguments.

```bash
cd tooling/cli_tools/openbao_stack_setup
uv run stack-setup secret set active-directory \
  --context <kube-context> \
  --client <client-name>
```

The command's enabled-only semantics are unchanged. It updates OpenBao,
refreshes the ExternalSecret, and reconciles the Active Directory HelmRelease;
it does not enable federation or bypass the runtime gate. Disabled selection is
rejected before prompting or opening OpenBao. Missing or failed enabled consumers
remain fatal.

After reconciliation, inspect current Flux and HelmRelease conditions, the
Keycloak Pod, warning events and safe Job logs without printing credentials.
Confirm provider activation, exact mapped child paths and inherited roles, an
intended direct member's access, and denial for an unapproved or nested-only
member. Check affected applications and preserve unrelated users, local
memberships and persistent data. Reuse accepted feature-test evidence rather
than requiring a disposable server; live verification remains a separate
operator action, not a claim made by this document update.

Disabling federation disables an existing managed provider. It also removes the
AD CA mount/watch and directory egress from the Keycloak Pod. The disabled
configuration Job omits directory inputs and bind credentials; it does not
delete groups, local memberships or stored OpenBao credentials.

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
