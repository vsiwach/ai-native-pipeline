# GPU run — 2026-07-05 (Act 1 NVIDIA / Act 2 AMD)

Same model, same MAX version, two vendors; per-second rented pods.

| Pool | Pod | GPU | DC | Image | $/hr (actual) |
|---|---|---|---|---|---|
| a100-nvidia | m5urqsu7knad09 | A100 80GB PCIe | CA-MTL-3 | modular/max-nvidia-full:26.4.0 | 1.39 |
| mi300x-amd | 65w5tzxtzhsdqv | MI300X 192GB OAM | EU-RO-1 | modular/max-amd:26.4.0 | 2.19 |

Model: Qwen/Qwen2.5-14B-Instruct. Serving: MAX container entrypoint
(`--model …`, port 8000, RunPod proxy `https://<pod>-8000.proxy.runpod.net/v1`).

Flow per pool: /v1/models smoke → `./dev bench` (60 req, docs-agent profile,
actual $/hr) → docs-assist candidate re-pointed at the pod → replay evals
through the router (shadow fills with REAL grounded answers) → `./dev
certify` at the 0.90 parity gate + 800 ms TTFT gate → teardown, ledger
closed. Artifacts land in this directory; the passing cert becomes
vercel-deploy/certs/latest.json.
