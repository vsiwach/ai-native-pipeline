# Qwen3-ASR
Source: https://docs.baseten.co/examples/models/transcription/qwen3-asr

Alibaba's Qwen3-ASR is a compact 1.7B speech-to-text model with multilingual transcription support.

<div>
  <a href="/examples/models/capabilities/speech-to-text">Speech-to-text</a>
</div>

## Setup

To get started, sign into Baseten with Truss and then install the OpenAI SDK.

<Columns>
  <Column>
    **Sign in to Baseten**

    ```sh theme={"system"}
    uvx truss login --browser
    ```
  </Column>

  <Column>
    **Install the OpenAI SDK**

    ```sh theme={"system"}
    uv pip install openai
    ```
  </Column>
</Columns>

[Qwen/Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) is a 1.7B-parameter encoder-decoder model.

This preset serves Qwen3-ASR on a single H100 40GB through vLLM, tuned for fast multilingual transcription.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100\_40GB × 1</Card>
  <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
  <Card title="Concurrency" icon="layer-group">256</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir qwen3-asr-1.7b-latency && cd qwen3-asr-1.7b-latency
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:qwen3-asr-1.7b preset:latency"
model_metadata:
  repo_id: Qwen/Qwen3-ASR-1.7B
  example_model_input:
    stream: false
    messages:
      - role: user
        content:
          - type: audio_url
            audio_url:
              url: https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav
  tags:
    - openai-compatible
secrets:
  hf_access_token: null
weights:
  - source: "hf://Qwen/Qwen3-ASR-1.7B@main"
    mount_location: "/app/checkpoint/model"
    auth_secret_name: "hf_access_token"
base_image:
  image: vllm/vllm-openai:v0.22.0-cu129
docker_server:
  start_command: sh -c "vllm serve /app/checkpoint/model --tensor-parallel-size 1 --served-model-name Qwen/Qwen3-ASR-1.7B --gpu-memory-utilization 0.8 --host 0.0.0.0 --port 8000 --load-format runai_streamer"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
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
system_packages:
  - python3.10-venv
  - ffmpeg
  - openmpi-bin
  - libopenmpi-dev
runtime:
  predict_concurrency: 256
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                       | Value            | What it does                                                                                                   |
| -------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
| `--tensor-parallel-size`   | `1`              | Number of GPUs to shard the model across.                                                                      |
| `--gpu-memory-utilization` | `0.8`            | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
| `--load-format`            | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model qwen3-asr-1.7b-latency was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Your **model ID** is printed in the `truss push` output (`abcd1234` in the example). Use it wherever you see `{model_id}` in the next section.

## Call the model

Your deployment serves an OpenAI-compatible chat completions API at `/v1/chat/completions` that accepts audio inputs. Replace `{model_id}` with your model ID and make sure `BASETEN_API_KEY` is set.

Send audio as an `audio_url` content item on a chat message. The model returns the transcription as the assistant message content.

<Tabs>
  <Tab title="Python">
    ```python main.py theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["BASETEN_API_KEY"],
        base_url="https://model-{model_id}.api.baseten.co/environments/production/sync/v1",
    )

    response = client.chat.completions.create(
        model="Qwen/Qwen3-ASR-1.7B",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {
                            "url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav"
                        },
                    }
                ],
            }
        ],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="cURL">
    ```sh theme={"system"}
    curl -s https://model-{model_id}.api.baseten.co/environments/production/sync/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "Qwen/Qwen3-ASR-1.7B",
        "messages": [
          {"role": "user", "content": [
            {"type": "audio_url", "audio_url": {"url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav"}}
          ]}
        ]
      }'
    ```
  </Tab>
</Tabs>
