# Export to Datadog
Source: https://docs.baseten.co/observability/export-metrics/datadog

Export metrics from Baseten to Datadog

The Baseten metrics endpoint can be integrated with [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) by configuring a Prometheus receiver that scrapes the endpoint. This allows Baseten metrics to be pushed to a variety of popular exporters. See the [OpenTelemetry registry](https://opentelemetry.io/ecosystem/registry/?component=exporter) for a full list.

**Using OpenTelemetry Collector to push to Datadog**

```yaml config.yaml theme={"system"}
receivers:  
  # Configure a Prometheus receiver to scrape the Baseten metrics endpoint.
  prometheus:
    config:
      scrape_configs:
        - job_name: 'baseten'
          scrape_interval: 60s
          metrics_path: '/metrics'
          scheme: https
          authorization:
            type: "Api-Key"
            credentials: "{BASETEN_API_KEY}"
          static_configs:
            - targets: ['app.baseten.co']
processors:
  batch:
exporters:
  # Configure a Datadog exporter.
  datadog:
    api:
      key: "{DATADOG_API_KEY}"
service:
  pipelines:
    metrics:
      receivers: [prometheus]
      processors: [batch]
      exporters: [datadog]
```
