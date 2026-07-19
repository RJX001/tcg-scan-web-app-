resource "grafana_dashboard" "this" {
  provider = grafana.cloud

  for_each = fileset("${path.module}/dashboards", "*.json")

  config_json = file("${path.module}/dashboards/${each.value}")
  folder      = grafana_folder.tcgscan.uid
  overwrite   = true
}
