from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


def _tick():
    return {
        "status": "IMPROVEMENT_QUEUE_STABLE",
        "pass": True,
        "progress_count": 0,
        "actions": [],
    }


def test_assurance_claim_routes_explicitly():
    expected = {
        "schema": "PROJECT_BRAIN_CLAIM_INSTANCE_ASSURANCE_RUNTIME_V1",
        "status": "PASS__FROZEN_CLAIM_INSTANCE_ASSURANCE_CLOSED",
        "pass": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    bundle = {"schema": "BUNDLE"}
    with patch.object(fabric.claim_assurance, "evaluate", return_value=expected) as evaluate:
        with patch.object(fabric.improvement_driver, "drain", return_value=_tick()):
            out = fabric.run({
                "mode": "ASSURANCE_CLAIM",
                "payload": {"bundle": bundle},
                "options": {"learn": False},
            })
    evaluate.assert_called_once_with(bundle, repo_root=fabric.ROOT)
    assert out["status"] == "FABRIC_DISPATCH_COMPLETE", out
    assert out["inner_pass"] is True, out
    assert out["mode"] == "ASSURANCE_CLAIM", out
    assert "ASSURANCE_CLAIM" not in fabric.R3_DIRECT_EXPERIENCE_MODES


def test_assurance_claim_missing_bundle_fails_closed():
    with patch.object(fabric.claim_assurance, "evaluate") as evaluate:
        out = fabric.run({
            "mode": "ASSURANCE_CLAIM",
            "payload": {},
            "options": {"learn": False},
        })
    evaluate.assert_not_called()
    assert out["status"] == "FAIL_CLOSED", out
    assert out["pass"] is False, out
    assert "ASSURANCE_CLAIM_BUNDLE_NOT_OBJECT" in out["reason"]
