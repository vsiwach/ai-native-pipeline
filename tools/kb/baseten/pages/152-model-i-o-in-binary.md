# Model I/O in binary
Source: https://docs.baseten.co/inference/output-format/binary

Decode and save binary model output

Baseten and Truss natively support model I/O in binary and use msgpack encoding for efficiency.

## Deploy a basic Truss for binary I/O

If you need a deployed model to try the invocation examples below, follow these steps to create and deploy a minimal Truss that accepts and returns binary data. The Truss performs no operations and is purely illustrative.

<Accordion title="Steps for deploying an example Truss">
  <Steps>
    <Step title="Create a Truss">
      To create a Truss, run:

      ```sh Terminal theme={"system"}
      truss init binary_test
      ```

      This creates a Truss in a new directory `binary_test`. By default, newly created Trusses implement an identity function that returns the exact input they are given.
    </Step>

    <Step title="Add logging">
      Optionally, modify `binary_test/model/model.py` to log that the data received is of type `bytes`:

      ```python binary_test/model/model.py theme={"system"}
      def predict(self, model_input):
          # Run model inference here
          print(f"Input type: {type(model_input['byte_data'])}")
          return model_input
      ```
    </Step>

    <Step title="Deploy the Truss">
      Deploy the Truss to Baseten with:

      ```sh Terminal theme={"system"}
      truss push --watch
      ```
    </Step>
  </Steps>
</Accordion>

## Send raw bytes as model input

To send binary data as model input:

1. Set the `content-type` HTTP header to `application/octet-stream`
2. Use `msgpack` to encode the data or file
3. Make a POST request to the model

This code sample assumes you have a file `Gettysburg.mp3` in the current working directory. You can download the [11-second file from our CDN](https://cdn.baseten.co/docs/production/Gettysburg.mp3) or replace it with your own file.

```python call_model.py theme={"system"}
import os
import requests
import msgpack


model_id = "MODEL_ID"  # Replace this with your model ID
deployment = "development"  # `development`, `production`, or a deployment ID
baseten_api_key = os.environ["BASETEN_API_KEY"]
# Specify the URL to which you want to send the POST request
url = f"https://model-{model_id}.api.baseten.co/{deployment}/predict"
headers={
    "Authorization": f"Bearer {baseten_api_key}",
    "content-type": "application/octet-stream",
}

with open('Gettysburg.mp3', 'rb') as file:
    response = requests.post(
        url,
        headers=headers,
        data=msgpack.packb({'byte_data': file.read()})
    )

print(response.status_code)
print(response.headers)
```

<Note>
  To support certain types like numpy and datetime values, you may need to
  extend client-side `msgpack` encoding with the same [encoder and decoder used
  by
  Truss](https://github.com/basetenlabs/truss/blob/main/truss/templates/shared/serialization.py).
</Note>

## Parse raw bytes from model output

To use the output of a non-streaming model response, decode the response content:

```python call_model.py theme={"system"}
# Continues `call_model.py` from above

binary_output = msgpack.unpackb(response.content)

# Change extension if not working with mp3 data
with open('output.mp3', 'wb') as file:
    file.write(binary_output["byte_data"])
```

## Streaming binary outputs

You can also stream output as binary. This is useful for sending large files or reading binary output as it is generated.

In the `model.py`, you must create a streaming output.

```python model/model.py theme={"system"}
# Replace the predict function in your Truss
def predict(self, model_input):
    import os

    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "tmpfile.txt")
    with open(file_path, mode="wb") as file:
            file.write(bytes(model_input["text"], encoding="utf-8"))

    def iterfile():
        # Get the directory of the current file
        current_dir = os.path.dirname(__file__)
        # Construct the full path to the .wav file
        file_path = os.path.join(current_dir, "tmpfile.txt")
        with open(file_path, mode="rb") as file_like:
            yield from file_like

    return iterfile()
```

Then, in your client, use the streaming output directly without decoding:

```python stream_model.py theme={"system"}
import os
import requests
import json

model_id = "MODEL_ID"  # Replace this with your model ID
deployment = "development"  # `development`, `production`, or a deployment ID
baseten_api_key = os.environ["BASETEN_API_KEY"]
# Specify the URL to which you want to send the POST request
url = f"https://model-{model_id}.api.baseten.co/{deployment}/predict"
headers={
    "Authorization": f"Bearer {baseten_api_key}",
}

s = requests.Session()
with s.post(
    # Endpoint for production deployment, see API reference for more
    f"https://model-{model_id}.api.baseten.co/{deployment}/predict",
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    data=json.dumps({"text": "Lorem Ipsum"}),
    # Include stream=True as an argument so the requests library knows to stream
    stream=True,
) as response:
    for token in response.iter_content(1):
        print(token) # Prints bytes
```

## Next steps

<CardGroup>
  <Card title="File I/O" icon="file" href="/inference/output-format/files">
    Pass files and URLs as model input and save output to disk
  </Card>

  <Card title="Streaming" icon="bolt" href="/inference/streaming">
    Stream text responses token by token
  </Card>
</CardGroup>
