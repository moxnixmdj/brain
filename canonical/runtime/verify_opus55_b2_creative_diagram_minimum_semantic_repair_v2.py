"""Fail-closed current-state verifier for the V2 creative/diagram repair candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json": "07de409df048ba2e8e9598f917fa937656b2f354",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json": "37c58301f1e002a200dc93a2e7d771cd1ffc5dcb",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15_ACTIVATION_V1.json": "e4667972a22e8e1c60aaa4542950abc68e89067c",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json": "300fb663e6b598b389961ddf663d88abcd206545",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json": "8206cb013b5cd0d653ffa70d1e867f8c4d4630b8",
    "canonical/governance/OPUS55_FUNCTIONAL_ROLE_BASIS_TARGET_DISCOVERY_FALSIFICATION_ACTIVATION_20261005_V1.json": "1898ecf493d21b340e9de7f62a71880f5d0b90f5",
    "canonical/governance/OPUS55_TARGET_DISCOVERY_COMPLETENESS_CERTIFICATE_V1_ACTIVATION_V1.json": "8382da2ed68c531e596f0cbe424f7028d30eae50",
    "canonical/governance/TERMINAL_FRONTIER_COMPILER_V2.json": "cfdebaf429e66f118b5e9bccc147feb1f054ed01",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py": "9476c34e34f64f0e5babd00fa2e5967f41b4f5bb",
}
CANDIDATE = "canonical/governance/OPUS55_B2_CREATIVE_DIAGRAM_MINIMUM_SEMANTIC_REPAIR_20261005_V2.json"
SYNTHESIS = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
DIAGRAM = "DIAGRAM_SEMANTIC_LAYOUT_PRESENTATION_NONINFERIOR"


class VerifyError(RuntimeError):
    pass


def raw(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise VerifyError(f"MISSING:{path}")
    return p.read_bytes()


def load(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        x = json.loads(raw(path, root))
    except json.JSONDecodeError as exc:
        raise VerifyError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(x, dict):
        raise VerifyError(f"NOT_OBJECT:{path}")
    return x


def blob(path: str, root: Path = ROOT) -> str:
    b = raw(path, root)
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def req(cond: bool, code: str) -> None:
    if not cond:
        raise VerifyError(code)


def verify(root: Path = ROOT) -> dict[str, Any]:
    for path, expected in FILES.items():
        actual = blob(path, root)
        req(actual == expected, f"BLOB_DRIFT:{path}:{expected}:{actual}")

    env = load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json", root)
    reg = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json", root)
    gap = load("canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json", root)
    state = load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json", root)
    cut = load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15.json", root)
    cut_activation = load("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_V15_ACTIVATION_V1.json", root)
    scorer_activation = load("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json", root)
    scorer = load("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json", root)
    role_guard = load("canonical/governance/OPUS55_FUNCTIONAL_ROLE_BASIS_TARGET_DISCOVERY_FALSIFICATION_ACTIVATION_20261005_V1.json", root)
    w4 = load("canonical/governance/OPUS55_TARGET_DISCOVERY_COMPLETENESS_CERTIFICATE_V1_ACTIVATION_V1.json", root)
    finality = load("canonical/governance/TERMINAL_FRONTIER_COMPILER_V2.json", root)
    candidate = load(CANDIDATE, root)
    mechanics = raw("canonical/runtime/html_svg_diagram_mechanics_v1.py", root).decode("utf-8")

    families = env.get("families")
    req(isinstance(families, list) and len(families) == 19 and env.get("target_family_count") == 19, "NOT_EXACT_19_FAMILIES")

    predicates = reg.get("predicates")
    req(isinstance(predicates, list), "REGISTRY_MISSING")
    ids = [str(p.get("id")) for p in predicates if isinstance(p, dict)]
    req(len(predicates) == 38 and len(ids) == 38 and len(set(ids)) == 38, "NOT_EXACT_38_UNIQUE")
    req(SYNTHESIS in ids, "SYNTHESIS_ATOM_MISSING")
    req(DIAGRAM not in ids, "PROPOSED_DIAGRAM_ATOM_ALREADY_EXISTS")

    current = state.get("current_acceptance") or {}
    req(current.get("proved_atomic") == 14 and current.get("unresolved_atomic") == 24, "NOT_CURRENT_14_24")
    partition = state.get("current_residual_root_partition") or {}
    req(SYNTHESIS in (partition.get("root2_only") or []), "SYNTHESIS_NOT_UNRESOLVED_ROOT2_ONLY")

    groups = cut.get("current_information_positive_action_groups")
    req(isinstance(groups, list), "V15_GROUPS_MISSING")
    f = [x for x in groups if isinstance(x, dict) and x.get("id") == "F_SYNTHESIS_COMPARATOR_CAPACITY_OR_STRONGER_PROOF"]
    req(len(f) == 1 and f[0].get("predicates") == [SYNTHESIS], "V15_SYNTHESIS_GROUP_DRIFT")
    action = str(f[0].get("action") or "").upper()
    req("NO_MATCHED_CASE_EXECUTION_YET" in action, "V15_NO_EXECUTION_GUARD_MISSING")
    req(cut_activation.get("scheduling_authority") is True, "V15_NOT_ACTIVE_SCHEDULING")
    req(cut_activation.get("execution_authority") is False and cut_activation.get("fresh_reality_authority") is False, "V15_AUTHORITY_TOO_STRONG")

    req("PREEXPOSURE" in str(scorer_activation.get("status") or "").upper(), "SCORER_NOT_PREEXPOSURE")
    auth = scorer_activation.get("authority") or {}
    req(auth.get("execution") is False and auth.get("promotion") is False and auth.get("fresh_reality") is False, "SCORER_ACTIVATION_AUTHORITY_TOO_STRONG")
    remaining = scorer.get("remaining_after_activation_if_verified") or []
    for token in [
        "FROZEN_MATCHED_CASE_POPULATION_AND_EXPLICIT_FRESH_REALITY_AUTHORITY",
        "BRAIN_AND_OPUS_IDENTICAL_CASE_EXECUTION",
        "MATCHED_QUALITY_RESULT",
    ]:
        req(token in remaining, f"SCORER_REMAINING_DRIFT:{token}")
    req("BEFORE_ANY_MATCHED_CASE_EXPOSURE" in str(scorer.get("objective") or "").upper(), "SCORER_PREEXPOSURE_OBJECTIVE_MISSING")
    req("NO_TERMINAL_CASE_GENERATION_OR_EXPOSURE" in (scorer.get("hard_rules") or []), "SCORER_NO_EXPOSURE_RULE_MISSING")

    role_truth = role_guard.get("active_truth") or {}
    req(role_truth.get("functional_role_basis_alone_proves_target_discovery_complete") is False, "ROLE_TAXONOMY_FALSE_SHORTCUT_REOPENED")
    req(role_truth.get("literal_target_discovery_complete") is False, "ROLE_TAXONOMY_LITERAL_FINALITY_REOPENED")

    req(w4.get("scheduling_authority") is True, "W4_DISCOVERY_COVERAGE_NOT_ACTIVE")
    req("NO_CLAIM_TERMINAL_TRUE" in (w4.get("hard_nonclaims") or []), "W4_TERMINAL_NONCLAIM_MISSING")

    truth = finality.get("current_recomputed_truth") or {}
    req(truth.get("target_discovery_complete") is False and truth.get("terminal") is False, "LITERAL_FINALITY_GUARD_NOT_FALSE")
    w4_boundary = finality.get("repair", {}).get("w4_boundary") or {}
    req("NOT_STANDALONE_LITERAL_FINALITY_WITNESS" in str(w4_boundary.get("state") or ""), "W4_LITERAL_BOUNDARY_MISSING")

    recompute = gap.get("exact_recomputation") or {}
    req(recompute.get("current_registry_has_creative_generation_predicate") is False, "CREATIVE_ATOM_PREEXISTS")
    req(recompute.get("current_registry_has_diagram_output_quality_predicate") is False, "DIAGRAM_QUALITY_ATOM_PREEXISTS")

    req("Content selection, layout quality, and presentation quality are explicitly outside scope." in mechanics, "DIAGRAM_MECHANICS_SCOPE_BOUNDARY_MISSING")
    for token in ["typed IR validation", "safe SVG", "structural round-trip", "real-browser render smoke"]:
        req(token.lower() in mechanics.lower(), f"DIAGRAM_MECHANICS_CEILING_TOKEN_MISSING:{token}")

    req(candidate.get("independent_verification_required") is True, "CANDIDATE_INDEPENDENCE_MISSING")
    for k in ["scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"]:
        req(candidate.get(k) is False, f"CANDIDATE_AUTHORITY_NONZERO:{k}")
    for k, v in (candidate.get("accounting") or {}).items():
        req(v == 0, f"CANDIDATE_ACCOUNTING_NONZERO:{k}")
    minimal = candidate.get("minimality") or {}
    req(minimal.get("family_count_after") == 19, "PROJECTED_FAMILY_COUNT_NOT_19")
    req(minimal.get("atomic_count_after_if_integrated") == 39, "PROJECTED_ATOMIC_COUNT_NOT_39")
    req(minimal.get("proved_atomic_after_if_integrated") == 14, "PROJECTED_PROVED_NOT_14")
    req(minimal.get("unresolved_atomic_after_if_integrated") == 25, "PROJECTED_UNRESOLVED_NOT_25")
    proposed = candidate.get("breakthrough", {}).get("diagram", {}).get("new_atomic_obligation") or {}
    req(proposed.get("id") == DIAGRAM, "PROPOSED_DIAGRAM_ID_DRIFT")

    return {
        "status": "PASS",
        "verified_current_state": "19_FAMILIES__38_ATOMS__14_PROVED__24_UNRESOLVED",
        "synthesis_predicate": "UNRESOLVED_PREEXPOSURE",
        "diagram_mechanics": "DETERMINISTIC_CEILING_BOUND__SEMANTIC_LAYOUT_PRESENTATION_EXCLUDED",
        "w4": "TOP_LEVEL_DISCOVERY_COVERAGE_ONLY__NOT_LITERAL_FINALITY",
        "candidate_projection_if_later_integrated": "19_FAMILIES__39_ATOMS__14_PROVED__25_UNRESOLVED",
        "credit_delta": 0,
        "fresh_reality": False,
        "important_nonclaim": "THIS_VERIFIER_DOES_NOT_PROVE_HISTORICAL_NONEXPOSURE_OUTSIDE_THE_BOUND_CANONICAL_PREEXPOSURE_STATE; SEPARATE_INDEPENDENT_VERIFICATION_REMAINS_REQUIRED",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
