# Grafana as code (Terraform)

Provisions the **TCG Scan** folder and dashboards under `dashboards/` into Grafana Cloud.

## Layout

| Path | Role |
|---|---|
| `main.tf` | Provider + Terraform block |
| `folders.tf` | `TCG Scan` folder (`uid=tcgscan`) |
| `dashboards.tf` | `for_each` over `dashboards/*.json` |
| `dashboards/` | Dashboard JSON (source of truth) |
| `dashboards/api-overview.json` | High-level API health |
| `dashboards/scan-funnel.json` | Scan / ML SLI snapshot |
| `dashboards/api-deep-dive.json` | Per-route/host investigation + event taxonomy |
| `alerts.tf` | `tcgscan-api` rule group (routes to existing contact point) |

Datasources are the stack defaults (`grafanacloud-prom`, `grafanacloud-logs`). Do not recreate them in Terraform.

### Contact point (do not manage)

Alerts use `notification_settings.contact_point = var.alert_contact_point` (default **`telegram`**). That contact point already exists in Grafana Cloud with the bot token. **Never** add a `grafana_contact_point` resource here — Terraform create/replace/destroy would wipe or rotate it.

## Local apply

```bash
cd infra/grafana
cp terraform.tfvars.example terraform.tfvars   # fill in URL + token
terraform init
terraform plan
terraform apply
```

Or via env (no tfvars file):

```bash
export TF_VAR_grafana_url="https://YOUR_STACK.grafana.net"
export TF_VAR_grafana_auth="glsa_..."
terraform plan
```

### Import existing Cloud resources (one-time)

The MCP-created folder/dashboard already exist. Before the first apply against a non-empty stack:

```bash
terraform import 'grafana_folder.tcgscan' tcgscan
terraform import 'grafana_dashboard.this["api-overview.json"]' tcgscan-api-overview
terraform import 'grafana_rule_group.api' 'tcgscan:tcgscan-api'
# scan-funnel dashboard is new — no import needed
# telegram contact point — never import / never manage
```

## CI

`.github/workflows/grafana.yml` plans on PRs and applies on `main` when `infra/grafana/**` changes.

Required GitHub Actions secrets:

| Secret | Maps to |
|---|---|
| `GRAFANA_URL` | `TF_VAR_grafana_url` |
| `GRAFANA_AUTH` | `TF_VAR_grafana_auth` |

State is stored in the Actions cache (not committed). On an empty state file the workflow imports the existing `tcgscan` folder and `tcgscan-api-overview` dashboard before planning.

## Adding a dashboard

1. Drop a new `*.json` under `dashboards/` with a stable `uid`.
2. Open a PR — plan should show one create.
3. Merge to `main` to apply.
