from __future__ import annotations

import json
import tempfile
from pathlib import Path

from canonical.runtime import live_capability_ownership_v1 as o


def test_manifest_is_fail_closed_provider_ontology():
    manifest = o._load_manifest()
    assert manifest["default"] == "NOT_LIVE_OWNED_UNLESS_ADMITTED_BY_ONE_PROVIDER"
    assert set(manifest["providers"]) == set(o.EXPECTED_PROVIDERS)


def test_h100_historical_id_collision_is_disambiguated_by_route():
    ids, collisions = o._h100_owned_ids([
        {"capability_id": "CAP_X", "route": "ROUTE_A"},
        {"capability_id": "CAP_X", "route": "ROUTE_B"},
        {"capability_id": "CAP_Y", "route": "ROUTE_C"},
    ])
    assert ids == [
        "h100:CAP_X@ROUTE_A",
        "h100:CAP_X@ROUTE_B",
        "h100:CAP_Y",
    ]
    assert collisions == [{
        "capability_id": "CAP_X",
        "row_count": 2,
        "routes": ["ROUTE_A", "ROUTE_B"],
        "ownership_ids": ["h100:CAP_X@ROUTE_A", "h100:CAP_X@ROUTE_B"],
    }]


def test_active_skill_selector_rejects_unverified_active_skill():
    state = {
        "skills": {
            "skill:x": {
                "active": True,
                "skill": {"verified_skill": False, "reuse_authorized": True},
            }
        }
    }
    try:
        o._active_skill_ids(state)
    except o.LiveOwnershipError as exc:
        assert "ACTIVE_SKILL_NOT_VERIFIED" in str(exc)
    else:
        raise AssertionError("expected fail-closed active skill rejection")


def test_current_authority_and_receipt_bindings_are_exact():
    out = o._authority_binding_check()
    assert out["pass"] is True, out
    assert out["mismatch_count"] == 0
    assert out["checked_binding_count"] > 12


def test_authority_binding_fails_closed_on_tampered_hash():
    pointer = json.loads(o.AUTHORITY_PATH.read_text(encoding="utf-8"))
    pointer["live_capability_ownership_20261008_v1"]["unified_fabric"]["git_blob_sha"] = "0" * 40
    with tempfile.TemporaryDirectory() as td:
        tampered = Path(td) / "CURRENT_TERMINAL_AUTHORITY.json"
        tampered.write_text(json.dumps(pointer), encoding="utf-8")
        out = o._authority_binding_check(authority_path=tampered)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__R1_AUTHORITY_OR_RECEIPT_DRIFT"
    assert any(
        row.get("field") == "unified_fabric"
        and row.get("reason") == "GIT_BLOB_SHA_MISMATCH"
        for row in out["mismatches"]
    )


def test_empty_dynamic_skill_state_is_valid_provider():
    with tempfile.TemporaryDirectory() as td:
        state_path = Path(td) / "state.json"
        state_path.write_text(json.dumps({
            "schema": "PROJECT_BRAIN_SELF_IMPROVEMENT_STATE_V1",
            "version": 1,
            "episodes": {},
            "skills": {},
            "pareto_frontiers": {},
            "failures": {},
            "reuse": {},
            "stats": {
                "verified_episode_count": 0,
                "verified_skill_count": 0,
                "active_skill_count": 0,
                "failure_class_count": 0,
            },
        }), encoding="utf-8")
        out = o.evaluate(
            {
                "RAW_GOAL": "x",
                "BOUND_CAPABILITY": "x",
                "LEARNING_EPISODE": "x",
                "H100_INFERENCE": "x",
                "CERTIFIED_ROUTE": "x",
            },
            self_improvement_state_path=state_path,
        )
        # Other direct engine modes may be absent from this synthetic descriptor set,
        # but every provider carrier above is present.
        assert out["pass"] is True
        assert out["live_owned_equals_fabric_reachable"] is True
        assert out["providers"]["ACTIVE_VERIFIED_LEARNED_SKILLS"]["count"] == 0
