from canonical.runtime.external_side_effect_admission_v1 import (
    blocker_lease_key,
    evaluate,
)

GEN = "2026-10-09"
TARGET = "CODING_FRONTIERCODE_GE_54_4"
BLOCKER = "FRONTIERCODE_OWNER_INTAKE_AND_ZERO_COST_UNBOUND"
LEASE = blocker_lease_key(GEN, TARGET, BLOCKER)

DISTINCTIONS = [
    "EXACT_INTAKE_CHANNEL",
    "CONFIGURED_SYSTEM_ELIGIBILITY",
    "ACCEPTED_HARNESS_INTERFACE",
    "ZERO_COST_TERMS",
]


def cut(action_id="owner-query"):
    return {
        "distinctions": DISTINCTIONS,
        "already_resolved": [],
        "observations": [
            {
                "id": action_id,
                "covers": DISTINCTIONS,
                "cost": 1.0,
            }
        ],
    }


def payload(action_id="owner-query"):
    return {
        "canonical_generation": GEN,
        "capability_target": TARGET,
        "causal_blocker": BLOCKER,
        "proposed_action": {
            "action_id": action_id,
            "requested_distinctions": DISTINCTIONS,
        },
        "prior_actions": [],
        "minimum_reality_cut": cut(action_id),
    }


def test_no_prior_action_and_exact_minimum_cut_admits():
    out = evaluate(payload())
    assert out["pass"] is True, out
    assert out["admitted"] is True
    assert out["duplicate_prior_action_count"] == 0


def test_frontiercode_prior_owner_inquiry_blocks_duplicate_while_waiting():
    p = payload("oct9-general-contact")
    p["prior_actions"] = [{
        "action_id": "oct3-owner-inquiry",
        "blocker_lease_key": LEASE,
        "state": "EVENT_WAIT_ONLY",
        "awaiting_external_event": True,
        "requested_distinctions": DISTINCTIONS,
        "source_path": (
            "canonical/governance/"
            "FRONTIERCODE_HOSTED_EVALUATION_INQUIRY_FIXED_POINT_20261008_V1.json"
        ),
    }]
    out = evaluate(p)
    assert out["pass"] is False, out
    assert out["status"] == (
        "BLOCKED__DUPLICATE_EXTERNAL_SIDE_EFFECT__EVENT_WAIT_ONLY"
    )
    assert out["duplicate_prior_actions"][0]["action_id"] == "oct3-owner-inquiry"


def test_relabeling_recipient_does_not_evade_same_causal_lease():
    p = payload("send-to-general-contact")
    p["prior_actions"] = [{
        "action_id": "send-to-ben",
        "canonical_generation": GEN,
        "capability_target": TARGET,
        "causal_blocker": BLOCKER,
        "state": "WAITING_FOR_REPLY",
        "requested_distinctions": DISTINCTIONS,
    }]
    out = evaluate(p)
    assert out["pass"] is False, out
    assert out["blocker_lease_key"] == LEASE


def test_unverified_material_delta_does_not_reopen_duplicate():
    p = payload("new-query")
    p["prior_actions"] = [{
        "action_id": "old-query",
        "blocker_lease_key": LEASE,
        "state": "EVENT_WAIT_ONLY",
        "requested_distinctions": DISTINCTIONS,
    }]
    p["material_delta"] = {
        "verified": False,
        "changes_terminal_decision": True,
        "new_route_authoritatively_bound": True,
        "source_path": "canonical/evidence/new-route.json",
        "source_sha": "a" * 40,
    }
    out = evaluate(p)
    assert out["pass"] is False, out
    assert "MATERIAL_DELTA_NOT_VERIFIED" in out["material_delta_errors"]


def test_verified_new_owner_route_can_reopen_pending_lease_when_cut_selects_it():
    p = payload("new-official-intake")
    p["prior_actions"] = [{
        "action_id": "old-query",
        "blocker_lease_key": LEASE,
        "state": "EVENT_WAIT_ONLY",
        "requested_distinctions": DISTINCTIONS,
    }]
    p["material_delta"] = {
        "verified": True,
        "changes_terminal_decision": True,
        "new_route_authoritatively_bound": True,
        "source_path": "canonical/evidence/new-owner-intake.json",
        "source_sha": "b" * 40,
    }
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["material_delta_required"] is True
    assert out["material_delta_valid"] is True


def test_action_not_in_exact_minimum_cut_fails_closed():
    p = payload("expensive-query")
    p["minimum_reality_cut"] = {
        "distinctions": DISTINCTIONS,
        "already_resolved": [],
        "observations": [
            {
                "id": "cheaper-query",
                "covers": DISTINCTIONS,
                "cost": 1.0,
            },
            {
                "id": "expensive-query",
                "covers": DISTINCTIONS,
                "cost": 2.0,
            },
        ],
    }
    out = evaluate(p)
    assert out["pass"] is False, out
    assert "PROPOSED_ACTION_NOT_IN_EXACT_MINIMUM_REALITY_CUT" in out["errors"]


def test_query_for_already_resolved_distinctions_fails_closed():
    p = payload("redundant-query")
    p["minimum_reality_cut"] = {
        "distinctions": DISTINCTIONS,
        "already_resolved": DISTINCTIONS,
        "observations": [
            {
                "id": "redundant-query",
                "covers": DISTINCTIONS,
                "cost": 1.0,
            }
        ],
    }
    out = evaluate(p)
    assert out["pass"] is False, out
    assert "NO_REALITY_QUERY_REQUIRED" in out["errors"]
