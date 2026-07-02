# Transcribe audio with Chains
Source: https://docs.baseten.co/examples/chains-audio-transcription

Process hours of audio in seconds using efficient chunking, distributed inference, and optimized GPU resources.

<Card title="View example on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/chains-examples/docs/audio-transcription" />

This guide walks through building an audio transcription pipeline using Chains. You'll break down large media files, distribute transcription tasks across autoscaling deployments, and leverage high-performance GPUs for rapid inference.

# Overview

This Chain enables fast, high-quality transcription by:

* **Partitioning** long files (10+ hours) into smaller segments.
* **Detecting silence** to optimize split points.
* **Parallelizing inference** across multiple GPU-backed deployments.
* **Batching requests** to maximize throughput.
* **Using range downloads** for efficient data streaming.
* Leveraging `asyncio` for concurrent execution.

# Chain structure

Transcription is divided into two processing layers:

1. **Macro chunks:** Large segments (\~300s) split from the source media file. These are processed in parallel to handle massive files efficiently.
2. **Micro chunks:** Smaller segments (\~5–30s) extracted from macro chunks and sent to the Whisper model for transcription.

# Implement the Chainlets

## `Transcribe` (Entrypoint Chainlet)

Handles transcription requests and dispatches tasks to worker Chainlets.

Function signature:

```python theme={"system"}
async def run_remote(
  self,
  media_url: str,
  params: data_types.TranscribeParams
) -> data_types.TranscribeOutput:
```

**Steps:**

* Validates that the media source supports **range downloads**.
* Uses **FFmpeg** to extract metadata and duration.
* Splits the file into **macro chunks**, optimizing split points at silent sections.
* Dispatches **macro chunk tasks** to the MacroChunkWorker for processing.
* Collects **micro chunk transcriptions**, merges results, and returns the final text.

**Example request:**

```bash theme={"system"}
curl -X POST $INVOCATION_URL \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -d '<JSON_INPUT>'
```

```json theme={"system"}
{
  "media_url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
  "params": {
    "micro_chunk_size_sec": 30,
    "macro_chunk_size_sec": 300
  }
}
```

## `MacroChunkWorker` (Processing Chainlet)

Processes **macro chunks** by:

* **Extracting** relevant time segments using **FFmpeg**.
* **Streaming audio** instead of downloading full files for low latency.
* **Splitting segments** at silent points.
* **Encoding** audio in base64 for efficient transfer.
* **Distributing micro chunks** to the Whisper model for transcription.

This Chainlet **runs in parallel** with multiple instances autoscaled dynamically.

## `WhisperModel` (Inference Model)

A separately deployed **Whisper** model Chainlet handles speech-to-text transcription.

* Deployed **independently** to allow fast iteration on business logic without redeploying the model.
* Used **across different Chains** or accessed directly as a standalone model.
* Supports **multiple environments** (for example, dev, prod) using the same instance.

Whisper can also be deployed as a **standard Truss model**, separate from the Chain.

# Optimize performance

Even for very large files, **processing time remains bounded** by parallel execution.

## Key performance tuning parameters:

* `micro_chunk_size_sec` → Balance GPU utilization and inference latency.
* `macro_chunk_size_sec` → Adjust chunk size for optimal parallelism.
* **Autoscaling settings** → Tune concurrency and replica counts for load balancing.

Example speedup:

```json theme={"system"}
{
  "input_duration_sec": 734.26,
  "processing_duration_sec": 82.42,
  "speedup": 8.9
}
```

# Deploy and run the Chain

## Deploy WhisperModel first:

```bash theme={"system"}
truss chains push whisper_chainlet.py
```

Copy the **invocation URL** and update `WHISPER_URL` in `transcribe.py`.

## Deploy the transcription Chain:

```bash theme={"system"}
truss chains push transcribe.py
```

## Run transcription on a sample file:

```bash theme={"system"}
curl -X POST $INVOCATION_URL \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -d '<JSON_INPUT>'
```

***

# Next steps

* Learn more about [Chains](/development/chain/overview).
* Optimize GPU **autoscaling** for peak efficiency.
* Extend the pipeline with **custom business logic**.
