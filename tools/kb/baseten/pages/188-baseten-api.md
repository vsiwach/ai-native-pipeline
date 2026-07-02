# baseten api
Source: https://docs.baseten.co/reference/cli/baseten/api

Make raw API requests

Make raw HTTP requests to Baseten management or inference APIs.

The HTTP method defaults to GET, or POST when `--field`, `--raw-field`, or `--input` is provided. JSON responses are pretty-printed by default; non-JSON responses are streamed raw. Use `--jq` to filter JSON responses.

## management

```sh theme={"system"}
baseten api management [OPTIONS] <api-path>
```

Make raw HTTP requests to the Baseten management API (api.baseten.co).

Paths are relative to /v1/, so 'baseten api management models' requests /v1/models.

### Options

<ParamField type="TEXT (repeatable)">
  Add a string field (key=value), parsed as JSON value
</ParamField>

<ParamField type="TEXT (repeatable)">
  Add a request header (key:value)
</ParamField>

<ParamField type="TEXT">
  Read request body from file (use - for stdin)
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  HTTP method, defaults to GET or POST if fields are provided
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT (repeatable)">
  Add a raw string field (key=value)
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

GET a management resource

```sh theme={"system"}
baseten api management models
```

POST a management resource with fields

```sh theme={"system"}
baseten api management models --field name=my-model
```

### Filter output with `--jq`

List model IDs from /v1/models

```sh theme={"system"}
baseten api management models --jq '.models[].id'
```

### Output

**Text mode (`--output text`):** The HTTP response body, passed through verbatim. JSON responses are pretty-printed; non-JSON responses are streamed raw to stdout.

**JSON mode (`--output json`):** payload type `cmd.JSONUndefined`.

Shape depends on the requested endpoint. See the management API OpenAPI spec at [https://api.baseten.co/v1/spec](https://api.baseten.co/v1/spec).

## inference

```sh theme={"system"}
baseten api inference [OPTIONS] <api-path>
```

Make raw HTTP requests to a Baseten inference endpoint.

Requires either `--model-id` or `--chain-id` to identify the target. Use `--environment` to target a specific environment (e.g. production).

### Options

<ParamField type="TEXT">
  Chain ID to target
</ParamField>

<ParamField type="TEXT">
  Environment name (e.g. production)
</ParamField>

<ParamField type="TEXT (repeatable)">
  Add a string field (key=value), parsed as JSON value
</ParamField>

<ParamField type="TEXT (repeatable)">
  Add a request header (key:value)
</ParamField>

<ParamField type="TEXT">
  Read request body from file (use - for stdin)
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  HTTP method, defaults to GET or POST if fields are provided
</ParamField>

<ParamField type="TEXT">
  Model ID to target
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT (repeatable)">
  Add a raw string field (key=value)
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

POST a predict body to a model

```sh theme={"system"}
baseten api inference production/predict --model-id <model-id> --field prompt=hello
```

### Filter output with `--jq`

Filter a JSON predict response

```sh theme={"system"}
baseten api inference production/predict --model-id <model-id> --field prompt=hello --jq '.result'
```

### Output

**Text mode (`--output text`):** The inference endpoint's response body, passed through verbatim. JSON responses are pretty-printed; non-JSON responses are streamed raw.

**JSON mode (`--output json`):** payload type `cmd.JSONUndefined`.

Shape depends on the model and endpoint. See the inference API OpenAPI spec at [https://api.baseten.co/inference-spec](https://api.baseten.co/inference-spec).
