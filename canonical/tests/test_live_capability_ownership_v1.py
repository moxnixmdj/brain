from __future__ import annotations

import json
import tempfile
from pathlib import Path

from canonical.runtime import live_capability_ownership_v1 as o


def test_manifest_is_fail_closed_provider_ontology():
    manifest = o._load_manifest()
    assert manifest["default"] == "NOT_LIVE_OWNED_UNLESS_D_FINAL_CERTIFIED"
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


def test_empty_dynamic_skill_state_is_structurally_valid_but_ownership_is_d_final_gated():
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
        assert out["providers"]["ACTIVE_VERIFIED_LEARNED_SKILLS"]["count"] == 0
        assert out["structurally_admitted_equals_fabric_reachable"] is True
        assert set(out["live_owned_capability_ids"]).issubset(
            set(out["live_admitted_capability_ids"])
        )
        assert out["live_owned_capability_count"] <= out["live_admitted_capability_count"]
        assert (
            out["live_owned_capability_count"] + out["d_final_missing_capability_count"]
            == out["live_admitted_capability_count"]
        )
        assert out["experimental_execution_without_ownership_permitted"] is True
        if out["d_final_missing_capability_count"]:
            assert out["pass"] is False
            assert out["r1_structural_closure"] is False
            assert out["d_final_coverage_complete"] is False
