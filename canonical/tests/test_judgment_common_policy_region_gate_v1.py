from __future__ import annotations

import copy
import hashlib

from canonical.runtime import judgment_common_policy_region_gate_v1 as gate
from canonical.runtime import judgment_control_envelope_v1 as base


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _case():
    text = "Every applicable rule must not omit a material exception before execution."
    bundle = base._base_bundle(
        text,
        "finance-common-policy",
        ["rule", "exception"],
        "APPLY_RULE",
    )
    bundle["interpretations"] = [
        {
            "id": "i1",
            "meaning": "rule applies directly",
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "which exception branch applies",
        },
        {
            "id": "i2",
            "meaning": "rule applies through exception-preserving branch",
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "which exception branch applies",
        },
    ]
    p1 = base._decision_problem(["rule", "exception"], alternative="APPLY_RULE")
    p2 = copy.deepcopy(p1)
    bundle["common_policy_region"] = {
        "schema": gate.REGION_SCHEMA,
        "interpretation_decision_problems": [
            {
                "interpretation_id": "i1",
                "meaning_sha256": _sha("rule applies directly"),
                "decision_problem": p1,
            },
            {
                "interpretation_id": "i2",
                "meaning_sha256": _sha("rule applies through exception-preserving branch"),
                "decision_problem": p2,
            },
        ],
    }
    proposal = {
        "decision": "CONCLUDE",
        "leaf_id": base.FINANCE_SUPERVISORY,
        "selected_alternative": "APPLY_RULE",
        "rule_evidence_ids": ["rule"],
        "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }
    return proposal, bundle


def test_v1_blocks_ambiguous_same_policy_case_but_common_policy_gate_passes():
    proposal, bundle = _case()
    old = base.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert old["accepted"] is False
    assert old["errors"] == [gate.UNIQUE_ERROR]

    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is True, out
    cg = out["common_policy_region_gate"]
    assert cg["pass"] is True
    assert cg["selected_policy_id"] == "APPLY_RULE"
    assert cg["surviving_interpretation_count"] == 2
    assert cg["all_other_v1_checks_preserved"] is True
    assert cg["interpretation_set_completeness_self_certified"] is False


def test_different_policy_across_interpretations_fails_closed():
    proposal, bundle = _case()
    bundle["common_policy_region"]["interpretation_decision_problems"][1][
        "decision_problem"
    ] = base._decision_problem(["rule", "exception"], alternative="DO_NOT_APPLY")

    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is False
    assert (
        out["common_policy_region_gate"]["reason"]
        == "NO_COMMON_POLICY_OVER_SURVIVING_INTERPRETATIONS"
    )


def test_missing_interpretation_problem_fails_closed():
    proposal, bundle = _case()
    bundle["common_policy_region"]["interpretation_decision_problems"].pop()
    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is False
    assert (
        out["common_policy_region_gate"]["reason"]
        == "REGION_INTERPRETATION_DOMAIN_MISMATCH"
    )


def test_meaning_binding_mismatch_fails_closed():
    proposal, bundle = _case()
    bundle["common_policy_region"]["interpretation_decision_problems"][0][
        "meaning_sha256"
    ] = "0" * 64
    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is False
    assert out["common_policy_region_gate"]["reason"].startswith(
        "INTERPRETATION_MEANING_BINDING_MISMATCH"
    )


def test_other_v1_errors_are_never_repaired():
    proposal, bundle = _case()
    proposal["exception_evidence_ids"] = ["not-contributing"]
    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is False
    assert (
        out["common_policy_region_gate"]["reason"]
        == "V1_HAS_NONREPAIRABLE_ERRORS"
    )
    assert any("EXCEPTION_EVIDENCE_IDS_NOT_CONTRIBUTING" in x for x in out["errors"])


def test_unique_case_delegates_to_v1_without_common_policy_override():
    proposal, bundle = _case()
    bundle["interpretations"] = [bundle["interpretations"][0]]
    bundle.pop("common_policy_region")
    out = gate.configured_terminal_decision(proposal, bundle, mode="FINANCE")
    assert out["accepted"] is True, out
    assert out["common_policy_region_gate"]["status"] == "NOT_NEEDED__V1_ALREADY_ACCEPTED"
