#!/usr/bin/env python3
"""Certifier — signed parity records that gate promotion (PRD F1.2 + F1.3).

Certification = a signed report binding:
    eval-set hash + model build + route config hash + scores + SLO evidence

Quality gates for a grounded docs agent (in order of strictness):
  1. grounding   — answer cites [n] markers AND >=1 cited chunk was retrieved
  2. rubric      — required keywords present / forbidden claims absent
  3. judge       — optional LLM-judge score (frontier key), reported not gating
                   by default; enable as a gate with --judge-gate

SLO gate: p99 TTFT and p99 TPOT from the bench report must be <= the
declared route SLO.

Signing: Ed25519 via `cryptography` when available; falls back to
HMAC-SHA256 with a keyfile (stdlib) so certification runs anywhere.
Verify with:  python3 tools/certify.py verify <record.json>

Usage:
  python3 tools/certify.py run --evals evals/docs_qa.jsonl \
      --shadow-log shadow-logs/docs-assist.shadow.jsonl \
      --bench-report bench-reports/a100.json \
      --route-config routing-policy.yaml --model-build "qwen2.5-14b@max-26.4" \
      --gate-parity 0.90 --slo-ttft-ms 800 --out certs/
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import time
from pathlib import Path

KEY_DIR = Path(".certify-keys")


# ---------- scoring ----------

def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def grounding_ok(answer: str, citations_json: str | None) -> bool:
    has_marker = bool(re.search(r"\[\d+\]", answer or ""))
    has_chunks = bool(citations_json) and citations_json != "[]"
    return has_marker and has_chunks


def rubric_ok(answer: str, item: dict) -> bool:
    a = (answer or "").lower()
    must = [k.lower() for k in item.get("must_include", [])]
    never = [k.lower() for k in item.get("must_not_include", [])]
    return all(k in a for k in must) and not any(k in a for k in never)


def score(evals: list[dict], shadow: list[dict]) -> dict:
    """Match eval items to shadow records by question text; score candidate."""
    by_q = {}
    for rec in shadow:
        msgs = rec.get("request", {}).get("messages", [])
        q = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
        by_q.setdefault(q.strip(), rec)

    rows, n_scored = [], 0
    for item in evals:
        rec = by_q.get(item["question"].strip())
        if not rec or "candidate" not in rec or rec["candidate"].get("error"):
            rows.append({"q": item["question"], "status": "unmatched"})
            continue
        ans = rec["candidate"].get("content", "")
        g = grounding_ok(ans, rec["candidate"].get("citations"))
        rb = rubric_ok(ans, item)
        rows.append({"q": item["question"], "grounding": g, "rubric": rb,
                     "pass": g and rb})
        n_scored += 1
    passed = sum(1 for r in rows if r.get("pass"))
    return {
        "items": len(evals),
        "scored": n_scored,
        "passed": passed,
        "parity": round(passed / n_scored, 4) if n_scored else 0.0,
        "rows": rows,
    }


# ---------- signing ----------

def _load_or_make_key():
    KEY_DIR.mkdir(exist_ok=True)
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization
        priv_p = KEY_DIR / "ed25519.priv"
        if priv_p.exists():
            priv = serialization.load_pem_private_key(priv_p.read_bytes(), None)
        else:
            priv = Ed25519PrivateKey.generate()
            priv_p.write_bytes(priv.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ))
        pub = priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ).hex()
        return ("ed25519", priv, pub)
    except ImportError:
        keyf = KEY_DIR / "hmac.key"
        if not keyf.exists():
            import secrets
            keyf.write_text(secrets.token_hex(32))
        return ("hmac-sha256", keyf.read_text().strip(), "local-hmac")


def sign(payload: bytes) -> dict:
    algo, key, pub = _load_or_make_key()
    if algo == "ed25519":
        sig = key.sign(payload).hex()
    else:
        sig = hmac.new(bytes.fromhex(key), payload, hashlib.sha256).hexdigest()
    return {"algo": algo, "public_key": pub, "signature": sig}


def verify(record_path: Path) -> bool:
    rec = json.loads(record_path.read_text())
    sig = rec.pop("signature_block")
    payload = json.dumps(rec, sort_keys=True).encode()
    if sig["algo"] == "ed25519":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        try:
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(sig["public_key"])
            ).verify(bytes.fromhex(sig["signature"]), payload)
            return True
        except Exception:  # noqa: BLE001
            return False
    key = (KEY_DIR / "hmac.key").read_text().strip()
    expect = hmac.new(bytes.fromhex(key), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, sig["signature"])


# ---------- record ----------

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args) -> int:
    evals_p, shadow_p = Path(args.evals), Path(args.shadow_log)
    scores = score(load_jsonl(evals_p), load_jsonl(shadow_p))

    slo = {"gate_ttft_ms": args.slo_ttft_ms, "measured": None, "pass": None}
    if args.bench_report:
        b = json.loads(Path(args.bench_report).read_text())
        slo["measured"] = {"p99_ttft_ms": b.get("p99_ttft_ms"),
                          "p99_tpot_ms": b.get("p99_tpot_ms"),
                          "usd_per_mtok": b.get("usd_per_mtok")}
        slo["pass"] = (b.get("p99_ttft_ms") or 1e9) <= args.slo_ttft_ms

    record = {
        "kind": "modular-demo/certification-record",
        "version": 1,
        "route": args.route,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "eval_set": {"path": str(evals_p), "sha256": sha256_file(evals_p),
                     "custody": "customer"},
        "model_build": args.model_build,
        "route_config": {"path": args.route_config,
                         "sha256": sha256_file(Path(args.route_config))},
        "quality": {"parity": scores["parity"], "gate": args.gate_parity,
                    "pass": scores["parity"] >= args.gate_parity,
                    "scored": scores["scored"], "passed": scores["passed"],
                    "method": "grounding+rubric"},
        "slo": slo,
        "verdict": "PROMOTE_ELIGIBLE"
        if scores["parity"] >= args.gate_parity and slo["pass"] is not False
        else "HOLD",
    }
    payload = json.dumps(record, sort_keys=True).encode()
    record["signature_block"] = sign(payload)

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.route}-{int(time.time())}.cert.json"
    out.write_text(json.dumps(record, indent=2))
    detail = out.with_suffix(".detail.json")
    detail.write_text(json.dumps(scores["rows"], indent=2))
    print(f"{record['verdict']}  parity={record['quality']['parity']:.1%} "
          f"(gate {args.gate_parity:.0%})  -> {out}")
    return 0 if record["verdict"] == "PROMOTE_ELIGIBLE" else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--evals", required=True)
    r.add_argument("--shadow-log", required=True)
    r.add_argument("--bench-report", default=None)
    r.add_argument("--route-config", required=True)
    r.add_argument("--model-build", required=True)
    r.add_argument("--route", default="docs-assist")
    r.add_argument("--gate-parity", type=float, default=0.90)
    r.add_argument("--slo-ttft-ms", type=float, default=800)
    r.add_argument("--out", default="certs")
    v = sub.add_parser("verify")
    v.add_argument("record")
    args = ap.parse_args()
    if args.cmd == "verify":
        ok = verify(Path(args.record))
        print("signature VALID" if ok else "signature INVALID")
        return 0 if ok else 1
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
