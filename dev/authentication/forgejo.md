# Forgejo Authentication

Forgejo uses Keycloak for human OIDC sign-in and its own native sessions,
repository permissions, API tokens, and SSH keys afterward. Private-alpha SSO
admission and native permissions are runtime-verified, but this is not yet a
stable platform release; see
[status and scope](../architecture/forgejo.md#status-and-scope).

## Human Sign-In

The confidential Keycloak client is `forgejo`. The native Forgejo authentication
source is exactly `keycloak`, using the existing canonical issuer
`https://<auth-hostname>/realms/<realm>`, discovery, and `openid`, `profile`, and
`email` scopes. The exact callback is:

```text
https://forgejo.example.com/user/oauth2/keycloak/callback
```

The registered web origin is `https://forgejo.example.com`. Private tunneling
must preserve these identities, not replace them with localhost or a different
port. Native external account registration is enabled; local registration and
automatic account linking are disabled. Existing accounts and unexpected auth
sources require review, not automatic linking or deletion.

## Roles And Admission

The approved selection-gated contract adds these groups only when Forgejo is
selected:

| Group | Effective role | Native meaning |
| --- | --- | --- |
| `/access/neurwerk-forgejo-users` | `forgejo-user` | Required for human admission. |
| `/access/neurwerk-forgejo-admins` | `forgejo-admin`, which includes `forgejo-user` | Maps an admitted user to Forgejo administrator. |

The disabled catalog remains at 13 standard groups; the selected catalog has
15. `platform-admin` and the platform administrator group do not automatically
inherit Forgejo access. Membership must be assigned explicitly. The chart
selects the separate `files/forgejo-access.yaml` catalog only when enabled;
verify both rendered modes before adoption. Disabling
selection is not a promise to delete already-created groups, roles, or accounts.

The native source consumes a flat multivalued `forgejo_roles` claim, including
the ID token and userinfo representations required by Forgejo. The OIDC Job's
contract is `fullScopeAllowed: false` with explicit scope mappings limited to
`forgejo-user` and `forgejo-admin`. The registration Job reconciles and checks those
mappings; verify actual issued claims during acceptance. Do not accept a mapper
that exposes unrelated realm roles.

The client attaches only the shared `profile` and `email` scopes by default,
with no optional scopes. Registration changes the Forgejo client's attachments,
not the shared scope definitions; its role mapper is client-local.

This is Forgejo's native authentication boundary, not a per-request Keycloak JWT
role check on every Forgejo API or Git operation. Repository and organization
authorization remain native. Other applications' API role checks remain required
and unchanged; this integration does not weaken the general platform rule.

## Native Credentials

Automation uses Forgejo-native tokens or SSH keys with explicitly approved
permissions. Keycloak passwords, OIDC client secrets, platform API keys, and
Forgejo tokens are not interchangeable. Do not reuse the recovery administrator
for normal automation. No runners or repository migration credentials are
provisioned by this integration.

Keycloak role removal, account disabling, or an upstream directory change does
not guarantee live revocation of existing Forgejo sessions, tokens, personal SSH
keys, or repository deploy keys. An identity-provider outage also does not prove
that already-authenticated native access has stopped.

## Mandatory Offboarding

Offboarding requires an authorized administrator to complete both identity and
native Forgejo actions:

1. Remove the relevant Keycloak or directory membership and disable the identity
   according to the identity owner's process.
2. Disable the native Forgejo account and revoke its active sessions and tokens.
3. Remove or revoke personal SSH keys and inventory repository deploy keys
   separately. Revoke or rotate deploy keys the departing person controlled;
   account disabling alone is not sufficient evidence for those keys.
4. Review repository and organization ownership, team membership, service
   credentials, and integrations. Transfer ownership and replace shared
   credentials under an approved plan so no repository is orphaned.
5. Verify that former session, token, HTTPS Git, and SSH access are rejected,
   while intended remaining owners retain access. Record results, not credentials.

The actual-image acceptance run must test these boundaries. Do not claim
continuous Keycloak enforcement or automatic offboarding without that evidence.

## Emergency Access

The fixed local administrator `forgejo-recovery` is for authorized recovery only.
Normal operation has `forgejo.recoveryLoginEnabled: false`. The initial password
is created through OpenBao but is used only to create an absent account; changing
OpenBao does not reset an existing account's password. Follow the private-only
[recovery procedure](../operations/forgejo.md#emergency-login) for any use or reset.
