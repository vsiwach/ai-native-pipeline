# Get deployment metrics
Source: https://docs.baseten.co/reference/loops-api/deployments/get-deployment-metrics

post /v1/loops/deployments/{deployment_id}/metrics
Returns per-node GPU/CPU/memory utilization and Knative queue-proxy request rate / concurrency / latency for the trainer pods. The sampler half of a Loops deployment is an OracleVersion and uses the existing model-metrics endpoint.
