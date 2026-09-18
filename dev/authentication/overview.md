# Authentication Overview

Keycloak issues tokens for users and service clients. Applications use verified
Keycloak claims for authentication and role-based authorization.

AgentGateway accepts two credential types:

```text
OIDC caller    -> Keycloak access token -> local JWT validation
API client     -> API key               -> API-key bridge validation
```

Both paths produce a verified principal and AgentGateway permissions.
Authentication identifies the caller. Authorization decides which application,
operation, model, or MCP server that caller may use.

## Identity Ownership

Keycloak owns local identities, realm roles, OIDC clients, and group-to-role
mappings.

When Microsoft Active Directory federation is enabled:

- Active Directory owns the user's password, account state, email address, and
  direct group membership.
- Keycloak uses read-only federation with `NO_CACHE` and verified LDAPS by
  default. Plaintext LDAP requires explicit `allowInsecureLdap: true` and the
  staged runtime gate below.
- Exactly one group list selects direct AD memberships: legacy `groupNames`
  uses same-name `neurwerk-` groups below `/access`; staged `groupMappings`
  creates source-named children under existing canonical groups. Children
  inherit parent roles, but full-path group claims retain the actual child
  paths. Nested AD membership does not grant access.
- Built-in `READ_ONLY` mappers resolve membership without plugins or local
  membership copies.
- Platform defaults define the canonical groups and application role mappings;
  clients inherit them and own memberships, directory settings, and explicit
  model and MCP grants.
- Authentication fails closed when Keycloak cannot verify the current Active
  Directory state.
- A local Keycloak break-glass administrator remains available for recovery.

Mapping and plaintext support is implemented in published, verified Tooling
`0.7.0` and Keycloak charts `1.1.0`, but Base pin adoption is pending;
existing chart pins remain unchanged. Mapping reconciliation and transitions disable
the provider until validation succeeds; partial failures leave it disabled for
retry. Existing tokens and application sessions are not immediately revoked.
See [Active Directory Federation](keycloak.md#active-directory-federation) for
the exact image gate, operator sequence and retry rules.

Application roles and AgentGateway permissions are separate. Membership in a
broad LLM access group does not grant access to Studio, LibreChat, Dify, or
Keycloak administration. Conversely, application or administrator membership
does not implicitly grant model or MCP access. MCP access never automatically
grants model access. The canonical set contains 13 platform-defined groups; see
[Roles And Access Groups](keycloak.md#roles-and-access-groups).

Base unifies existing supported application roles under `platform-admin` by
default, with the narrow subtract-only client setting
`authKeycloak.platformAdminRoleExclusions: []`. This is not new root, Kubernetes,
or OpenBao administrator authority, nor unrestricted rights in every product;
roles such as `studio-user` retain their existing scope. The initial administrator
defaults to `/access/neurwerk-platform-admins` only. Model/MCP groups and their
explicit baseline grants remain separate and unchanged.

The staged optional Forgejo catalog adds two groups only when selected. Under
the implemented policy, enabled Forgejo supplies inherited `forgejo-admin` and
`forgejo-user` access to platform administrators unless `forgejo-admin` is
excluded. Implementation does not establish live adoption or membership cleanup.
See [Keycloak](keycloak.md#uniform-application-administration) for the exact
exclusion contract and [Forgejo authentication](forgejo.md) for its native
authentication and offboarding boundary.

## Authorization

### Realm Roles

Realm roles control application admission and focused administrative features.
Examples include:

- `studio-user`: access Studio.
- `librechat-user`: access LibreChat.
- `librechat-admin`: access LibreChat and its SSO-only Admin Panel.
- `pii-admin`: use Studio's PII policy tools.
- `keycloak-admin`: use Keycloak administration features.
- `api-key-admin`: manage API keys for another user.
- `langfuse-admin`: view another principal's usage in Studio. The historical
  role name remains the authorization contract even though usage is sourced
  from AgentGateway rather than Langfuse.

Applications must enforce roles at the API boundary. Hiding a feature in the UI
is not authorization.

Forgejo's staged integration uses native OIDC role admission followed by native
session, API, and repository authorization, not a Keycloak claim check on each
Git or API request. This scoped native boundary does not change the API role
requirements for the other platform applications.

Studio permits callers to read their own usage. Reading another principal's
usage requires the existing `langfuse-admin` realm role and does not grant
access to that user's Keycloak profile. The Studio API enforces both cases and
uses the authorized route's opaque target user ID to filter records. AgentGateway
sets each stored record's attribution only from verified identity; the browser
does not call AgentGateway or set that attribution value.

Studio `0.9.0` admin Users and recent-sign-ins routes require both
`studio-user` and `keycloak-admin`, forwarding the administrator's own token to
Keycloak. Base realm-roles chart `2.0.2` adds `realm-management/view-events` to
the `keycloak-admin` composite. This grants broader upstream event reads, not
only Studio's filtered sign-in summary; see
[Keycloak event access](keycloak.md#studio-event-access). Alpha rollout evidence
does not establish adoption by clients on existing signed platform releases.

### AgentGateway Permissions

AgentGateway uses Keycloak client roles with this permission format:

```text
llm:invoke
model:<model-id>:invoke
mcp:<server-id>:invoke
```

Model requests require both `llm:invoke` and the matching
`model:<model-id>:invoke` permission. MCP requests require `llm:invoke` and the
matching `mcp:<server-id>:invoke` permission.

The platform chart derives role definitions from the client's selected
OpenRouter models; selection alone is not an access grant. The global safe
default and both client policies use `grantToAccessGroups: false`; the template
rejects `true`. Clients explicitly grant model roles only to
`/access/neurwerk-llm-all-users` and MCP roles only to
`/access/neurwerk-mcp-all-users` through
`authKeycloak.agentgatewayAccessGroups`, together with the required `llm:invoke`
permission. Other groups and cross-resource grants are rejected. The
`all` groups cover only explicitly granted resources, not future catalog
additions. Clients also declare roles for direct, local, or custom model
destinations. Dify and managed API-key grants remain explicit subsets and are
validated against the effective role catalog.

API keys contain an immutable permission grant. During validation, the API-key
bridge intersects that grant with the enabled principal's current AgentGateway
roles. Revoked or expired keys and disabled principals are rejected.

The bridge source also returns sorted, unique full Keycloak group paths in
`groups`, in both the validation body and trusted header. Memberships belong to
the key's principal (the service account for managed keys), share the entitlement
cache TTL, and never expand the permission grant; lookup failures fail closed.
AgentGateway keeps groups internal and accepts older bridge responses without
them as `[]`. This addition needs a new bridge image release and adoption;
published bridge `0.6.0` does not return groups.

## Trust Boundaries

- Services validate JWT signatures, issuer, audience or authorized party,
  expiry, subject, and required roles before trusting claims.
- AgentGateway derives identity only from a verified JWT `sub` claim or the
  API-key bridge's trusted authorization response.
- AgentGateway records the verified JWT `sub` or trusted API-key
  `principal_id` as the opaque `agentgateway.user` usage attribute. OIDC and API
  key traffic for the same user therefore aggregate under the same principal.
- AgentGateway removes caller credentials and reserved identity headers before
  forwarding requests to model or MCP backends.
- Backend credentials are managed separately from caller credentials.
- Studio derives browser authorization data from its authenticated
  `/api/session` endpoint. Browser-side token claims are not an authorization
  source.
- Studio authorizes PII policy operations, then calls PII Engine over mTLS. It
  never forwards the user's JWT to PII Engine.
- Confidential client secrets and service credentials are stored in OpenBao and
  materialized as namespace-local Kubernetes Secrets.

## Related Documentation

- [Keycloak](keycloak.md)
- [Forgejo native authentication (staged)](forgejo.md)
- [OIDC clients](oidc.md)
- [API keys](api-keys.md)
- [Routing and AgentGateway](../architecture/routing.md)
- [Secret architecture](../architecture/secrets.md)
