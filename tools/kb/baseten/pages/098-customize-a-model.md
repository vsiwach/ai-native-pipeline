# Customize a model
Source: https://docs.baseten.co/examples/customize-a-model

Deploy a model with custom Python code using the Truss Model class.

Most models on Baseten deploy with just a `config.yaml` and an inference engine. But when you need custom preprocessing, postprocessing, or want to run a model architecture that the built-in engines don't support, you can write Python code in a `model.py` file. Truss provides a `Model` class with three methods (`__init__`, `load`, and `predict`) that give you full control over how your model initializes, loads weights, and handles requests.

This guide walks through deploying [Phi-3-mini-4k-instruct](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct), a 3.8B parameter LLM, using custom Python code. If you haven't deployed a config-only model yet, start with [Deploy your first model](/examples/deploy-your-first-model).

## Install and sign in

Before you begin, [sign up](https://app.baseten.co/signup) or [sign in](https://app.baseten.co/login) to Baseten, then install [uv](https://docs.astral.sh/uv/), a fast Python package manager.

Install the Truss CLI and connect it to your Baseten account. Browser login opens a tab to approve this device, so there's no API key to copy and paste.

<Columns>
  <Column>
    **Install Truss**

    ```sh theme={"system"}
    uv tool install truss
    ```
  </Column>

  <Column>
    **Sign in**

    ```sh theme={"system"}
    truss login --browser
    ```
  </Column>
</Columns>

<Tip>
  Prefer not to install? Run `uvx truss login --browser` to use the same flow without a permanent install, and use `uvx truss …` for the rest of this guide.
</Tip>

***

## Create a Truss project

Create a new Truss:

```sh theme={"system"}
truss init phi-3-mini && cd phi-3-mini
```

When prompted, give your Truss a name like `Phi 3 Mini`.

This command scaffolds a project with the following structure:

```
phi-3-mini/
  model/
    __init__.py
    model.py
  config.yaml
  data/
  packages/
```

The key files are:

* `model/model.py`: Your model code with `load()` and `predict()` methods.
* `config.yaml`: Dependencies, resources, and deployment settings.
* `data/`: Optional directory for data files bundled with your model.
* `packages/`: Optional directory for local Python packages.

Truss uses this structure to build and deploy your model automatically. You
define your model in `model.py` and your infrastructure in `config.yaml`, no
Dockerfiles or container management required.

***

## Implement model code

Replace the contents of `model/model.py` with the following code. This loads [Phi-3-mini-4k-instruct](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct) using the `transformers` library and PyTorch:

```python model/model.py theme={"system"}
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class Model:
    def __init__(self, **kwargs):
        self._model = None
        self._tokenizer = None

    def load(self):
        self._model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct",
            device_map="cuda",
            torch_dtype="auto"
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct"
        )

    def predict(self, request):
        messages = request.pop("messages")
        model_inputs = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(model_inputs, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self._model.generate(input_ids=inputs["input_ids"], max_length=256)
        return {"output": self._tokenizer.decode(outputs[0], skip_special_tokens=True)}
```

Truss models follow a three-method pattern that separates initialization from inference:

| Method     | When it's called                     | What to do here                                            |
| ---------- | ------------------------------------ | ---------------------------------------------------------- |
| `__init__` | Once when the class is created       | Initialize variables, store configuration, set secrets.    |
| `load`     | Once at startup, before any requests | Load model weights, tokenizers, and other heavy resources. |
| `predict`  | On every API request                 | Process input, run inference, return response.             |

The `load` method runs during the container's cold start, before your model receives traffic. This keeps expensive operations (like downloading large model weights) out of the request path.

### Understand the request/response flow

The `predict` method receives `request`, a dictionary containing the JSON body from the API call:

```python theme={"system"}
# API call with: {"messages": [{"role": "user", "content": "Hello"}]}
def predict(self, request):
    messages = request.pop("messages")  # Extract from request
    # ... run inference ...
    return {"output": result}  # Return dict becomes JSON response
```

Whatever dictionary you return becomes the API response. You control the input parameters and output format.

### GPU and memory patterns

A few patterns in this code are common across GPU models:

* **`device_map="cuda"`**: Loads model weights directly to GPU.
* **`.to("cuda")`**: Moves input tensors to GPU for inference.
* **`torch.no_grad()`**: Disables gradient tracking to save memory (gradients aren't needed for inference).

***

## Configure dependencies and GPU

The `config.yaml` file defines your model's environment and compute resources.

### Set Python version and dependencies

```yaml config.yaml theme={"system"}
python_version: py311
requirements:
  - six==1.17.0
  - accelerate==0.30.1
  - einops==0.8.0
  - transformers==4.41.2
  - torch==2.3.0
```

**Key configuration options:**

| Field             | Purpose                                   | Example                           |
| ----------------- | ----------------------------------------- | --------------------------------- |
| `python_version`  | Python version for your container.        | `py39`, `py310`, `py311`, `py312` |
| `requirements`    | Python packages to install (pip format).  | `torch==2.3.0`                    |
| `system_packages` | System-level dependencies (apt packages). | `ffmpeg`, `libsm6`                |

For the complete list of configuration options, see the [Truss reference config](/reference/truss-configuration).

<Note>
  Always pin exact versions (such as `torch==2.3.0`, not `torch>=2.0`). This ensures reproducible builds and your model behaves the same way every time it's deployed.
</Note>

### Allocate a GPU

The `resources` section specifies what hardware your model runs on:

```yaml config.yaml theme={"system"}
resources:
  accelerator: T4
  use_gpu: true
```

Match your GPU to your model's VRAM requirements. For Phi-3-mini (approximately 7.6 GB), a T4 (16 GB) provides headroom for inference.

| GPU  | VRAM     | Good for                                     |
| ---- | -------- | -------------------------------------------- |
| T4   | 16 GB    | Small models, embeddings, fine-tuned models. |
| L4   | 24 GB    | Medium models (7B parameters).               |
| A10G | 24 GB    | Medium models, image generation.             |
| A100 | 40/80 GB | Large models (13B-70B parameters).           |
| H100 | 80 GB    | Very large models, high throughput.          |

<Tip>
  A rough rule for estimating VRAM: 2 GB per billion parameters for float16 models. A 7B model needs approximately 14 GB VRAM minimum.
</Tip>

***

## Deploy the model

Push your model to Baseten:

```sh theme={"system"}
truss push --watch
```

You should see:

```output theme={"system"}
✨ Model Phi 3 Mini was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

`truss push` prints your model ID (for example, `abc1d2ef`). You'll need it to call the model's API. You can also find it in your [Baseten dashboard](https://app.baseten.co/models/).

***

## Call the model API

After the deployment shows "Active" in the dashboard, call the model API:

<Tabs>
  <Tab title="Truss CLI">
    From your Truss project directory, run:

    ```sh theme={"system"}
    truss predict --data '{"messages": [{"role": "user", "content": "What is AGI?"}]}'
    ```

    You should see:

    ```output theme={"system"}
    Calling predict on development deployment...
    {
      "output": "AGI stands for Artificial General Intelligence..."
    }
    ```

    The Truss CLI uses your saved credentials and automatically targets the correct deployment.
  </Tab>

  <Tab title="cURL">
    Replace `YOUR_MODEL_ID` with your model ID (for example, `abc1d2ef`):

    ```sh theme={"system"}
    curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/development/predict \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"messages": [{"role": "user", "content": "What is AGI?"}]}'
    ```

    You should see:

    ```output theme={"system"}
    {"output": "AGI stands for Artificial General Intelligence..."}
    ```
  </Tab>

  <Tab title="Python">
    Replace `YOUR_MODEL_ID` with your model ID:

    ```python main.py theme={"system"}
    import requests
    import os

    model_id = "YOUR_MODEL_ID"  # Replace with your model ID (for example, "abc1d2ef")
    baseten_api_key = os.environ["BASETEN_API_KEY"]

    resp = requests.post(
        f"https://model-{model_id}.api.baseten.co/development/predict",
        headers={"Authorization": f"Bearer {baseten_api_key}"},
        json={
            "messages": [
                {"role": "user", "content": "What is AGI?"}
            ]
        }
    )

    print(resp.json())
    ```

    You should see:

    ```output theme={"system"}
    {"output": "AGI stands for Artificial General Intelligence..."}
    ```
  </Tab>
</Tabs>

***

## Use live reload for development

To avoid long deploy times when testing changes, use live reload:

```sh theme={"system"}
truss watch
```

You should see:

```output theme={"system"}
   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
🚰 Attempting to sync truss with remote
No changes observed, skipping patching.
👀 Watching for changes to truss...
```

When you save changes to `model.py`, Truss automatically patches the deployed model:

```output theme={"system"}
Changes detected, creating patch...
Created patch to update model code file: model/model.py
Model Phi 3 Mini patched successfully.
```

This saves time by patching only the updated code without rebuilding Docker containers or restarting the model server.

***

## Promote to production

Once you're happy with the model, deploy it to production:

```sh theme={"system"}
truss push --promote
```

This changes the API endpoint from `/development/predict` to `/production/predict`:

```sh theme={"system"}
curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/production/predict \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is AGI?"}]}'
```

<Tip>
  Your model ID is printed in the `truss push` output. You can also find it in your [Baseten dashboard](https://app.baseten.co/models/).
</Tip>

***

## Next steps

<CardGroup>
  <Card title="Model configuration" icon="gear" href="/development/model/configuration">
    Full reference for dependencies, secrets, resources, and deployment settings.
  </Card>

  <Card title="Model implementation" icon="code" href="/development/model/model-class">
    Core `Model` lifecycle, method signatures, and sync vs. async inference patterns.
  </Card>

  <Card title="HTTP endpoints" icon="message" href="/development/model/streaming-and-endpoints#v1-endpoints">
    Add `chat_completions`, `completions`, `embeddings`, `messages`, or `responses` when custom model code should serve matching HTTP routes.
  </Card>

  <Card title="Streaming output" icon="bolt" href="/development/model/streaming-and-endpoints#streaming">
    Return generated tokens incrementally for lower perceived latency.
  </Card>

  <Card title="Custom health checks" icon="heart-pulse" href="/development/model/health-checks">
    Configure probe thresholds and define custom readiness or liveness logic.
  </Card>

  <Card title="Autoscaling" icon="arrows-up-down" href="/deployment/autoscaling/overview">
    Scale GPU replicas based on demand with configurable concurrency targets.
  </Card>

  <Card title="Deploy your first model" icon="cube" href="/examples/deploy-your-first-model">
    Deploy a model with just a config file, no custom Python needed.
  </Card>
</CardGroup>
