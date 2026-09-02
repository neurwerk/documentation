# Observability

The platform handles metrics, logs, and model traces as separate data flows.
Observability services are internal by default. Langfuse can be exposed through
its Gateway when external access is enabled.

## Metrics And Alerts

`kube-prometheus-stack` provides Prometheus, Alertmanager, Grafana,
kube-state-metrics, and Prometheus Node Exporter. Product charts add
`ServiceMonitor`, `PodMonitor`, and `PrometheusRule` resources where monitoring
is implemented.

Prometheus and Alertmanager store data on Rook/Ceph block storage. Grafana reads
its administrator credentials from a namespace-local Secret populated from
OpenBao.

### Email Alerts

The platform release enables email alerts by default. A client provides the
non-secret SMTP host, sender, and recipient. OpenBao provides the SMTP username
and password through External Secrets. A client without a working SMTP
destination must disable email explicitly.

Alertmanager sends email only for critical alerts and sends a notification when
they resolve. Warning and informational alerts remain visible in Alertmanager
and Grafana. The always-firing `Watchdog` alert uses the null receiver.

## Logs

```text
container logs
-> Fluent Bit DaemonSet
-> OpenSearch over verified TLS
-> fluent-bit-* indices
-> Ceph object-storage snapshots
```

Fluent Bit tails container logs on each eligible node, adds Kubernetes metadata,
and writes to OpenSearch with a dedicated ingest identity. Verify the
DaemonSet's desired and ready counts when checking log collection.

OpenSearch is internal, single-node, persistent, and protected by TLS. After the
configured hot period, it snapshots `fluent-bit-*` indices to Ceph object
storage and removes them from hot storage.

Studio queries logs with a separate read-only OpenSearch identity. Browsers do
not connect to OpenSearch directly.

The OpenSearch volume and snapshot repository use the same Rook/Ceph failure
domain. Snapshots are retention storage, not an independent backup.

## Model And MCP Traces

```text
AgentGateway data plane
-> OpenTelemetry collector in monitor-langfuse
-> Langfuse
-> ClickHouse, Valkey, Ceph object storage, and shared PostgreSQL
```

Langfuse stores traces for request-level investigation. Studio also uses
Langfuse to calculate per-user token and cost totals. Prometheus and Grafana
remain the source for aggregate latency and reliability views.

### Trace Content

Every model and MCP destination must set `contentTracingEnabled` explicitly.
Omission defaults to `true` and may retain:

- model prompts and textual completions;
- MCP tool arguments and results.

Treat trace storage as sensitive application data. Do not add credentials,
authorization headers, or unnecessary personal data to telemetry.

When `contentTracingEnabled` is `false`, AgentGateway omits those content
attributes. The trace can still contain non-content data such as the verified
principal, session identifiers, destination, operation, status, timing, token
usage, and cost when available.

`contentTracingEnabled` and `piiEnabled` are independent. PII processing does
not guarantee that content tracing is disabled.

### User Attribution

Langfuse uses an opaque, verified Keycloak principal ID:

- OIDC requests use the verified JWT `sub` claim.
- API-key requests use the API-key bridge's trusted `principal_id`.

Caller-supplied identity headers are not trusted. User API keys retain their
owner's Keycloak subject. Managed service credentials identify the related
Keycloak service account.

### Trace Exclusions

The private RAG embedding listener disables AgentGateway access logs, tracing,
and external processing because embedding requests may contain complete
documents. This does not guarantee that the embedding backend produces no
telemetry. Code Interpreter also bypasses AgentGateway tracing.

## LLM User Experience

AgentGateway metrics include request duration, time to first token, time per
output token, token usage, status, and failure reason. PII metrics include
extProc-to-engine request latency, engine analysis duration, and queue wait.

The platform adds two low-cardinality dimensions:

- `request_size`, a bucket for serialized request size;
- `llm_streaming`, which is `true`, `false`, or `unknown`.

Compare latency only within the same model, streaming mode, and request-size
bucket. Review observation counts and histogram overflow with percentiles,
especially at low traffic. Use time per output token for decode speed; do not
divide request latency by input tokens.

The `LLM User Experience` Grafana dashboard is stored as JSON in the
AgentGateway chart and provisioned through a labeled ConfigMap. Update the chart
JSON, not the Grafana UI.

## Telemetry Safety

- Do not use request, conversation, session, user, token, or content identifiers
  as Prometheus labels. Correlate individual requests in traces or logs.
- PII metrics may use bounded entity types, actions, callers, decisions, and
  failure categories. They must not include entity values, spans, scores, or
  prompt-derived identifiers.
- Normal PII Engine logs include bounded failure metadata and evaluation result
  metadata such as decisions, entity types, and counts. They do not include
  request payloads or entity text.
- PII Engine `DEBUG` logs can include exception messages and tracebacks with
  sensitive request data. Enable `DEBUG` only for a bounded investigation, then
  restore `INFO`. Fluent Bit retains these logs under the normal log policy.

## Operational Boundaries

- Metrics, logs, and traces depend on the cluster's Rook/Ceph failure domain.
- Langfuse's `postgres_langfuse` database shares the operations PostgreSQL
  process, PVC, and recovery point. See
  [Shared PostgreSQL](postgresql.md#persistence-and-recovery).
- Critical-alert delivery depends on Alertmanager, DNS, the SMTP provider, and
  the OpenBao-backed SMTP credential.
- A healthy collector, logger, or application Pod does not prove end-to-end
  telemetry delivery.
- The platform supplies retention and resource defaults. Clients can override
  them through their configuration and product values.
- Not every product has a complete monitor and alert contract. Pod readiness is
  not proof of end-to-end feature health.

## Inspection Commands

Confirm the Kubernetes context before querying a cluster:

```bash
kubectl config current-context
kubectl get servicemonitors,podmonitors,prometheusrules -A
kubectl get pods -n monitor-kube-prometheus-stack
kubectl get daemonset -n monitor-fluent-bit
kubectl get pods -n monitor-opensearch
kubectl get pods -n monitor-langfuse
```

Use port-forwarding and approved credentials for internal operational UIs.
