window.REPLAY = {
 "generated_from": "benchmarks/raw/ \u2014 committed evidence, no synthesis",
 "deploy": {
  "attempts": [
   {
    "name": "L4:2x24x96",
    "outcome": "never scheduled (30 min silent)",
    "lesson": "2-GPU node scarcity; no capacity signal (friction #6)"
   },
   {
    "name": "T4x4x16",
    "outcome": "host-RAM OOM crash-loop",
    "lesson": "16 GiB host can't materialize 8B weights (friction #7)"
   },
   {
    "name": "H100 Engine-Builder",
    "outcome": "BUILD_FAILED, logs API-invisible",
    "lesson": "docs agent: resources under documented example scale (friction #12)"
   },
   {
    "name": "A10Gx8x32",
    "outcome": "org-gated at push",
    "lesson": "GPU families gated per workspace, no pre-flight (friction #13)"
   },
   {
    "name": "T4x8x32 #1",
    "outcome": "import crash: transformers/vllm skew",
    "lesson": "docs agent + logs: pin transformers==4.53.2 (friction #14)"
   },
   {
    "name": "T4x8x32 #2",
    "outcome": "ACTIVE \u2014 but env pointer poisoned",
    "lesson": "promote required after failed first deploy (friction #15)"
   }
  ],
  "final": {
   "deployment": "w52yvzr",
   "instance": "T4x8x32",
   "model": "Qwen/Qwen3-8B-AWQ (open weights, Apache-2.0)",
   "engine": "vLLM 0.9.1 custom Truss",
   "cold_start_s": 360,
   "warm_ttft_ms": 333,
   "usd_per_hour": 0.9
  },
  "agent_findings": [
   {
    "finding": "Requests during warm-up park then 500 \u2014 gate readiness before traffic",
    "source": "docs.baseten.co/deployment/autoscaling/request-lifecycle"
   },
   {
    "finding": "Billing starts when a replica is up, not when serving",
    "source": "docs.baseten.co/organization/billing"
   },
   {
    "finding": "weights: block (BDN) would cut the 6-min cold start",
    "source": "docs.baseten.co/development/model/bdn"
   },
   {
    "finding": "Model API limits are account-tier: 15 RPM unverified / 120 verified",
    "source": "docs.baseten.co/inference/model-apis/rate-limits-and-budgets"
   }
  ]
 },
 "traffic": {
  "requests": [
   {
    "prompt": "Why do voice agents need low time-to-first-token?",
    "answer": "Voice agents need low time-to-first-token to provide immediate feedback and maintain user engagement by quickly responding to user input.",
    "replica": "baseten-l4",
    "model": "Qwen3-8B-AWQ (dedicated T4)",
    "ttft_ms": 332.8,
    "tokens_per_sec": 25.4,
    "cost_usd": 0.0003583
   },
   {
    "prompt": "Name one benefit of KV-cache reuse.",
    "answer": "It significantly reduces latency and computational cost by avoiding the re-computation of key and value tensors for previously processed tokens.",
    "replica": "model-api-spill",
    "model": "GLM-4.7 (Baseten Model APIs, serverless)",
    "ttft_ms": 717.9,
    "tokens_per_sec": 210.4,
    "cost_usd": 6.38e-05
   }
  ]
 },
 "chaos": {
  "baseline": {
   "label": "agent OFF (2026-07-02, live Baseten pool)",
   "timeline": [
    {
     "t": 0.0,
     "event": "load_start",
     "detail": "2.0 rps streaming, model=qwen3-8b"
    },
    {
     "t": 4.04,
     "event": "inject",
     "detail": "{\"latency_ms\": 600.0, \"error_rate\": 0.0}"
    },
    {
     "t": 79.08,
     "event": "timeout",
     "detail": "no resolution within 75.0s \u2014 FAIL"
    }
   ],
   "outcome": "75s of fault \u2014 never detected, never resolved"
  },
  "drills": [
   {
    "label": "latency +600ms on dedicated T4 (2026-07-03)",
    "timeline": [
     {
      "t": 0.0,
      "event": "load_start",
      "detail": "1.2 rps streaming, model=qwen3-8b"
     },
     {
      "t": 4.03,
      "event": "inject",
      "detail": "{\"latency_ms\": 600.0, \"error_rate\": 0.0}"
     },
     {
      "t": 12.66,
      "event": "detected",
      "detail": "INC-0001: baseten-l4 breaching serving SLO \u2014 50% of recent requests"
     },
     {
      "t": 12.66,
      "event": "quarantined",
      "detail": "traffic spilled to healthy pool"
     },
     {
      "t": 12.69,
      "event": "cleared",
      "detail": "fault removed \u2014 agent must now verify"
     },
     {
      "t": 21.34,
      "event": "resolved",
      "detail": "MTTR 8.8s (agent=True)"
     }
    ],
    "mttr_s": 8.8,
    "spill_requests": 10,
    "spill_target": "model-api-spill (GLM-4.7 serverless)"
   },
   {
    "label": "90% error storm on dedicated T4 (2026-07-03)",
    "timeline": [
     {
      "t": 0.0,
      "event": "load_start",
      "detail": "1.2 rps streaming, model=qwen3-8b"
     },
     {
      "t": 4.03,
      "event": "inject",
      "detail": "{\"latency_ms\": 0.0, \"error_rate\": 0.9}"
     },
     {
      "t": 10.61,
      "event": "detected",
      "detail": "INC-0002: baseten-l4 breaching serving SLO \u2014 50% of recent requests"
     },
     {
      "t": 10.61,
      "event": "quarantined",
      "detail": "traffic spilled to healthy pool"
     },
     {
      "t": 10.62,
      "event": "cleared",
      "detail": "fault removed \u2014 agent must now verify"
     },
     {
      "t": 19.74,
      "event": "resolved",
      "detail": "MTTR 9.2s (agent=True)"
     }
    ],
    "mttr_s": 9.2,
    "spill_requests": null,
    "spill_target": "model-api-spill (GLM-4.7 serverless)"
   }
  ],
  "incidents": [
   {
    "id": "INC-0003",
    "title": "model-api-spill breaching serving SLO \u2014 50% of recent requests \u00b7 last healthy pool, quarantine withheld",
    "mttr_s": 27.7,
    "agent": true,
    "actions": [
     "detected SLO breach rate 50% over 4 requests on model-api-spill",
     "probe passed (454ms)",
     "probe failed (524ms)",
     "probe failed (531ms)",
     "probe failed (531ms)",
     "probe passed (441ms)",
     "probe passed (434ms)"
    ]
   },
   {
    "id": "INC-0002",
    "title": "baseten-l4 breaching serving SLO \u2014 50% of recent requests",
    "mttr_s": 9.2,
    "agent": true,
    "actions": [
     "detected SLO breach rate 50% over 6 requests on baseten-l4",
     "quarantined baseten-l4; traffic spills to healthy pools",
     "probe passed (364ms)",
     "probe passed (352ms)",
     "reinstated baseten-l4 \u2014 2 consecutive probes within SLO"
    ]
   },
   {
    "id": "INC-0001",
    "title": "baseten-l4 breaching serving SLO \u2014 50% of recent requests",
    "mttr_s": 8.8,
    "agent": true,
    "actions": [
     "detected SLO breach rate 50% over 6 requests on baseten-l4",
     "quarantined baseten-l4; traffic spills to healthy pools",
     "probe passed (404ms)",
     "probe passed (358ms)",
     "reinstated baseten-l4 \u2014 2 consecutive probes within SLO"
    ]
   }
  ],
  "all_drills": [
   {
    "stamp": "20260702-152811",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "16.07",
    "quarantined_s": "",
    "mttr_s": "4.0",
    "resolved": "True"
   },
   {
    "stamp": "20260702-153057",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "19.49",
    "quarantined_s": "19.49",
    "mttr_s": "8.7",
    "resolved": "True"
   },
   {
    "stamp": "20260702-153157",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "7.09",
    "quarantined_s": "7.09",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-153507",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "",
    "quarantined_s": "",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-154142",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "17.83",
    "quarantined_s": "17.83",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-154451",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "4.55",
    "quarantined_s": "",
    "mttr_s": "4.0",
    "resolved": "True"
   },
   {
    "stamp": "20260702-154535",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "10.31",
    "quarantined_s": "",
    "mttr_s": "4.0",
    "resolved": "True"
   },
   {
    "stamp": "20260702-155248",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "9.3",
    "quarantined_s": "9.3",
    "mttr_s": "2.0",
    "resolved": "True"
   },
   {
    "stamp": "20260702-155332",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "7.18",
    "quarantined_s": "7.18",
    "mttr_s": "46.4",
    "resolved": "True"
   },
   {
    "stamp": "20260702-155503",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "9.4",
    "quarantined_s": "9.4",
    "mttr_s": "3.5",
    "resolved": "True"
   },
   {
    "stamp": "20260702-155845",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "19.31",
    "quarantined_s": "19.31",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-160159",
    "scenario": "errors",
    "pool": "model-api-b",
    "model": "glm-4.7",
    "detected_s": "",
    "quarantined_s": "",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-160511",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "36.04",
    "quarantined_s": "36.04",
    "mttr_s": "82.2",
    "resolved": "True"
   },
   {
    "stamp": "20260702-161342",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "15.52",
    "quarantined_s": "15.52",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-161651",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "59.2",
    "quarantined_s": "",
    "mttr_s": "84.7",
    "resolved": "True"
   },
   {
    "stamp": "20260702-161952",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "15.85",
    "quarantined_s": "15.85",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-163119",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "18.76",
    "quarantined_s": "18.76",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-163219",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "7.08",
    "quarantined_s": "7.08",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-163309",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "17.18",
    "quarantined_s": "17.18",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-164306",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "17.7",
    "quarantined_s": "17.7",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-164328",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "45.91",
    "quarantined_s": "45.91",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-164455",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "17.29",
    "quarantined_s": "17.29",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-164555",
    "scenario": "combo",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "15.03",
    "quarantined_s": "15.03",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-184106",
    "scenario": "errors",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "4.54",
    "quarantined_s": "4.54",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-185334",
    "scenario": "latency",
    "pool": "model-api-a",
    "model": "glm-4.7",
    "detected_s": "16.17",
    "quarantined_s": "16.17",
    "mttr_s": "8.1",
    "resolved": "True"
   },
   {
    "stamp": "20260702-201639",
    "scenario": "latency",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "",
    "quarantined_s": "",
    "mttr_s": "",
    "resolved": "False"
   },
   {
    "stamp": "20260702-201834",
    "scenario": "latency",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "39.53",
    "quarantined_s": "39.53",
    "mttr_s": "8.7",
    "resolved": "True"
   },
   {
    "stamp": "20260702-201958",
    "scenario": "errors",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "17.24",
    "quarantined_s": "17.24",
    "mttr_s": "17.6",
    "resolved": "True"
   },
   {
    "stamp": "20260702-202107",
    "scenario": "combo",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "17.24",
    "quarantined_s": "17.24",
    "mttr_s": "8.7",
    "resolved": "True"
   },
   {
    "stamp": "20260703-154911",
    "scenario": "latency",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "12.66",
    "quarantined_s": "12.66",
    "mttr_s": "8.8",
    "resolved": "True"
   },
   {
    "stamp": "20260703-155011",
    "scenario": "errors",
    "pool": "baseten-l4",
    "model": "qwen3-8b",
    "detected_s": "10.61",
    "quarantined_s": "10.61",
    "mttr_s": "9.2",
    "resolved": "True"
   }
  ]
 },
 "stats": {
  "hero": {
   "blended_cost_per_mtok_usd": 2.17,
   "cost_vs_single_pool_pct": -27,
   "mttr_rolling_s": 9,
   "note": "captured live from /v1/metrics/hero during the 2026-07-03 session (screenshot + benchmarks/raw/devboard-20260703/)"
  },
  "pools": [
   {
    "id": "baseten-l4",
    "model": "Qwen3-8B-AWQ",
    "kind": "dedicated T4x8x32",
    "ttft_p50_ms": 349.8,
    "ttft_p99_ms": 484.7,
    "tpot_p50_ms": 28.6,
    "tpot_p99_ms": 34.0,
    "slo": "TTFT<500ms TPOT<60ms",
    "status": "healthy"
   },
   {
    "id": "model-api-spill",
    "model": "GLM-4.7",
    "kind": "serverless Model API",
    "ttft_p50_ms": 454.3,
    "ttft_p99_ms": 610.7,
    "tpot_p50_ms": 8.7,
    "tpot_p99_ms": 80.1,
    "slo": "TTFT<500ms TPOT<60ms",
    "status": "p99 over voice SLO (fine as spill target)"
   }
  ]
 }
};
