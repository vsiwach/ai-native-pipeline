# Voxtral
Source: https://docs.baseten.co/examples/models/transcription/voxtral

Mistral's Voxtral Mini Realtime is a 4B speech-to-text model tuned for real-time streaming transcription.

<div>
  <a href="/examples/models/capabilities/speech-to-text">Speech-to-text</a>
</div>

## Setup

To get started, sign into Baseten with Truss and then install the `websockets` library.

<Columns>
  <Column>
    **Sign in to Baseten**

    ```sh theme={"system"}
    uvx truss login --browser
    ```
  </Column>

  <Column>
    **Install websockets**

    ```sh theme={"system"}
    uv pip install websockets
    ```
  </Column>
</Columns>

[mistralai/Voxtral-Mini-4B-Realtime-2602](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602) is a 4B-parameter encoder-decoder model.

This preset serves Voxtral Mini Realtime on H100 40GB, tuned for low-latency streaming transcription.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100\_40GB × 1</Card>
  <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir voxtral-mini-4b-latency && cd voxtral-mini-4b-latency
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:voxtral-mini-4b preset:latency"
model_metadata:
  repo_id: mistralai/Voxtral-Mini-4B-Realtime-2602
secrets:
  hf_access_token: null
weights:
  - source: "hf://mistralai/Voxtral-Mini-4B-Realtime-2602@main"
    mount_location: "/app/checkpoint/model"
    auth_secret_name: "hf_access_token"
environment_variables:
  VLLM_DISABLE_COMPILE_CACHE: "1"
base_image:
  image: vllm/vllm-openai:v0.22.0-cu129
docker_server:
  start_command: >-
    sh -c "VLLM_DISABLE_COMPILE_CACHE=1 vllm serve /app/checkpoint/model
    --tensor-parallel-size 1
    --served-model-name mistralai/Voxtral-Mini-4B-Realtime-2602
    --host 0.0.0.0
    --port 8000
    --compilation-config '{\"cudagraph_mode\": \"PIECEWISE\"}'"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/realtime
  server_port: 8000
resources:
  accelerator: H100_40GB:1
  cpu: "1"
  memory: 10Gi
  use_gpu: true
requirements:
  - vllm[audio]
  - librosa
  - torch
  - torchaudio
  - pynvml
  - ffmpeg-python
  - websockets
system_packages:
  - python3.10-venv
  - ffmpeg
  - openmpi-bin
  - libopenmpi-dev
runtime:
  is_websocket_endpoint: true
  transport:
    kind: websocket
    ping_interval_seconds: null
    ping_timeout_seconds: null
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                     | Value                             | What it does                                                |
| ------------------------ | --------------------------------- | ----------------------------------------------------------- |
| `--tensor-parallel-size` | `1`                               | Number of GPUs to shard the model across.                   |
| `--compilation-config`   | `{"cudagraph_mode": "PIECEWISE"}` | vLLM compilation passes (op fusion, dead-code elimination). |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model voxtral-mini-4b-latency was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Your **model ID** is printed in the `truss push` output (`abcd1234` in the example). Use it wherever you see `{model_id}` in the next section.

## Call the model

This preset exposes a WebSocket streaming endpoint at `/v1/realtime` for low-latency, incremental transcription. See the [streaming transcription API reference](/reference/inference-api/predict-endpoints/streaming-transcription-api) for the message protocol, Python client example, and supported audio formats.
