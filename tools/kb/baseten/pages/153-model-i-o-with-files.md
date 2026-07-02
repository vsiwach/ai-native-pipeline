# Model I/O with files
Source: https://docs.baseten.co/inference/output-format/files

Call models by passing a file or URL

Baseten supports file-based input and output during inference, whether the file is local or remote and whether you handle it in the Truss or in your client code.

## Files as input

### Send a file with JSON-serializable content

The Truss CLI has a `-f` flag to pass file input. If you're using the API endpoint from Python, get file contents with the standard `f.read()` function.

<CodeGroup>
  ```sh Truss CLI theme={"system"}
  truss predict -f input.json
  ```

  ```python call_model.py theme={"system"}
  import os
  import json
  import requests

  model_id = ""
  # Read secrets from environment variables
  baseten_api_key = os.environ["BASETEN_API_KEY"]

  # Read input as JSON
  with open("input.json", "r") as f:
      data = json.load(f)

  resp = requests.post(
      # Endpoint for production deployment, see API reference for more
      f"https://model-{model_id}.api.baseten.co/production/predict",
      headers={"Authorization": f"Bearer {baseten_api_key}"},
      json=data,
  )

  print(resp.json())
  ```
</CodeGroup>

### Send a file with non-serializable content

The `-f` flag for `truss predict` only applies to JSON-serializable content. For other files, like the audio files required by MusicGen Melody, base64-encode the file content before you send it:

```python call_model.py theme={"system"}
import os
import base64
import requests

model_id = ""
# Read secrets from environment variables
baseten_api_key = os.environ["BASETEN_API_KEY"]

# Open a local file and base64-encode it (mono WAV, 48kHz sample rate)
with open("mymelody.wav", "rb") as f:
    encoded_str = base64.b64encode(f.read()).decode("utf-8")

# Build a JSON-serializable payload
data = {"prompts": ["happy rock", "energetic EDM", "sad jazz"], "melody": encoded_str, "duration": 8}

resp = requests.post(
    # Endpoint for production deployment, see API reference for more
    f"https://model-{model_id}.api.baseten.co/production/predict",
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json=data,
)

# Decode the base64 audio clips in the response and save them
for idx, clip in enumerate(resp.json()["data"]):
    with open(f"clip_{idx}.wav", "wb") as f:
        f.write(base64.b64decode(clip))
```

### Send a URL to a public file

Rather than encoding and serializing a file to send in the HTTP request, write a Truss that takes a URL as input and loads the content in the `preprocess()` function. Here's an example from [Whisper in the model library](https://www.baseten.co/library/whisper/):

```python model/model.py theme={"system"}
from tempfile import NamedTemporaryFile
import requests

# Get file content without blocking GPU
def preprocess(self, request):
    resp = requests.get(request["url"])
    return {"content": resp.content}

# Use file content in model inference
def predict(self, model_input):
    with NamedTemporaryFile() as fp:
        fp.write(model_input["content"])
        result = whisper.transcribe(
            self._model,
            fp.name,
            temperature=0,
            best_of=5,
            beam_size=5,
        )
        segments = [
            {"start": r["start"], "end": r["end"], "text": r["text"]}
            for r in result["segments"]
        ]
    return {
        "language": whisper.tokenizer.LANGUAGES[result["language"]],
        "segments": segments,
        "text": result["text"],
    }
```

## Files as output

### Save model output to a local file

Saving model output to a local file needs no Baseten-specific code. Use the standard `>` operator in bash or the `file.write()` function in Python:

<CodeGroup>
  ```sh Truss CLI theme={"system"}
  truss predict -d '"Model input!"' > output.json
  ```

  ```python call_model.py theme={"system"}
  import os
  import json
  import requests

  model_id = ""
  # Read secrets from environment variables
  baseten_api_key = os.environ["BASETEN_API_KEY"]

  # Call model
  resp = requests.post(
      # Endpoint for production deployment, see API reference for more
      f"https://model-{model_id}.api.baseten.co/production/predict",
      headers={"Authorization": f"Bearer {baseten_api_key}"},
      json="Model input!",
  )
  # Serialize the JSON response and write it to file
  with open("output.json", "w") as f:
      f.write(json.dumps(resp.json()))
  ```
</CodeGroup>

Output for some models, like image and audio generation models, may need to be decoded before you save it. See our [image generation example](/examples/image-generation) for how to parse base64 output.
