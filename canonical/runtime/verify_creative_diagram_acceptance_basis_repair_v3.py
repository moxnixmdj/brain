"""Fail-closed verifier for CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V3_20261005."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V3_20261005.json"
CREATIVE_ATOM = "CREATIVE_TEXT_GENERATION_QUALITY_NONINFERIOR"

EXPECTED = {
    "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V2_20261005.json": "02ee9918fc38f3bdee96f847d04e7fd1337b9e46",
    "canonical/governance/STATIC_SVG_DIAGRAM_MECHANICS_KERNEL_20261005_V1.json": "5680d37569e95923c62b9292af96abad7ca39e98",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json": "8206cb013b5cd0d653ffa70d1e867f8c4d4630b8",
    "canonical/verification/CREATIVE_TEXT_METRIC_INDEPENDENCE_WOLFRAM_VERIFICATION_20261005_V1.json": "47e0782a83e5c26d265df44606f509bb32d8a35c",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json": "07de409df048ba2e8e9598f917fa937656b2f354",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json": "7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
    "canonical/runtime/html_svg_diagram_mechanics_v1.py": "9476c34e34f64f0e5babd00fa2e5967f41b4f5bb",
    "canonical/runtime/svg_diagram_render_oracle_v1.py": "9a66f7d915fa6d510c9cda50b569f6e4ddd8eb25",
}


class VerificationError(RuntimeError):
    pass


def _raw(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise VerificationError(f"MISSING_FILE:{path}")
    return p.read_bytes()


def _load(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        obj = json.loads(_raw(path, root))
    except json.JSONDecodeError as exc:
        raise VerificationError(f"INVALID_JSON:{path}:{exc}") from exc
    if not isinstance(obj, dict):
        raise VerificationError(f"NOT_OBJECT:{path}")
    return obj


def _git_blob_sha(path: str, root: Path = ROOT) -> str:
    payload = _raw(path, root)
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def _must(condition: bool, code: str) -> None:
    if not condition:
        raise VerificationError(code)


def _contract(registry: dict[str, Any], behavior_id: str) -> dict[str, Any]:
    rows = registry.get("active_contracted_residuals")
    _must(isinstance(rows, list), "BEHAVIOR_REGISTRY_ROWS_MISSING")
    hits = [row for row in rows if isinstance(row, dict) and row.get("behavior_id") == behavior_id]
    _must(len(hits) == 1, f"BEHAVIOR_IDENTITY:{behavior_id}")
    return hits[0]


def verify(root: Path = ROOT) -> dict[str, Any]:
    for path, expected in EXPECTED.items():
        actual = _git_blob_sha(path, root)
        _must(actual == expected, f"BOUND_BLOB_DRIFT:{path}:{expected}:{actual}")

    predecessor = _load("canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V2_20261005.json", root)
    kernel = _load("canonical/governance/STATIC_SVG_DIAGRAM_MECHANICS_KERNEL_20261005_V1.json", root)
    behaviors = _load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", root)
    synthesis = _load("canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json", root)
    independence = _load("canonical/verification/CREATIVE_TEXT_METRIC_INDEPENDENCE_WOLFRAM_VERIFICATION_20261005_V1.json", root)
    acceptance = _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json", root)
    gap = _load("canonical/governance/CREATIVE_DIAGRAM_TERMINAL_PROOF_BASIS_GAP_20261005_V1.json", root)
    root_state = _load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json", root)
    candidate = _load(CANDIDATE, root)
    compiler_source = _raw("canonical/runtime/html_svg_diagram_mechanics_v1.py", root).decode("utf-8")
    renderer_source = _raw("canonical/runtime/svg_diagram_render_oracle_v1.py", root).decode("utf-8")

    creative_v2 = predecessor.get("creative_text_repair") or {}
    _must(
        creative_v2.get("minimum_surviving_learned_obligation_count") == 1,
        "PREDECESSOR_CREATIVE_OBLIGATION_COUNT_DRIFT",
    )
    _must(
        creative_v2.get("minimum_surviving_learned_obligation") == "OPEN_ENDED_CREATIVE_TEXT_QUALITY",
        "PREDECESSOR_CREATIVE_OBLIGATION_IDENTITY_DRIFT",
    )

    reduction_v2 = predecessor.get("action_group_f_reduction") or {}
    _must(
        reduction_v2.get("new_broad_learned_primitive_count") == 1,
        "PREDECESSOR_TOTAL_LEARNED_PRIMITIVE_COUNT_DRIFT",
    )
    _must(
        reduction_v2.get("new_broad_learned_primitive") == CREATIVE_ATOM,
        "PREDECESSOR_CREATIVE_ATOM_DRIFT",
    )
    _must(
        reduction_v2.get("diagram_new_broad_learned_primitive_count") == 0,
        "PREDECESSOR_DIAGRAM_LEARNED_PRIMITIVE_NONZERO",
    )
    replacement = reduction_v2.get("candidate_replacement_basis") or []
    for required in [
        "CREATIVE_TEXT_GENERATION_QUALITY_NONINFERIOR",
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001__DIAGRAM_CONDITION",
        "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001__VISUAL_ENCODING_CONDITION_WHERE_APPLICABLE",
        "HTML_SVG_RENDER_STRUCTURE_MECHANICS_CEILING",
    ]:
        _must(required in replacement, f"PREDECESSOR_REPLACEMENT_BASIS_MISSING:{required}")

    parent = kernel.get("parent_repair") or {}
    parent_path = "canonical/governance/CREATIVE_DIAGRAM_ACCEPTANCE_BASIS_REPAIR_V2_20261005.json"
    _must(parent.get("path") == parent_path, "KERNEL_PARENT_PATH_DRIFT")
    _must(parent.get("git_blob_sha") == EXPECTED[parent_path], "KERNEL_PARENT_SHA_DRIFT")
    _must(
        parent.get("exact_residual") == "HTML_SVG_RENDER_STRUCTURE_MECHANICS_CEILING",
        "KERNEL_RESIDUAL_DRIFT",
    )
    _must(kernel.get("independent_verification_required") is True, "KERNEL_INDEPENDENT_VERIFICATION_NOT_REQUIRED")
    for key, value in (kernel.get("accounting") or {}).items():
        _must(value == 0, f"KERNEL_CREDIT_OR_SPEND_NONZERO:{key}")
    contract = kernel.get("behavior_contract_candidate") or {}
    boundary = str(contract.get("dependency_boundary") or "").upper()
    for token in [
        "CONTENT SELECTION",
        "SEMANTIC DIAGRAM DECOMPOSITION",
        "LAYOUT JUDGMENT",
        "READABILITY",
        "PRESENTATION QUALITY",
    ]:
        _must(token in boundary, f"KERNEL_DEPENDENCY_BOUNDARY_MISSING:{token}")

    artifact = _contract(behaviors, "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001")
    evidence = _contract(behaviors, "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001")
    _must(
        "layout" in str(artifact.get("required_output_or_action") or "").lower(),
        "ARTIFACT_JUDGMENT_LAYOUT_ROLE_MISSING",
    )
    _must(
        "evidence" in str(evidence.get("required_output_or_action") or "").lower(),
        "EVIDENCE_SYNTHESIS_SELECTION_ROLE_MISSING",
    )
    family_map = behaviors.get("family_to_residual_contracts") or {}
    _must(
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001" in (family_map.get("ARTIFACT_CREATION") or []),
        "ARTIFACT_CREATION_CONTRACT_MAPPING_MISSING",
    )
    _must(
        "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001" in (family_map.get("COMMUNICATION_AND_SYNTHESIS") or []),
        "COMMUNICATION_SYNTHESIS_CONTRACT_MAPPING_MISSING",
    )

    dimensions = ((synthesis.get("scorer_contract") or {}).get("dimensions")) or {}
    _must(isinstance(dimensions, dict), "SYNTHESIS_DIMENSIONS_MISSING")
    expected_dimensions = {
        "claim_to_source_fidelity",
        "uncertainty_and_disagreement_preservation",
        "audience_adaptation",
        "format_and_style_constraints",
        "compression_without_decision_relevant_loss",
    }
    _must(set(dimensions) == expected_dimensions, "SYNTHESIS_FROZEN_DIMENSIONS_DRIFT")
    lowered_keys = " ".join(dimensions).lower()
    for forbidden in ["creative", "novel", "originality", "imagination"]:
        _must(forbidden not in lowered_keys, f"CREATIVE_DIMENSION_ALREADY_PRESENT:{forbidden}")

    independence_subject = independence.get("subject") or {}
    synthesis_path = "canonical/governance/SYNTHESIS_DIMENSION_SCORERS_AND_STRICT_REDUCER_V1.json"
    _must(
        independence_subject.get("git_blob_sha") == EXPECTED[synthesis_path],
        "INDEPENDENCE_SUBJECT_SHA_DRIFT",
    )
    wolfram = independence.get("wolfram_result") or {}
    _must(wolfram.get("satisfiable") is True, "INDEPENDENCE_COUNTERMODEL_NOT_SATISFIABLE")
    countermodel = wolfram.get("countermodel") or {}
    for key in ["a1", "a2", "a3", "a4", "a5", "b1", "b2", "b3", "b4", "b5"]:
        _must(
            countermodel.get(key) == 1,
            f"INDEPENDENCE_COUNTERMODEL_EXISTING_DIMENSION_DRIFT:{key}",
        )
    _must(
        countermodel.get("cA") == 0 and countermodel.get("cB") == 1,
        "INDEPENDENCE_COUNTERMODEL_CREATIVE_VALUES_DRIFT",
    )
    _must(
        (independence.get("independent_verification") or {}).get("result")
        == "PASS__CONSTRUCTIVE_COUNTERMODEL_FOUND",
        "INDEPENDENCE_VERIFICATION_RESULT_DRIFT",
    )
    for key, value in (independence.get("accounting") or {}).items():
        _must(value == 0, f"INDEPENDENCE_ACCOUNTING_NONZERO:{key}")

    predicates = acceptance.get("predicates")
    _must(isinstance(predicates, list), "ACCEPTANCE_PREDICATES_MISSING")
    ids = [row.get("id") for row in predicates if isinstance(row, dict)]
    _must(
        len(predicates) == 38 and len(ids) == 38 and len(set(ids)) == 38,
        "ACCEPTANCE_REGISTRY_NOT_EXACT_38_UNIQUE",
    )
    _must(CREATIVE_ATOM not in ids, "CREATIVE_ATOM_ALREADY_PRESENT")

    recomputation = gap.get("exact_recomputation") or {}
    _must(
        recomputation.get("current_registry_has_creative_generation_predicate") is False,
        "CREATIVE_GAP_ALREADY_CLOSED",
    )
    _must(
        recomputation.get("current_registry_has_diagram_output_quality_predicate") is False,
        "DIAGRAM_GAP_REGISTRY_FACT_DRIFT",
    )

    state = root_state.get("current_acceptance") or {}
    _must(
        state.get("proved_atomic") == 14 and state.get("unresolved_atomic") == 24,
        "ROOT_STATE_NOT_14_24",
    )
    _must(state.get("terminal") is False, "ROOT_STATE_TERMINAL_UNEXPECTED")

    _must(
        "Content selection, layout quality, and presentation quality are explicitly outside scope."
        in compiler_source,
        "COMPILER_SCOPE_BOUNDARY_MISSING",
    )
    _must("Real-engine render oracle" in renderer_source, "REAL_RENDER_ORACLE_IDENTITY_MISSING")
    _must(
        '"terminal_authority": False' in renderer_source,
        "RENDER_ORACLE_TERMINAL_AUTHORITY_BOUNDARY_MISSING",
    )
    _must(
        '"capability_credit_delta": 0' in renderer_source,
        "RENDER_ORACLE_CREDIT_BOUNDARY_MISSING",
    )

    minimal = candidate.get("minimality") or {}
    _must(
        minimal.get("family_count_after") == 19 and minimal.get("family_mutations") == 0,
        "CANDIDATE_FAMILY_PROJECTION_DRIFT",
    )
    _must(minimal.get("atomic_count_after_if_integrated") == 39, "CANDIDATE_ATOMIC_PROJECTION_DRIFT")
    _must(minimal.get("proved_atomic_after_if_integrated") == 14, "CANDIDATE_PROVED_PROJECTION_DRIFT")
    _must(
        minimal.get("unresolved_atomic_after_if_integrated") == 25,
        "CANDIDATE_UNRESOLVED_PROJECTION_DRIFT",
    )
    _must(
        minimal.get("new_broad_diagram_learned_primitives") == 0,
        "CANDIDATE_DIAGRAM_LEARNED_PRIMITIVE_NONZERO",
    )
    _must(minimal.get("new_diagram_acceptance_atoms") == 0, "CANDIDATE_DIAGRAM_ATOM_NONZERO")
    _must(
        minimal.get("new_creative_text_acceptance_atoms") == 1,
        "CANDIDATE_CREATIVE_ATOM_COUNT_NOT_ONE",
    )

    verification_path = (
        "canonical/verification/CREATIVE_TEXT_METRIC_INDEPENDENCE_WOLFRAM_VERIFICATION_20261005_V1.json"
    )
    c_auth = (candidate.get("authorities") or {}).get("creative_metric_independence_verification") or {}
    _must(c_auth.get("git_blob_sha") == EXPECTED[verification_path], "CANDIDATE_INDEPENDENCE_BINDING_DRIFT")
    logical = (candidate.get("creative_text_reduction") or {}).get("logical_independence_verification") or {}
    _must(
        logical.get("result") == "PASS__CONSTRUCTIVE_COUNTERMODEL",
        "CANDIDATE_LOGICAL_INDEPENDENCE_RESULT_DRIFT",
    )

    proposed = ((candidate.get("creative_text_reduction") or {}).get("new_acceptance_atom")) or {}
    _must(proposed.get("id") == CREATIVE_ATOM, "CANDIDATE_CREATIVE_ATOM_ID_DRIFT")
    _must(
        proposed.get("fresh_reality_authority") is False,
        "CANDIDATE_CREATIVE_ATOM_FRESH_REALITY_AUTHORITY",
    )

    _must(candidate.get("independent_verification_required") is True, "CANDIDATE_INDEPENDENT_VERIFICATION_NOT_REQUIRED")
    for key in ["scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"]:
        _must(candidate.get(key) is False, f"CANDIDATE_AUTHORITY_NONZERO:{key}")
    for key, value in (candidate.get("accounting") or {}).items():
        _must(value == 0, f"CANDIDATE_ACCOUNTING_NONZERO:{key}")

    return {
        "status": "PASS",
        "current_acceptance": "19_FAMILIES__38_ATOMS__14_PROVED__24_UNRESOLVED",
        "new_family_mutations": 0,
        "new_diagram_learned_primitives": 0,
        "new_diagram_acceptance_atoms": 0,
        "new_creative_text_acceptance_atoms": 1,
        "creative_atom": CREATIVE_ATOM,
        "creative_metric_independence": "INDEPENDENT_WOLFRAM_CONSTRUCTIVE_COUNTERMODEL_PASS",
        "svg_kernel": "CONCRETE_BRAIN_OWNED_CANDIDATE__INDEPENDENT_VERIFICATION_STILL_REQUIRED",
        "projected_if_creative_atom_integrated_unproved": "19_FAMILIES__39_ATOMS__14_PROVED__25_UNRESOLVED",
        "credit_delta": 0,
        "fresh_reality": False,
        "terminal": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
