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
- Keycloak accesses Active Directory through read-only LDAPS with `NO_CACHE`.
- Only direct membership in approved `neurwerk-` groups is synchronized under
  Keycloak's `/access` group.
- Git-reviewed client configuration maps those groups to Keycloak roles.
- Authentication fails closed when Keycloak cannot verify the current Active
  Directory state.
- A local Keycloak break-glass administrator remains available for recovery.

Application roles and AgentGateway permissions are separate. Membership in a
broad LLM access group does not grant access to Studio, LibreChat, Dify, or
Keycloak administration.

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

Studio permits callers to read their own usage. Reading another principal's
usage requires the existing `langfuse-admin` realm role and does not grant
access to that user's Keycloak profile. The Studio API enforces both cases and
uses the authorized route's opaque target user ID to filter records. AgentGateway
sets each stored record's attribution only from verified identity; the browser
does not call AgentGateway or set that attribution value.

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

The platform chart derives roles from the client's selected OpenRouter models.
The client policy decides whether those roles are added to every declared
AgentGateway access group. Clients continue to declare broad `llm:invoke`, MCP
roles, and roles for their direct, local, or custom model destinations. Dify and
managed API-key grants remain explicit subsets and are validated against the
effective role catalog.

API keys contain an immutable permission grant. During validation, the API-key
bridge intersects that grant with the enabled principal's current AgentGateway
roles. Revoked or expired keys and disabled principals are rejected.

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
- [OIDC clients](oidc.md)
- [API keys](api-keys.md)
- [Routing and AgentGateway](../architecture/routing.md)
- [Secret architecture](../architecture/secrets.md)
