# Build and deploy an LLM
Source: https://docs.baseten.co/examples/deploy-a-llm

Package and deploy an LLM with Truss, from model setup to inference.

<Card title="View example on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/02-llm" />

This guide walks through deploying Mistral-7B, a powerful large language model (LLM), using Truss. You'll configure the model, set up inference, allocate resources, and deploy it as an API endpoint.

# Set up your model

Start by importing the necessary libraries:

```python model/model.py theme={"system"}
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
```

Specify the Hugging Face model checkpoint:

```python model/model.py theme={"system"}
CHECKPOINT = "mistralai/Mistral-7B-v0.1"

```

# Define the model class

Create a `Model` class that loads Mistral-7B and its tokenizer when the server starts:

```python model/model.py theme={"system"}
class Model:
    def __init__(self, **kwargs) -> None:
        self.tokenizer = None
        self.model = None

    def load(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            CHECKPOINT, torch_dtype=torch.float16, device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
```

# Implement inference

The `predict` function handles inference by tokenizing input, generating text, and decoding the output.

```python model/model.py theme={"system"}
    def predict(self, request: dict):
        prompt = request.pop("prompt")
        generate_args = {
            "max_new_tokens": request.get("max_new_tokens", 128),
            "temperature": request.get("temperature", 1.0),
            "top_p": request.get("top_p", 0.95),
            "top_k": request.get("top_k", 50),
            "repetition_penalty": 1.0,
            "use_cache": True,
            "do_sample": True,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }

        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.cuda()

        with torch.no_grad():
            output = self.model.generate(input_ids=input_ids, **generate_args)
            return self.tokenizer.decode(output[0])
```

# Configure your deployment

## Define dependencies

Specify the necessary Python packages in `config.yaml`:

```yaml config.yaml theme={"system"}
model_name: Mistral 7B
python_version: py311
requirements:
  - transformers==4.42.3
  - sentencepiece==0.1.99
  - accelerate==0.23.0
  - torch==2.0.1
  - numpy==1.26.4
```

## Allocate compute resources

Mistral-7B requires an NVIDIA A10G GPU for efficient inference:

```yaml config.yaml theme={"system"}
resources:
  accelerator: A10G
  use_gpu: true
```

# Deploy the model

Push your Truss to Baseten:

```bash theme={"system"}
$ truss push
```

Once deployed, call the model using the Truss CLI:

```bash theme={"system"}
$ truss predict --published -d '{"prompt": "What is a large language model?"}'
```

Or send a request to the API endpoint:

```python theme={"system"}
import requests

response = requests.post(
    "https://model-{yourmodelid}.api.baseten.co/production/predict",
    headers={"Authorization": "Bearer EMPTY"},
    json={"prompt": "Explain quantum computing in simple terms"}
)

print(response.json())
```

# Check for optimized engine support

For optimized performance we have open-source and Baseten optimized engines, such as Baseten's TensorRT-LLM, Baseten-Embeddings-Inference, vLLM and SGLang.
