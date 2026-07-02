# Traffic patterns
Source: https://docs.baseten.co/deployment/autoscaling/traffic-patterns

Identify your traffic pattern and configure autoscaling settings to match.

<AutoscaleChartEngine />

Different traffic patterns require different autoscaling configurations.
Identify your pattern below for recommended starting settings.

<Note>
  These are **starting points**, not final answers. Monitor your
  deployment's performance and adjust based on observed behavior. See
  [Autoscaling](/deployment/autoscaling/overview) for parameter details.
</Note>

## Identify your pattern

Not sure which pattern you have? Check your metrics:

1. Go to your model's **Metrics** tab in the Baseten dashboard.
2. Look at **Inference volume** and **Replicas** over the past week.
3. Compare to the patterns below.

| You see...                                            | Your pattern is...              |
| ----------------------------------------------------- | ------------------------------- |
| Frequent small spikes that quickly return to baseline | [Jittery](#jittery-traffic)     |
| Sharp jumps that stay high for a while                | [Bursty](#bursty-traffic)       |
| Long flat periods with occasional large bursts        | [Scheduled](#scheduled-traffic) |
| Gradual rises and falls, smooth curves                | [Steady](#steady-traffic)       |

<Note>
  Some workloads are a mix of patterns. If your traffic has both smooth diurnal patterns AND occasional bursts, optimize for the bursts (they cause the most pain) and accept slightly higher cost during steady periods.
</Note>

## Jittery traffic

Small, frequent spikes that quickly return to baseline.

<AutoscaleJittery />

### Characteristics

* Baseline replica count is steady, but **spikes up by 2x several times per hour**.
* Spikes are short-lived and return to baseline quickly.
* Often not real load growth, just temporary surges causing overreaction.

### Common causes

* Consumer products with intermittent usage bursts.
* Traffic splitting or A/B testing with low percentages.
* Polling clients with synchronized intervals.

### Recommended settings

| Parameter          | Value             | Why                                             |
| ------------------ | ----------------- | ----------------------------------------------- |
| Autoscaling window | **2-5 minutes**   | Smooth out noise, avoid reacting to every spike |
| Scale-down delay   | **300-600s**      | Moderate stability                              |
| Target utilization | **70%**           | Default is fine                                 |
| Concurrency target | Benchmarked value | Start conservative                              |

A longer autoscaling window averages out the jitter so the autoscaler doesn't chase every small spike. You're trading reaction speed for stability, which is acceptable when the spikes aren't sustained load increases.

<Tip>
  If you're still seeing oscillation with these settings, increase the scale-down delay before lowering target utilization.
</Tip>

## Bursty traffic

<AutoscaleBursty />

### Characteristics

* Traffic **jumps sharply** (2x+ within 60 seconds).
* Stays high for a sustained period before dropping.
* The "pain" is queueing and latency spikes while new replicas start.

### Common causes

* Daily morning ramp-up (users starting their day).
* Marketing events, product launches, viral moments.
* Top-of-hour scheduled jobs or cron-triggered traffic.

### Recommended settings

| Parameter          | Value      | Why                                           |
| ------------------ | ---------- | --------------------------------------------- |
| Autoscaling window | **30-60s** | React quickly to genuine load increases       |
| Scale-down delay   | **900s+**  | Handle back-to-back waves without thrashing   |
| Target utilization | **50-60%** | More headroom absorbs the burst while scaling |
| Min replicas       | **≥2**     | Redundancy + reduces cold start impact        |

Short window means fast reaction. Long delay prevents scaling down between waves. Lower utilization gives you buffer capacity while new replicas start.

### Pre-warming for predictable bursts

If your bursts are predictable (morning ramp, scheduled events), pre-warm by bumping min replicas before the expected spike:

```bash Request theme={"system"}
curl -X PATCH \
  https://api.baseten.co/v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -d '{"min_replica": 5}'
```

After the burst subsides, reset to your normal minimum:

```bash Request theme={"system"}
curl -X PATCH \
  https://api.baseten.co/v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -d '{"min_replica": 2}'
```

<Tip>
  Automate pre-warming with cron jobs or your orchestration system.
  Bumping min replicas 10-15 minutes before known peaks avoids cold starts for the first requests after the spike.
</Tip>

## Scheduled traffic

<AutoscaleScheduled />

### Characteristics

* **Long periods of low or zero traffic**.
* Large bursts tied to job schedules (hourly, daily, weekly).
* Traffic patterns are predictable but infrequent.

### Common causes

* ETL pipelines and data processing jobs.
* Embedding backfills and batch inference.
* Periodic evaluation or testing jobs.
* Document processing triggered by user uploads.

### Recommended settings

| Parameter          | Value                                                           | Why                                       |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------- |
| Min replicas       | **0** (if cold starts acceptable) or **1** (during job windows) | Cost savings when idle                    |
| Scale-down delay   | **Moderate to high**                                            | Jobs often come in waves                  |
| Autoscaling window | **60-120s**                                                     | Don't overreact to the first few requests |
| Target utilization | **70%**                                                         | Default is fine                           |

Scale-to-zero saves significant cost during idle periods. The moderate window prevents overreacting to the initial requests of a batch. If jobs come in waves, a longer delay keeps replicas warm between them.

### Scheduled pre-warming

For predictable batch jobs, use cron + API to pre-warm.

5 minutes before the hourly job, scale up:

```bash Terminal theme={"system"}
0 * * * * curl -X PATCH \
  https://api.baseten.co/v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -d '{"min_replica": 3}'
```

30 minutes after the job completes, scale back down:

```bash Terminal theme={"system"}
30 * * * * curl -X PATCH \
  https://api.baseten.co/v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -d '{"min_replica": 0}'
```

<Warning>
  If you use scale-to-zero, the first request of each batch will experience a [cold start](/deployment/autoscaling/cold-starts). For latency-sensitive batch jobs, keep min replicas at 1 during expected job windows.
</Warning>

## Steady traffic

<AutoscaleSteady />

### Characteristics

* Traffic **rises and falls gradually** over the day.
* Classic diurnal pattern with no sharp edges.
* Predictable, cyclical behavior.

### Common causes

* Always-on inference APIs with consistent user base.
* B2B applications with business-hours usage.
* Production workloads with stable, mature traffic.

### Recommended settings

| Parameter          | Value        | Why                            |
| ------------------ | ------------ | ------------------------------ |
| Target utilization | **70-80%**   | Can run replicas hotter safely |
| Autoscaling window | **60-120s**  | Moderate reaction speed        |
| Scale-down delay   | **300-600s** | Moderate                       |
| Min replicas       | **≥2**       | Redundancy for production      |

Without sudden spikes, you don't need as much headroom. You can run replicas at higher utilization (lower cost) because load changes are gradual and predictable. The autoscaler has time to react.

<Tip>
  Smooth traffic is the easiest to tune. Start with defaults, monitor for a week, then optimize for cost by gradually raising target utilization while watching p95 latency.
</Tip>

## Next steps

* [Autoscaling](/deployment/autoscaling/overview): Full parameter documentation.
* [Troubleshooting autoscaling](/troubleshooting/deployments#autoscaling-issues): Diagnose and fix common problems.
* [Truss configuration reference](/reference/truss-configuration): Configure predict\_concurrency in your model.
