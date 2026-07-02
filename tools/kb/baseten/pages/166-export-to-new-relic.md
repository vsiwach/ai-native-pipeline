# Export to New Relic
Source: https://docs.baseten.co/observability/export-metrics/new-relic

Export metrics from Baseten to New Relic

Export Baseten metrics to New Relic by integrating with [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/). This involves configuring a Prometheus receiver that scrapes Baseten's metrics endpoint and configuring a New Relic exporter to send the metrics to your observability backend.

**Using OpenTelemetry Collector to push to New Relic**

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
  # Configure a New Relic exporter. Visit New Relic documentation to get your regional otlp endpoint.
  otlphttp/newrelic:
    endpoint: https://otlp.nr-data.net
    headers:
      api-key: "{NEW_RELIC_KEY}"
service:
  pipelines:
    metrics:
      receivers: [prometheus]
      processors: [batch]
      exporters: [otlphttp/newrelic]
```
