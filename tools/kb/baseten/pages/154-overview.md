# Overview
Source: https://docs.baseten.co/inference/overview

Inference on Baseten: Model APIs, self-deployed models, how responses are delivered, structured outputs, tool calling, and client configuration.

Inference on Baseten is the path from your application to a model running in Baseten's infrastructure, whether you use [Model APIs](/inference/model-apis/overview) for hosted models or deploy your own with [Truss](/development/model/overview). You don't provision GPUs or build your own routing layer: Baseten authenticates each request, matches it to a deployment environment, and runs it on a replica. This page assumes you already have a Baseten account and an API key.

To call popular open models without a Truss project first, use the public OpenAI-compatible endpoint at `https://inference.baseten.co/v1` with your [Baseten API key](/organization/api-keys) and the OpenAI SDK pointed at that base URL. The [Model APIs](/inference/model-apis/overview) documentation lists models, pricing, and feature support. For what happens after the gateway (routing, replicas, queuing, retries, cold starts), see [Request lifecycle](/deployment/autoscaling/request-lifecycle).

If you're an AI lab serving your own hosted model to your own customers under a branded URL, with federated keys and per-customer billing, see [Frontier Gateway](/frontier-gateway/overview).

## Inference API

When you deploy your own model, pick an interface that matches your payloads. Engine-Builder-LLM, BIS-LLM, and BEI expose `/v1/chat/completions` (or `/v1/embeddings` for BEI) on `https://inference.baseten.co/v1` with OpenAI-compatible parameters for structured outputs, tool calling, reasoning, and streaming. Custom Truss code can use `/predict` for arbitrary JSON when chat or embeddings are not a good fit. Use the [Inference API reference](/reference/inference-api/overview) for paths, methods, and errors.

## Synchronous inference

Synchronous calls return a full response in one round trip, which fits interactive use (chat, code completion, classification, embeddings) where the client can wait for the answer. See [Call your model](/inference/calling-your-model) for predict-style URLs across development, environment, and published deployments.

## Streaming

Streaming sends tokens as they are generated over server-sent events, which suits long generations and UIs where partial output beats a blank wait. See [Streaming](/inference/streaming) for client patterns and engine notes.

## Asynchronous inference

Async inference returns a request ID quickly and completes later through webhook or polling, which suits batch work, long documents, or any case where the caller should not hold a connection open for minutes. See [Async inference](/inference/async) for webhooks, status endpoints, and failures.

## Structured outputs and tool calling

Structured outputs constrain the model to a JSON schema you define; tool calling lets the model invoke your functions and continue the turn. Both align with OpenAI SDK parameters where supported on [Model APIs](/inference/model-apis/overview) and engine-backed deployments. Read [Structured outputs](/inference/structured-outputs) and [Function calling](/inference/function-calling) for implementation details.

## Client configuration

For sustained load, tune connection reuse, timeouts, and parallelism. The Baseten Performance Client covers common cases; see [Performance client](/inference/performance-client) and [HTTP client configuration](/inference/http-client-configuration) for direct HTTP tuning.
