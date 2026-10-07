from __future__ import annotations

from canonical.runtime.dominance_sufficiency_v1 import (
    INPUT_SCHEMA,
    compile_dominance_sufficiency,
)


SHA = "a" * 40


def receipt(**flags):
    return {"path": "canonical/x.json", "git_blob_sha": SHA, **flags}


def base_doc():
    return {
        "schema": INPUT_SCHEMA,
        "hypothesis_coverage_receipt": receipt(
            scope_complete=True,
            independent_or_objective=True,
        ),
        "hypotheses": [
            {"id": "h1", "plausible": True},
            {"id": "h2", "plausible": True},
        ],
        "configurations": [
            {
                "id": "A",
                "brain_owned": True,
                "ownership_receipt": receipt(
                    donor_independent=True,
                    independent_or_objective=True,
                ),
                "bounds": {
                    "h1": {
                        "brain_lower": "1.0",
                        "comparator_upper": "0.8",
                        "bound_receipt": receipt(
                            scope_complete=True,
                            independent_or_objective=True,
                        ),
                    },
                    "h2": {
                        "brain_lower": "0.9",
                        "comparator_upper": "0.8",
                        "bound_receipt": receipt(
                            scope_complete=True,
                            independent_or_objective=True,
                        ),
                    },
                },
            }
        ],
    }


def test_passes_when_one_owned_configuration_is_noninferior_in_every_live_world():
    out = compile_dominance_sufficiency(base_doc())
    assert out["status"] == "PASS__DOMINANCE_SUFFICIENT_WITHOUT_HYPOTHESIS_DISAMBIGUATION"
    assert out["selected_configuration"] == "A"
    assert out["worst_case_margin"] == "0.1"
    assert out["additional_target_information_required_by_this_certificate"] is False


def test_different_best_actions_are_irrelevant_when_one_configuration_still_dominates():
    doc = base_doc()
    doc["hypotheses"][0]["best_action"] = "A"
    doc["hypotheses"][1]["best_action"] = "B"
    out = compile_dominance_sufficiency(doc)
    assert out["status"].startswith("PASS__DOMINANCE_SUFFICIENT")


def test_negative_margin_in_one_live_world_keeps_certificate_open():
    doc = base_doc()
    doc["configurations"][0]["bounds"]["h2"]["brain_lower"] = "0.7"
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "OPEN__NO_ROBUST_NONINFERIOR_BRAIN_OWNED_CONFIGURATION"
    assert out["additional_target_information_required_by_this_certificate"] is True


def test_non_owned_configuration_cannot_certify_dominance():
    doc = base_doc()
    doc["configurations"][0]["brain_owned"] = False
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "OPEN__NO_ROBUST_NONINFERIOR_BRAIN_OWNED_CONFIGURATION"


def test_scope_incomplete_hypothesis_set_fails_closed():
    doc = base_doc()
    doc["hypothesis_coverage_receipt"]["scope_complete"] = False
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert "HYPOTHESIS_COVERAGE_RECEIPT_SCOPE_COMPLETE_NOT_TRUE" in out["errors"]


def test_missing_live_hypothesis_bound_fails_closed():
    doc = base_doc()
    del doc["configurations"][0]["bounds"]["h2"]
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert "LIVE_HYPOTHESIS_BOUND_SET_MISMATCH" in out["errors"][0]


def test_objective_ceiling_route_is_admitted():
    doc = base_doc()
    for hid in ("h1", "h2"):
        doc["configurations"][0]["bounds"][hid]["brain_lower"] = "1"
        doc["configurations"][0]["bounds"][hid]["comparator_upper"] = "1"
    out = compile_dominance_sufficiency(doc)
    assert out["status"].startswith("PASS__DOMINANCE_SUFFICIENT")
    assert out["worst_case_margin"] == "0"


def test_donor_dependent_configuration_fails_closed():
    doc = base_doc()
    doc["configurations"][0]["ownership_receipt"]["donor_independent"] = False
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert "DONOR_INDEPENDENT_NOT_TRUE" in out["errors"][0]


def test_selects_largest_worst_case_margin_then_lexicographic_id():
    doc = base_doc()
    b = {
        "id": "B",
        "brain_owned": True,
        "ownership_receipt": receipt(
            donor_independent=True,
            independent_or_objective=True,
        ),
        "bounds": {
            hid: {
                "brain_lower": "0.95",
                "comparator_upper": "0.8",
                "bound_receipt": receipt(
                    scope_complete=True,
                    independent_or_objective=True,
                ),
            }
            for hid in ("h1", "h2")
        },
    }
    doc["configurations"].append(b)
    out = compile_dominance_sufficiency(doc)
    assert out["selected_configuration"] == "B"
    assert out["worst_case_margin"] == "0.15"


def test_nonfinite_bound_fails_closed():
    doc = base_doc()
    doc["configurations"][0]["bounds"]["h1"]["brain_lower"] = "NaN"
    out = compile_dominance_sufficiency(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert "NONFINITE" in out["errors"][0]
