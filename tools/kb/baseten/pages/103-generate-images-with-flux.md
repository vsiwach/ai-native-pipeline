# Generate images with Flux
Source: https://docs.baseten.co/examples/image-generation

Deploy Flux Schnell as a text-to-image endpoint.

<Card title="View example on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/04-image-generation" />

In this example, we go through a Truss that serves a text-to-image model. We
use Flux Schnell, which is one of the highest performing text-to-image models out
there today.

# Set up imports and torch settings

In this example, we use the Hugging Face diffusers library to build our text-to-image model.

```python model/model.py theme={"system"}
import base64
import math
import random
import logging
from io import BytesIO

import numpy as np
import torch
from diffusers import FluxPipeline
from PIL import Image

logging.basicConfig(level=logging.INFO)
MAX_SEED = np.iinfo(np.int32).max
```

# Define the `Model` class and load function

In the `load` function of the Truss, we implement logic involved in
downloading and setting up the model. For this model, we use the
`FluxPipeline` class in `diffusers` to instantiate our Flux pipeline,
and configure a number of relevant parameters.

See the [diffusers docs](https://huggingface.co/docs/diffusers/index) for details
on all of these parameters.

```python model/model.py theme={"system"}
class Model:
    def __init__(self, **kwargs):
        self.pipe = None
        self.weights_dir = "/models/flux"

    def load(self):
        self.pipe = FluxPipeline.from_pretrained(self.weights_dir, torch_dtype=torch.bfloat16).to("cuda")
```

This is a utility function for converting a PIL image to base64.

```python model/model.py theme={"system"}
    def convert_to_b64(self, image: Image) -> str:
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_b64

```

# Define the predict function

The `predict` function contains the actual inference logic. The steps here are:

* Setting up the generation params. These include things like the prompt, image width, image height, number of inference steps, etc.
* Running the Diffusion Pipeline
* Convert the resulting image to base64 and return it

```python model/model.py theme={"system"}
    def predict(self, model_input):
        seed = model_input.get("seed")
        prompt = model_input.get("prompt")
        prompt2 = model_input.get("prompt2")
        max_sequence_length = model_input.get(
            "max_sequence_length", 256
        )  # 256 is max for FLUX.1-schnell
        guidance_scale = model_input.get(
            "guidance_scale", 0.0
        )  # 0.0 is the only value for FLUX.1-schnell
        num_inference_steps = model_input.get(
            "num_inference_steps", 4
        )  # schnell is timestep-distilled
        width = model_input.get("width", 1024)
        height = model_input.get("height", 1024)
        if not math.isclose(guidance_scale, 0.0):
            logging.warning(
                "FLUX.1-schnell does not support guidance_scale other than 0.0"
            )
            guidance_scale = 0.0
        if not seed:
            seed = random.randint(0, MAX_SEED)
        if len(prompt.split()) > max_sequence_length:
            logging.warning(
                "FLUX.1-schnell does not support prompts longer than 256 tokens, truncating"
            )
            tokens = prompt.split()
            prompt = " ".join(tokens[: min(len(tokens), max_sequence_length)])
        generator = torch.Generator().manual_seed(seed)

        image = self.pipe(
            prompt=prompt,
            guidance_scale=guidance_scale,
            max_sequence_length=max_sequence_length,
            num_inference_steps=num_inference_steps,
            width=width,
            height=height,
            output_type="pil",
            generator=generator,
        ).images[0]

        b64_results = self.convert_to_b64(image)
        return {"data": b64_results}

```

# Set up the `config.yaml`

Running Flux Schnell requires a handful of Python libraries, including
`diffusers`, `transformers`, and others.

```yaml config.yaml theme={"system"}
external_package_dirs: []
weights:
  - source: "hf://black-forest-labs/FLUX.1-schnell@main"
    mount_location: "/models/flux"
    allow_patterns:
      - "*.json"
      - "*.safetensors"
    ignore_patterns:
      - "flux1-schnell.safetensors"
model_metadata:
  example_model_input: {"prompt": 'black forest gateau cake spelling out the words "FLUX SCHNELL", tasty, food photography, dynamic shot'}
model_name: Flux.1-schnell
python_version: py311
requirements:
  - git+https://github.com/huggingface/diffusers.git@v0.32.2
  - transformers
  - accelerate
  - sentencepiece
  - protobuf
resources:
  accelerator: H100_40GB
  use_gpu: true
secrets: {}
system_packages:
  - ffmpeg
  - libsm6
  - libxext6
```

## Configure resources for Flux Schnell

Note that we need an H100 40GB GPU to run this model.

```yaml config.yaml theme={"system"}
resources:
  accelerator: H100_40GB
  use_gpu: true
secrets: {}
```

## System packages

Running diffusers requires `ffmpeg` and a couple other system
packages.

```yaml config.yaml theme={"system"}
system_packages:
  - ffmpeg
  - libsm6
  - libxext6
```

## Enable caching

Flux Schnell is a large model, and downloading it from Hugging Face on every cold start would take several minutes. The [Baseten Delivery Network (BDN)](/development/model/bdn) mirrors weights to Baseten's infrastructure once and serves them from multi-tier caches close to your replicas, so cold starts read from a nearby cache instead of re-downloading from upstream.

To enable BDN, add a `weights` block to your config:

```yaml theme={"system"}
weights:
  - source: "hf://black-forest-labs/FLUX.1-schnell@main"
    mount_location: "/models/flux"
    allow_patterns:
      - "*.json"
      - "*.safetensors"
    ignore_patterns:
      - "flux1-schnell.safetensors"
```

The `model.py` `load()` method then reads weights from `mount_location` instead of pulling from Hugging Face.

# Deploy the model

Deploy the model like you would other Trusses, with:

```bash theme={"system"}
truss push flux/schnell
```

# Run an inference

Use a Python script to call the model once it's deployed and parse its response. We parse the resulting base64-encoded string output into an actual image file: `output_image.jpg`.

```python infer.py theme={"system"}
import httpx
import os
import base64
from PIL import Image
from io import BytesIO

# Replace the empty string with your model id below
model_id = ""
baseten_api_key = os.environ["BASETEN_API_KEY"]

# Function used to convert a base64 string to a PIL image
def b64_to_pil(b64_str):
    return Image.open(BytesIO(base64.b64decode(b64_str)))

data = {
  "prompt": 'red velvet cake spelling out the words "FLUX SCHNELL", tasty, food photography, dynamic shot'
}

# Call model endpoint
res = httpx.post(
    f"https://model-{model_id}.api.baseten.co/production/predict",
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json=data
)

# Get output image
res = res.json()
output = res.get("data")

# Convert the base64 model output to an image
img = b64_to_pil(output)
img.save("output_image.jpg")
```
