#!/usr/bin/env python3
"""Information-safe scope-equivalence gate for terminal proof substitution.

V1 checked declared behavior/interaction coverage. V2 adds the missing
anti-shortcut requirement: the candidate proof route must not expose any
load-bearing variable that the represented behavior is required to infer,
judge, discover, ground, rank, or synthesize.

This gate grants no capability credit. It only decides whether a proposed
replacement population is admissible as evidence for the frozen behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_SCOPE_EQUIVALENT_PROOF_GATE_V2_VERDICT"

PROOF_MODES = {
    "THEORETICAL_CEILING",
    "FORMAL_PROOF",
    "EXHAUSTIVE_FINITE_VERIFICATION",
    "PUBLIC_FIXED_BAR_SCOPE_EQUIVALENT",
    "ABSOLUTE_BEHAVIORAL_PROTOCOL",
}

RELATIONS = {
    "population": {"EXACT", "CANDIDATE_SUPERSET_PROVEN"},
    "environment": {"EXACT", "CANDIDATE_STRICTER_PROVEN"},
    "oracle": {"EXACT", "CANDIDATE_STRONGER_PROVEN"},
}

INFORMATION_RELATIONS = {
    "EXACT_CANDIDATE_VISIBLE_INFORMATION",
    "CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN",
}


def _strings(value: Any, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{name} must be {'a' if not allow_empty else 'a possibly empty'} string list")
    if not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f"{name} contains invalid entries")
    vals = [x.strip() for x in value]
    if len(vals) != len(set(vals)):
        raise ValueError(f"{name} contains duplicates")
    return vals


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        required = set(_strings(data.get("required_behavior_ids"), "required_behavior_ids"))
        covered = set(_strings(data.get("candidate_behavior_ids"), "candidate_behavior_ids"))
        req_inter = set(_strings(data.get("required_interaction_ids"), "required_interaction_ids"))
        cand_inter = set(_strings(data.get("candidate_interaction_ids"), "candidate_interaction_ids"))
        inference = set(_strings(data.get("required_inference_ids"), "required_inference_ids", allow_empty=True))
        visible_derived = set(_strings(
            data.get("candidate_visible_derived_or_oracle_ids"),
            "candidate_visible_derived_or_oracle_ids",
            allow_empty=True,
        ))
        hidden_oracle = set(_strings(
            data.get("hidden_oracle_ids"), "hidden_oracle_ids", allow_empty=True
        ))
        anti_shortcuts = set(_strings(
            data.get("anti_shortcut_mutation_ids"),
            "anti_shortcut_mutation_ids",
            allow_empty=True,
        ))
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "admissible": False,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
        }

    missing_beh = sorted(required - covered)
    missing_inter = sorted(req_inter - cand_inter)
    if missing_beh:
        errors.append("MISSING_REQUIRED_BEHAVIORS:" + ",".join(missing_beh))
    if missing_inter:
        errors.append("MISSING_REQUIRED_INTERACTIONS:" + ",".join(missing_inter))

    mode = data.get("proof_mode")
    if mode not in PROOF_MODES:
        errors.append("UNAPPROVED_PROOF_MODE")

    receipts = data.get("relation_receipts")
    if not isinstance(receipts, dict):
        receipts = {}
        errors.append("RELATION_RECEIPTS_MISSING")
    for key, allowed in RELATIONS.items():
        relation = data.get(f"{key}_relation")
        if relation not in allowed:
            errors.append(f"{key.upper()}_RELATION_NOT_PROVEN")
        elif relation != "EXACT":
            receipt = receipts.get(key)
            if not isinstance(receipt, str) or not receipt.strip():
                errors.append(f"{key.upper()}_RELATION_RECEIPT_MISSING")

    info_relation = data.get("candidate_information_relation")
    if info_relation not in INFORMATION_RELATIONS:
        errors.append("CANDIDATE_INFORMATION_RELATION_NOT_PROVEN")
    if info_relation == "CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN":
        receipt = receipts.get("candidate_information")
        if not isinstance(receipt, str) or not receipt.strip():
            errors.append("CANDIDATE_INFORMATION_RELATION_RECEIPT_MISSING")

    # Core V2 law: nothing the original behavior must infer may be supplied as a
    # derived label, gold score, hidden causal identity, ideal action, support
    # classification, ground-truth ranking, or equivalent answer-bearing field.
    leaked = sorted(inference & visible_derived)
    if leaked:
        errors.append("LOAD_BEARING_INFERENCE_LEAKED_TO_CANDIDATE:" + ",".join(leaked))

    # A direct proof should keep load-bearing truth in the independent oracle
    # whenever practical. Formal/theoretical proofs are exempt because their
    # acceptance may be deductive rather than case-oracle based.
    if mode not in {"THEORETICAL_CEILING", "FORMAL_PROOF"}:
        missing_hidden = sorted(inference - hidden_oracle)
        if missing_hidden:
            errors.append("LOAD_BEARING_INFERENCE_WITHOUT_HIDDEN_ORACLE:" + ",".join(missing_hidden))
        if inference and not anti_shortcuts:
            errors.append("ANTI_SHORTCUT_MUTATIONS_MISSING")

    unresolved = data.get("unresolved_required_dimensions")
    if not isinstance(unresolved, list) or not all(isinstance(x, str) for x in unresolved):
        errors.append("UNRESOLVED_DIMENSIONS_FIELD_INVALID")
    elif unresolved:
        errors.append("UNRESOLVED_REQUIRED_DIMENSIONS:" + ",".join(sorted(set(unresolved))))

    subjective = set(data.get("required_subjective_quality_dimensions") or [])
    subjective_covered = set(data.get("candidate_subjective_quality_dimensions") or [])
    if not all(isinstance(x, str) and x for x in subjective | subjective_covered):
        errors.append("SUBJECTIVE_DIMENSION_FIELD_INVALID")
    missing_subjective = sorted(subjective - subjective_covered)
    if missing_subjective:
        errors.append("MISSING_SUBJECTIVE_QUALITY_DIMENSIONS:" + ",".join(missing_subjective))

    for key in (
        "zero_incremental_spend",
        "independent_acceptance",
        "contamination_safe",
        "candidate_route_owned_or_noncapability_jit_only",
        "candidate_does_not_receive_hidden_oracle_payload",
        "candidate_does_not_receive_reference_solution",
    ):
        if data.get(key) is not True:
            errors.append(key.upper() + "_NOT_TRUE")

    if data.get("opaque_target_capability_provider") is not False:
        errors.append("OPAQUE_TARGET_CAPABILITY_PROVIDER_NOT_FALSE")
    if data.get("target_weakened") is not False:
        errors.append("TARGET_WEAKENING_NOT_FALSE")

    source = data.get("source_private_or_nonexecutable_surface")
    candidate = data.get("candidate_proof_route")
    if not isinstance(source, str) or not source:
        errors.append("SOURCE_SURFACE_MISSING")
    if not isinstance(candidate, str) or not candidate:
        errors.append("CANDIDATE_ROUTE_MISSING")

    errors = sorted(set(errors))
    return {
        "schema": SCHEMA,
        "status": "ADMISSIBLE_SUBSTITUTION" if not errors else "FAIL_CLOSED",
        "admissible": not errors,
        "source_surface": source,
        "candidate_route": candidate,
        "proof_mode": mode,
        "required_behavior_count": len(required),
        "covered_behavior_count": len(required & covered),
        "required_interaction_count": len(req_inter),
        "covered_interaction_count": len(req_inter & cand_inter),
        "required_inference_ids": sorted(inference),
        "leaked_inference_ids": leaked,
        "errors": errors,
        "rule": (
            "SUBSTITUTE_ONLY_IF_SCOPE_IS_EQUAL_OR_STRONGER_AND_CANDIDATE_VISIBLE_"
            "INFORMATION_DOES_NOT_CONTAIN_ANY_LOAD_BEARING_INFERENCE_THE_REPRESENTED_"
            "BEHAVIOR_MUST_PRODUCE"
        ),
    }


def self_test() -> None:
    base = {
        "source_private_or_nonexecutable_surface": "PRIVATE_X",
        "candidate_proof_route": "ABSOLUTE_Y",
        "required_behavior_ids": ["B1"],
        "candidate_behavior_ids": ["B1"],
        "required_interaction_ids": ["I1"],
        "candidate_interaction_ids": ["I1"],
        "proof_mode": "ABSOLUTE_BEHAVIORAL_PROTOCOL",
        "population_relation": "EXACT",
        "environment_relation": "EXACT",
        "oracle_relation": "EXACT",
        "relation_receipts": {},
        "candidate_information_relation": "EXACT_CANDIDATE_VISIBLE_INFORMATION",
        "required_inference_ids": ["JUDGMENT"],
        "candidate_visible_derived_or_oracle_ids": [],
        "hidden_oracle_ids": ["JUDGMENT"],
        "anti_shortcut_mutation_ids": ["LEAK_JUDGMENT"],
        "unresolved_required_dimensions": [],
        "required_subjective_quality_dimensions": [],
        "candidate_subjective_quality_dimensions": [],
        "zero_incremental_spend": True,
        "independent_acceptance": True,
        "contamination_safe": True,
        "candidate_route_owned_or_noncapability_jit_only": True,
        "candidate_does_not_receive_hidden_oracle_payload": True,
        "candidate_does_not_receive_reference_solution": True,
        "opaque_target_capability_provider": False,
        "target_weakened": False,
    }
    assert evaluate(base)["admissible"] is True

    leaked = dict(base)
    leaked["candidate_visible_derived_or_oracle_ids"] = ["JUDGMENT"]
    out = evaluate(leaked)
    assert out["admissible"] is False
    assert any(x.startswith("LOAD_BEARING_INFERENCE_LEAKED") for x in out["errors"])

    missing = dict(base)
    missing["hidden_oracle_ids"] = []
    assert evaluate(missing)["admissible"] is False

    no_mut = dict(base)
    no_mut["anti_shortcut_mutation_ids"] = []
    assert evaluate(no_mut)["admissible"] is False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"status": "SELF_TEST_PASS"}, sort_keys=True))
        return 0
    if args.input is None:
        ap.error("input required unless --self-test")
    out = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["admissible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
