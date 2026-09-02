# API Keys

The Keycloak API-key bridge authenticates non-browser AgentGateway callers.
Keycloak remains the source of principal state and permissions.

## Deployment Status

> **Warning:** The platform chart currently pins bridge image `0.1.0`, while the
> chart and AgentGateway policy require the versioned contract implemented by
> the current `0.5.3` service source. Do not deploy this release until the image
> pin is corrected and the rendered platform is validated.

## User Keys

Management endpoints require a valid Keycloak bearer token. Users manage their
own keys. The `api-key-admin` realm role allows management for another user.

Creating a key requires:

- a name of 1 to 64 characters that starts with a letter or number and contains
  only letters, numbers, `.`, `_`, or `-`;
- 1 to 128 unique permissions;
- an expiry of 1 to 365 days;
- permissions that are a subset of the target user's AgentGateway roles.

The key value is returned only at creation. The bridge stores its SHA-256 digest
and metadata in SQLite. The default limit is 20 stored keys per user.

Expired keys cannot authenticate, but remain listed and count toward the limit
until revoked. Revocation deletes the database record. Keys cannot be edited,
renewed, or viewed again; create a replacement and revoke the old key.

## Managed Service Keys

Managed keys are file-backed service-account credentials. They do not use the
user-key database, expiry, quota, or management endpoints.

Each managed-key slot contains:

- a non-secret version-2 JSON grant in a ConfigMap;
- a lowercase SHA-256 verifier in an OpenBao-backed Secret.

The grant identifies the key, service-account client, and immutable permissions.
The bridge reloads both slots for every request. Primary and secondary keys can
overlap during rotation. An empty secondary verifier disables that slot.

All configured slots must be readable and valid. An incomplete or malformed
slot makes `/validate` return `503`, including for user keys. Readiness does not
validate managed-key files.

The Dify managed grant and Keycloak service account use
`authKeycloak.difyAgentgatewayClientRoles`. This list must:

- include `llm:invoke`;
- contain no duplicates;
- be a subset of `authKeycloak.agentgatewayClientRoles`;
- include `model:<model-id>:invoke` for every configured Dify model.

## Validation

AgentGateway sends an API key to `GET` or `POST /validate` through `x-api-key`
or `Authorization: Bearer <key>`. If both headers are present, `x-api-key` takes
precedence.

```text
API key
-> managed verifier or user-key digest match
-> enabled Keycloak principal and AgentGateway roles
-> intersection with the key's immutable grant
-> version-1 authorization decision
-> AgentGateway permission checks
```

Entitlement lookups are cached for 30 seconds by default. A valid key with no
current permissions returns an empty list, which AgentGateway denies.

The bridge returns trusted credential, principal, and permission metadata.
AgentGateway removes both credential headers after route selection and before
forwarding the request upstream.

## Permissions

Valid permissions are:

```text
llm:invoke
model:<resource-id>:invoke
mcp:<resource-id>:invoke
```

Model requests require `llm:invoke` and the route's concrete model permission.
MCP requests require `llm:invoke` and the route's concrete MCP permission.

## Deployment Contract

The HelmRelease, values ConfigMaps, managed-grant ConfigMap, OpenBao-backed
Secret, and SQLite PVC belong in `auth-keycloak-api-key-bridge`. Flux cannot
read Helm values from another namespace.

Ownership is split as follows:

- the bridge chart renders the non-secret managed grants;
- the OpenBao secret-sync package creates the ExternalSecret for the Keycloak
  client secret and managed-key verifier hashes;
- the consuming service receives the raw managed key through its own
  namespace-local Secret.

Raw keys and verifier hashes must never enter Git, ConfigMaps, or logs. Grants
contain no secret material and must not be stored in OpenBao.

Readiness checks SQLite, structurally complete RSA/RS256 Keycloak signing keys,
client credentials, and authenticated access to the AgentGateway client. Use
key IDs or short hash prefixes for diagnosis, never complete keys.
