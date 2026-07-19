# Alert rules for tcgscan-api.
#
# Contact point: reference the existing Grafana Cloud "telegram" contact point by
# name only. Do NOT manage grafana_contact_point here — Terraform must never
# create/replace/destroy that resource (bot token lives only in Grafana).

locals {
  prom_uid = "grafanacloud-prom"
  loki_uid = "grafanacloud-logs"
  api_job  = "tcgscan/tcgscan-api"
  api_svc  = "tcgscan/tcgscan-api"

  alert_dashboard_uid = "tcgscan-api-overview"
}

resource "grafana_rule_group" "api" {
  provider = grafana.cloud

  name             = "tcgscan-api"
  folder_uid       = grafana_folder.tcgscan.uid
  interval_seconds = 60

  # ---------------------------------------------------------------------------
  # Existing Cloud rule (imported) — outbound httpx slower than 7.5s
  # ---------------------------------------------------------------------------
  rule {
    uid       = "bfsj60809bsw0c"
    name      = "API outbound HTTP request slower than 7.5s"
    condition = "B"
    for       = "0s"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "warning"
    }

    annotations = {
      summary      = "At least one outbound httpx request from tcgscan-api took longer than 7.5s in the last 10 minutes."
      description  = "Value is the number of outbound HTTP client requests slower than 7.5s (nearest histogram bucket above the 7s target) over the last 10m. Check the 'HTTP client (outbound httpx)' row on the TCG Scan — API Overview dashboard and Tempo httpx spans to identify the slow host."
      dashboardUid = local.alert_dashboard_uid
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.prom_uid

      relative_time_range {
        from = 600
        to   = 0
      }

      model = jsonencode({
        refId         = "A"
        expr          = "sum(increase(http_client_duration_milliseconds_count{job=\"${local.api_job}\"}[10m])) - sum(increase(http_client_duration_milliseconds_bucket{job=\"${local.api_job}\", le=\"7500\"}[10m]))"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "gt"
            params = [0]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }

  # ---------------------------------------------------------------------------
  # ERROR-level Loki lines (sre.md Phase 4) — pages when alertable failures land
  # ---------------------------------------------------------------------------
  rule {
    uid       = "tcgscan-api-error-logs"
    name      = "API ERROR logs"
    condition = "B"
    for       = "2m"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "critical"
    }

    annotations = {
      summary      = "tcgscan-api emitted ERROR-level logs in the last 5 minutes."
      description  = "Query: {service_name=\"${local.api_svc}\", level=\"ERROR\"}. Every ERROR is either a real incident or a severity to demote (see sre.md). Open the API Overview logs row and jump to Tempo via trace_id."
      dashboardUid = local.alert_dashboard_uid
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.loki_uid

      relative_time_range {
        from = 600
        to   = 0
      }

      model = jsonencode({
        refId         = "A"
        expr          = "sum(count_over_time({service_name=\"${local.api_svc}\", level=\"ERROR\"}[5m]))"
        queryType     = "instant"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "gt"
            params = [0]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }

  # ---------------------------------------------------------------------------
  # API availability — 5xx ratio above draft SLO (99.5%)
  # ---------------------------------------------------------------------------
  rule {
    uid       = "tcgscan-api-5xx-ratio"
    name      = "API 5xx ratio high"
    condition = "B"
    for       = "10m"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "critical"
      slo      = "availability"
    }

    annotations = {
      summary      = "tcgscan-api 5xx ratio is above 0.5% for 10 minutes."
      description  = "Draft SLO: availability ≥ 99.5%. Check Request rate by status code on API Overview and recent ERROR logs."
      dashboardUid = local.alert_dashboard_uid
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.prom_uid

      relative_time_range {
        from = 600
        to   = 0
      }

      model = jsonencode({
        refId         = "A"
        expr          = "sum(rate(http_server_duration_milliseconds_count{job=\"${local.api_job}\", http_status_code=~\"5..\"}[10m])) / clamp_min(sum(rate(http_server_duration_milliseconds_count{job=\"${local.api_job}\"}[10m])), 1e-9)"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "gt"
            params = [0.005]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }

  # ---------------------------------------------------------------------------
  # Scan success rate — draft SLO ≥ 99% ok+cache_hit
  # ---------------------------------------------------------------------------
  rule {
    uid       = "tcgscan-scan-success-rate"
    name      = "Scan success rate low"
    condition = "B"
    for       = "15m"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "warning"
      slo      = "scan_success"
    }

    annotations = {
      summary      = "Scan success rate (ok+cache_hit) is below 99% for 15 minutes."
      description  = "Draft SLO from sre.md. Check Scan Funnel + Scan rate by outcome on API Overview. NoData stays OK until scan metrics exist."
      dashboardUid = "tcgscan-scan-funnel"
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.prom_uid

      relative_time_range {
        from = 900
        to   = 0
      }

      # Require nonzero scan traffic so idle periods stay NoData (OK), not 0% success.
      model = jsonencode({
        refId         = "A"
        expr          = "(sum(rate(tcgscan_scan_count_total{job=\"${local.api_job}\", tcgscan_scan_outcome=~\"ok|cache_hit\"}[15m])) / sum(rate(tcgscan_scan_count_total{job=\"${local.api_job}\"}[15m]))) and (sum(rate(tcgscan_scan_count_total{job=\"${local.api_job}\"}[15m])) > 0)"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "lt"
            params = [0.99]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }

  # ---------------------------------------------------------------------------
  # Scan p95 latency — draft SLO < 2.5s
  # ---------------------------------------------------------------------------
  rule {
    uid       = "tcgscan-scan-p95-latency"
    name      = "Scan p95 latency high"
    condition = "B"
    for       = "15m"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "warning"
      slo      = "scan_latency"
    }

    annotations = {
      summary      = "Scan p95 latency is above 2.5s for 15 minutes."
      description  = "Draft SLO from Phase-1 KPI / sre.md. Check Scan duration + stage p95 panels. NoData stays OK until scan metrics exist."
      dashboardUid = "tcgscan-scan-funnel"
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.prom_uid

      relative_time_range {
        from = 900
        to   = 0
      }

      model = jsonencode({
        refId         = "A"
        expr          = "histogram_quantile(0.95, sum by (le) (rate(tcgscan_scan_duration_seconds_bucket{job=\"${local.api_job}\"}[15m])))"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "gt"
            params = [2.5]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }

  # ---------------------------------------------------------------------------
  # ML fallback ratio — draft SLO < 1% when Modal URLs configured
  # ---------------------------------------------------------------------------
  rule {
    uid       = "tcgscan-ml-fallback-ratio"
    name      = "ML fallback ratio high"
    condition = "B"
    for       = "15m"

    no_data_state  = "OK"
    exec_err_state = "OK"

    labels = {
      service  = "tcgscan-api"
      severity = "warning"
      slo      = "ml_fallback"
    }

    annotations = {
      summary      = "ML fallback ratio is above 1% for 15 minutes."
      description  = "Share of tcgscan.ml.requests with mode=fallback. Check Modal endpoint health and the ML panels on API Overview / Scan Funnel."
      dashboardUid = "tcgscan-scan-funnel"
    }

    notification_settings {
      contact_point = var.alert_contact_point
    }

    data {
      ref_id         = "A"
      datasource_uid = local.prom_uid

      relative_time_range {
        from = 900
        to   = 0
      }

      model = jsonencode({
        refId         = "A"
        expr          = "sum(rate(tcgscan_ml_requests_total{job=\"${local.api_job}\", tcgscan_ml_mode=\"fallback\"}[15m])) / clamp_min(sum(rate(tcgscan_ml_requests_total{job=\"${local.api_job}\"}[15m])), 1e-9)"
        instant       = true
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id         = "B"
      datasource_uid = "__expr__"

      relative_time_range {
        from = 0
        to   = 0
      }

      model = jsonencode({
        refId      = "B"
        type       = "threshold"
        expression = "A"
        conditions = [{
          evaluator = {
            type   = "gt"
            params = [0.01]
          }
        }]
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }
  }
}
