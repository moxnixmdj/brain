from canonical.runtime.u_scope_complete_depletion_orchestrator_v1 import evaluate


def test_whole_region_common_policy_authorizes_u_subtraction():
    out = evaluate({
        "region_id": "R",
        "scope_complete": True,
        "cells": [
            {"world_id": "w1", "membership_proved": True},
            {"world_id": "w2", "membership_proved": True},
        ],
        "policy_regions": [{
            "policy_id": "P",
            "world_ids": ["w1", "w2"],
            "adequacy_proved": True,
            "independent_or_objective": True,
        }],
        "observations": [],
    })
    assert out["pass"] is True
    assert out["u_subtraction_authorized"] is True
    assert out["status"] == "PASS__WHOLE_REGION_COMMON_POLICY_CLOSED"


def test_scope_incomplete_never_authorizes_subtraction():
    out = evaluate({
        "region_id": "R",
        "scope_complete": False,
        "cells": [{"world_id": "w1", "membership_proved": True}],
        "policy_regions": [{
            "policy_id": "P",
            "world_ids": ["w1"],
            "adequacy_proved": True,
            "independent_or_objective": True,
        }],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["u_subtraction_authorized"] is False
    assert out["reason"] == "SCOPE_COMPLETENESS_UNPROVED"


def test_no_common_policy_returns_minimum_discriminator_not_fake_closure():
    out = evaluate({
        "region_id": "R",
        "scope_complete": True,
        "cells": [
            {"world_id": "w1", "membership_proved": True},
            {"world_id": "w2", "membership_proved": True},
        ],
        "policy_regions": [
            {
                "policy_id": "P1",
                "world_ids": ["w1"],
                "adequacy_proved": True,
                "independent_or_objective": True,
            },
            {
                "policy_id": "P2",
                "world_ids": ["w2"],
                "adequacy_proved": True,
                "independent_or_objective": True,
            },
        ],
        "observations": [{
            "observation_id": "q",
            "cost_units": 1,
            "outcome_map_complete": True,
            "outcomes": {"w1": False, "w2": True},
        }],
    })
    assert out["pass"] is True
    assert out["status"] == "PASS__MINIMUM_TRUTHFUL_DISCRIMINATOR_PLAN"
    assert out["first_observation_id"] == "q"
    assert out["u_subtraction_authorized"] is False


def test_policy_adequacy_cannot_self_certify():
    out = evaluate({
        "region_id": "R",
        "scope_complete": True,
        "cells": [{"world_id": "w1", "membership_proved": True}],
        "policy_regions": [{
            "policy_id": "P",
            "world_ids": ["w1"],
            "adequacy_proved": False,
            "independent_or_objective": True,
        }],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["u_subtraction_authorized"] is False
    assert out["reason"] == "POLICY_ADEQUACY_UNPROVED:P"
