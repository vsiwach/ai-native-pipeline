# WebSockets
Source: https://docs.baseten.co/development/model/websockets

Enable real-time, streaming, bidirectional communication using WebSockets for Truss models and Chains.

WebSockets provide a persistent, full-duplex communication channel between clients and server-side models or chains. Full duplex means chunks of data can flow client→server and server→client simultaneously and repeatedly, without reopening the connection.

Use cases include real-time audio transcription, AI phone calls, and agents with turn-based interactions. WebSockets are also a fit when you need server-side state: requests in the same session always route to the replica holding that state.

## WebSockets in Truss models

A Truss WebSocket model implements a single `websocket` method in place of the usual `preprocess`, `predict`, and `postprocess` methods. All input and output flows through the WebSocket object itself, not through arguments or return values. `load` still works as it does for HTTP models.

1. Initialize your Truss:

```bash Terminal theme={"system"}
truss init websocket-model
```

See the [`truss init` reference](/reference/cli/truss/init) for full options.

2. Replace the `predict` method in `model/model.py` with a `websocket` method. For example:

```python model/model.py theme={"system"}
import fastapi

class Model:
    async def websocket(self, websocket: fastapi.WebSocket):
        try:
            while True:
                message = await websocket.receive_text()
                await websocket.send_text(f"WS obtained: {message}")
        except fastapi.WebSocketDisconnect:
            pass
```

3. Set `runtime.transport.kind=websocket` in `config.yaml`:

```yaml config.yaml theme={"system"}
...
runtime:
  transport:
    kind: websocket
```

4. Deploy the model:

```bash Terminal theme={"system"}
truss push
```

This creates a published deployment. For live-reload during development, use `truss push --watch`.

For deployment options, see the [`truss push` reference](/reference/cli/truss/push).

### Constraints and behavior

* Message exchange runs in a loop until the client disconnects. To close the connection from the server, call `websocket.close()`.
* WebSockets support bidirectional streaming, so you don't need multiple HTTP round-trips.
* Don't implement `predict`, `preprocess`, or `postprocess`. Baseten doesn't call them.
* Baseten accepts the connection for you, so don't call `websocket.accept()`. You can close the connection yourself when you're done; otherwise Baseten closes it after your `websocket` method returns.

### Call the model

Use [websocat](https://github.com/vi/websocat) to call the model:

```bash Terminal theme={"system"}
websocat -H="Authorization: Bearer $BASETEN_API_KEY" \
   wss://model-{MODEL_ID}.api.baseten.co/environments/production/websocket
Hello # Your input.
WS obtained: Hello # Echoed from model.
# ctrl+c to close connection.
```

<Note>
  The path depends on the environment or deployment you're calling:

  * **Environment:** `wss://model-{MODEL_ID}.api.baseten.co/environments/{ENVIRONMENT_NAME}/websocket`
  * **Deployment:** `wss://model-{MODEL_ID}.api.baseten.co/deployment/{DEPLOYMENT_ID}/websocket`
  * **Regional environment:** `wss://model-{MODEL_ID}-{ENV_NAME}.api.baseten.co/websocket`. See [Regional environments](/deployment/environments#regional-environments).

  See the [WebSocket endpoint reference](/reference/inference-api/predict-endpoints/environments-websocket) for full details.
</Note>

## WebSockets in Chains

Chains wrap WebSockets in a reduced `WebSocketProtocol` object. Processing happens in `run_remote` as usual, but inputs and outputs both flow through the WebSocket itself using async `send_*` and `receive_*` methods (`text`, `bytes`, and `json` variants). A convenience `receive` method handles both `str` and `bytes`.

### Example chainlet

```python chainlet.py theme={"system"}
import fastapi
import truss_chains as chains

class Dependency(chains.ChainletBase):
    async def run_remote(self, name: str) -> str:
        return f"Hello from dependency, {name}."

@chains.mark_entrypoint
class WSEntrypoint(chains.ChainletBase):
    def __init__(self, dependency=chains.depends(Dependency)):
        self._dependency = dependency

    async def run_remote(self, websocket: chains.WebSocketProtocol) -> None:
        try:
            while True:
                message = await websocket.receive_text()
                if message == "dep":
                    response = await self._dependency.run_remote("WSEntrypoint")
                else:
                    response = f"You said: {message}"
                await websocket.send_text(response)
        except fastapi.WebSocketDisconnect:
            print("Disconnected.")
```

### Constraints and behavior

* Your `run_remote` signature must use `WebSocketProtocol`. It mirrors `fastapi.WebSocket`, except you can't call `accept()`. Baseten has already accepted the connection by the time your chainlet runs.
* `run_remote` accepts no other arguments when using WebSockets.
* The return type must be `None`. Send any data back to the client through the WebSocket instead.
* WebSockets are only supported on the *entrypoint* chainlet, not on dependencies.
* Unlike Truss models, Chains don't require you to set `runtime.transport.kind`.

### Call the chain

Use [websocat](https://github.com/vi/websocat) to call the chain:

```bash Terminal theme={"system"}
websocat -H="Authorization: Bearer $BASETEN_API_KEY" \
   wss://chain-{CHAIN_ID}.api.baseten.co/environments/production/websocket
```

<Note>
  Like models, chains accept WebSocket connections on either a deployment or environment path. For regional environments, use `wss://chain-{CHAIN_ID}-{ENV_NAME}.api.baseten.co/websocket`. See [Regional environments](/deployment/environments#regional-environments).

  See the [WebSocket endpoint reference](/reference/inference-api/predict-endpoints/environments-websocket) for full details.
</Note>

## WebSockets with custom servers

Deploy a WebSocket server from a custom Docker image using the [`docker_server`](/development/model/custom-server) configuration. This fits when you already have a WebSocket server packaged as a container, or when you need a runtime Baseten's managed images don't provide.

### Configuration

Set the following in `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: bryanzhang2/custom_ws:v0.0.4
docker_server:
  start_command: /app/server
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/websocket
  server_port: 8081
model_name: custom_ws
runtime:
  transport:
    kind: "websocket"
```

### Required fields

* `predict_endpoint`: The WebSocket endpoint path on your server, for example `/v1/websocket` or `/ws`.
* `runtime.transport.kind`: Must be `"websocket"`.
* `start_command`: Command that starts your WebSocket server.
* `readiness_endpoint`: HTTP path for readiness probes.
* `liveness_endpoint`: HTTP path for liveness probes.

### Call the model

Use [websocat](https://github.com/vi/websocat) to connect to your custom server:

```bash Terminal theme={"system"}
websocat -H="Authorization: Bearer $BASETEN_API_KEY" \
   wss://model-{MODEL_ID}.api.baseten.co/environments/production/websocket
```

Baseten routes the connection to the `predict_endpoint` path on your server.

<Info>
  For more on custom server deployment, see [Custom servers](/development/model/custom-server).
</Info>

## Deployment and concurrency considerations

### Scheduling

Baseten schedules new WebSocket connections onto the least-utilized replica until every replica holds `maxConcurrency - 1` concurrent connections. At that point, Baseten adds replicas up to the `maxReplica` limit.

Baseten scales down when the replica count exceeds `minReplica` and at least one replica has zero connections. Idle replicas are removed one at a time.

Two factors matter more for WebSockets than for HTTP:

* **Resource utilization:** HTTP requests are stateless, so Baseten can rebalance them freely. WebSocket connections stay pinned to a replica for their lifetime and count against that replica's concurrency target even when idle. Manage connection efficiency on the client side.
* **Stateful complexity:** WebSocket handlers often hold server-side state, which adds lifecycle work (disconnects, cleanup, reconnection logic).

### Lifetime guarantees

Baseten guarantees every WebSocket connection lasts at least 1 hour. In practice, connections run much longer. The 1-hour floor exists so Baseten can restart and rebalance internal services without breaking long-lived sessions.

### Concurrency changes

Lowering `maxConcurrency` doesn't close existing connections. Open WebSockets keep running until they close naturally, even if a replica ends up above the new target.

For example, if a replica holds 10 active WebSockets and you change `maxConcurrency` from 10 to 5, Baseten leaves all 10 open. They drain naturally as clients disconnect, or when the 1-hour lifetime guarantee triggers an internal restart.

### Promotion

You can promote a WebSocket model or chain to an environment through the REST API or UI, the same way you promote HTTP deployments.

On promotion, Baseten routes new connections to the new deployment, but existing connections stay on the previous deployment until they terminate. This means older deployments can take longer to scale down than HTTP deployments: their connections outlive the promotion.

### Maximum message size

Baseten enforces a 100 MiB limit on individual messages sent over a WebSocket. Both clients and models are capped at 100 MiB per outgoing message. There's no cap on the total data sent over a connection's lifetime.

## Monitoring

WebSocket deployments expose the same performance metrics as HTTP deployments. The rest of this section covers the differences that matter: status codes reported on connection close, how connection duration is measured, and what counts toward input and output size.

### Inference volume

The Metrics page tracks inference volume as the number of connections per minute. Baseten publishes each data point *after* the connection closes, so every point carries the status the connection ended with.

Two families of status codes appear for WebSocket deployments:

* **HTTP status codes** for connections that failed before the WebSocket upgrade completed.
* **WebSocket close codes** for connections that completed the upgrade and later closed.

#### HTTP status codes

| Code  | Label           | What it means                                                                                                                          |
| ----- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `408` | Request timeout | The WebSocket upgrade request timed out before a replica accepted it.                                                                  |
| `504` | Gateway timeout | No replica became available in time. Typically indicates a cold start that exceeded the configured timeout, or a saturated deployment. |

#### WebSocket close codes

[RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455#section-7.4) defines the full set of WebSocket close codes. The Metrics page surfaces this subset:

| Code   | Label                       | What it means                                                                                           |
| ------ | --------------------------- | ------------------------------------------------------------------------------------------------------- |
| `1000` | Normal closure              | Either side closed the connection cleanly. This is normal, expected traffic.                            |
| `1001` | Going away                  | One side is going away, for example a replica restarting or a browser navigating away.                  |
| `1002` | Protocol error              | One side sent a frame that violates the WebSocket protocol.                                             |
| `1003` | Unsupported data            | One side received a frame type it cannot accept, for example binary data on a text-only endpoint.       |
| `1005` | No status received          | The connection closed without a status code. Reserved and not sent on the wire.                         |
| `1006` | Abnormal closure            | The connection dropped without a close frame. Usually caused by a network failure or a replica crash.   |
| `1007` | Invalid frame payload data  | A message payload was inconsistent with its declared type, for example non-UTF-8 bytes in a text frame. |
| `1008` | Policy violation            | One side closed the connection for a policy reason it did not want to publish.                          |
| `1009` | Message too big             | A message exceeded the 100 MiB per-message limit. See [Maximum message size](#maximum-message-size).    |
| `1010` | Mandatory extension missing | The client expected a WebSocket extension that the server did not negotiate.                            |
| `1011` | Internal error              | The server side hit an unexpected error that forced the connection to close. Check your model logs.     |
| `1012` | Service restart             | The replica is restarting.                                                                              |
| `1013` | Try again later             | The replica is temporarily overloaded.                                                                  |
| `1014` | Bad gateway                 | An upstream gateway returned an invalid response.                                                       |
| `1015` | TLS handshake failure       | Reserved and not sent on the wire.                                                                      |

For the full specification, see [CloseEvent codes on MDN](https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code).

<Note>
  The Metrics page filters out codes that don't help with debugging model behavior, such as rate-limit responses and connections that never reached a terminal state. Grafana and other lower-level tools might show these codes anyway.
</Note>

### End-to-end connection duration

Duration is measured from when the connection opens to when it closes, and published after the connection ends. Reported at p50, p90, p95, and p99.

### Connection input and output size

Cumulative bytes transferred over the connection's lifetime, reported at p50, p90, p95, and p99:

* **Connection input size:** Bytes sent by the client to the server.
* **Connection output size:** Bytes sent by the server to the client.
