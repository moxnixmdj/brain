from unittest.mock import patch

from canonical.runtime.universal_escape_resolver_v1 import resolve


def test_unbound_escape_membership_fails_before_any_planning():
    with patch("canonical.runtime.universal_escape_resolver_v1.ul.route") as planner:
        out = resolve(
            escape_cell_id="e1",
            escape_membership_bound=False,
            admission_candidates={},
            v9_args={},
        )
    assert out["pass"] is False
    assert out["reason"] == "ESCAPE_MEMBERSHIP_NOT_BOUND"
    planner.assert_not_called()


def test_source_positive_admission_short_circuits_learning():
    with patch("canonical.runtime.universal_escape_resolver_v1.source_db.evaluate") as gate, patch(
        "canonical.runtime.universal_escape_resolver_v1.ul.route"
    ) as planner:
        gate.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "status": "PASS__SOURCE_PROVED_POSITIVE_ADEQUACY_CELL_ADMISSIBLE_TO_D_B",
            "cell_id": "e1",
            "selected_policy_id": "p1",
        }
        out = resolve(
            escape_cell_id="e1",
            escape_membership_bound=True,
            admission_candidates={
                "D_SOURCE_POSITIVE_ADEQUACY": {
                    "route": "D_SOURCE_POSITIVE_ADEQUACY",
                    "payload": {"cell_id": "e1"},
                }
            },
            v9_args={},
        )
    assert out["pass"] is True
    assert out["selected_admission_route"] == "D_SOURCE_POSITIVE_ADEQUACY"
    assert out["universal_learning_invoked"] is False
    planner.assert_not_called()


def test_existing_semantic_elision_admission_short_circuits_learning():
    with patch("canonical.runtime.universal_escape_resolver_v1.db.evaluate") as gate, patch(
        "canonical.runtime.universal_escape_resolver_v1.ul.route"
    ) as planner:
        gate.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "status": "PASS__CELL_ADMISSIBLE_TO_D_B_VIA_B_ROBUST_COMMON_POLICY",
            "cell_id": "e1",
            "policy_id": "p1",
        }
        out = resolve(
            escape_cell_id="e1",
            escape_membership_bound=True,
            admission_candidates={
                "B_ROBUST_COMMON_POLICY": {
                    "route": "B_ROBUST_COMMON_POLICY",
                    "payload": {},
                }
            },
            v9_args={},
        )
    assert out["pass"] is True
    assert out["db_admission_authorized"] is True
    assert out["selected_admission_route"] == "B_ROBUST_COMMON_POLICY"
    assert out["universal_learning_invoked"] is False
    planner.assert_not_called()


def test_wrong_cell_admission_cannot_promote_escape_cell():
    with patch("canonical.runtime.universal_escape_resolver_v1.db.evaluate") as gate, patch(
        "canonical.runtime.universal_escape_resolver_v1.ul.route"
    ) as planner:
        gate.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "status": "PASS",
            "cell_id": "some-other-cell",
            "policy_id": "p1",
        }
        planner.return_value = {
            "route": "LEARN",
            "next_action": {"type": "SAFE_PROBE", "id": "q"},
        }
        out = resolve(
            escape_cell_id="e1",
            escape_membership_bound=True,
            admission_candidates={
                "B_ROBUST_COMMON_POLICY": {
                    "route": "B_ROBUST_COMMON_POLICY",
                    "payload": {},
                }
            },
            v9_args={},
        )
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False
    assert out["universal_learning_invoked"] is True
    assert out["learning_next_action"]["id"] == "q"


def test_planning_never_mints_admission_credit():
    with patch("canonical.runtime.universal_escape_resolver_v1.ul.route") as planner:
        planner.return_value = {
            "route": "PROOF_SUFFICIENT_NO_EMPIRICAL_LEARNING",
            "next_action": {"type": "USE_PROOF_CLOSURE_OR_EXECUTE_SEPARATELY_VERIFIED_CAPABILITY"},
        }
        out = resolve(
            escape_cell_id="e1",
            escape_membership_bound=True,
            admission_candidates={},
            v9_args={},
        )
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
