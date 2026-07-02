# Generate speech with Kokoro
Source: https://docs.baseten.co/examples/text-to-speech

Deploy Kokoro as a text-to-speech endpoint.

<Card title="View example on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/kokoro" />

In this example, you'll deploy [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) as a Truss endpoint. Kokoro is an open-weight TTS model with 82 million parameters that runs on a single T4 GPU. Version 1.0 ships American and British English voices out of the box, with additional languages available by adding the corresponding `misaki` extras. The endpoint returns 24 kHz mono audio as a base64-encoded WAV file.

By the end of this tutorial, you'll be able to generate audio like this:

<AudioSample label="Kokoro welcome sample" />

# Set up imports

Kokoro exposes two classes: `KModel` (the weights and forward pass) and `KPipeline` (G2P and voice management). By default both download from Hugging Face on first use. This Truss uses the [Baseten Delivery Network](/development/model/bdn) to mirror the weights to a local mount instead, so cold starts skip the download and `load` points `KModel` and `KPipeline` at that mount.

```python model/model.py theme={"system"}
import base64
import io
import logging
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wav
import torch
from kokoro import KModel, KPipeline

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000
DEFAULT_VOICE = "af_heart"
REPO_ID = "hexgrad/Kokoro-82M"
WEIGHTS_DIR = Path("/weights/kokoro")
```

# Define the `Model` class and `load` function

Load `KModel` from the BDN-mounted `config.json` and `kokoro-v1_0.pth`, then read every voicepack from `/weights/kokoro/voices/` into memory. Each `KPipeline` reuses the shared model and inherits the preloaded voicepacks, so no request ever reaches Hugging Face.

<Note>
  The base `kokoro` package only ships English G2P. To use Japanese or Mandarin voices, add `misaki[ja]` or `misaki[zh]` to the `requirements` block in `config.yaml`. Spanish, French, Hindi, Italian, and Portuguese voices use the `espeak-ng` fallback, which is already installed below.
</Note>

```python model/model.py theme={"system"}
class Model:
    def __init__(self, **kwargs):
        self._pipelines: dict[str, KPipeline] = {}
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._km: KModel | None = None
        self._voicepacks: dict[str, torch.FloatTensor] = {}

    def load(self):
        logger.info(f"Loading Kokoro from {WEIGHTS_DIR} on {self._device}.")
        self._km = (
            KModel(
                repo_id=REPO_ID,
                config=str(WEIGHTS_DIR / "config.json"),
                model=str(WEIGHTS_DIR / "kokoro-v1_0.pth"),
            )
            .to(self._device)
            .eval()
        )
        for voice_file in (WEIGHTS_DIR / "voices").glob("*.pt"):
            self._voicepacks[voice_file.stem] = torch.load(
                str(voice_file), weights_only=True
            )
        self._pipelines["a"] = self._make_pipeline("a")
        logger.info(f"Kokoro loaded with {len(self._voicepacks)} voicepacks.")

    def _make_pipeline(self, lang_code: str) -> KPipeline:
        pipeline = KPipeline(lang_code=lang_code, repo_id=REPO_ID, model=self._km)
        pipeline.voices.update(self._voicepacks)
        return pipeline

    def _pipeline_for(self, lang_code: str) -> KPipeline:
        if lang_code not in self._pipelines:
            self._pipelines[lang_code] = self._make_pipeline(lang_code)
        return self._pipelines[lang_code]
```

# Define the `predict` function

`KPipeline` is a generator that yields one `(graphemes, phonemes, audio)` tuple per chunk. It splits English on phoneme boundaries (510-phoneme chunks) and non-English on sentence boundaries, so you don't need to pre-chunk long input. Concatenate the per-chunk audio tensors and encode the result as a base64 WAV.

The full set of voices is listed in the model's [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md). Voice names follow the pattern `<lang><gender>_<name>`, for example `af_heart` (American female), `bm_lewis` (British male), or `ef_dora` (Spanish female).

```python model/model.py theme={"system"}
    def predict(self, model_input):
        text = str(model_input.get("text", "Hi, I'm Kokoro."))
        voice = str(model_input.get("voice", DEFAULT_VOICE))
        speed = float(model_input.get("speed", 1.0))

        pipeline = self._pipeline_for(voice[0])

        chunks = []
        for _, _, audio in pipeline(text, voice=voice, speed=speed):
            if audio is None:
                continue
            if hasattr(audio, "cpu"):
                audio = audio.cpu().numpy()
            chunks.append(audio)

        if not chunks:
            raise ValueError("No audio generated; check the input text and voice.")
        audio = np.concatenate(chunks)

        buffer = io.BytesIO()
        wav.write(buffer, SAMPLE_RATE, audio)
        return {"base64": base64.b64encode(buffer.getvalue()).decode("utf-8")}
```

# Set up the `config.yaml`

The `kokoro` package pulls `torch` and `transformers` as transitive dependencies, so the requirements list stays short. Use the `weights` block to specify the Hugging Face source and a `mount_location` for the model files. This uses [BDN](/development/model/bdn), which mirrors the weights once and serves them from multi-tier caches on every cold start.

```yaml config.yaml theme={"system"}
environment_variables: {}
model_metadata:
  example_model_input:
    text: "Kokoro is an open-weight TTS model with 82 million parameters that delivers comparable quality to larger models while being significantly faster and more cost-efficient."
    voice: af_heart
    speed: 1.0
model_name: kokoro
python_version: py311
requirements:
- kokoro>=0.9.4
- numpy
- scipy
resources:
  accelerator: T4
  use_gpu: true
runtime:
  predict_concurrency: 1
secrets: {}
weights:
- source: "hf://hexgrad/Kokoro-82M@f3ff3571791e39611d31c381e3a41a3af07b4987"
  mount_location: "/weights/kokoro"
  allow_patterns:
    - "config.json"
    - "kokoro-v1_0.pth"
    - "voices/*.pt"
system_packages:
- espeak-ng
```

## Configure resources for Kokoro

A T4 GPU runs Kokoro's 82M parameters with room to spare.

```yaml config.yaml theme={"system"}
resources:
  accelerator: T4
  use_gpu: true
```

## System packages

Kokoro uses `espeak-ng` as a fallback grapheme-to-phoneme backend for out-of-dictionary words and non-English languages.

```yaml config.yaml theme={"system"}
system_packages:
- espeak-ng
```

# Deploy the model

Deploy the model like you would any other Truss:

```bash theme={"system"}
truss push kokoro
```

# Generate a WAV file

Call the deployed model and decode the base64 response to a `.wav` file.

```python infer.py theme={"system"}
import httpx
import base64
import os

# Set model_id to your deployed model's ID.
model_id = ""
baseten_api_key = os.environ["BASETEN_API_KEY"]

with httpx.Client() as client:
    resp = client.post(
        f"https://model-{model_id}.api.baseten.co/production/predict",
        headers={"Authorization": f"Bearer {baseten_api_key}"},
        json={"text": "Hello world", "voice": "af_heart", "speed": 1.0},
        timeout=None,
    )

response_data = resp.json()
audio_bytes = base64.b64decode(response_data["base64"])

with open("output.wav", "wb") as f:
    f.write(audio_bytes)

print("Audio saved to output.wav")
```

Running `infer.py` decodes the base64 response into `output.wav` in your working directory. Select the file in your file browser, then select play to hear Kokoro speak the text from your request.

<Note>
  The first inference call after a cold start takes a few seconds while Kokoro compiles its CUDA kernels. Subsequent calls return audio in under a second.
</Note>

# Other TTS options

For higher-throughput or streaming use cases, see:

* [Orpheus 3B WebSocket TTS](https://github.com/basetenlabs/truss-examples/tree/main/orpheus-3b-websockets): real-time streaming over WebSocket with TensorRT-LLM on an H100.
* [Chatterbox TTS](https://github.com/basetenlabs/truss-examples/tree/main/chatterbox-tts): voice cloning from a reference audio clip.
* [Piper TTS](https://github.com/basetenlabs/truss-examples/tree/main/piper-tts): CPU-only TTS for low-latency, low-cost deployments.
