# Websocket environment
Source: https://docs.baseten.co/reference/inference-api/predict-endpoints/environments-websocket

Connect over WebSocket to the deployment associated with an environment.

Use this endpoint to connect over WebSockets to the deployment associated with the specified [environment](/deployment/environments).

`entity` is `model` or `chain`, depending on whether you call a Baseten model or a Chain.

```sh theme={"system"}
wss://{entity}-{entity_id}.api.baseten.co/environments/{env_name}/websocket
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
  The name of the environment you want to connect to.
</ParamField>

<ParamField type="string">
  Your Baseten API key, passed as `Authorization: Bearer $BASETEN_API_KEY`. `Api-Key` is also accepted as the scheme.
</ParamField>

<RequestExample>
  ```sh websocat theme={"system"}
  websocat -H 'Authorization: Bearer EMPTY' \
      wss://{entity}-{model_id}.api.baseten.co/environments/{env_name}/websocket
  ```
</RequestExample>
