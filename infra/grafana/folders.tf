resource "grafana_folder" "tcgscan" {
  provider = grafana.cloud

  title = "TCG Scan"
  uid   = "tcgscan"
}
