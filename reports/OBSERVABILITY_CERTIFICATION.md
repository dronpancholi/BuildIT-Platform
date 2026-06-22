# Observability Certification — Phase 1.4

**Verdict:** OBSERVABILITY PARTIAL
**Executed:** 2026-06-01T16:22:54.364974+00:00
**Pillars:** 4/5 PASS

## Pillar Results

### Pillar: Metrics — PASS

- **canonical_endpoint**: /metrics
- **existing_endpoint**: /api/v1/metrics
- **canonical_status**: 200
- **existing_status**: 200
- **size_bytes_canonical**: 95247
- **help_lines_canonical**: 83
- **type_lines_canonical**: 83
- **metric_line_count_canonical**: 801
- **unique_families**: 11
- **sample_families**: 11 items (sample: ['http_request_duration_seconds_bucket', 'http_request_duration_seconds_count', 'http_request_duration_seconds_created'])
- **identicals**: False

### Pillar: Logs — PASS

- **total_lines**: 3206
- **lines_with_trace_id**: 173
- **lines_with_tenant_id**: 270
- **lines_with_service**: 1243
- **lines_with_environment**: 1243
- **level_distribution**: {"INFO": 948, "WARNING": 75, "DEBUG": 217, "ERROR": 10}
- **lines_last_hour**: 0
- **structured_format**: JSON-ish key=value (structlog)

### Pillar: Traces — PASS

- **unique_trace_ids**: 88
- **unique_span_ids**: 88
- **traces_with_multiple_log_lines**: 24
- **max_lines_per_trace**: 7
- **sample_trace_id**: 4a09a148-0e49-4bc3-ab3d-2d4f3c9226d6
- **format**: W3C trace_id (32 hex) + span_id (16 hex) propagated via structlog context

### Pillar: Audit — PASS

- **audit_event_count**: 16
- **event_distribution**: thread.replied|OutreachThread|8
email.inbound_reply|OutreachThread|8
- **update_blocked_by_trigger**: True
- **rls_enabled**: True
- **immutable_trigger**: prevent_audit_modification BEFORE DELETE OR UPDATE
- **tenant_isolation_policy**: audit_log_tenant_isolation USING (tenant_id = current_setting('app.current_tenant')::uuid)

### Pillar: Alerts — PARTIAL

- **alerting_service_exists**: True
- **alert_classes**: []
- **alert_handlers**: ['start', 'stop', 'run_cycle']
- **alert_thresholds**: ['> 0', '> 1000', '> 500', '> 0', '> 50']
- **alert_log_lines**: 0
- **webhook_destinations**: []
- **sse_realtime**: True

## Summary

{
  "pillars_total": 5,
  "pillars_passed": 4,
  "pillar_statuses": {
    "metrics": "PASS",
    "logs": "PASS",
    "traces": "PASS",
    "audit": "PASS",
    "alerts": "PARTIAL"
  },
  "all_pass": false,
  "verdict": "OBSERVABILITY PARTIAL"
}
