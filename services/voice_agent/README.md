# voice-agent

The BYOC demo's migrated route: a **voice-workload** deployment of the
[docs_assist](../docs_assist) app — short conversational turns, grounded
cited answers, held to the repo's voice SLO (**TTFT p99 < 500 ms, TPOT
p99 < 60 ms**). This directory is a manifest-only, workload-flavored
deployment (same pattern as `services/qwen3_8b`): the app code lives in
`services/docs_assist`; this manifest names the route, its tier, and its
image.

Bench it with the voice profile:

    ./dev bench --profile voice --slo-ttft-ms 500 ...

Tests pin the manifest contract + Dockerfile render (declaration-only
service). See `services/docs_assist/README.md` for the app itself.
