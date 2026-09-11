# AgentGateway Streaming Workaround

Status: not deployed. The gateway policy must not be adopted
until compatible bridge/extProc images are published and integration gates pass.

## Why It Is Needed

AgentGateway 1.5.0 treats authentication expressions using `response.body` as a
reason to buffer the application response too. This delays MCP and LLM streams,
even when a valid JWT skips the API-key bridge call. Increasing timeouts does
not fix it.

## The Workaround

The API-key bridge adds `x-agentgateway-auth-context` to successful validation
responses. It contains compact ASCII JSON with `contract_version`, `principal_id`,
and `permissions`. The existing JSON response body stays unchanged.

The gateway reads this trusted auth-response header, not caller headers or the
auth body. Missing or invalid metadata denies access. The header stays internal
and is stripped from application requests and responses. Do not add a
`response.body` fallback: it would restore the buffering dependency.

The header value is limited to 64 KiB. Oversized decisions return a generic 503;
permissions are never truncated. This budget was checked over the current
HTTP/1.1 auth connection; transport changes need revalidation.

The accompanying extProc correction accepts empty MCP DELETE 202 and 204
responses. HTTP errors keep their status with a fixed safe body, so optional GET
405, expired-session 404, and authentication errors no longer become false
processor 503s. Upstream OAuth challenges and diagnostics are not forwarded.
Correlated JSON-RPC and tool errors remain operation errors. This does not add
retries, migrate MCP versions, or change PII policy.

## Validation And Removal

`base/tests/live/agentgateway/README.md` documents the verified binary installation
and opt-in `make streaming-acceptance` check. Normal `make check` does not need
the binary. The local regression proves streaming before upstream EOF; it does
not certify real clients, JWT recovery, PII, or production deployment.

Adoption remains blocked on the separate session-isolation and late-stream-error
integration gates. Publish and adopt the bridge before the header-only gateway
policy. A source merge alone does not update running images.

Remove the workaround only after a reviewed AgentGateway release fixes the
dependency scope and passes the same streaming regression without the header.
Track upstream [#875](https://github.com/agentgateway/agentgateway/issues/875) and
[#876](https://github.com/agentgateway/agentgateway/issues/876).
The related [#2581](https://github.com/agentgateway/agentgateway/issues/2581) was
closed by a double-polling fix, not a fix for this buffering dependency.
