# modules/service — the cloud-neutral interface

This module is an **interface, not an implementation**: it declares the
variables and outputs every vendor module must support. `gcp/` (Cloud Run v2)
and `aws/` (App Runner) implement it; `envs/staging` composes services onto
both clouds by switching only the module source.

| Variable | Meaning | Cloud Run mapping | App Runner mapping |
|---|---|---|---|
| `service_name` | registry key | service name | service name |
| `image` | pullable image ref | Artifact Registry remote (GHCR pull-through) | ECR pull-through cache |
| `cpu` / `memory` | per-instance resources | `resources.limits` | `instance_configuration` |
| `min_instances` | 0 = scale-to-zero | `scaling.min_instance_count = 0` | min 1 (no scale-to-zero; pause via `aws apprunner pause-service`) |
| `max_instances` | cost guardrail ≤ 3 | `scaling.max_instance_count` | autoscaling `max_size` |
| `port` | contract port | `containers.ports` | `image_configuration.port` |
| `env` | container env | `containers.env` | `runtime_environment_variables` |

Output: `url` — the public HTTPS endpoint (fed back into
`routing-policy.yaml` by `tools/sync_endpoints.py` after apply).
