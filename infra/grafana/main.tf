terraform {
  required_version = ">= 1.5.0"

  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = ">= 2.9.0, < 5.0.0"
    }
  }
}

provider "grafana" {
  alias = "cloud"

  url  = var.grafana_url
  auth = var.grafana_auth
}
