# Cold starts
Source: https://docs.baseten.co/deployment/autoscaling/cold-starts

Learn what makes a cold start slow and how to shrink it for your model.

<MiniDiagramEngine />

A *cold start* is the time a fresh replica spends starting up before it can accept traffic. A request that triggers one waits in the queue until the replica is ready, so the cold-start duration sets the latency floor for that request. The following diagram traces a deployment through that cycle, from **Scaled to zero** to **Active** and back, with the startup steps that add up to the wait.

<MiniColdStart />

## Cold start triggers

Every new replica cold-starts before it can serve traffic, no matter why it was created.

*Scale-from-zero* applies when a deployment's `min_replica` is 0. Once traffic stays at zero for the full [`scale_down_delay`](/deployment/autoscaling/overview#how-autoscaling-works), the autoscaler shuts down every replica. The next request finds nothing running and waits for a full startup, so users feel this cold start directly.

*Scaling events* happen while a deployment is already serving traffic. When load crosses the scaling threshold, the autoscaler adds replicas, and each one cold-starts before it can serve traffic. The replicas already running keep serving in the meantime, so users notice only when load grows faster than new replicas can start up.

## Contributing factors

A new replica works through these steps in order, and their durations add up to the cold-start time:

| Step                  | What happens                                                                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Container pull        | The replica downloads your Docker image layers.                                                                                                                                    |
| Weight load           | Model weights (often 10s to 100s of GB) move from storage into GPU memory.                                                                                                         |
| Engine initialization | Your model's setup code runs. For inference engines like vLLM and SGLang, this includes capturing CUDA graphs, compiling kernels with `torch.compile`, and profiling the KV cache. |

Baseten provides the [Baseten Delivery Network (BDN)](/development/model/bdn), which speeds up weight load by mirroring your weights and caching them next to your replicas. Each scale-up then reads them from a nearby cache instead of re-downloading hundreds of gigabytes from the source. Baseten also streams your container image in the background, so container pull rarely dominates.

That leaves engine initialization as the step you usually own. It dominates for small models (a few billion parameters or fewer), where CUDA graph capture and `torch.compile` can run well over a minute, and Baseten doesn't cache those artifacts unless you opt in. For the largest models (70B+ parameters or large mixture-of-experts), even BDN can't make hundreds of gigabytes instant, so weight load stays the dominant step.

Cold start time isn't a fixed number. It varies with model size and the GPU you run on, so benchmark your own model rather than relying on a single figure.

## Reduce cold starts

The biggest win comes from shrinking whichever step dominates startup. When that isn't enough, keep replicas warm so requests skip the cold start entirely.

### Faster weight loading

BDN runs automatically on engine-builder deployments. On any other deployment, turn it on by adding a [`weights`](/development/model/bdn) block to your config.

### Compilation caching

`torch.compile` and CUDA graph capture rerun on every fresh replica unless their output is cached. [Torch compile caching](/development/model/runtime-caching#torch-compile-caching), built on [b10cache](/development/model/runtime-caching), persists those artifacts so a new replica loads them instead of recompiling, which cuts compilation from minutes to roughly 5 to 20 seconds.

### Warm replicas

`min_replica` sets a floor on running replicas. Keep it at 1 or higher so a replica stays warm to serve the first request. You pay for that replica while it's idle, but the request no longer waits for a startup. Set it in the dashboard or through the [autoscaling settings API](/reference/management-api/deployments/autoscaling/updates-a-deployments-autoscaling-settings):

```json Autoscaling settings theme={"system"}
{
  "min_replica": 1
}
```

For production redundancy, set `min_replica` to 2 or higher so one replica can fail during maintenance without causing cold starts.

Your replica floor trades cost against latency:

| Approach                         | Cost                                                                      | Latency                                                       | Best for                                              |
| -------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------- |
| Scale to zero (`min_replica: 0`) | No charge while idle; wake-up minutes are [billed](/organization/billing) | First request waits for a full cold start                     | Batch jobs, development, and spiky low-volume traffic |
| Always on (`min_replica` ≥ 1)    | Pay for idle replicas                                                     | No cold start from idle, though new replicas still cold-start | Latency-sensitive production traffic                  |

Start warm for production, and scale to zero only when an occasional slow first request is acceptable.

### Pre-warming

For predictable traffic spikes, raise `min_replica` ahead of the expected load:

```bash Terminal theme={"system"}
# 10-15 minutes before expected spike
curl -X PATCH \
  https://api.baseten.co/v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -d '{"min_replica": 5}'
```

After traffic stabilizes, reset to your normal minimum.

### Scale-down delay

A longer scale-down delay keeps replicas warm through brief traffic dips. The default is 15 minutes (900 seconds); this example doubles it to 30 minutes:

```json Autoscaling settings theme={"system"}
{
  "scale_down_delay": 1800
}
```

A replica that's still warm when traffic returns serves immediately, with no cold start.

## Next steps

* [Request lifecycle](/deployment/autoscaling/request-lifecycle): What happens to requests during cold starts, including queuing and timeout behavior.
* [Autoscaling](/deployment/autoscaling/overview): Configure `min_replica`, `scale_down_delay`, and the rest of the scaling settings.
* [Traffic patterns](/deployment/autoscaling/traffic-patterns): Pre-warming strategies for different traffic types.
* [Billing and usage](/organization/billing): How cold-start time is metered.
* [Troubleshooting](/troubleshooting/deployments#autoscaling-issues): Diagnose cold start issues.
