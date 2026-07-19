variable "grafana_url" {
  description = "Grafana Cloud stack URL (e.g. https://rubyjuniper2812.grafana.net)"
  type        = string
}

variable "grafana_auth" {
  description = "Grafana service account token (Viewer/Editor with dashboards:write) or basic auth"
  type        = string
  sensitive   = true
}

variable "alert_contact_point" {
  description = "Name of an existing Grafana contact point to route alerts to. Terraform references it only — it must NOT create/delete the contact point."
  type        = string
  default     = "telegram"
}
