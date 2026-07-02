# Deploy LLMs with Ollama
Source: https://docs.baseten.co/examples/ollama

Run LLMs on Ollama as a custom Docker server.

[Ollama](https://ollama.com/) is a popular lightweight LLM inference server, similar to vLLM or SGLang. This guide deploys an Ollama model as a custom Docker server on Baseten.

This configuration serves [TinyLlama](https://ollama.com/library/tinyllama) with Ollama on a CPU instance. The deployment process is the same for larger Ollama models. Adjust the `resources` and the `ollama pull` target in `start_command` to match your model's requirements.

## Set up your environment

This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step. Sign in to Baseten and install `requests` to call the deployed model from Python. Browser login opens a tab to approve this device, so there's no API key to copy and paste.

<Columns>
  <Column>
    **Sign in to Baseten**

    ```sh theme={"system"}
    uvx truss login --browser
    ```
  </Column>

  <Column>
    **Install requests**

    ```sh theme={"system"}
    uv pip install requests
    ```
  </Column>
</Columns>

## Configure the model

Create a directory with a `config.yaml` file:

```sh theme={"system"}
mkdir tinyllama-ollama
touch tinyllama-ollama/config.yaml
```

Copy the following configuration into `config.yaml`:

```yaml config.yaml theme={"system"}
model_name: ollama-tinyllama
base_image:
  image: python:3.11-slim
build_commands:
  - apt-get update && apt-get install -y curl ca-certificates zstd
  - curl -fsSL https://ollama.com/install.sh | sh
docker_server:
  start_command: sh -c "ollama serve & sleep 5 && ollama pull tinyllama && wait"
  readiness_endpoint: /api/tags
  liveness_endpoint: /api/tags
  predict_endpoint: /api/generate
  server_port: 11434
resources:
  cpu: "4"
  memory: 8Gi
```

The `base_image` is a lightweight Python image. The `build_commands` install the system packages that the Ollama install script requires (`curl`, `ca-certificates`, and `zstd`), then download and install Ollama. The slim base image doesn't include these packages by default.

The `start_command` launches the Ollama server, waits for it to initialize, and then pulls the TinyLlama model. The `readiness_endpoint` and `liveness_endpoint` both point to `/api/tags`, which returns successfully when Ollama is running. The `predict_endpoint` maps Baseten's `/predict` route to Ollama's `/api/generate` endpoint.

This example only needs 4 CPUs and 8 GB of memory. For a complete list of resource options, see the [Resources](/deployment/resources) page.

## Deploy the model

Push the model to Baseten to start the deployment:

```sh theme={"system"}
uvx truss push tinyllama-ollama
```

You should see output like:

```output theme={"system"}
✨ Model ollama-tinyllama was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Copy the model ID from the output for the next step.

The first deploy can take several minutes while Baseten pulls the base image and Ollama downloads TinyLlama on container start. Subsequent scale-ups reuse the cached image and start much faster.

## Call the model

Ollama's `/api/generate` is mapped to Baseten's `/predict` route, so you can call the deployed model with any HTTP client:

<Tabs>
  <Tab title="Truss CLI">
    To run inference with Truss, use the `predict` command:

    ```sh theme={"system"}
    truss predict -d '{"model": "tinyllama", "prompt": "Write a short story about a robot dreaming", "stream": false, "options": {"num_predict": 50}}'
    ```
  </Tab>

  <Tab title="cURL">
    To run inference with cURL, use the following command:

    ```sh theme={"system"}
    curl -s -X POST "https://model-MODEL_ID.api.baseten.co/production/predict" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{"model": "tinyllama", "prompt": "Write a short story about a robot dreaming", "stream": false, "options": {"num_predict": 50}}' \
      | jq -j '.response'
    ```
  </Tab>

  <Tab title="Python">
    To run inference with Python, use the following:

    ```python call_model.py theme={"system"}
    import os
    import requests

    model_id = "MODEL_ID"
    baseten_api_key = os.environ["BASETEN_API_KEY"]

    response = requests.post(
        f"https://model-{model_id}.api.baseten.co/production/predict",
        headers={"Authorization": f"Bearer {baseten_api_key}"},
        json={
            "model": "tinyllama",
            "prompt": "Write a short story about a robot dreaming",
            "stream": False,
            "options": {"num_predict": 50},
        },
    )
    print(response.json()["response"])
    ```
  </Tab>
</Tabs>

Replace `MODEL_ID` with the model ID from your deployment output.

You should see:

```output theme={"system"}
It was a dreary, grey day when the robots started to dream.
They had been programmed to think like humans, but it wasn't until they began to dream that they realized just how far apart they actually were.
```

***

## Next steps

For higher-throughput serving on GPUs with OpenAI-compatible endpoints, see the vLLM and SGLang examples.

<CardGroup>
  <Card title="Deploy LLMs with vLLM" icon="bolt" href="/examples/vllm">
    Serve open-source LLMs on vLLM with prefix caching and the OpenAI-compatible API.
  </Card>

  <Card title="Deploy LLMs with SGLang" icon="gauge-high" href="/examples/sglang">
    Serve open-source LLMs on SGLang's high-performance runtime with the OpenAI-compatible API.
  </Card>
</CardGroup>
