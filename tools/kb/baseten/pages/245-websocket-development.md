# Websocket development
Source: https://docs.baseten.co/reference/inference-api/predict-endpoints/development-websocket

Connect over WebSocket to the development deployment of a model or chain.

Use this endpoint to connect over WebSockets to the development deployment of a model or chain.

```sh theme={"system"}
wss://{entity}-{entity_id}.api.baseten.co/development/websocket
```

See [WebSockets](/development/model/websockets) for more details.

### Parameters

<ParamField type="string">
  The type of entity you want to connect to. Either `model` or `chain`.
</ParamField>

<ParamField type="string">
  The ID of the model or chain you want to connect to.
</ParamField>

<ParamField type="string">
  Your Baseten API key, passed as `Authorization: Bearer $BASETEN_API_KEY`. `Api-Key` is also accepted as the scheme.
</ParamField>

<RequestExample>
  ```sh websocat theme={"system"}
  websocat -H 'Authorization: Bearer EMPTY' \
      wss://{entity}-{entity_id}.api.baseten.co/development/websocket
  ```
</RequestExample>
