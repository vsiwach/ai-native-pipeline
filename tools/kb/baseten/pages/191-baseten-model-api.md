# baseten model-api
Source: https://docs.baseten.co/reference/cli/baseten/model-api

Manage Model APIs

List and inspect Baseten Model APIs.

Authenticate with `baseten auth login` or the `BASETEN_API_KEY` environment variable.

## describe

```sh theme={"system"}
baseten model-api describe [OPTIONS]
```

Describe a single Model API by name.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Name of the Model API to describe.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Describe a Model API by name

```sh theme={"system"}
baseten model-api describe --model <name>
```

### Filter output with `--jq`

Print the Model API's invoke URL

```sh theme={"system"}
baseten model-api describe --model <name> --jq '.invoke_url'
```

### Output

**Text mode (`--output text`):** Field-per-line summary of the Model API.

**JSON mode (`--output json`):** payload type `managementapi.ModelAPI`.

## list

```sh theme={"system"}
baseten model-api list [OPTIONS]
```

List the Model APIs the workspace has added.

Pass `--all` to browse the full visible catalog instead of just the added ones.

### Options

<ParamField type="BOOL">
  Browse the full visible catalog instead of only the Model APIs the workspace has added.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

List the Model APIs the workspace has added

```sh theme={"system"}
baseten model-api list
```

Browse the full visible catalog

```sh theme={"system"}
baseten model-api list --all
```

### Filter output with `--jq`

Print just the Model API names

```sh theme={"system"}
baseten model-api list --jq '.items[].name'
```

### Output

**Text mode (`--output text`):** Table with columns: NAME, CONTEXT, $/1M IN, $/1M OUT, ADDED. When no Model APIs match, prints "No Model APIs found." to stderr.

**JSON mode (`--output json`):** payload type `cmd.ModelAPIList`.

## predict

```sh theme={"system"}
baseten model-api predict [OPTIONS]
```

POST an inference request to a Model API and write the response to stdout.

The request is sent to `--url`, which defaults to the OpenAI chat-completions endpoint on the shared inference host. Override it for other shapes (e.g. /v1/messages, /v1/embeddings) or different hosts.

`--content` is the simple path: it builds an OpenAI chat-completions body with a single user message and `--model` as the model, and prints just the assistant's reply. It is only valid for OpenAI chat URLs and requires `--model`.

`--data` and `--file` send a request body verbatim, so any format the endpoint accepts works (OpenAI, Anthropic, embeddings, custom). The response is written as-is: JSON is pretty-printed, streams and binary bodies are passed through.

### Options

<ParamField type="TEXT">
  Single user message; builds an OpenAI chat-completions request and prints the assistant's reply. Only valid for OpenAI chat URLs and requires --model.

  Mutually exclusive with other flags in group `predict-input`.
</ParamField>

<ParamField type="TEXT">
  Inline request body, sent verbatim.

  Mutually exclusive with other flags in group `predict-input`.
</ParamField>

<ParamField type="TEXT">
  Path to a file containing the request body, sent verbatim. Use '-' for stdin.

  Mutually exclusive with other flags in group `predict-input`.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Name of the Model API. Required with --content, where it sets the request's model.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Endpoint to POST the request to. Defaults to [https://inference.baseten.co/v1/chat/completions](https://inference.baseten.co/v1/chat/completions).
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Send a single user message

```sh theme={"system"}
baseten model-api predict --model <name> --content "hello"
```

Send a full OpenAI-shaped body and stream it as JSONL

```sh theme={"system"}
baseten model-api predict --model <name> --data '{"model":"<name>","messages":[{"role":"user","content":"hi"}],"stream":true}' --output jsonl
```

### Filter output with `--jq`

Extract the assistant's message content

```sh theme={"system"}
baseten model-api predict --model <name> --content "hi" --jq '.choices[0].message.content'
```

### Output

**Text mode (`--output text`):** With `--content`, the assistant message text. With `--data`/`--file`, the response body as-is (pretty-printed JSON, or a raw stream/binary body).

**JSON mode (`--output json`):** payload type `cmd.JSONUndefined`.

Under `--output json`, `--content` emits the full chat-completions response. For `--data`/`--file`, a streamed response becomes one JSON record per chunk under `--output jsonl`, and a binary body is base64-encoded under a 'body' key.
