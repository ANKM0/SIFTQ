import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from loop_eval.human_rate import classify_cause, summarize


def test_classify_cause_uses_feedback_and_blocked_reason() -> None:
    assert classify_cause({"last_feedback": "unknown"}) == "routing"
    assert classify_cause({"last_feedback": "verification_fix"}) == "verification"
    assert classify_cause({"last_feedback": "review_human"}) == "review"
    assert classify_cause({"last_feedback": "product_feedback"}) == "spec_product"
    assert classify_cause({"last_feedback": "model_limit"}) == "model_infra"
    assert classify_cause({"blocked_reason": "path outside agent write scope"}) == "permission"
    assert classify_cause({"status": "failed"}) == "model_infra"


def test_summarize_computes_rates_and_causes() -> None:
    states = [
        {"status": "done", "updated_at": "2026-09-01T00:00:00+00:00"},
        {"status": "done", "updated_at": "2026-09-02T00:00:00+00:00"},
        {"status": "human", "last_feedback": "unknown", "updated_at": "2026-09-03T00:00:00+00:00"},
        {"status": "human", "last_feedback": "verification_fix", "updated_at": "2026-08-03T00:00:00+00:00"},
        {"status": "failed", "updated_at": "2026-08-04T00:00:00+00:00"},
        {"status": "running", "updated_at": "2026-09-05T00:00:00+00:00"},
    ]

    summary = summarize(states)

    assert summary["total"] == 5
    assert summary["done"] == 2
    assert summary["human"] == 2
    assert summary["failed"] == 1
    assert summary["closure_rate"] == 0.4
    assert summary["human_rate"] == 0.4
    assert summary["human_causes"]["routing"] == 1
    assert summary["human_causes"]["verification"] == 1
    assert summary["monthly"]["2026-09"]["total"] == 3
    assert summary["monthly"]["2026-09"]["human"] == 1
    assert summary["monthly"]["2026-08"]["human"] == 1
