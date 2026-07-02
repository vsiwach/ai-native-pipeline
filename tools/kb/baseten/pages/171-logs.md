# Logs
Source: https://docs.baseten.co/observability/logs

Scope logs by environment or deployment, then filter by request ID for individual predictions.

Baseten assigns a unique request ID to every predict call and returns it in the `X-Baseten-Request-Id` response header, so you can trace a single prediction through your model's logs.

<Note>
  Per-request log filtering requires Truss version 0.15.5 or later. Upgrade with `pip install --upgrade truss`.
</Note>

## Scope by environment or deployment

The Logs tab can show entries from a single deployment or from every deployment in an environment. Use the dropdowns at the top of the tab to switch.

Environment scope aggregates logs across every deployment in that environment, including past deployments still serving traffic during a rollout. Use it to follow a request across deployment boundaries or to watch a promotion in progress.

Deployment scope restricts logs to a single deployment ID. Use it to isolate behavior to one version, such as a development deployment.

The same scope applies to live tail and historical search.

## Get the request ID

The first step is capturing the request ID from the response. Baseten includes it in every predict response, regardless of whether the call is synchronous, asynchronous, or gRPC. The exact location depends on the protocol you're using:

<Tabs>
  <Tab title="HTTP">
    When you make a predict call, include the `-sD-` flag to print response headers alongside the body:

    ```bash theme={"system"}
    curl -sD- -X POST "https://model-{MODEL_ID}.api.baseten.co/production/predict" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"prompt": "Hello"}'
    ```

    The request ID appears as a response header:

    ```
    X-Baseten-Request-Id: 31255019cf83c4d0c7492a5006591e1f502a5
    ```
  </Tab>

  <Tab title="gRPC">
    For gRPC calls, the request ID is in the response trailer metadata rather than an HTTP header. Use the `-vv` flag with `grpcurl` to surface it:

    ```bash theme={"system"}
    grpcurl -vv \
      -H "baseten-authorization: Api-Key $BASETEN_API_KEY" \
      -H "baseten-model-id: model-{MODEL_ID}" \
      -d '{"name": "World"}' \
      model-{MODEL_ID}.grpc.api.baseten.co:443 \
      example.Greeter/SayHello
    ```

    Look for `x-baseten-request-id` in the trailer metadata at the end of the response:

    ```
    x-baseten-request-id: 31255019cf83c4d0c7492a5006591e1f502a5
    ```
  </Tab>

  <Tab title="Async">
    Async predict calls return the request ID in two places: the response header and the JSON body, so you can capture it programmatically without parsing headers:

    ```bash theme={"system"}
    curl -sD- -X POST "https://model-{MODEL_ID}.api.baseten.co/production/async_predict" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"prompt": "Hello"}'
    ```

    ```
    X-Baseten-Request-Id: 31255019cf83c4d0c7492a5006591e1f502a5
    ```

    ```json theme={"system"}
    {"request_id": "31255019cf83c4d0c7492a5006591e1f502a5"}
    ```
  </Tab>
</Tabs>

## Filter logs by request ID

Once you have a request ID, open the model's logs page and enter it in the search filter bar using the `requestId:` prefix:

```
requestId:31255019cf83c4d0c7492a5006591e1f502a5
```

The view narrows to show only log entries from that request. Each log line also displays the request ID alongside the replica ID, so you can confirm you're looking at the right trace even when scrolling through mixed output.

## Logging with request context

For standard Truss models, Baseten automatically attaches the request ID to any log emitted through Python's `logging` module during a predict call. No configuration is required. Use a logger:

```python theme={"system"}
import logging

logger = logging.getLogger(__name__)

class Model:
    def predict(self, request):
        logger.info("Starting prediction")  # request_id is added automatically
        ...
```

## Custom servers

For standard Truss models, Baseten handles request ID logging automatically through the framework's built-in JSON formatter. No configuration is required.

Custom servers don't have this built-in support, so you'll need to do two things: extract the `x-baseten-request-id` header from incoming requests, and include it as a top-level `request_id` key in your JSON log output. Both steps are covered in the setup guides for [custom HTTP servers](/development/model/custom-server#per-request-logging) and [custom gRPC servers](/development/model/grpc#per-request-logging).

## Download logs

Download a deployment's logs as a file from the **Logs** tab. Baseten runs the export as a background job and saves the file when it's ready, so the download reflects the full time range and filters you selected, not only the lines loaded in the view.

1. Open the **Logs** tab and set the deployment or environment scope, time range, and any filters (level, request ID, replica, or search).
2. Select **Download CSV** or **Download JSON**.
3. The file downloads automatically once it finishes preparing.

A single download covers up to 7 days and 100,000 log lines. If you reach either limit, shorten the time range or add filters and export again.

### Fetch logs from the CLI

To pull logs from a terminal or script, use the Baseten CLI:

```bash theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --since 1h
```

Scope the window with `--start` and `--end` or `--since`, up to 7 days. Stream live logs with `--tail`, and pass `--output jsonl` for machine-readable output. See the [`baseten model deployment logs`](/reference/cli/baseten/model-deployment#logs) reference for the full set of filters.

## Export logs to an OTLP endpoint

You can stream the same logs that appear in the Baseten UI to any backend that accepts [OTLP over HTTP](https://opentelemetry.io/docs/specs/otlp/#otlphttp), including Honeycomb, Datadog, Grafana Cloud, and Sentry. Once configured, every new log line is forwarded to your endpoint in near real time, so you can build dashboards, alerts, and long-term retention on top of your inference traffic without scraping the UI.

<Note>
  Log export is rolling out gradually. If the **OTEL connection** card isn't visible in your settings, contact Baseten support to enable it for your organization.
</Note>

### What gets exported

The exporter forwards every log you would see in the Baseten UI, which includes:

* **Build logs:** image builds for new deployments.
* **Deploy and promotion logs:** lifecycle events emitted as a deployment activates, scales, or is promoted to an environment.
* **Serving logs:** stdout and stderr from your model replicas, including anything you write through Python's `logging` module.

Each record is sent as an OTLP `LogRecord` with `service.name = "baseten"` and an allowlisted set of attributes:

| Attribute          | Description                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------- |
| `message`          | The log line.                                                                                |
| `model_id`         | Stable ID of the model the log came from.                                                    |
| `model_version_id` | Deployment (model version) the log came from.                                                |
| `environment`      | Environment name, such as `production` or `staging`, when the deployment is attached to one. |
| `replica`          | Replica ID for serving logs.                                                                 |
| `request_id`       | Per-prediction request ID. Matches the `X-Baseten-Request-Id` header.                        |
| `training_job_id`  | Training job ID for training logs.                                                           |
| `chainlet_id`      | Chainlet ID for [Chains](/development/chain/overview).                                       |
| `exc_info`         | Formatted Python traceback, when the log carries an exception.                               |

Baseten maps the original log level to OTLP `SeverityNumber` and `SeverityText` (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) and strips internal labels that aren't on the allowlist before export, so your backend only receives the same fields you see in the UI.

Exports start from the moment the connection is enabled. Historical logs are not backfilled, and delivery is best-effort: Baseten retries transient failures with exponential backoff, but records can be dropped if your endpoint is unreachable for an extended period.

### Configure a connection

Each Baseten organization can have one OTLP destination at a time.

<Steps>
  <Step title="Open settings">
    Go to **Settings → General** and find the **OTEL connection** card.
  </Step>

  <Step title="Add a connection">
    Click **Add connection** and fill in:

    * **Endpoint URL:** The full URL of your OTLP/HTTP logs receiver, including the path (`/v1/logs` for most receivers). See the integration notes below for per-vendor examples.
    * **Header name:** The HTTP header your backend uses to authenticate.
    * **Header value:** The credential for that header. The value is stored encrypted and never displayed again after you save it.
  </Step>

  <Step title="Save and verify">
    Save the connection. New log records start flowing to your endpoint within a few seconds. Click **Test** on the saved connection to send a probe log and confirm the endpoint and credentials are accepted. For an end-to-end check, send a prediction to a deployment and look for its request ID in your backend.

    <Note>The **Test** button is not supported for custom OTLP endpoints. Logs are still forwarded to your endpoint, but you can't send a probe from the UI to verify the connection.</Note>
  </Step>
</Steps>

To rotate credentials or change destinations, use the edit icon on the saved connection. Removing the connection stops exports immediately.

### Integration notes

The endpoint and header values below come from each vendor's OTLP/HTTP documentation. Check those docs for the most current values for your account and region.

<Tabs>
  <Tab title="Honeycomb">
    Honeycomb accepts OTLP/HTTP at `https://api.honeycomb.io/v1/logs` (or a region-specific host such as `https://api.eu1.honeycomb.io/v1/logs`). Authenticate with an ingest API key:

    * **Endpoint URL:** `https://api.honeycomb.io/v1/logs`
    * **Header name:** `x-honeycomb-team`
    * **Header value:** Your Honeycomb ingest API key.

    On Honeycomb environments that route by `service.name`, logs land in a dataset named `baseten`. Honeycomb Classic accounts and other dataset-routing setups route differently. See [Honeycomb's OTLP/HTTP reference](https://docs.honeycomb.io/send-data/logs/honeycomb-exporter/) for dataset routing and regional endpoints.
  </Tab>

  <Tab title="Datadog">
    Datadog accepts OTLP/HTTP logs directly on its intake endpoint, so you don't need to run the Datadog Agent or an OpenTelemetry Collector. Authenticate with a Datadog API key:

    * **Endpoint URL:** `https://http-intake.logs.<site>.datadoghq.com/v1/logs`, where `<site>` is your Datadog site (`us1`, `us3`, `us5`, `eu`, `ap1`, and so on).
    * **Header name:** `dd-api-key`
    * **Header value:** An API key from your Datadog **Organization Settings → API Keys** page (at `https://<site>.datadoghq.com/organization-settings/api-keys`).

    See [Datadog's OTLP logs intake docs](https://docs.datadoghq.com/opentelemetry/setup/otlp_ingest/logs/) for the per-site endpoint and request format.
  </Tab>

  <Tab title="Grafana Cloud">
    Grafana Cloud exposes an OTLP gateway per stack. Use the gateway URL and basic auth token from your stack's **OpenTelemetry** connection page:

    * **Endpoint URL:** `https://otlp-gateway-<zone>.grafana.net/otlp/v1/logs`
    * **Header name:** `Authorization`
    * **Header value:** `Basic <base64(instanceID:token)>`

    The exported logs appear in Loki and can be queried alongside the rest of your Grafana Cloud telemetry. See [Grafana Cloud's OTLP setup docs](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/) for the exact gateway URL and token format.
  </Tab>

  <Tab title="Sentry">
    Sentry accepts OTLP/HTTP logs on a per-project ingest endpoint. Authenticate with your project's public key:

    * **Endpoint URL:** `https://o<orgId>.ingest.sentry.io/api/<projectId>/integration/otlp/v1/logs`
    * **Header name:** `x-sentry-auth`
    * **Header value:** `sentry sentry_key=<publicKey>`

    Find the org ID, project ID, and public key in your Sentry project under **Settings → Client Keys (DSN)**. See [Sentry's direct OTLP logs docs](https://docs.sentry.io/concepts/otlp/direct/logs/) for details.
  </Tab>
</Tabs>

Other OTLP/HTTP collectors work the same way. If your backend isn't listed, fill in the endpoint URL and the auth header (name and value) it documents for OTLP, and Baseten will start sending logs to it.
