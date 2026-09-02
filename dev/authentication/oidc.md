# OIDC Clients

OIDC clients connect applications and services to the client Keycloak realm.
Each integration has a chart under `base/charts/keycloak/oidc/` and a release
contract under `base/releases/keycloak/`.

## Configuration Sources

OIDC values are merged in this order, from lowest to highest priority:

```text
chart values.yaml
base/releases/shared/
base/releases/keycloak/app-defaults.yaml
OpenBao-backed Secret
client_*/config/client.yaml
client_*/apps/keycloak/values.yaml
```

Client IDs, hostnames, redirect URIs, origins, roles, and feature choices are
non-secret. Clients that use an OIDC secret receive it through an OpenBao-backed
Kubernetes Secret. Studio is a public client. AgentGateway validates JWTs from
Keycloak's JWKS endpoint and does not consume a client secret.

## Registration

Each OIDC chart runs `upsert-oidc-client` as a Helm post-install and post-upgrade
Job. The tool:

- creates a missing client or updates its settings;
- replaces redirect URIs and web origins with the configured lists;
- verifies the configured client secret when one is supplied;
- creates missing client roles, audience mappers, and service-account grants.

Roles, audience mappers, and service-account grants are add-only. Removing them
from values does not remove them from Keycloak. Clean up obsolete entries as an
explicit authorization change.

The tool accepts singular redirect URI and web origin variables or JSON arrays.
Arrays take precedence and must contain unique, non-empty, absolute HTTPS URLs.
A service-only client may leave the singular values blank.

## LibreChat Callbacks

LibreChat and its Admin Panel share one confidential OIDC client. Register the
Admin Panel callback on the main API and its hostname as an additional web
origin:

```text
https://<main-librechat-host>/api/admin/oauth/openid/callback
https://<admin-panel-host>
```

When `mcp.enabled` is `true`, the chart adds one callback for each server in the
client-owned `mcp.servers` list:

```text
https://<main-librechat-host>/api/mcp/<server>/oauth/callback
```

MCP server names must be unique, lowercase DNS subdomains with 1 to 48
characters. LibreChat configuration and OIDC registration use the same server
list.

## Token Handling

Consumers implement token checks separately:

- AgentGateway, the API-key bridge, and Dify verify token signatures, issuers,
  audiences, expiry, and subjects before authorization. Their additional checks
  include the claims each component uses, such as `iat`, `azp`, email, and roles.
- Studio delegates verification to its Keycloak middleware, then requires a
  subject, typed realm roles, and `studio-user`.
- LibreChat currently reads required and administrator roles from decoded
  access-token claims after the OIDC login flow.

Do not copy decode-only role checks. New authorization code must use claims from
a cryptographically verified token and fail closed if it cannot verify the
issuer or signing keys.

## Add or Change a Client

1. Update the correct platform or client-owned values.
2. Add or update the product chart under `charts/keycloak/oidc/<product>/`.
3. Add or update its release under `releases/keycloak/` and declare required
   HelmRelease dependencies.
4. Keep client secrets in OpenBao, never in values files.
5. Add authentication and role tests in the consuming service.
6. Use exact redirect URIs and web origins. Avoid broad wildcards.
7. Plan explicit cleanup when removing roles, audience mappers, or
   service-account grants.
