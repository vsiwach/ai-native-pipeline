# Tracing
Source: https://docs.baseten.co/observability/tracing

Investigate the prediction flow in detail

Baseten’s Truss server includes built-in [OpenTelemetry](https://opentelemetry.io/) (OTEL) instrumentation, with support for custom tracing.

Tracing helps diagnose performance bottlenecks but introduces minor overhead, so it is **disabled by default**.

## Export builtin trace data to Honeycomb

1. **Create a Honeycomb API** key and add it to [Baseten secrets](https://app.baseten.co/settings/secrets).
2. **Update** `config.yaml` for the target model:

```yaml config.yaml theme={"system"}
environment_variables:
  HONEYCOMB_DATASET: your_dataset_name
runtime:
  enable_tracing_data: true
secrets:
  HONEYCOMB_API_KEY: '***'
```

3. **Send requests with tracing**

* Provide traceparent headers for distributed tracing.
* If omitted, Baseten generates random trace IDs.

## Add custom OTEL instrumentation

To define custom spans and events, integrate OTEL directly:

```python model.py theme={"system"}
import time
from typing import Any, Generator

import opentelemetry.exporter.otlp.proto.http.trace_exporter as oltp_exporter
import opentelemetry.sdk.resources as resources
import opentelemetry.sdk.trace as sdk_trace
import opentelemetry.sdk.trace.export as trace_export
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({resources.SERVICE_NAME: "UserModel"}))
)
tracer = trace.get_tracer(__name__)
trace_provider = trace.get_tracer_provider()


class Model:
    def __init__(self, **kwargs) -> None:
        honeycomb_api_key = kwargs["secrets"]["HONEYCOMB_API_KEY"]
        honeycomb_exporter = oltp_exporter.OTLPSpanExporter(
            endpoint="https://api.honeycomb.io/v1/traces",
            headers={
                "x-honeycomb-team"   : honeycomb_api_key,
                "x-honeycomb-dataset": "marius_testing_user",
            },
        )
        honeycomb_processor = sdk_trace.export.BatchSpanProcessor(honeycomb_exporter)
        trace_provider.add_span_processor(honeycomb_processor)

    @tracer.start_as_current_span("load_model")
    def load(self):
        ...

    def preprocess(self, model_input):
        with tracer.start_as_current_span("preprocess"):
            ...
            return model_input

    @tracer.start_as_current_span("predict")
    def predict(self, model_input: Any) -> Generator[str, None, None]:
        with tracer.start_as_current_span("start-predict") as span:
            def inner():
                time.sleep(0.01)
                for i in range(5):
                    span.add_event("yield")
                    yield str(i)

            return inner()
```

Baseten’s built-in tracing **does not interfere** with user-defined OTEL implementations.
