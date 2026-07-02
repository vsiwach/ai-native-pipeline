# Add system packages
Source: https://docs.baseten.co/examples/system-packages

Deploy a model with both Python and system dependencies.

<Card title="View example on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/10-using-system-packages" />

In this example, we build a Truss with a model that requires specific system packages.

To add system packages to your model serving environment, open `config.yaml` and
update the `system_packages` key with a list of apt-installable Debian packages:

```yaml config.yaml theme={"system"}
system_packages:
  - tesseract-ocr
```

For this example, we use the [LayoutLM Document QA](https://huggingface.co/impira/layoutlm-document-qa) model,
a multimodal model that answers questions about provided invoice documents. This model requires a system
package, tesseract-ocr, which needs to be included in the model serving environment.

# Set up the model.py

For this model, we use the HuggingFace transformers library, and the document-question-answering task.

```python model/model.py theme={"system"}
from transformers import pipeline


class Model:
    def __init__(self, **kwargs) -> None:
        self._model = None

    def load(self):
        self._model = pipeline(
            "document-question-answering",
            model="impira/layoutlm-document-qa",
        )

    def predict(self, model_input):
        return self._model(model_input["url"], model_input["prompt"])
```

# Set up the config.yaml file

The main items that need to be configured in `config.yaml` are the `requirements`
and `system_packages` sections.

<Note>
  Pin exact versions for your Python dependencies so a new release can't
  introduce a breaking change between deploys.
</Note>

```yaml config.yaml theme={"system"}
environment_variables: {}
external_package_dirs: []
model_metadata:
  example_model_input:
    {
      "url": "https://templates.invoicehome.com/invoice-template-us-neat-750px.png",
      "prompt": "What is the invoice number?",
    }
model_name: LayoutLM Document QA
python_version: py39
requirements:
  - Pillow==10.0.0
  - pytesseract==0.3.10
  - torch==2.0.1
  - transformers==4.30.2
resources:
  cpu: "4"
  memory: 16Gi
  use_gpu: false
  accelerator: null
secrets: {}
system_packages:
  - tesseract-ocr
```

# Deploy the model

From the Truss directory, deploy the model with:

```bash theme={"system"}
$ truss push ./my-truss
```

You can then invoke the model with:

```bash theme={"system"}
$ truss predict --published -d '{"url": "https://templates.invoicehome.com/invoice-template-us-neat-750px.png", "prompt": "What is the invoice number?"}'
```
