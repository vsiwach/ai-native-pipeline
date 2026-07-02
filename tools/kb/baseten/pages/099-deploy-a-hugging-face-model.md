# Deploy a Hugging Face model
Source: https://docs.baseten.co/examples/deploy-a-hugging-face-model

Deploy Gemma 4 26B on Baseten with vLLM, BDN-cached weights, EAGLE3 speculative decoding, and prefix caching.

Deploy open-source LLMs from [Hugging Face](https://huggingface.co/) on Baseten using vLLM and Truss. You write a `config.yaml`, push with the Truss CLI, and get an OpenAI-compatible API endpoint. No custom Python code or Dockerfile required.

Deploy [Gemma 4 26B Instruct](https://huggingface.co/RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic) on two H100 GPUs with vLLM, using EAGLE3 speculative decoding and prefix caching. Weights mirror once through the Baseten Delivery Network (BDN), so replicas scale up without re-downloading from Hugging Face.

## Set up your environment

<Steps>
  <Step title="Log in to Baseten with the Truss CLI">
    Authenticate by opening a browser. Truss caches the credentials for subsequent commands:

    ```sh theme={"system"}
    uvx truss login --browser
    ```

    You should see:

    ```output theme={"system"}
    Opening browser for authentication...
    Successfully logged in.
    ```
  </Step>

  <Step title="Add a Hugging Face access token">
    Gemma is gated and requires a license click-through:

    1. Accept Google's license terms on the [Gemma model page](https://huggingface.co/google/gemma-4-26B-A4B-it). The weights in this example come from RedHatAI's FP8 fork; your Hugging Face token grants access to both repos.
    2. Create a read-only [user access token](https://huggingface.co/docs/hub/en/security-tokens).
    3. Save the token as a secret named `hf_access_token` in your [Baseten workspace](https://app.baseten.co/settings/secrets).
  </Step>
</Steps>

***

## Configure the model

Create a project directory and open it:

```sh theme={"system"}
mkdir gemma-4-26b && cd gemma-4-26b
```

Create a `config.yaml` and copy the following configuration into it:

```yaml config.yaml theme={"system"}
model_name: Gemma 4 26B Instruct
model_metadata:
  example_model_input:
    model: google/gemma-4-26B-A4B-it
    messages:
      - role: user
        content: "What does Gemma stand for?"
    stream: true
    max_tokens: 512
    temperature: 1.0
  tags:
    - openai-compatible

base_image:
  image: vllm/vllm-openai:v0.21.0

weights:
  - source: "hf://RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic@main"
    mount_location: "/app/checkpoint/gemma"
    auth_secret_name: "hf_access_token"

docker_server:
  start_command: >-
    sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/gemma
    --tensor-parallel-size $GPU_COUNT
    --served-model-name google/gemma-4-26B-A4B-it
    --max-num-seqs 16
    --max-model-len auto
    --gpu-memory-utilization 0.9
    --enable-prefix-caching
    --speculative-config.model RedHatAI/gemma-4-26B-A4B-it-speculator.eagle3
    --speculative-config.num_speculative_tokens 3
    --speculative-config.method eagle3
    --trust-remote-code
    --enable-auto-tool-choice
    --reasoning-parser gemma4
    --tool-call-parser gemma4"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000

environment_variables:
  VLLM_LOGGING_LEVEL: INFO

resources:
  accelerator: H100:2
  use_gpu: true

secrets:
  hf_access_token: null

runtime:
  predict_concurrency: 8
  health_checks:
    startup_threshold_seconds: 300
    restart_threshold_seconds: 300
    stop_traffic_threshold_seconds: 120
```

Think of this config as connected decisions, not a flat list of fields:

* **Weights:** which Hugging Face checkpoint BDN mirrors and where it mounts inside the container.
* **Server settings** (`base_image`, `docker_server`): how vLLM starts and which routes Baseten forwards to.
* **Resources and runtime:** the GPU shape and how Baseten handles traffic while the replica warms up or fails health checks.
* **Secrets and metadata:** the credentials injected into the container and what shows up in the dashboard **Try** panel.

***

## Deploy the model

Push the model to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output like:

```output theme={"system"}
✨ Model Gemma 4 26B Instruct was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

`truss push` prints your model ID (for example, `abc1d2ef`). You'll need it to call the model's API. You can also find it in your [Baseten dashboard](https://app.baseten.co/models/).

The first deploy takes 5–10 minutes while Baseten pulls the vLLM base image and BDN mirrors the FP8 weights and the EAGLE3 speculator from Hugging Face. Subsequent scale-ups reuse the cached image and weights. Watch progress in the logs linked above.

***

## Call the model

Once the deployment shows **Active** in the dashboard, call it with a [Baseten API key](https://app.baseten.co/settings/api_keys). Export your key before sending the request:

```sh theme={"system"}
export BASETEN_API_KEY="EMPTY"
```

Replace `{model_id}` in the examples below with your model ID from the deploy output.

<Tabs>
  <Tab title="cURL">
    Send a streaming chat completion from the command line:

    ```sh theme={"system"}
    curl -N -X POST "https://model-{model_id}.api.baseten.co/environments/production/sync/v1/chat/completions" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "model": "google/gemma-4-26B-A4B-it",
        "messages": [
          {"role": "user", "content": "Explain prefix caching in two sentences."}
        ],
        "max_tokens": 200,
        "stream": true
      }'
    ```

    Tokens stream back as Server-Sent Events, one `data:` chunk at a time. The Python tab below shows the same call with the chunks reassembled into prose.
  </Tab>

  <Tab title="Python">
    Send a streaming chat completion with the OpenAI SDK. Save the following as `call_model.py`:

    ```python call_model.py theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        base_url="https://model-{model_id}.api.baseten.co/environments/production/sync/v1",
        api_key=os.environ["BASETEN_API_KEY"],
    )

    stream = client.chat.completions.create(
        model="google/gemma-4-26B-A4B-it",
        messages=[
            {"role": "user", "content": "Explain prefix caching in two sentences."}
        ],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="")
    ```

    Run the script with `uv`, which pulls the OpenAI SDK on the fly:

    ```sh theme={"system"}
    uv run --with openai python call_model.py
    ```

    Tokens print to stdout as they arrive:

    ```output theme={"system"}
    Prefix caching is an optimization technique that stores the processed computational states (KV cache) of common prompt prefixes to avoid redundant processing. By reusing these cached states for similar subsequent requests, it significantly reduces latency and computational costs during inference.
    ```
  </Tab>
</Tabs>

<Tip>
  The `model` argument in your request must match the `--served-model-name` flag in `start_command`, or the API returns a 400.
</Tip>

Any code that works with the OpenAI SDK works with your deployment: point `base_url` at your model's endpoint. To route traffic through a third-party OpenAI-compatible gateway, see [External LLM gateways](/inference/calling-your-model#external-llm-gateways).

***

## Run a production inference server

This deployment is a template for productionizing open-source LLMs from Hugging Face, not just a one-time demo. Baseten runs vLLM as a managed server with health checks, autoscaling, and BDN-cached weights, and exposes an OpenAI-compatible API your existing clients can call without changes.

Two vLLM features in the `start_command` speed up inference at scale. EAGLE3 speculative decoding runs a small draft model alongside the main model and accepts matching token predictions, cutting decode latency by roughly 30–40% on most LLM workloads. Prefix caching reuses the KV cache when requests share a prompt prefix, such as a system prompt, RAG context, or multi-turn history, which can cut time-to-first-token by an order of magnitude on chat and retrieval workloads.

The same pattern works across model families: BDN handles weight delivery, vLLM serves the model, and Baseten handles replicas, routing, and monitoring in production.

***

## Next steps

### Adapt to another model

Port the template incrementally. Change and validate one layer before moving to the next.

* **Weights:** Point `weights[].source` at the new repo and update the path in `start_command`. Keep `auth_secret_name` for gated models, and pin a revision (for example, `@main` or a commit hash) for reproducibility.
* **Served model name:** Set `--served-model-name` to the public model ID your clients will send, and update the `model` field in `example_model_input` to match.
* **Model-specific vLLM flags:** Swap or drop reasoning and tool-call parsers (the `gemma4` parsers only apply to Gemma 4). Remove the `--speculative-config.*` flags if no EAGLE3 speculator is published for your target.
* **Hardware:** Resize `resources.accelerator` for the new checkpoint's memory footprint. Confirm utilization in the deployment logs and `nvidia-smi`.
* **Runtime tuning:** Tune `runtime.predict_concurrency` alongside `--max-num-seqs` once you know your traffic pattern.
* **Rollback:** Promote a working config to a separate [environment](/deployment/environments) and roll forward only after smoke tests pass.

### Related resources

<CardGroup>
  <Card title="Autoscaling" icon="arrows-up-down" href="/deployment/autoscaling/overview">
    Configure replicas, concurrency targets, and scale-to-zero for production traffic.
  </Card>

  <Card title="Customize a model" icon="code" href="/examples/customize-a-model">
    Add custom Python when you need preprocessing, postprocessing, or unsupported architectures.
  </Card>
</CardGroup>
