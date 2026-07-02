# Transcribe Pre-Recorded Audio
Source: https://docs.baseten.co/reference/inference-api/predict-endpoints/transcription-api

POST https://model-{model_id}.api.baseten.co/production/predict
Transcribe a pre-recorded audio file using a deployed transcription model.

Use this endpoint to call the [production environment](/deployment/environments) of your model.

```sh theme={"system"}
https://model-{model_id}.api.baseten.co/environments/production/predict
```

**If you are deploying this model as a chain**, you can call it in the following way

```sh theme={"system"}
https://chain-{chain_id}.api.baseten.co/environments/production/run_remote
```

### Parameters

<ParamField type="string">
  The ID of the model you want to call.
</ParamField>

<ParamField type="string">
  Your Baseten API key, passed as `Authorization: Bearer $BASETEN_API_KEY`. `Api-Key` is also accepted as the scheme.
</ParamField>

### Body

<ParamField type="object">
  The audio input options. You must provide one of `url`, `audio_b64`, or `audio_bytes`.

  * **url** (`string`): URL of the audio file.
  * **audio\_b64** (`string`): Base64-encoded audio content.
  * **audio\_bytes** (`bytes`): Raw audio bytes.

  <Warning>
    Request bodies are capped at [100 MB](/reference/inference-api/overview#request-size). For larger files, pass a URL through `audio.url` instead of inlining with `audio_b64` or `audio_bytes`.
  </Warning>
</ParamField>

<ParamField type="object">
  Parameters for controlling Whisper's behavior.

  * **prompt** (`string`, optional): Optional transcription prompt.
  * **audio\_language** (`string`, default=`"en"`): Language of the input audio. Set to `"auto"` for automatic detection.
  * **language\_detection\_only** (`boolean`, default=`false`): If `true`, only return the automatic language detection result without transcribing.
  * **language\_options** (`list[string]`, default=`[]`): List of language codes to consider for language detection, for example `["en", "zh"]`. This could improve language detection accuracy by scoping the language detection to a specific set of languages that only makes sense for your use case. By default, we consider [all languages](https://platform.openai.com/docs/guides/speech-to-text#supported-languages) supported by Whisper model. <span>\[Added since v0.5.0]</span>
  * **use\_dynamic\_preprocessing** (`boolean`, default=`false`): Enables dynamic range compression to process audio with variable loudness.
  * **show\_word\_timestamps** (`boolean`, default=`false`): If `true`, include word-level timestamps in the output. <span>\[Added since v0.4.0]</span>
  * **enable\_vad** (`boolean`, default=`true`): If `true`, enable audio chunking by voice activity detection (VAD) model. If `false`, the model can only process up to 30 seconds of audio at a time. <span>\[Added since v0.6.0]</span>
  * **show\_beam\_results** (`boolean`, default=`false`): If `true`, include transcriptions from all beams of beam search in the response. <span>\[Added since v0.7.5]</span>
  * **enable\_chunk\_level\_language\_detection** (`boolean`, default=`false`): If `true`, language detection is performed at the chunk/segment level instead of file level. <span>\[Added since v0.7.6]</span>
</ParamField>

<ParamField type="object">
  Advanced parameters for controlling Whisper's sampling behavior.

  * **beam\_width** (`integer`, optional): Beam search width for decoding. Controls the number of candidate sequences to maintain during beam search. <span>\[Added since v0.6.0]</span>
  * **length\_penalty** (`float`, optional): Length penalty applied to the output. Higher values encourage longer outputs. <span>\[Added since v0.6.0]</span>
  * **repetition\_penalty** (`float`, optional): Penalty for repeating tokens. Higher values discourage repetition. <span>\[Added since v0.6.0]</span>
  * **beam\_search\_diversity\_rate** (`float`, optional): Controls diversity in beam search. Higher values increase diversity among beam candidates. <span>\[Added since v0.6.0]</span>
  * **no\_repeat\_ngram\_size** (`integer`, optional): Prevents repetition of n-grams of the specified size. <span>\[Added since v0.6.0]</span>
</ParamField>

<ParamField type="object">
  Advanced settings for automatic speech recognition (ASR) process.

  * **beam\_size** (`integer`, default=`1`): Beam search size for decoding. We support beam size up to 5. <span>\[Deprecated since v0.6.0. Use `whisper_input.whisper_params.whisper_sampling_params.beam_width` instead.]</span>
  * **length\_penalty** (`float`, default=`2.0`): Length penalty applied to ASR output. Length penalty can only work when `beam_size` is greater than 1. <span>\[Deprecated since v0.6.0. Use `whisper_input.whisper_params.whisper_sampling_params.length_penalty` instead.]</span>
</ParamField>

<ParamField type="object">
  Parameters for controlling voice activity detection (VAD) process.

  * **max\_speech\_duration\_s** (`integer`, default=`29`): Maximum duration of speech in seconds to be considered a speech segment. `max_speech_duration_s` cannot be over 30 because Whisper model can only take up to 30 seconds audio input. <span>\[Added since v0.4.0]</span>
  * **min\_silence\_duration\_ms** (`integer`, default=`3000`): In the end of each speech chunk wait for min\_silence\_duration\_ms before separating it. <span>\[Added since v0.4.0]</span>
  * **threshold** (`float`, default=`0.5`): Speech threshold. VAD outputs speech probabilities for each audio chunk, probabilities above this value are considered as speech. It is better to tune this parameter for each dataset separately, but "lazy" 0.5 is pretty good for most datasets. <span>\[Added since v0.4.0]</span>
</ParamField>

<RequestExample>
  ```python Python theme={"system"}
  import os
  import requests

  model_id = ""

  # Read secrets from environment variables
  baseten_api_key = os.environ["BASETEN_API_KEY"]

  # Define the request payload
  payload = {
      "whisper_input": {
          "audio": {
              "url": "https://example.com/audio.wav",  # Replace with actual URL
              # "audio_b64": "BASE64_ENCODED_AUDIO",   # Uncomment if using Base64
          },
          "whisper_params": {
              "prompt": "Optional transcription prompt",
              "audio_language": "en",
          },
      },
  }

  resp = requests.post(
      f"https://model-{model_id}.api.baseten.co/environments/production/predict",
      headers={"Authorization": f"Bearer {baseten_api_key}"},
      json=payload,
  )

  print(resp.json())
  ```

  ```sh cURL theme={"system"}
  curl -X POST https://model-{model_id}.api.baseten.co/environments/production/predict \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "whisper_input": {
        "audio": {
          "url": "https://example.com/audio.mp3"
        },
        "whisper_params": {
          "prompt": "Optional transcription prompt",
          "audio_language": "en"
        }
      }
    }'

  ```

  ```javascript Node.js theme={"system"}
  const fetch = require("node-fetch");

  const modelId = "";
  const apiKey = process.env.BASETEN_API_KEY;

  const payload = {
    whisper_input: {
      audio: {
        url: "https://example.com/audio.mp3",
      },
      whisper_params: {
        prompt: "Optional transcription prompt",
        audio_language: "en",
      },
    },
  };

  const resp = await fetch(
    `https://model-${modelId}.api.baseten.co/environments/production/predict`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  const data = await resp.json();
  console.log(data);
  ```
</RequestExample>

<ResponseExample>
  ```json Example Response theme={"system"}
  {
    "language_code": "en",
    "language_prob": null,
    "segments": [
      {
        "text": "That's one small step for man, one giant leap for mankind.",
        "log_prob": -0.8644908666610718,
        "start_time": 0,
        "end_time": 9.92
      }
    ]
  }
  ```
</ResponseExample>
