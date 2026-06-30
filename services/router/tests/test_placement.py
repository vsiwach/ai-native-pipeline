"""Placement policy — region/compliance eligibility and right-of-way."""

from router_app.placement import (ADMIT, DENY, PREEMPT, QUEUE, eligible_pools,
                                   plan_admission)

POLICY = {
    "capacity_preference": ["cheapest"],
    "compliance": {"regimes": ["hipaa", "pci"],
                   "sensitive_capacity_tags": ["sensitive"]},
    "pools": [
        {"id": "gcp-us", "region": "us-central1", "provider": "gcp-cloudrun-cpu",
         "cold_start_s": 8, "cost_rank": 1, "tags": []},
        {"id": "aws-us", "region": "us-east-1", "provider": "aws-apprunner-cpu",
         "cold_start_s": 12, "cost_rank": 2, "tags": []},
        {"id": "gcp-hipaa", "region": "us-central1", "provider": "gcp-cloudrun-cpu",
         "cold_start_s": 10, "cost_rank": 3, "tags": ["sensitive"],
         "compliance_regimes": ["hipaa"]},
    ],
}


def test_compliance_request_denied_ordinary_capacity():
    pools = eligible_pools({"compliance": "hipaa"}, POLICY)
    ids = [p["id"] for p in pools]
    assert ids == ["gcp-hipaa"]              # only matching sensitive capacity
    assert "gcp-us" not in ids and "aws-us" not in ids


def test_non_compliant_request_prefers_ordinary_then_sensitive_last():
    pools = eligible_pools({}, POLICY)
    ids = [p["id"] for p in pools]
    assert ids[-1] == "gcp-hipaa"            # sensitive ranked last for filler
    assert set(ids[:2]) == {"gcp-us", "aws-us"}


def test_region_preference_orders_in_region_first():
    pools = eligible_pools({"region": "us-east-1"}, POLICY)
    assert pools[0]["region"] == "us-east-1"


def test_admit_when_capacity_available():
    plan = plan_admission({"compliance": "hipaa"}, POLICY["pools"][2],
                          occupants=[], capacity=2, policy=POLICY)
    assert plan["action"] == ADMIT


def test_compliance_preempts_non_compliant_on_full_sensitive_pool():
    occupants = [{"id": "job-A", "compliance": None},
                 {"id": "job-B", "compliance": None}]
    plan = plan_admission({"compliance": "hipaa"}, POLICY["pools"][2],
                          occupants=occupants, capacity=2, policy=POLICY)
    assert plan["action"] == PREEMPT
    assert plan["victim"] == "job-A"


def test_compliance_queues_when_sensitive_pool_full_of_compliant_work():
    occupants = [{"id": "job-A", "compliance": "hipaa"},
                 {"id": "job-B", "compliance": "hipaa"}]
    plan = plan_admission({"compliance": "hipaa"}, POLICY["pools"][2],
                          occupants=occupants, capacity=2, policy=POLICY)
    assert plan["action"] == QUEUE


def test_compliance_denied_on_non_matching_pool():
    plan = plan_admission({"compliance": "pci"}, POLICY["pools"][2],  # hipaa pool
                          occupants=[], capacity=2, policy=POLICY)
    assert plan["action"] == DENY
