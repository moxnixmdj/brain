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
