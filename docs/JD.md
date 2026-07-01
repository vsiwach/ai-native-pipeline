# Baseten — Product Manager, Inference Infrastructure (target JD)

Source: LinkedIn posting, 2026. This file is the evaluation rubric for
STAFF-SKEPTIC: every feature must map to a line below.

## The role
Once a model is deployed, keeping it fast, reliable, and economical at scale
is where production inference is won or lost. You'll own the surface that
makes that happen: how deployments autoscale, how traffic is routed, how the
system fails over, and how workloads scale across clusters and regions. You'll
own these as products end to end — both how they work under the hood and how
customers configure and observe them.

## Impact and outcomes (feature mapping in parentheses)
- Own how workloads scale and where they land — autoscaling to demand (up
  under load, down to zero when idle) and a single placement policy
  expressing region, compliance regime, and capacity preference, with
  compliance-bound workloads given right-of-way on sensitive capacity.
  (→ F2 autoscaling, F3 placement policy)
- Make production inference reliable by default — every request reaches a
  healthy replica, rolling deploys never drop traffic, region-aware routing
  with multi-region / active-active and fallback as first-class policy, and
  health-aware recovery from stuck or bad replicas. (→ F4 reliability)
- Build the release engine beneath safe rollouts — the traffic-shifting that
  powers canary/shadow/A/B, warm-ups, drain, and probes. (→ F5 release engine)
- Push the cost/performance frontier for serving AI at scale — latency,
  throughput, uptime, and cost-efficiency, plus a measurable decline in MTTR
  through self-serve incident management. (→ F1 baselines + F6 incident agent
  + F7 console)

## What they're looking for
- 8+ years PM incl. infrastructure, distributed systems, or ML serving.
- Reasons fluently about scaling, routing, failover, cost/perf frontier —
  earns the respect of staff engineers.
- Owns capabilities end to end, backend through UX.
- Bonus: hands-on GPU infra, Kubernetes, vLLM / TensorRT-LLM / SGLang.

## Not for you if
- You don't like getting technical; prefer strategy/docs over shipping;
  lean applied-AI over platform/systems/GPU infrastructure.
