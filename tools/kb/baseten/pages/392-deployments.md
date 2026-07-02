# Deployments
Source: https://docs.baseten.co/troubleshooting/deployments

Troubleshoot common problems during model deployment

## Issue: `truss push` can't find `config.yaml`

```sh theme={"system"}
[Errno 2] No such file or directory: '/path/to/your-truss/config.yaml'
```

### Fix: set correct target directory

The directory `truss push` is looking at is not a Truss. Make sure you're giving `truss push` access to the correct directory by:

* Running `truss push` from the directory containing the Truss. You should see the file `config.yaml` when you run `ls` in your working directory.
* Or passing the target directory as an argument, such as `truss push /path/to/my-truss`.

## Issue: unexpected failure during model build

During the model build step, there can be unexpected failures from temporary circumstances. An example is a network error while downloading model weights from Hugging Face or installing a Python package from PyPi.

### Fix: restart deploy from Baseten UI

First, check your model logs to determine the exact cause of the error. If it's an error during model download, package installation, or similar, you can try restarting the deploy from the model dashboard in your workspace.

## Issue: a single replica is stuck or unhealthy

One replica of a multi-replica deployment can fail while the others keep serving, for example by hanging, becoming unresponsive, or consuming excessive memory. Restarting the whole deployment is heavier than the problem warrants.

### Fix: terminate the affected replica

Terminate just the bad replica. The deployment's autoscaler brings up a fresh replica to maintain your target replica count, so traffic keeps flowing on the healthy replicas while the replacement starts. Get the replica ID from the deployment's replica list, then run:

```sh theme={"system"}
baseten model deployment replica terminate --model-id <model-id> --deployment-id <deployment-id> --replica-id <replica-id>
```

The command prompts for confirmation; pass `--yes` to skip it. See [`baseten model deployment replica`](/reference/cli/baseten/model-deployment-replica) for the full option set, or call the [terminate replica endpoint](/reference/management-api/deployments/terminates-deployment-replica) directly.

***

## Autoscaling issues

Before troubleshooting, review [Autoscaling](/deployment/autoscaling/overview) for parameter details, [Traffic patterns](/deployment/autoscaling/traffic-patterns) for pattern-specific recommendations, and [Request lifecycle](/deployment/autoscaling/request-lifecycle) for HTTP status codes and timeout behavior.

### Latency spikes during scaling events

**Symptoms**: TTFT (time to first token) or p95/p99 latency degrades when replicas are added or removed.

**Causes**:

* Replicas terminated while handling in-flight requests
* Cold start delays while new replicas initialize

**Solutions** (in order of priority):

1. Increase [**scale-down delay**](/deployment/autoscaling/overview#scale-down-delay) (for example, 300s → 900s) to reduce how often replicas are removed.
2. Increase [**min replicas**](/deployment/autoscaling/overview#minimum-replicas) to reduce cold start frequency.
3. Lower [**target utilization**](/deployment/autoscaling/overview#target-utilization) to provide more headroom during scaling.

### Replicas oscillating (thrash)

**Symptoms**: Replica count bounces repeatedly (for example, 8↔9) even with relatively stable traffic.

**Causes**: Autoscaler reacting to short-term traffic noise or internal model fluctuations.

**Solutions** (in order of priority):

1. Increase **scale-down delay**: this is the primary lever for oscillation.
2. Increase [**autoscaling window**](/deployment/autoscaling/overview#autoscaling-window) to smooth out noise.
3. Lower [**max scale-down rate**](/deployment/autoscaling/overview#max-scale-down-rate) so each scale-down step removes fewer replicas.
4. Only then consider lowering **target utilization** for more headroom.

<Warning>
  Don't use target utilization as the primary fix for thrash. Scale-down delay is more effective and doesn't waste capacity.
</Warning>

### Slow scale-up / "Scaling up replicas" persists

**Symptoms**: New replicas take many minutes (or longer) to become ready. The deployment shows "Scaling up replicas" for an extended period.

**Causes**:

* GPU capacity not available in your region
* Slow model initialization (large weights, slow downloads)

**Solutions**:

1. **Pre-warm** by bumping min replicas through the API before expected load spikes.
2. Contact support about capacity pool availability.
3. Check if optimized images are being used (look for "streaming-enabled image" in logs).

### Model scales to zero before testing

**Symptoms**: A newly deployed model scales down to zero before you can send your first test request.

**Solution**: Set `min_replica = 1` during testing. After testing, you can set it back to 0 if you want scale-to-zero behavior.

### Async queue growing without bound

**Symptoms**: The async queue size keeps increasing and requests are not being processed fast enough.

**Cause**: Requests are arriving faster than the deployment can process them.

**Solutions**:

1. Increase [**max replicas**](/deployment/autoscaling/overview#maximum-replicas) to add more processing capacity.
2. Increase [**concurrency target**](/deployment/autoscaling/overview#concurrency-target) if your model can handle more concurrent requests.
3. Lower **target utilization** to trigger scaling earlier.

### Bill higher than expected

**Symptoms**: GPU costs are higher than anticipated, especially during low-traffic periods.

**Solutions**:

1. Raise **concurrency target** to squeeze more throughput from each replica.
2. Monitor **p95 latency** as you raise concurrency. If latency stays stable, keep raising; if it rises sharply, you've gone too far.
3. Enable **scale-to-zero** (min replicas = 0) for intermittent workloads.
4. Review your traffic patterns and adjust settings accordingly. See [Traffic patterns](/deployment/autoscaling/traffic-patterns).

### Cold starts taking too long

**Symptoms**: First request after scale-from-zero takes several minutes. Logs show extended time in model loading or container initialization.

**Causes**:

* Large model weights (10s–100s of GB)
* Slow network downloads from model registries
* Heavy initialization code in `load()` method

**Solutions**:

1. Look for "streaming-enabled image" in logs. This confirms image streaming is active.
2. Keep `min_replica ≥ 1` to avoid cold starts entirely.
3. Pre-warm before expected traffic spikes using the [autoscaling API](/reference/management-api/deployments/autoscaling/updates-a-deployments-autoscaling-settings).

See [Cold starts](/deployment/autoscaling/cold-starts) for detailed optimization strategies.

### Development deployment won't scale

**Symptoms**: Development deployment won't scale beyond 1 replica under load. Can't change autoscaling settings.

**Cause**: Development deployments have fixed autoscaling settings that cannot be modified. They run 0 to 1 replicas, so they scale to zero when idle, but max replicas is locked at 1.

**Solution**: Promote to a production deployment to enable full autoscaling. Development deployments are optimized for iteration with live reload, not traffic handling.

See [Development deployments](/deployment/autoscaling/overview#development-deployments) for the fixed settings.

### Not sure which traffic pattern I have

**Symptoms**: Unsure how to configure autoscaling because traffic behavior is unclear.

**Solution**:

1. Go to your model's **Metrics** tab in the Baseten dashboard.
2. Look at **Inference volume** and **Replicas** over the past week.
3. Identify your pattern:

| You see...                                  | Pattern         | Key settings to adjust                      |
| ------------------------------------------- | --------------- | ------------------------------------------- |
| Frequent small spikes returning to baseline | Noisy/jittery   | Longer autoscaling window                   |
| Sharp jumps that stay high                  | Bursty          | Short window, long delay, lower utilization |
| Long flat periods with occasional bursts    | Batch/scheduled | Scale-to-zero, pre-warming                  |
| Gradual rises and falls                     | Smooth/steady   | Higher utilization is safe                  |

See [Traffic patterns](/deployment/autoscaling/traffic-patterns) for detailed recommendations.

### Concurrency target misconfigured

**Symptoms**: Either unexpectedly high costs OR high latency despite having replicas available.

**Diagnosis**:

* **Too low** (common): Running many more replicas than needed. Default of 1 is conservative but expensive.
* **Too high**: Requests queue at replicas, causing latency even when replica count looks healthy.

**Solutions**:

1. Benchmark your model to find actual throughput capacity.
2. Use starting points by model type:

| Model type              | Starting concurrency |
| ----------------------- | -------------------- |
| Standard Truss          | 1                    |
| vLLM / LLM inference    | 32–128               |
| Text embeddings (TEI)   | 32                   |
| Image generation (SDXL) | 1                    |

3. Gradually increase while monitoring p95 latency. Stop when latency rises sharply.

See [Concurrency target](/deployment/autoscaling/overview#concurrency-target) for full guidance.

<Note>
  For detailed autoscaling configuration, see [Autoscaling](/deployment/autoscaling/overview). For pattern-specific recommendations, see [Traffic patterns](/deployment/autoscaling/traffic-patterns).
</Note>
