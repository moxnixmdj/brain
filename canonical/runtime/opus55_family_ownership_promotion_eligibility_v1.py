"""Fail-closed family-local ownership-promotion eligibility verifier.

This proves eligibility only. It grants no family credit and mutates no authority.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_BLOBS = {
    "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"7fe34915c98a416c85ac8a62aa0ae6802b2ae39c",
    "canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"e0dbd996c18bdb818693ab0d217d751594a03d0f",
    "canonical/verification/OPUS55_ACCEPTANCE_CALIBRATION_AUDIT_20261002_V3.json":"c50034c670f797d91fa443d244853071f09bd37a",
    "canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json":"60a7c1139cad315d977bf5ed97e708cc5ec3fcc7",
    "canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json":"cb3b7c4b6c4e1f2a0471c6b6be72c4ca9ebddc80",
    "canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    "canonical/runtime/delegation_whole_scope_candidate_v2.py":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
    "canonical/capabilities/opus55/OPUS55_SCOPED_SUBAGENT_DELEGATION_COORDINATION_V1.json":"92446c0ea1eb6801db58bd757ab62a24710d3b6b",
    "canonical/verification/DELEGATION_TEMPORAL_CEILING_TRANSMUTATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"5023cc222a44f99b57785f5954cc95a29b739193",
}

ROUTES = {
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING":"canonical/runtime/tool_discovery_information_safe_candidate.py",
    "SUBAGENT_DELEGATION_AND_COORDINATION":"canonical/runtime/delegation_whole_scope_candidate_v2.py",
}

ALLOWED_IMPORT_ROOTS = {
    "canonical/runtime/tool_discovery_information_safe_candidate.py":{"__future__","typing"},
    "canonical/runtime/delegation_whole_scope_candidate_v2.py":{"__future__","collections","heapq","itertools","math","typing"},
}

def _load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def _blob(rel: str) -> str:
    return subprocess.check_output(["git","hash-object",str(ROOT / rel)],text=True).strip()

def _assert_exact_blobs() -> None:
    for rel,want in EXPECTED_BLOBS.items():
        got=_blob(rel)
        assert got == want, (rel,got,want)

def _assert_stdlib_only(rel: str) -> None:
    text=(ROOT/rel).read_text(encoding="utf-8")
    compile(text,rel,"exec")
    roots=set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node,ast.Import):
            roots.update(a.name.split(".",1)[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            roots.add(node.module.split(".",1)[0])
    assert roots <= ALLOWED_IMPORT_ROOTS[rel], (rel,sorted(roots))

def _assert_witness_doc(d: dict[str, Any], family: str, expected_cases: int) -> None:
    assert d["family"] == family
    assert d["verified"] is True
    assert d["independent"] is True
    assert d["contamination_clean"] is True
    assert d["binds_frozen_protocol"] is True
    assert d["scope_relation"] == "PROVEN_STRONGER"
    assert d["closes_entire_protocol"] is True
    assert d["source_case_count"] == expected_cases
    assert d["result"]["brain_lower_bound"] == 1
    assert d["result"]["theoretical_upper_bound"] == 1
    assert d["promotion_authority"] is False

def _assert_witness(rel: str, family: str, expected_cases: int) -> None:
    _assert_witness_doc(_load(rel), family, expected_cases)

def _assert_current_prestate() -> None:
    m=_load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
    assert "2_VERIFIED_OWNED" in m["status"]
    assert m["summary"]["verified_owned_equal_or_better_capabilities"] == [
        "EXACT_SYMBOLIC_COMPUTATION",
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    ]
    rows={r["family"]:r for r in m["rows"]}
    for fam in ROUTES:
        assert rows[fam]["status"] == "OWNED_COMPONENT_NOT_FULL_FAMILY"
        assert rows[fam]["postwave_opus55_acceptance_status"].startswith("PASS_")
        assert rows[fam]["postwave_ownership_credit"].startswith("ZERO_")
    p=m["postwave_acceptance_summary"]
    assert p["calibrated_family_count"] == 4
    assert p["verified_owned_family_count"] == 2
    assert p["pending_acceptance_family_count"] == 15
    assert p["promotion_authority"] is False

def _assert_acceptance_calibration() -> None:
    a=_load("canonical/verification/OPUS55_ACCEPTANCE_CALIBRATION_AUDIT_20261002_V3.json")
    assert a["public_verifier"]["conclusion"] == "success"
    assert a["result"]["acceptance_calibrated_family_count"] == 4
    assert a["result"]["acceptance_pending_family_count"] == 15
    assert set(a["result"]["acceptance_calibrated_families"]) == {
        "EXACT_SYMBOLIC_COMPUTATION",
        "LONG_HORIZON_MEMORY_AND_CONTINUITY",
        "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "SUBAGENT_DELEGATION_AND_COORDINATION",
    }
    assert a["fresh_acceptance_cases_consumed"] == 0
    assert a["terminal_results_replayed"] == 0
    assert a["incremental_spend_usd"] == 0

def _assert_global_postconditions() -> None:
    g=_load("canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    assert g["public_verifier"]["conclusion"] == "success"
    c=g["result"]["counters"]
    assert c == {
        "donor_dependent_required_behaviors":0,
        "unresolved_verifier_mutations":0,
        "unresolved_composition_failures":0,
    }
    p=g["result"]["terminal_predicates"]
    assert all(p.values())
    assert g["incremental_spend_usd"] == 0

def _assert_family_local_ownership_substrate() -> None:
    for rel in ROUTES.values():
        _assert_stdlib_only(rel)

    scoped=_load("canonical/capabilities/opus55/OPUS55_SCOPED_SUBAGENT_DELEGATION_COORDINATION_V1.json")
    assert scoped["status"].startswith("VERIFIED_OWNED_EQUAL_OR_BETTER")
    assert all(str(v).startswith("PASS") for v in scoped["ownership_tests"].values())
    assert scoped["incremental_spend_usd"] == 0

    tool_text=(ROOT/ROUTES["TOOL_DISCOVERY_SELECTION_AND_LEARNING"]).read_text(encoding="utf-8")
    assert "proof evaluator" in tool_text
    assert "hidden capability table" in tool_text
    assert "import openai" not in tool_text.lower()
    assert "import anthropic" not in tool_text.lower()

    del_text=(ROOT/ROUTES["SUBAGENT_DELEGATION_AND_COORDINATION"]).read_text(encoding="utf-8")
    assert "hidden optimum" in del_text
    assert "import openai" not in del_text.lower()
    assert "import anthropic" not in del_text.lower()

def _assert_existing_four_family_transmutation() -> None:
    t=_load("canonical/verification/DELEGATION_TEMPORAL_CEILING_TRANSMUTATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    assert t["public_verifier"]["conclusion"] == "success"
    assert t["result"]["family_count"] == 19
    assert t["result"]["closed_family_count"] == 4
    assert t["result"]["open_family_count"] == 15
    assert "CLOSED_SET_EXACTLY_SYMBOLIC_MEMORY_TOOL_DISCOVERY_AND_DELEGATION" in t["verified"]

def verify() -> dict[str, Any]:
    _assert_exact_blobs()
    _assert_current_prestate()
    _assert_acceptance_calibration()
    _assert_global_postconditions()
    _assert_witness("canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json","TOOL_DISCOVERY_SELECTION_AND_LEARNING",180)
    _assert_witness("canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json","SUBAGENT_DELEGATION_AND_COORDINATION",132)
    _assert_family_local_ownership_substrate()
    _assert_existing_four_family_transmutation()

    contract=_load("canonical/governance/OPUS55_FAMILY_OWNERSHIP_PROMOTION_ELIGIBILITY_V1.json")
    assert contract["pre_state"]["strict_verified_owned_families"] == 2
    exp=contract["expected_eligibility_result"]
    assert exp["eligible_family_count"] == 2
    assert set(exp["eligible_families"]) == set(ROUTES)
    assert exp["projected_strict_owned_families_if_separately_promoted"] == 4
    assert exp["projected_remaining_unowned_families"] == 15
    assert exp["terminal_goal_achieved"] is False
    assert exp["no_other_family_credit"] is True
    assert contract["new_reality_units"] == 0
    assert contract["terminal_cases_replayed"] == 0
    assert contract["incremental_spend_usd"] == 0
    assert contract["promotion_authority"] is False

    return {
        "schema":"PROJECT_BRAIN_OPUS55_FAMILY_OWNERSHIP_PROMOTION_ELIGIBILITY_RESULT_V1",
        "status":"PASS__TWO_FAMILY_LOCAL_PROMOTIONS_ELIGIBLE__ZERO_REALITY__ZERO_CREDIT_UNTIL_ATOMIC_PROMOTION",
        "eligible_families":sorted(ROUTES),
        "current_strict_owned_families":2,
        "projected_strict_owned_families_after_atomic_promotion":4,
        "remaining_unowned_families_after_atomic_promotion":15,
        "terminal_goal_achieved":False,
        "new_reality_units":0,
        "terminal_cases_replayed":0,
        "incremental_spend_usd":0,
        "promotion_authority":False,
    }

if __name__ == "__main__":
    print(json.dumps(verify(),sort_keys=True))
