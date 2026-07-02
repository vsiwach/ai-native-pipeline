# Transcribe streaming audio
Source: https://docs.baseten.co/reference/inference-api/predict-endpoints/streaming-transcription-api

Transcribe audio in real time over a WebSocket connection.

The streaming audio transcription endpoint is **ONLY** compatible with **websockets** not with the REST API.

To begin using the transcription endpoint, establish a connection over WebSocket. Once connected, you must first send a metadata JSON object (as a string) over the WebSocket. This metadata informs the model about the format and type of audio data it should expect.

After the metadata is sent, you can begin streaming raw audio bytes directly over the same WebSocket connection.

```sh theme={"system"}
wss://model-{model_id}.api.baseten.co/environments/production/websocket
```

### Parameters

<ParamField type="string">
  The ID of the model you want to call.
</ParamField>

<ParamField type="string">
  Your Baseten API key, passed as `Authorization: Bearer $BASETEN_API_KEY`. `Api-Key` is also accepted as the scheme.
</ParamField>

### Websocket Metadata

<ParamField type="object">
  These parameters configure the Voice Activity Detector (VAD) and allow you to tune behavior such as speech endpointing.

  * **threshold** (`float`, default=`0.5`): The probability threshold for detecting speech, between 0.0 and 1.0. Frames with a probability above this value are considered speech. A higher threshold makes the VAD more selective, reducing false positives from background noise.
  * **min\_silence\_duration\_ms** (`int`, default=`300`): The minimum duration of silence (in milliseconds) required to determine that speech has ended.
  * **speech\_pad\_ms** (`int`, default=`0`): Padding (in milliseconds) added to both the start and end of detected speech segments to avoid cutting off words prematurely.
</ParamField>

<ParamField type="object">
  Parameters for controlling streaming ASR behavior.

  * **encoding** (`string`, default=`"pcm_s16le"`): Audio encoding format.
  * **sample\_rate** (`int`, default=`16000`): Audio sample rate in Hz. Whisper models are optimized for a sample rate of 16,000 Hz.
  * **enable\_partial\_transcripts** (`boolean`, optional): If set to true, intermediate (partial) transcripts will be sent over the WebSocket as audio is received. For most voice AI use cases, we recommend setting this to `false`.
  * **partial\_transcript\_interval\_s** (`float`, default=`0.5`): Interval in seconds that the model waits before sending a partial transcript, if partials are enabled.
  * **final\_transcript\_max\_duration\_s** (`int`, default=`30`): The maximum duration of buffered audio (in seconds) before a final transcript is forcibly returned. This value should not exceed `30`.
</ParamField>

<ParamField type="object">
  Parameters for controlling Whisper's behavior.

  * **prompt** (`string`, optional): Optional transcription prompt.
  * **audio\_language** (`string`, default=`"en"`): Language of the input audio. Set to `"auto"` for automatic detection.
  * **language\_detection\_only** (`boolean`, default=`false`): If `true`, only return the automatic language detection result without transcribing.
  * **language\_options** (`list[string]`, default=`[]`): List of language codes to consider for language detection, for example `["en", "zh"]`. This could improve language detection accuracy by scoping the language detection to a specific set of languages that only makes sense for your use case. By default, we consider [all languages](https://platform.openai.com/docs/guides/speech-to-text#supported-languages) supported by Whisper model. <span>\[Added since v0.5.0]</span>
  * **use\_dynamic\_preprocessing** (`boolean`, default=`false`): Enables dynamic range compression to process audio with variable loudness.
  * **show\_word\_timestamps** (`boolean`, default=`false`): If `true`, include word-level timestamps in the output. <span>\[Added since v0.4.0]</span>
  * **show\_beam\_results** (`boolean`, default=`false`): If `true`, include transcriptions from all beams of beam search in the response. <span>\[Added since v0.7.5]</span>
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
  <span>Deprecated since v0.6.0.</span> Use `whisper_params.whisper_sampling_params` instead. Specifically, replace `beam_size` with `whisper_params.whisper_sampling_params.beam_width` and `length_penalty` with `whisper_params.whisper_sampling_params.length_penalty`.
</ParamField>

<RequestExample>
  ```python Python theme={"system"}
  import asyncio
  import websockets
  import sounddevice as sd
  import numpy as np
  import json
  import os

  model_id = ""  # Baseten model id here
  baseten_api_key = os.environ["BASETEN_API_KEY"]

  # Audio config
  SAMPLE_RATE = 16000
  CHUNK_SIZE = 512
  CHANNELS = 1

  headers = {"Authorization": f"Bearer {baseten_api_key}"}

  # Metadata to send first
  metadata = {
      "streaming_vad_config": {
          "threshold": 0.5,
          "min_silence_duration_ms": 300,
          "speech_pad_ms": 30
      },
      "streaming_params": {
          "encoding": "pcm_s16le",
          "sample_rate": SAMPLE_RATE,
          "enable_partial_transcripts": True
      },
      "whisper_params": {"audio_language": "en"},
  }

  async def stream_microphone_audio(ws_url):
      loop = asyncio.get_running_loop()
      async with websockets.connect(ws_url, additional_headers=headers) as ws:
          print("Connected to server")

          # Send the metadata JSON blob
          await ws.send(json.dumps(metadata))
          print("Sent metadata to server")

          send_queue = asyncio.Queue()

          # Start audio stream
          def audio_callback(indata, frames, time_info, status):
              if status:
                  print(f"Audio warning: {status}")
              int16_data = (indata * 32767).astype(np.int16).tobytes()
              loop.call_soon_threadsafe(send_queue.put_nowait, int16_data)

          with sd.InputStream(
                  samplerate=SAMPLE_RATE,
                  blocksize=CHUNK_SIZE,
                  channels=CHANNELS,
                  dtype="float32",
                  callback=audio_callback,
          ):
              print("Streaming mic audio...")

              async def send_audio():
                  while True:
                      chunk = await send_queue.get()
                      await ws.send(chunk)

              async def receive_messages():
                  while True:
                      response = await ws.recv()
                      message = json.loads(response)
                      msg_type = message.get("type")

                      if msg_type == "transcription":
                          is_final = message.get("is_final")
                          text = " ".join(s.get("text", "") for s in message.get("segments", []))
                          print(f"[{'final' if is_final else 'partial'}] {text}")
                      else:
                          print(f"[{msg_type}] {message.get('body')}")

              # Run send + receive tasks concurrently
              await asyncio.gather(send_audio(), receive_messages())

  ws_url = f"wss://model-{model_id}.api.baseten.co/environments/production/websocket"
  asyncio.run(stream_microphone_audio(ws_url))
  ```
</RequestExample>

<ResponseExample>
  ```json Example Response theme={"system"}
  {
    "type": "transcription",
    "is_final": true,
    "transcription_num": 4,
    "language_code": "en",
    "language_prob": null,
    "audio_length_sec": 9.92,
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

***

## FAQ

### How do I handle end of audio to avoid losing the last utterance?

By default, the VAD-based endpointing only triggers a transcript when it detects a period of silence after speech. If you close the connection abruptly without signaling end-of-audio, **any speech still buffered that hasn't hit a silence boundary will be lost**.

To flush the buffer and get a final transcript for all remaining audio, send an `end_audio` control message before closing the connection:

```json theme={"system"}
{"type": "end_audio"}
```

The server will:

1. Immediately acknowledge: `{"type": "end_audio", "body": {"status": "acknowledged"}}`
2. Finish transcribing all remaining buffered audio, sending any final transcription results
3. Signal completion: `{"type": "end_audio", "body": {"status": "finished"}}`

After receiving `finished`, it is safe to close the connection.

```python Python theme={"system"}
import asyncio
import signal
import websockets
import sounddevice as sd
import numpy as np
import json
import os

SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms per chunk

headers = {"Authorization": f"Bearer {os.environ['BASETEN_API_KEY']}"}
ws_url = "wss://model-{model_id}.api.baseten.co/environments/production/websocket"
metadata = {
    "streaming_params": {"encoding": "pcm_s16le", "sample_rate": SAMPLE_RATE},
    "whisper_params": {"audio_language": "en"},
}

async def stream_mic():
    loop = asyncio.get_running_loop()
    send_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    def audio_callback(indata, frames, time_info, status):
        loop.call_soon_threadsafe(
            send_queue.put_nowait, (indata * 32767).astype(np.int16).tobytes()
        )

    # Ctrl+C sets stop_event instead of raising KeyboardInterrupt,
    # so the end_audio handshake can complete cleanly before closing.
    loop.add_signal_handler(signal.SIGINT, lambda: loop.call_soon_threadsafe(stop_event.set))

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(json.dumps(metadata))
        print("Recording. Press Ctrl+C to stop.\n")

        async def send_audio():
            with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=CHUNK_SIZE,
                                channels=1, dtype="float32", callback=audio_callback):
                while not stop_event.is_set():
                    try:
                        chunk = await asyncio.wait_for(send_queue.get(), timeout=0.1)
                        await ws.send(chunk)
                    except asyncio.TimeoutError:
                        continue
            # Drain any chunks buffered after stop
            while not send_queue.empty():
                await ws.send(send_queue.get_nowait())
            # Flush remaining speech buffered on the server
            await ws.send(json.dumps({"type": "end_audio"}))

        async def receive_messages():
            # Receive concurrently with send_audio; VAD may trigger transcription
            # results while audio is still being sent; sequential receive would miss them.
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "transcription":
                    text = " ".join(s["text"] for s in msg.get("segments", []))
                    print(f"[{'final' if msg['is_final'] else 'partial'}] {text}")
                elif msg.get("type") == "end_audio":
                    if msg.get("body", {}).get("status") == "finished":
                        break  # All audio processed; safe to close

        await asyncio.gather(send_audio(), receive_messages())

asyncio.run(stream_mic())
```

<Warning>
  Do not rely on simply closing the WebSocket to flush audio. Always send `{"type": "end_audio"}` and wait for `{"status": "finished"}` before closing to ensure you receive all transcription results.
</Warning>

***

### How do I process multiple audio sessions without reconnecting every time?

Each WebSocket connection is a **single streaming session**. The metadata (language, VAD config, encoding, etc.) is fixed at connection time and can't be changed mid-session. Once the server sends `{"status": "finished"}` in response to `end_audio`, the session is complete and the connection will close.

To process multiple files or conversation turns, **open a new connection for each session**. To minimize reconnection latency in high-throughput scenarios, establish the next connection before the previous one has fully closed (overlapping connections):

```python Python theme={"system"}
import asyncio
import time
import websockets
import json
import os

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512          # ~32ms per chunk, matches live mic cadence
CHUNK_SIZE = CHUNK_SAMPLES * 2  # bytes (pcm_s16le = 2 bytes/sample)
CHUNK_DURATION_S = CHUNK_SAMPLES / SAMPLE_RATE

headers = {"Authorization": f"Bearer {os.environ['BASETEN_API_KEY']}"}
ws_url = "wss://model-{model_id}.api.baseten.co/environments/production/websocket"


async def transcribe_session(audio_bytes: bytes, language: str = "en") -> str:
    """Open a new connection, transcribe one audio buffer, close cleanly."""
    metadata = {
        "streaming_params": {"encoding": "pcm_s16le", "sample_rate": SAMPLE_RATE},
        "whisper_params": {"audio_language": language},
    }
    transcripts = []

    async with websockets.connect(ws_url, additional_headers=headers) as ws:
        await ws.send(json.dumps(metadata))

        async def send_audio():
            for i in range(0, len(audio_bytes), CHUNK_SIZE):
                chunk = audio_bytes[i : i + CHUNK_SIZE]
                # VAD requires ≥ 512 samples per chunk. Zero-pad the last
                # chunk if the file doesn't divide evenly.
                if len(chunk) < CHUNK_SIZE:
                    chunk = chunk + b"\x00" * (CHUNK_SIZE - len(chunk))
                await ws.send(chunk)
                # Pace at real-time speed so VAD sees audio at the same
                # cadence as a live mic; sending faster causes idle timeouts.
                await asyncio.sleep(CHUNK_DURATION_S)
            await ws.send(json.dumps({"type": "end_audio"}))

        async def receive_messages():
            # Receive concurrently; VAD may emit transcripts while audio
            # is still being sent; sequential receive would miss them.
            async for raw in ws:
                message = json.loads(raw)
                if message.get("type") == "transcription":
                    transcripts.append(
                        " ".join(s["text"] for s in message.get("segments", []))
                    )
                elif message.get("type") == "end_audio":
                    if message.get("body", {}).get("status") == "finished":
                        break

        await asyncio.gather(send_audio(), receive_messages())

    return " ".join(transcripts)


async def process_sequential(audio_files: list[bytes]):
    """One connection per file, each opened after the previous one closes."""
    for audio in audio_files:
        transcript = await transcribe_session(audio)
        print(f"Transcript: {transcript}")


async def process_overlapping(audio_files: list[bytes]):
    """All connections opened in parallel; wall-clock time ≈ longest file."""
    results = await asyncio.gather(*[transcribe_session(a) for a in audio_files])
    for transcript in results:
        print(f"Transcript: {transcript}")
```

<Note>
  Each WebSocket connection maps to a dedicated worker on the server. Keeping connections alive unnecessarily will consume server resources. Use health check messages (`{"type": "health_check"}`) to verify a long-lived connection is still active before sending audio.
</Note>
