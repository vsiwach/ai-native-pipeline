# Named entity recognition
Source: https://docs.baseten.co/engines/bei/ner

Token-level entity classification on BEI-Bert with /predict_tokens

Named entity recognition (NER) classifies each token in an input string into entity categories such as person (`PER`), organization (`ORG`), location (`LOC`), and miscellaneous (`MISC`). NER models use the `ForTokenClassification` architecture and the `/predict_tokens` endpoint. NER requires BEI-Bert (`base_model: encoder_bert`); BEI does not support token-level outputs.

## Recommended models

* `dslim/bert-base-NER-uncased`: fast, compact NER for English. ([Truss example](https://github.com/basetenlabs/truss-examples/tree/main/custom-server/BEI-Bert-dslim-bert-base-ner-uncased))
* `tanaos/tanaos-NER-v1`: general-purpose NER.

## Configuration

Add to `config.yaml`:

```yaml theme={"system"}
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "baseten-admin/bert-base-ner-uncased"
      revision: main
    max_num_tokens: 16384
  runtime:
    webserver_default_route: /predict_tokens
```

## Request format

```json theme={"system"}
{
  "inputs": [["Apple is looking at buying U.K. startup for $1 billion"]],
  "truncate": true,
  "raw_scores": false,
  "aggregation_strategy": "max"
}
```

| Field                  | Type                    | Description                                                                                                                                                                                                                            |
| ---------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `inputs`               | list of list of strings | Batched text inputs to classify. Each inner list is a batch of texts.                                                                                                                                                                  |
| `raw_scores`           | boolean                 | When `true`, returns raw logit scores for all labels per token. When `false`, returns the top predicted label with its probability.                                                                                                    |
| `truncate`             | boolean                 | Truncates inputs that exceed the model's max sequence length.                                                                                                                                                                          |
| `truncation_direction` | string                  | Controls which end is truncated. Defaults to `"Right"`.                                                                                                                                                                                |
| `aggregation_strategy` | string                  | Merges sub-word tokens into entity spans. Accepts `"none"`, `"simple"`, `"first"`, `"average"`, or `"max"`. Use `"max"` to match `transformers.pipeline("ner", aggregation_strategy="max")`. Use `"none"` for token-level predictions. |

## Response format

With `aggregation_strategy: "max"` (recommended for production):

```json theme={"system"}
[
  [
    {"token": "Apple", "token_id": 0, "start": 0, "end": 5, "results": {"ORG": 0.9975586}},
    {"token": "U.K.", "token_id": 0, "start": 27, "end": 31, "results": {"LOC": 0.9980469}}
  ]
]
```

With `aggregation_strategy: "none"` and `raw_scores: true` (token-level with BIO labels):

```json theme={"system"}
[
  [
    {
      "token": "Apple",
      "token_id": 6207,
      "start": 0,
      "end": 5,
      "results": {
        "B-ORG": 6.7578125,
        "O": -1.7929688,
        "B-LOC": 0.6015625,
        "B-MISC": 0.2467041,
        "B-PER": 0.17675781,
        "I-ORG": -0.6484375,
        "I-MISC": -1.9873047,
        "I-LOC": -1.3808594,
        "I-PER": -2.21875
      }
    }
  ]
]
```

Token-level labels follow the [BIO tagging scheme](https://en.wikipedia.org/wiki/Inside%E2%80%93outside%E2%80%93beginning_\(tagging\)): `B-` marks the beginning of an entity, `I-` marks a continuation, and `O` means outside any entity.

## Python example

Using the Baseten [Performance Client](/inference/performance-client):

```python theme={"system"}
from baseten_performance_client import PerformanceClient
import os

client = PerformanceClient(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync"
)

response = client.batch_post(
    url_path="/predict_tokens",
    payloads=[{
        "inputs": [["Apple is looking at buying U.K. startup for $1 billion"]],
        "truncate": True,
        "raw_scores": False,
        "aggregation_strategy": "max"
    }]
)

for entity in response.data[0]:
    label = next(iter(entity["results"]))
    score = entity["results"][label]
    print(f"{entity['token']}: {label} ({score:.4f})")
```

NER models do not expose an OpenAI-compatible endpoint. Call `/predict_tokens` directly. The route also supports [async inference](/inference/async).

## Related

* [BEI-Bert overview](/engines/bei/bei-bert): Bidirectional encoder engine that hosts NER deployments.
* [BEI configuration reference](/engines/bei/bei-reference): Full `trt_llm` schema for build and runtime fields.
