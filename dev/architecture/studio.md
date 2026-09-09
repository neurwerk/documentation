# Studio

Studio admits authenticated callers with `studio-user`. Its default landing
page is the verified user's own info page, `/users/{subject}`. Self-service
profile, API keys, and usage do not require specialized administrator roles.
Login preserves explicit local deep links; invalid or external return targets
fall back to the default landing. Existing feature authorization remains in
force on deep links.

## Daily Model Usage

The user info page uses Recharts 3.10.0 to show daily stacked bars by requested
model, with an instant Tokens/USD switch, model visibility controls, and
selected-range token, reported USD, and call totals. Totals include hidden
models. The view refreshes every 30 seconds and marks failed or delayed refresh
data as stale. It never presents one user's or date range's data as another's.

`GET /api/users/{user_id}/usage/daily` accepts optional inclusive `start` and
`end` dates in `YYYY-MM-DD` format. Without `end`, the range ends today; without
`start`, it covers 30 days ending on `end`. Ranges must be ascending, at most
90 calendar days, and cannot end in the future. Invalid ranges return 422.

The response contains `timezone`, `start_date`, `end_date`, `today`, and `days`.
Each day contains `date` and `models`; each model entry contains nullable
`model`, `requests`, `total_tokens`, and `cost_usd`. Empty days remain present
with an empty model list. Null models are displayed as "Unknown model".

`K8S_STUDIO_USAGE_TIMEZONE` is an API environment setting, defaulting to
`Europe/Berlin`. Local-midnight boundaries are converted to half-open UTC
ranges, respecting 23-hour and 25-hour daylight-saving days. Today is capped
at the captured current time. Consecutive equal-duration historical days use
one gateway query; transition days and partial today are queried separately.
The browser displays calendar labels without applying its own timezone.

The API queries AgentGateway's private `/api/logs/analytics/summary`, grouping
by `requestModel`. Studio enforces self or `langfuse-admin` authorization and
injects the authorized target into the `agentgateway.user` filter. It returns
only validated usage data, never gateway filter options or raw upstream error
content. Invalid or unavailable upstream summaries return 502. The existing
period-totals `/usage` endpoint remains available.

Both chart metrics come from the same response. Costs are gateway-reported
sums, not recalculated model-price estimates; missing prices contribute zero
and partially priced aggregates cannot be identified. The view explicitly
notes that reported costs may omit unpriced requests. Separate input/output
token totals are not available from this analytics contract.

See [Observability](observability.md#studio-usage-analytics) for attribution,
storage, retention, and the separate Langfuse tracing flow, and
[Authentication](../authentication/overview.md#authorization) for role boundaries.
