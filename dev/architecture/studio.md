# Studio

Studio admits authenticated callers with `studio-user`. Its default landing
page is the verified user's own info page, `/users/{subject}`. Self-service
profile, API keys, and usage do not require specialized administrator roles.
Login preserves explicit local deep links; invalid or external return targets
fall back to the default landing. Existing feature authorization remains in
force on deep links.

## Admin Users And Recent Sign-ins

Studio [v0.9.0](https://github.com/neurwerk/k8s_stack_studio/releases/tag/v0.9.0)
implements this contract, coordinated with Base's realm-roles chart `2.0.2`.
Studio [PR #22](https://github.com/neurwerk/k8s_stack_studio/pull/22) and Base
[PR #107](https://github.com/neurwerk/k8s_stack_base/pull/107) are merged. Both
published image digests and their `linux/amd64` source revision were verified.
This does not change existing signed platform releases or stable adoption.

`GET /api/admin/users` retains its array response and optional `search`, with
`first` as a nonnegative offset (default `0`) and `max` from `1` to `25`
(default `25`). The Users page debounces search and cancels obsolete requests
when the search or page changes.

Status separates the account's `enabled` state (Enabled, Disabled, or unknown)
from email verification (verified, unverified, unknown, or no email). The
self-profile reports `enabled: null`: an issued JWT is not evidence of the
account's current enabled state, even when the caller is an administrator.

`GET /api/admin/recent-signins` accepts repeated `user_ids` query parameters
for 1-25 IDs. It returns UTC ISO timestamps `window_start` and `window_end`
exactly seven days apart, plus a `users` map keyed by requested user ID. Each
entry contains `status` and nullable `timestamp`:

| Status | Meaning | Timestamp |
| --- | --- | --- |
| `recorded` | Latest recorded successful `LOGIN` in the rolling seven-day window, across all realm clients | Normalized UTC ISO timestamp |
| `no_record` | No matching event recorded in that window | `null` |
| `unavailable` | Event access, lookup, or response validation failed | `null` |

Both routes require `studio-user` and `keycloak-admin` and delegate upstream
requests using the administrator's own bearer token, not service credentials.
Event reads additionally require Keycloak `realm-management/view-events`.
Studio queries by user and successful `LOGIN`, newest first, at most one event,
with epoch-millisecond window bounds and no client filter. Each batch permits
at most four concurrent event requests with a five-second HTTP timeout each.
Only summary statuses and normalized timestamps reach the browser, never raw
events or their details. Activity failures do not hide the Users list.

The UI shows a relative sign-in time with an exact UTC timestamp, "No record in
last 7 days", or "Unavailable". No record never means the user has never signed
in: event collection, custom-disabled `LOGIN` capture, and retention can limit
history. See [Keycloak event access](../authentication/keycloak.md#studio-event-access)
for the broader upstream permission and platform-owned provisioning.

### Alpha Verification

On 2026-09-13, the authorized alpha rollout reconciled Base revision
`beb2b790542127ca3f63a92bde5443833d9ffb3d` and the client's verified image
overrides. Studio API and Web ran the exact `0.9.0` image digests; the public
version endpoint returned `0.9.0`, the Users route returned 200, and both admin
APIs returned 401 without authentication. The realm-roles Job completed and its
log confirmed the `view-events` addition. All six Flux Kustomizations and all
49 HelmReleases were ready. Brief startup readiness warnings recovered with
zero Studio restarts; Studio and Keycloak logs showed no errors. The existing
authentication PostgreSQL Pod remained ready and its claim remained bound.

Isolated browser checks with synthetic data passed at desktop and mobile sizes,
including statuses, timestamps, search, pagination, and unavailable activity.
Live delegated administrator requests, saved-event configuration, and actual
user-history contents were not inspected; an existing administrator session is
needed for that final functional check. No bootstrap credentials were reused.

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

`K8S_STUDIO_USAGE_TIMEZONE` is an API environment setting with application default
`Europe/Berlin`. Base's existing chart default `frontendStudio.api.usageTimezone`
remains `UTC` and overrides the application default unless explicitly configured.
Local-midnight boundaries are converted to half-open UTC
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
