# AgentGateway Streaming And MCP Fixes

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
retries or migrate MCP versions.

## Stateless MCP

All gateway MCP backends use `Stateless`, without a configuration switch.
`agentgateway_extproc` rejects any incoming `Mcp-Session-Id` header before
forwarding or PII processing, including empty or duplicate headers and when PII
analysis is disabled. After HTTP parsing, authorization, and trusted metadata
validation, the response is HTTP 404 with this fixed body:

```json
{"error":"Stateful MCP sessions are currently unsupported pending an AgentGateway session-ownership fix. Reinitialize without Mcp-Session-Id."}
```

This tells a client with an old session to initialize again without the header.
Each accepted MCP call gets independent PII state. Analysis and reversal remain,
but an earlier blocked call does not automatically block the next one. Model
conversation IDs, login sessions, and conversation trace grouping are unchanged.

Brave and Context7 are the current targets. Future MCP integrations must support
sessionless calls; persistent gateway sessions and standalone event subscriptions
are not supported by this contract.

## Validation And Removal

`base/tests/live/agentgateway/README.md` documents the verified binary installation
and opt-in `make streaming-acceptance` check. Normal `make check` does not need
the binary. The local regression proves streaming before upstream EOF and native
stateless MCP initialization, tool calls, and GET/DELETE 405 responses. A separate
disposable check with the actual extProc service passed 68 HTTP checks, including
session-header rejection, fresh initialization, and fail-closed processor outage.
These checks do not certify real clients, JWT recovery, PII Engine, or deployment.

Publish and verify compatible bridge/extProc images before updating their pins.
Adopt the bridge before the header-only gateway policy. Coordinate the stateless
gateway and extProc activation: the new processor must not serve a stateful
gateway. Validate the clients on alpha before stable adoption. A source merge
alone does not update running images.

[Issue #108](https://github.com/neurwerk/k8s_stack_base/issues/108) tracks a separate
limitation: a late extProc failure can look like a normally completed response.
This is accepted for interactive chat and does not alone block these fixes.
Reassess before unattended actions. The reproduced rejected message was withheld;
no PII leak was demonstrated.

Remove the workaround only after a reviewed AgentGateway release fixes the
dependency scope and passes the same streaming regression without the header.
Track upstream [#875](https://github.com/agentgateway/agentgateway/issues/875) and
[#876](https://github.com/agentgateway/agentgateway/issues/876).
The related [#2581](https://github.com/agentgateway/agentgateway/issues/2581) was
closed by a double-polling fix, not a fix for this buffering dependency.
