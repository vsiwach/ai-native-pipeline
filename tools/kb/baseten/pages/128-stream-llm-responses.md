# Stream LLM responses
Source: https://docs.baseten.co/examples/streaming

Stream LLM output token by token.

<Card title="View on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/qwen/qwen-7b-chat" />

In this example, we go through a Truss that serves the Qwen 7B Chat LLM, and streams the output to the client.

# Why streaming?

LLMs generate tokens in sequence, so you can return useful output to users before the full response is
ready. Truss supports streaming output to do this.

# Set up the imports

In this example, we use the HuggingFace transformers library to build a text generation model.

```python model/model.py theme={"system"}
from threading import Thread
from typing import Dict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from transformers.generation import GenerationConfig
```

# Define the load function

In the `load` function of the Truss, we implement logic
involved in downloading the chat version of the Qwen 7B model and loading it into memory.

```python model/model.py theme={"system"}
class Model:
    def __init__(self, **kwargs):
        self.model = None
        self.tokenizer = None

    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen-7B-Chat", trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen-7B-Chat", device_map="auto", trust_remote_code=True
        ).eval()
```

# Define the preprocess function

In the `preprocess` function of the Truss, we set up a `generate_args` dictionary with some generation arguments from the inference request to be used in the `predict` function.

```python model/model.py theme={"system"}
    def preprocess(self, request: dict) -> dict:
        generate_args = {
            "max_new_tokens": request.get("max_new_tokens", 512),
            "temperature": request.get("temperature", 0.5),
            "top_p": request.get("top_p", 0.95),
            "top_k": request.get("top_k", 40),
            "repetition_penalty": 1.0,
            "no_repeat_ngram_size": 0,
            "use_cache": True,
            "do_sample": True,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        request["generate_args"] = generate_args
        return request
```

# Define the predict function

In the `predict` function of the Truss, we implement the actual
inference logic.

The two main steps are:

* Tokenize the input
* Call the model's `generate` function if we're not streaming the output, otherwise call the `stream` helper function

```python model/model.py theme={"system"}
    def predict(self, request: Dict):
        stream = request.pop("stream", False)
        prompt = request.pop("prompt")
        generation_args = request.pop("generate_args")
        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.cuda()

        if stream:
            return self.stream(input_ids, generation_args)

        with torch.no_grad():
            output = self.model.generate(inputs=input_ids, **generation_args)
            return self.tokenizer.decode(output[0])
```

## Define the `stream` helper function

In this helper function, we'll instantiate the `TextIteratorStreamer` object, which we'll later use for
returning the LLM output to users.

```python model/model.py theme={"system"}
    def stream(self, input_ids: list, generation_args: dict):
        streamer = TextIteratorStreamer(self.tokenizer)
```

When creating the generation parameters, ensure to pass the `streamer` object
that we created previously.

```python model/model.py theme={"system"}
        generation_config = GenerationConfig(**generation_args)
        generation_kwargs = {
            "input_ids": input_ids,
            "generation_config": generation_config,
            "return_dict_in_generate": True,
            "output_scores": True,
            "max_new_tokens": generation_args["max_new_tokens"],
            "streamer": streamer,
        }
```

Spawn a thread to run the generation, so that it does not block the main
thread.

```python model/model.py theme={"system"}
        with torch.no_grad():
            # Begin generation in a separate thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
```

In Truss, the way to achieve streaming output is to return a generator
that yields content. In this example, we yield the output of the `streamer`,
which produces output and yields it until the generation is complete.

We define this `inner` function to create our generator.

```python model/model.py theme={"system"}
            # Yield generated text as it becomes available
            def inner():
                for text in streamer:
                    yield text
                thread.join()
        return inner()
```

# Set up the `config.yaml`

Running Qwen 7B requires torch, transformers,
and a few other related libraries.

```yaml config.yaml theme={"system"}
model_name: qwen-7b-chat
model_metadata:
  example_model_input:
    prompt: What is the meaning of life?
requirements:
  - accelerate==0.23.0
  - tiktoken==0.5.1
  - einops==0.6.1
  - scipy==1.11.3
  - transformers_stream_generator==0.0.4
  - peft==0.5.0
  - deepspeed==0.11.1
  - torch==2.0.1
  - transformers==4.32.0
```

## Configure resources for Qwen

We will use an L4 to run this model.

```yaml config.yaml theme={"system"}
resources:
  accelerator: L4
  cpu: "4"
  memory: 16Gi
  use_gpu: true
```

# Deploy Qwen 7B Chat

Deploy the model like you would other Trusses, with:

```bash theme={"system"}
truss push qwen-7b-chat
```
