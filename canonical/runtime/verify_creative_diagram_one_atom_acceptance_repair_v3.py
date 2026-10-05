"""Fail-closed verifier for the one-atom creative/diagram acceptance repair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/CREATIVE_DIAGRAM_ONE_ATOM_ACCEPTANCE_REPAIR_20261005_V3.json"
SYNTHESIS = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
DIAGRAM = "DIAGRAM_SEMANTIC_LAYOUT_PRESENTATION_NONINFERIOR"

EXPECTED = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json": "07de409df048ba2e8e9598f917fa937656b2f354",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
    "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json": "0af1c2c05a3e6a5f21e33e2afb2a403eb35b7993",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json": "8206cb013b5cd0d653ffa70d1e867f8c4d4630b8",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json": "300fb663e6b598b389961ddf663d88abcd206545",
    "canonical/governance/SYNTHESIS_EXPLICIT_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_20261005_V1.json": "7804a1038e6b0f2f71aa559de63f695edefe80f0",
    "canonical/governance/SYNTHESIS_HIDDEN_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_V1.json": "ac12d96b7d060ba996f1f2672d66f05da628dd93",
    "canonical/governance/OPUS55_TARGET_COVERAGE_DOMAIN_FACTORIZATION_20261005_V1.json": "6eea5d77e85cf84d5694e4ac7bcef7970064a231",
    "canonical/governance/OPUS55_FIXED_INTERFACE_THINKING_CHANNEL_COUNTEREXAMPLE_20261005_V1.json": "3764ade3385926b92aabf1b091a4b06cf5cb7513",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py": "9476c34e34f64f0e5babd00fa2e5967f41b4f5bb",
    "canonical/runtime/svg_diagram_render_oracle_v1.py": "9a66f7d915fa6d510c9cda50b569f6e4ddd8eb25",
}


class VerificationError(RuntimeError):
    pass


def _raw(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise VerificationError(f"MISSING:{path}")
    return p.read_bytes()


def _json(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        x = json.loads(_raw(path, root))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(x, dict):
        raise VerificationError(f"NOT_OBJECT:{path}")
    return x


def _sha(path: str, root: Path = ROOT) -> str:
    b = _raw(path, root)
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def _must(cond: bool, code: str) -> None:
    if not cond:
        raise VerificationError(code)


def verify(root: Path = ROOT) -> dict[str, Any]:
    for path, expected in EXPECTED.items():
        actual = _sha(path, root)
        _must(actual == expected, f"BOUND_BLOB_DRIFT:{path}:{expected}:{actual}")

    env = _json("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json", root)
    reg = _json("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json", root)
    gap = _json("canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json", root)
    state = _json("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json", root)
    pointer = _json("canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json", root)
    scorer = _json("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json", root)
    scorer_activation = _json("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_ACTIVATION_V1.json", root)
    explicit = _json("canonical/governance/SYNTHESIS_EXPLICIT_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_20261005_V1.json", root)
    hidden = _json("canonical/governance/SYNTHESIS_HIDDEN_EVALUATOR_ROUTE_TRUTH_REPAIR_ACTIVATION_V1.json", root)
    factor = _json("canonical/governance/OPUS55_TARGET_COVERAGE_DOMAIN_FACTORIZATION_20261005_V1.json", root)
    thinking = _json("canonical/governance/OPUS55_FIXED_INTERFACE_THINKING_CHANNEL_COUNTEREXAMPLE_20261005_V1.json", root)
    candidate = _json(CANDIDATE, root)
    mechanics = _raw("canonical/runtime/html_svg_diagram_mechanics_v1.py", root).decode()
    render = _raw("canonical/runtime/svg_diagram_render_oracle_v1.py", root).decode()

    families = env.get("families")
    _must(isinstance(families, list) and len(families) == 19 and env.get("target_family_count") == 19, "FAMILY_UNIVERSE_NOT_19")

    predicates = reg.get("predicates")
    _must(isinstance(predicates, list), "REGISTRY_PREDICATES_MISSING")
    ids = [p.get("id") for p in predicates if isinstance(p, dict)]
    _must(len(predicates) == 38 and len(ids) == 38 and len(set(ids)) == 38, "REGISTRY_NOT_38_UNIQUE")
    _must(SYNTHESIS in ids, "SYNTHESIS_PREDICATE_MISSING")
    _must(DIAGRAM not in ids, "DIAGRAM_ATOM_ALREADY_PRESENT")

    current = state.get("current_acceptance") or {}
    _must(current.get("proved_atomic") == 14 and current.get("unresolved_atomic") == 24, "STATE_NOT_14_24")
    partition = state.get("current_residual_root_partition") or {}
    _must(SYNTHESIS in (partition.get("root2_only") or []), "SYNTHESIS_NOT_OPEN_ROOT2_ONLY")

    pstate = pointer.get("exact_state") or {}
    _must(pstate.get("total_families") == 19 and pstate.get("total_atomic") == 38, "POINTER_UNIVERSE_DRIFT")
    _must(pstate.get("proved_atomic") == 14 and pstate.get("unresolved_atomic") == 24 and pstate.get("terminal") is False, "POINTER_STATE_DRIFT")
    active = pointer.get("active_cut") or {}
    cut_path, cut_sha = active.get("path"), active.get("git_blob_sha")
    _must(isinstance(cut_path, str) and isinstance(cut_sha, str), "ACTIVE_CUT_POINTER_MALFORMED")
    _must(_sha(cut_path, root) == cut_sha, "ACTIVE_CUT_POINTER_BLOB_DRIFT")
    cut = _json(cut_path, root)
    groups = cut.get("current_information_positive_action_groups") or cut.get("minimum_zero_reality_action_groups")
    _must(isinstance(groups, list), "ACTIVE_CUT_GROUPS_MISSING")
    synth = [g for g in groups if isinstance(g, dict) and SYNTHESIS in (g.get("predicates") or [])]
    _must(len(synth) == 1, "SYNTHESIS_ACTIVE_GROUP_NOT_UNIQUE")
    _must("NO_MATCHED_CASE_EXECUTION" in str(synth[0].get("action") or "").upper(), "SYNTHESIS_MATCHED_EXECUTION_GUARD_MISSING")

    _must("PREEXPOSURE" in str(scorer.get("status") or "").upper(), "SYNTHESIS_SCORER_NOT_PREEXPOSURE")
    _must("BEFORE_ANY_MATCHED_CASE_EXPOSURE" in str(scorer.get("objective") or "").upper(), "PREEXPOSURE_OBJECTIVE_MISSING")
    remaining = scorer.get("remaining_after_activation_if_verified") or []
    for token in [
        "FROZEN_MATCHED_CASE_POPULATION_AND_EXPLICIT_FRESH_REALITY_AUTHORITY",
        "BRAIN_AND_OPUS_IDENTICAL_CASE_EXECUTION",
        "MATCHED_QUALITY_RESULT",
    ]:
        _must(token in remaining, f"SYNTHESIS_REMAINING_DRIFT:{token}")
    sauth = scorer_activation.get("authority") or {}
    _must(sauth.get("execution") is False and sauth.get("fresh_reality") is False, "SYNTHESIS_PREEXPOSURE_AUTHORITY_TOO_STRONG")

    _must("ABSOLUTE_CEILING" in str(explicit.get("priority_rule") or "") and "STRICT_PRIORITY" in str(explicit.get("priority_rule") or ""), "CEILING_FIRST_PRIORITY_MISSING")
    _must(explicit.get("execution_authority") is False and explicit.get("fresh_reality_authority") is False, "EXPLICIT_ROUTE_AUTHORITY_TOO_STRONG")
    _must(hidden.get("target_predicate") == SYNTHESIS, "HIDDEN_ROUTE_TARGET_DRIFT")
    _must("SYNTHESIS_PREDICATE_REMAINS_OPEN" in (hidden.get("hard_rules") or []), "HIDDEN_ROUTE_OPEN_RULE_MISSING")

    factor_state = factor.get("current_state_after_factorization") or {}
    _must(factor_state.get("target_coverage_proved") is False, "TARGET_COVERAGE_UNEXPECTEDLY_PROVED")
    _must(factor_state.get("family_role_totality_proved") is False, "FAMILY_TOTALITY_UNEXPECTEDLY_PROVED")
    condition_rule = str((factor.get("condition_handling") or {}).get("rule") or "").upper()
    _must("CREATIVITY" in condition_rule and "ACCEPTANCE_LABELS" in condition_rule, "CREATIVITY_CONDITION_FACTOR_MISSING")
    falsification = thinking.get("falsification") or {}
    _must(falsification.get("current_u_subset_a_claim_admissible") is False, "THINKING_COUNTEREXAMPLE_NOT_ACTIVE_IN_CANDIDATE_TRUTH")

    gap_state = gap.get("exact_recomputation") or {}
    _must(gap_state.get("current_registry_has_creative_generation_predicate") is False, "CREATIVE_ATOM_ALREADY_PRESENT")
    _must(gap_state.get("current_registry_has_diagram_output_quality_predicate") is False, "DIAGRAM_QUALITY_ATOM_ALREADY_PRESENT")

    _must("Content selection, layout quality, and presentation quality are explicitly outside scope." in mechanics, "MECHANICS_QUALITY_BOUNDARY_MISSING")
    for token in ["typed IR validation", "safe SVG", "structural round-trip", "real-browser render smoke"]:
        _must(token.lower() in mechanics.lower(), f"MECHANICS_TOKEN_MISSING:{token}")
    _must("real-engine render oracle" in render.lower(), "REAL_RENDER_ORACLE_MISSING")
    _must('"terminal_authority": False' in render and '"capability_credit_delta": 0' in render, "RENDER_ORACLE_CREDIT_BOUNDARY_MISSING")

    minimal = candidate.get("minimality") or {}
    _must(minimal.get("family_mutations") == 0 and minimal.get("family_count_after") == 19, "CANDIDATE_FAMILY_MUTATION_NONZERO")
    _must(minimal.get("new_atomic_predicates") == 1 and minimal.get("atomic_count_after_if_integrated") == 39, "CANDIDATE_ATOM_PROJECTION_DRIFT")
    _must(minimal.get("proved_atomic_after_if_integrated") == 14 and minimal.get("unresolved_atomic_after_if_integrated") == 25, "CANDIDATE_PROJECTION_NOT_14_25")
    _must(candidate.get("independent_verification_required") is True, "INDEPENDENT_VERIFICATION_NOT_REQUIRED")
    for k in ["scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"]:
        _must(candidate.get(k) is False, f"CANDIDATE_AUTHORITY_NONZERO:{k}")
    for k, v in (candidate.get("accounting") or {}).items():
        _must(v == 0, f"CANDIDATE_ACCOUNTING_NONZERO:{k}")

    return {
        "status": "PASS",
        "current_state": "19_FAMILIES_38_ATOMS_14_PROVED_24_UNRESOLVED_TERMINAL_FALSE",
        "family_mutations": 0,
        "creative_new_atoms": 0,
        "diagram_new_atoms": 1,
        "projected_if_integrated": "19_FAMILIES_39_ATOMS_14_PROVED_25_UNRESOLVED",
        "target_coverage_lane_decoupled_and_currently_open": True,
        "synthesis_preexposure_guard": True,
        "ceiling_first_priority": True,
        "credit_delta": 0,
        "fresh_reality": False,
        "nonclaim": "HISTORICAL_GLOBAL_NONEXPOSURE_IS_NOT_PROVED_BY_THIS CURRENT_STATE VERIFIER",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
