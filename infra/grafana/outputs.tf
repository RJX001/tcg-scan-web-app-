output "folder_uid" {
  description = "UID of the TCG Scan Grafana folder"
  value       = grafana_folder.tcgscan.uid
}

output "dashboard_uids" {
  description = "UIDs of managed dashboards (from JSON)"
  value = {
    for name, dash in grafana_dashboard.this :
    name => jsondecode(dash.config_json).uid
  }
}

output "alert_rule_group" {
  description = "Managed alert rule group name"
  value       = grafana_rule_group.api.name
}

output "alert_contact_point" {
  description = "Existing contact point name used by rules (not managed by Terraform)"
  value       = var.alert_contact_point
}
