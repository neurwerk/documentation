# Forgejo Operations

This runbook describes the optional integration. Forgejo is currently excluded
from stable platform release eligibility. Preparation, credential provisioning,
and application startup are separate stages.
Do not contact a cluster, open a tunnel, change credentials, or touch persistent
data without explicit authorization.

## Authorized Alpha Evaluation

On 2026-09-14, the operator authorized the initial private alpha rollout and
explicitly waived the pre-install shared-database backup for that rollout.
The client rollout issue records the scope. Existing database state was observed;
the waiver does not declare it empty, authorize deletion or replacement, or
establish that recovery is possible. It does not change backup requirements for
other rollouts or stable adoption.

This specific alpha evaluation may use the reviewed Forgejo source while its
packages remain excluded from stable release eligibility. No stable tag is
published or adopted by this exception. Keep the application suspended until
the operator completes the required OpenBao ceremony and credential consumers
converge. The operator will run that ceremony on their trusted workstation;
the backup waiver does not waive the two-custodian procedure.

## Before Adoption

1. Complete and review Base, Tooling, and client changes together. Verify disabled
   defaults, 13 groups when unselected and 15 when selected, default
   `platform-admin` inheritance of enabled Forgejo unless excluded, and
   `fullScopeAllowed: false` with only the two
   Forgejo role scope mappings. Verify `forgejo.oidc.caConfigMap` and its optional
   namespace-local `ca.crt` bundle when system roots do not trust the issuer.
2. Use `openbao-stack-setup` `0.2.12` from tooling commit
   `7a00c0d7a725a500ca251d699ce3f00dff57e660`, recorded in the optional package's
   prerequisites. Schema `4` alone does not prove that the selected optional
   catalog is installed. Do not substitute a moving branch.
3. Check that the target release explicitly permits the optional packages and
   has matching migration instructions. Staged exclusions are a stop condition
   for stable adoption; only the scoped alpha evaluation above is authorized
   before stable eligibility. Stable adoption requires a reviewed exact signed platform tag and
   the compatibility checks in [Supported Upgrades](upgrades.md).
4. Review the canonical hostname, approved private tunnel, local port `443`
   binding, browser trust, Pod DNS, Keycloak resolution, and egress. Exact
   Keycloak public IP CIDRs require verification against the Pod resolver if
   `public-dns` is selected. Do not change the shared routing mode merely to route Forgejo.
5. Verify backup and recovery arrangements for the complete operations database
   instance, Forgejo PVC, and durable credentials. Establish approved custody for
   the recovery password. Do not assume an existing target is empty.

Private runtime acceptance is recorded below. Public-mode, rotation, outage,
and full-recovery acceptance are not established by those results.

## Verified Alpha Results

On 2026-09-14, before the uniform platform-admin policy, the operator completed
credential reconciliation and authorized temporary test accounts, repositories,
and keys. The following historical checks passed:

- All Flux sources/stages and Helm releases Ready, with the exact pinned image.
- Production cert-manager certificate Ready and canonical hostname/chain verified
  through a loopback-bound test forward without disabling TLS verification.
- Keycloak normal-user and Forgejo-admin admission, with correct native admin
  status; a no-role user was denied and no native account was created for it.
- Private repository creation and anonymous denial; HTTPS Git push/clone and
  SSH fetch/push with an independently obtained, pinned public SSH host key.
- LFS batch upload/download with matching synthetic content and a committed
  Git LFS pointer; the standalone `git-lfs` client was not exercised.
- A Forgejo-only restart preserved Git history, LFS content, native account and
  token access, and the SSH host identity.
- The canonical Pod DNS name resolved to the Forgejo Service. A distinct
  unapproved Pod with explicit egress to Forgejo could not reach web or SSH.
- Cleanup removed all synthetic Keycloak/native users, repositories, tokens,
  SSH keys, test helpers and forwards. Database metadata checks found no
  remaining test users, repositories, tokens, or SSH keys.
- The shared operations PostgreSQL Pod remained unchanged with zero restarts;
  Ceph reported HEALTH_OK and the logging pipeline remained Ready.

Initial certificate-mount and startup-probe warnings cleared during startup.
The final runtime log check found no error or fatal entries. Keycloak mapper
readback required chart `0.1.1`: the server omits an empty role prefix and adds
defaults, so the verifier now normalizes only that empty value and explicitly
disables the introspection claim without relaxing other checks.

Tests used an HTTP client with canonical TLS identities and private forwards,
not a visual desktop/mobile browser check. The user's workstation still needs
its own canonical-hostname tunnel. The operator-selected existing account's
explicit Forgejo admin membership and both effective Forgejo roles were verified;
its prior declared groups remained present, with no pending account actions.
That check used explicit membership, not the subsequently implemented default
platform-admin inheritance; it does not verify the new policy or its cleanup.
No backup or full restore was performed under the scoped waiver;
public mode, credential/certificate rotation, and outage/offboarding drills
remain separate checks.

## Platform-Admin Transition

The implemented Base policy grants enabled Forgejo administration through
`platform-admin` by default, subject to the narrow
[application-role exclusions](../authentication/keycloak.md#uniform-application-administration).
Live adoption, removal of redundant client membership declarations, and live
membership cleanup are not established by the historical results above.

The subsequent authorized alpha transition passed on 2026-09-14 using Base
[PR #120](https://github.com/neurwerk/k8s_stack_base/pull/120), commit
`63ff2a0b9965075afcd543ad4839828ff8c96600`, and realm-roles chart `2.2.0`:

- The platform-admin composite gained the enabled Forgejo role while its entire
  inherited graph remained free of AgentGateway, model, and MCP grants.
- A fresh temporary account with only platform-admin group membership reached
  Forgejo's native admin interface and had zero effective AgentGateway roles.
  Its Keycloak and Forgejo accounts and test forward were removed afterward.
- The client removed its redundant direct-group declaration only after Base
  readiness and inherited SSO verification. The initial-admin Job then completed
  using the three intended platform/model/MCP memberships.
- Exactly one live membership was removed from the selected real account: the
  direct Forgejo-admin group. Before/after checks preserved all other memberships,
  account state, direct role mappings, effective realm and AgentGateway roles,
  and resource-group policies. Both Forgejo roles remained effective.
- All 51 Helm releases and all Flux stages were Ready afterward, and the
  temporary policy-check Pod and NetworkPolicy were removed.

These checks did not change the real account's password, sessions, native
tokens, SSH keys, or repositories. Client exclusion cases were validated by
rendered tests, not by temporarily withdrawing live administrator access.

For an authorized alpha client transition:

1. Adopt the reviewed Base implementation first. Verify its exact source revision
   and current-generation Ready conditions, including successful realm-role
   reconciliation, before changing the client's initial-admin membership list.
2. Verify the effective `platform-admin` composite and fresh Forgejo claims,
   admission, and native administrator status. Account for any approved
   `platformAdminRoleExclusions`; a direct Forgejo membership must not mask the
   inherited-role check. Confirm model/MCP groups, baseline grants, and resource
   policy are unchanged.
3. Only after Base is Ready and inheritance is verified, remove the redundant
   `/access/neurwerk-forgejo-admins` entry from the client's declared initial-admin
   list through its reviewed `main` change. Preserve the platform-admin membership
   and all intended separate model/MCP memberships and grants.
4. After that client change reconciles, explicitly remove only the now-redundant
   live Forgejo-admin group membership under separate cleanup authorization.
   Initial-admin provisioning adds memberships but never removes old ones.
   Preserve the group itself, other users, and unrelated memberships. Verify
   inherited access with fresh claims and native login after cleanup.
5. Record the actual revisions, readiness, effective permissions, and cleanup
   results in documentation only after verification. Do not infer completion
   from merged configuration or a successful render.

Excluding `forgejo-admin` reconciles removal of that direct composite grant, not
revocation of every access path. Direct application memberships and native
sessions, tokens, SSH keys, and deploy keys require the separate
[offboarding procedure](../authentication/forgejo.md#mandatory-offboarding)
when access is meant to end.

## Secret Contract

`stack-setup` selects the optional catalog on each run by reading
`forgejo.enabled` and the hostname from `client-values` in `auth-keycloak`.
Disabled or absent selection must not add Forgejo records or namespace roles.
Selection is additive, including on a target already at schema `4`; it is not
secret deletion or credential rotation when later disabled.

| OpenBao source | Delivery or use |
| --- | --- |
| `forgejo/internal:dbPassword` | `forgejo-runtime`; exact copy to `infra-postgres-operations/internal:forgejoPassword`. |
| `forgejo/internal:oidcClientSecret` | Init-only native source setup; exact copy to `auth-keycloak/internal:forgejoClientSecret`. |
| `forgejo/internal:secretKey` | Durable native encryption key. |
| `forgejo/internal:internalToken` | Durable internal API token. |
| `forgejo/internal:oauth2JwtSecret` | Durable native OAuth2/CSRF signing secret. |
| `forgejo/internal:lfsJwtSecret` | Durable LFS signing secret. |
| `forgejo/internal:adminPassword` | Initial creation of `forgejo-recovery` only. |

Tooling must use the version's native secret formats, preserve existing values,
and fail on conflicting copies rather than silently choosing one. The Base
SecretStore name is exactly `forgejo-openbao-secret-store` in `forgejo`; the
tooling refresh catalog uses that same name. Preserve this match
in the pinned release.

The secret stage delivers `forgejo-runtime` in `forgejo`,
`forgejo-postgres-values` in `infra-postgres-operations`, and
`forgejo-oidc-values` in `auth-keycloak`. Shared namespaces use their existing
OpenBao stores. Runtime mounts exclude the init-only OIDC and initial admin
credentials. Never print Secret values or place them in Git, rendered manifests,
scripts, shell arguments, logs, tickets, or chat.

Operations PostgreSQL chart `1.2.1` reads the optional provisioning password
directly from `forgejo-postgres-values:password`. Its `values.yaml` key still
triggers and validates provisioning. Enabling Forgejo leaves the shared database
Pod template and watched Secret unchanged; it does not intentionally restart
PostgreSQL. The job still reapplies the existing role/grant contract and adds
the Forgejo database, so this does not waive the backup requirement.

## Staged Activation

Use separate reviewed changes and readiness checkpoints after adoption is
authorized. The selector and the application Flux suspension are distinct gates.
This sequence is for initial activation, not a shutdown or restore procedure for
an already-running service.

1. Keep the application `forgejo` Kustomization suspended. Verify that no existing
   Forgejo HelmRelease is reconciling independently; suspending a parent alone
   does not suspend an already-created HelmRelease.
2. Resume `forgejo-namespaces`, then `client-forgejo-values`, with the selector
   still false. Verify namespace, non-secret ConfigMaps, trust delivery, and
   network boundaries without starting the application.
3. Resume `forgejo-secret-sync` to stage the SecretStore and ExternalSecrets.
   Missing optional OpenBao fields may leave this stage unready at this point.
   Do not wait for those fields before running the selected catalog, and do not
   add an application-readiness dependency to this stage.
4. Set `forgejo.enabled: true` and the canonical hostname in the shared client
   facts while keeping the application stage suspended. Reconcile the client
   values into both the optional namespace and the existing namespaces,
   especially `auth-keycloak/client-values`, before running tooling. A run while
   that selector is still false will not create the optional catalog.
5. Run the exact approved `stack-setup` version through the existing
   [catalog reconciliation procedure](openbao.md#reconcile-the-catalog), with
   explicit context/client and approved two-custodian recovery access. Shared
   PostgreSQL may now be waiting for `forgejoPassword`; the tool supplies the
   credential copy and converges its consumers. Do not require that blocked
   database to become Ready as a prerequisite for the secret stage or tool run.
6. Verify all three ExternalSecrets and their stores are Ready without reading
   values. Verify the database role/grants and operations PostgreSQL readiness,
   selected Keycloak roles, exact certificate approval, issuers, and DNS/trust
   prerequisites. Stop on copy conflicts or an unresolved dependency.
7. Only then resume the `forgejo` application stage. Its OIDC Job must finish
   before the Forgejo initializer starts. Verify native migration and application
   readiness, then perform the acceptance checks below.

An optional public Gateway is a separate decision. Private mode remains the
default. Do not enable public routing as a workaround for a broken private
tunnel, issuer trust, or secret dependency.

## Acceptance Checks

After explicit rollout authorization, confirm the Kubernetes context and inspect
Flux sources, Kustomizations, both Forgejo-related HelmReleases, warning events,
Certificate and approval conditions, affected Pods, and sanitized logs. Require
current-generation readiness; do not expose sensitive request content.

- Verify exact image digest, successful native initialization, and continued
  health of every consumer of the shared operations database.
- Confirm exactly one `forgejo-tls` Certificate and the selected issuer. Verify
  the consumer loaded the certificate. In public mode also require Gateway
  `Programmed=True` and `ResolvedRefs=True`; private mode requires no Gateway.
- Test canonical HTTPS through the real local `443` tunnel, browser trust, and
  Pod-side DNS separately. Verify strict Keycloak discovery and issuer trust.
- Test login rejection without `forgejo-user`, normal user admission, and native
  administrator mapping. Verify the claim contains only the approved Forgejo
  roles. With Forgejo enabled and no exclusion, verify platform-admin membership
  alone supplies both Forgejo roles and native administrator admission. With
  `forgejo-admin` excluded, verify that inherited grant is absent using a test
  identity without another Forgejo grant; do not mistake existing native access
  for proof of current Keycloak authorization.
- Test actual Git clone, fetch, and push over native HTTPS and approved private
  SSH, plus LFS upload/download and repository permission denial. Confirm no
  public SSH path exists. Never put tokens in command URLs or shell history.
- Test restart persistence of repositories, LFS, account state, and SSH host
  identity. Verify ordinary restarts do not regenerate keys or reset passwords.
- Test approved certificate/credential change handling and issuer-CA reload if
  configured. Keep key rotation distinct from initial provisioning; establish
  recovery consequences before changing encryption or signing keys.
- Test Keycloak outage behavior and the manual offboarding procedure, including
  native sessions, tokens, personal SSH keys, and repository deploy keys.
- Test emergency login closure and a complete coordinated restore in an
  authorized replacement environment before claiming recoverability.

Record which transport modes and operations were actually tested. Success in
private mode does not establish public-mode acceptance, or vice versa.

## Emergency Login

Emergency login requires explicit authorization, a named operator, an external
access record, and private-only access. It is not a normal sign-in fallback.

1. Confirm private mode and an approved canonical HTTPS tunnel. If public mode
   was in use, remove public exposure through the reviewed release configuration
   and verify the private path before opening native password login.
2. Temporarily set `forgejo.recoveryLoginEnabled: true` through the normal values
    and reconciliation process. This permits native web/password Basic
    authentication, not local registration; keep the exposure window short.
    Recovery initialization requires an existing enabled Keycloak source and an
    existing active recovery administrator, and skips remote source updates.
    It cannot initialize a new installation or create a recovery account.
    Forgejo still attempts provider discovery during web startup, so an issuer
    outage may delay startup until that request fails.
3. Sign in as `forgejo-recovery` using its approved custodied password. The
   OpenBao `adminPassword` is initial-only. Updating it or restarting the Pod
   does not reset an existing native account.
4. If the password is unavailable or a reset is required, stop for a separately
   approved native password-reset operation and custody update. Do not extract
   or print secrets, create cleartext reset scripts, put passwords in commands,
   or access private keys through `sudo`.
5. Finish the authorized repair, restore `recoveryLoginEnabled: false`, revoke
   emergency sessions and tokens, and verify native password login is closed.
   Record the purpose and result without credentials or recovery output.

Follow [Recovery Custody](recovery-custody.md) for any OpenBao recovery-root
operation. Its encrypted-media procedure protects OpenBao recovery material;
it does not itself reset or restore a Forgejo account.

## Backup And Failure Recovery

Preserve an application-consistent recovery set: the complete shared operations
database instance, `forgejo-data` including SSH host identity, durable OpenBao
records, and matching non-secret configuration. Store backups independently of
the production storage failure domain and test restoration with every affected
consumer. See [Shared PostgreSQL](../architecture/postgresql.md#persistence-and-recovery).

Disabling or uninstalling serving resources does not undo database migrations.
Retained storage is not a backup. Prefer a tested forward-fix or an authorized
coordinated replacement restore; do not promise a simple database downgrade,
Forgejo-only restore into the shared instance, or Helm rollback. Never delete
namespaces, volumes, OpenBao data, or recovery material as a troubleshooting step.
