from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {\n    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json":\n        "97412c8b7b107789c01906012163d3088991f1a4",\n    "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":\n        "a1d2dac1ab98462c3505543f8047442a60017d19",
    "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":
        "cff6a95cad0027f3e142a32fd028a27566a00ea5",
    "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json":
        "333bdc8306a19f005a600a47b415a4bd9cf9868c",
    "canonical/governance/TARGET_COMPLETENESS_INFORMATION_CUT_20261007_V1.json":
        "305b16f88c19ee5046ad0eb7ba0d57da6fab740b",
    "canonical/governance/HIDDEN_EVALUATOR_DOMINANCE_BOUNDARY_V1.json":
        "094d50ef0c2a54e7bc1b9cfd7f96c1b970b8b0ca",
    "canonical/governance/HIDDEN_EVALUATOR_MONOTONE_COUPLING_DOMINANCE_V1.json":
        "678f728089a8df815153af6dd58a88894dd0671f",
    "canonical/governance/HIDDEN_EVALUATOR_TARGET_FREE_TOP_SUPPORT_DOMINANCE_V1.json":
        "69e3ac04f0158bd2309c926d606d798449633f25",
    "canonical/governance/TARGET_QUOTIENT_EXACTNESS_NECESSITY_FALSIFIER_20261006_V1.json":
        "5223989fba70e0b4772a1cbc4853b4c593f323de",
    "canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json":
        "8a235f91ad3064714fab3ea73b324487d9b7f8e5",
}

THEOREM = (
    ROOT / "canonical/governance/"
    "L1_UNIVERSAL_ABC_SEMANTIC_INFORMATION_CUT_20261007_V1.json"
)

VALID_GLOBAL_COVERAGE_ROUTES = {
    "E_EXACT_TARGET_OR_UTILITY_QUOTIENT_COMPLETENESS",
    "S_PROVED_TARGET_SUBSET_OF_A_UTILITY_RELEVANT_SUPERDOMAIN_PLUS_BRAIN_DOMINANCE_OVER_THAT_SUPERDOMAIN",
    "G_PROVED_TARGET_GENERATED_BY_A_BASIS_AND_DOMINANCE_PRESERVING_TRANSFORMS",
    "F_EXHAUSTIVE_FULL_ENUMERATION_WHEN_THE_TERMINALLY_RELEVANT_TARGET_DOMAIN_IS_FINITE_AND_FULLY_ENUMERATED",
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def global_abc_gate(
    *,
    representation_complete: bool,
    coverage_route: str | None,
    all_cells_semantically_complete: bool,
    all_cells_positive_adequacy: bool,
    all_reached_transforms_local_c: bool,
) -> bool:
    # Representation is necessary for the chosen normal form but is never
    # sufficient for target membership/order/adequacy by itself.
    if not representation_complete:
        return False
    if coverage_route not in VALID_GLOBAL_COVERAGE_ROUTES:
        return False
    return (
        all_cells_semantically_complete
        and all_cells_positive_adequacy
        and all_reached_transforms_local_c
    )


def cell_information_route(
    semantic_class: str,
    *,
    complete_evaluator: bool = False,
    positive_adequacy: bool = False,
    monotone_class_proved: bool = False,
    top_support: bool = False,
    coupling_bound: bool = False,
    target_law_equality: bool = False,
    stronger_certificate: bool = False,
) -> str:
    if stronger_certificate:
        return "STRONGER_SCOPE_COMPLETE_CERTIFICATE"

    if semantic_class == "E_EXACT":
        if complete_evaluator and positive_adequacy:
            return "TARGET_FREE_CERTIFIED"
        return "E_SEMANTICS_OR_ADEQUACY_OPEN"

    if semantic_class == "M_RESTRICTED":
        if monotone_class_proved and top_support:
            return "TARGET_FREE_CERTIFIED"
        if monotone_class_proved and coupling_bound:
            return "TARGET_RELATIVE_CERTIFIED"
        return "M_ORDER_OR_DISTRIBUTION_OPEN"

    if semantic_class == "H_SEPARATING":
        if target_law_equality:
            return "TARGET_LAW_EQUIVALENCE_CERTIFIED"
        return "TARGET_LAW_OR_STRONGER_CERTIFICATE_REQUIRED"

    if semantic_class == "X_UNCLASSIFIED":
        return "FAIL_CLOSED_UNCLASSIFIED"

    raise ValueError("UNKNOWN_SEMANTIC_CLASS")


def verify() -> dict:
    errors: list[str] = []
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append("MISSING:" + rel)
        elif blob_sha(path) != expected:
            errors.append("SOURCE_DRIFT:" + rel)

    if not THEOREM.is_file():
        errors.append("MISSING:THEOREM")
        return {"pass": False, "errors": errors, "terminal": False}

    theorem = json.loads(THEOREM.read_text(encoding="utf-8"))
    routes = set(
        theorem.get("theorems", {})
        .get("global_non_circularity", {})
        .get("admissible_global_coverage_routes", [])
    )
    if routes != VALID_GLOBAL_COVERAGE_ROUTES:
        errors.append("GLOBAL_COVERAGE_ROUTE_SET")

    if global_abc_gate(
        representation_complete=True,
        coverage_route=None,
        all_cells_semantically_complete=True,
        all_cells_positive_adequacy=True,
        all_reached_transforms_local_c=True,
    ):
        errors.append("REPRESENTATION_ALONE_FALSELY_CLOSES_ABC")

    if not global_abc_gate(
        representation_complete=True,
        coverage_route="S_PROVED_TARGET_SUBSET_OF_A_UTILITY_RELEVANT_SUPERDOMAIN_PLUS_BRAIN_DOMINANCE_OVER_THAT_SUPERDOMAIN",
        all_cells_semantically_complete=True,
        all_cells_positive_adequacy=True,
        all_reached_transforms_local_c=True,
    ):
        errors.append("SOUND_SUPERDOMAIN_ROUTE_REJECTED")

    if cell_information_route(
        "E_EXACT", complete_evaluator=True, positive_adequacy=True
    ) != "TARGET_FREE_CERTIFIED":
        errors.append("E_ROUTE")

    if cell_information_route(
        "M_RESTRICTED", monotone_class_proved=True, top_support=True
    ) != "TARGET_FREE_CERTIFIED":
        errors.append("M_TOP_SUPPORT_ROUTE")

    if cell_information_route("H_SEPARATING") != (
        "TARGET_LAW_OR_STRONGER_CERTIFICATE_REQUIRED"
    ):
        errors.append("H_BOUNDARY")

    if cell_information_route("X_UNCLASSIFIED") != "FAIL_CLOSED_UNCLASSIFIED":
        errors.append("X_BOUNDARY")

    state = theorem.get("current_state", {})\n    if state.get("independent_top_level_terminal_predicates") != [\n        "COMPLETE_SELECTED_CONTEXT_ABC",\n        "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",\n    ]:\n        errors.append("V11_TOP_LEVEL_SET")\n    if state.get("current_accepted_family_effect_mediator_residual_count") != 0:\n        errors.append("CURRENT_ACCEPTED_D_NOT_SATURATED")
    for key in (
        "semantic_classification_complete_for_all_U",
        "utility_relevant_superdomain_dominance_complete",
        "generator_closure_complete",
        "exhaustive_target_domain_complete",
        "D_closed",
        "terminal",
    ):
        if state.get(key) is not False:
            errors.append("FALSE_CLOSURE:" + key)

    hard_nonclaims = set(theorem.get("hard_nonclaims", []))
    required = {
        "NO_CLAIM_TARGET_SPECIFIC_INFORMATION_IS_GLOBALLY_REQUIRED.",
        "NO_CLAIM_TARGET_SPECIFIC_INFORMATION_IS_GLOBALLY_AVOIDABLE.",
        "NO_CLAIM_COMPLETE_SELECTED_CONTEXT_ABC_IS_CLOSED.",
        "NO_CLAIM_D_IS_CLOSED.",
        "NO_TERMINAL_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT.",
    }
    if not required <= hard_nonclaims:
        errors.append("NONCLAIM_GUARD")

    return {
        "schema": "PROJECT_BRAIN_L1_ABC_SEMANTIC_INFORMATION_CUT_VERIFIER_V1",
        "pass": not errors,
        "errors": errors,
        "representation_complete_does_not_close_abc": not errors,
        "semantic_classes": ["E_EXACT", "M_RESTRICTED", "H_SEPARATING", "X_UNCLASSIFIED"],
        "global_coverage_route_count": len(VALID_GLOBAL_COVERAGE_ROUTES),
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
