# Overview
Source: https://docs.baseten.co/observability/export-metrics/overview

Export metrics from Baseten to your observability stack

Baseten provides a metrics endpoint in Prometheus format, allowing integration with observability tools like Prometheus, OpenTelemetry Collector, Datadog Agent, and Vector.

## Set up metrics scraping

<Steps>
  <Step title="Scrape endpoint: https://app.baseten.co/metrics" />

  <Step title="Authentication">
    Use the Authorization header with a [Baseten API key](https://app.baseten.co/settings/api_keys):

    ```json theme={"system"}
    {"Authorization": "Bearer YOUR_API_KEY"}
    ```
  </Step>

  <Step title="Scrape interval ">
    Recommended 1-minute interval (metrics update every 30 seconds).
  </Step>
</Steps>

## Supported integrations

Baseten metrics can be collected through [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) and exported to:

* [Prometheus](/observability/export-metrics/prometheus)
* [Datadog](/observability/export-metrics/datadog)
* [Grafana](/observability/export-metrics/grafana)
* [New Relic](/observability/export-metrics/new-relic)

For available metrics, see the [supported metrics reference](/observability/export-metrics/supported-metrics).

## Rate limits

* **6 requests per minute per organization**
* Exceeding this limit results in **HTTP 429 (Too Many Requests)** responses.
* To stay within limits, use a **1-minute scrape interval**.
