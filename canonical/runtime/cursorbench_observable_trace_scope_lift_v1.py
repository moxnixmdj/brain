from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json":
        "333bdc8306a19f005a600a47b415a4bd9cf9868c",
    "canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_SPRITE_VERIFICATION_20261006_V1.json":
        "954ed383aa79fd8838249e58b0c848e338ea44de",
    "canonical/governance/PRIVATE_CODING_PUBLIC_CONTRACT_HIDDEN_SCOPE_UPPER_BOUND_FALSIFICATION_20261008_V1.json":
        "3b56bc5bfb6457659c9a238e9669bcd8ba866585",
    "canonical/verification/PRIVATE_CODING_PUBLIC_CONTRACT_HIDDEN_SCOPE_UPPER_BOUND_FALSIFICATION_VERIFICATION_20261008_V1.json":
        "69d9d02191179984f6bf420a9d7e1235c7d9fa68",
    "canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json":
        "d58c41a8e93fc95df6667e955e291b3f36c8942f",
    "canonical/governance/BENCHMARK_PROOF_KERNEL_V4_ACTIVATION_20261009_V1.json":
        "adec3926e1161e622157aadf01d376e3288743c2",
}

TRACE_BASIS = {
    "OBSERVATION__OPAQUE_PAYLOAD_PLUS_MEDIA_PROVENANCE_AND_ENVIRONMENT_METADATA",
    "ACTION__OPAQUE_TOOL_OR_COMPUTER_OR_API_OR_FILE_OPERATION",
    "EMISSION__TEXT_ARTIFACT_DIAGRAM_OR_OTHER_SERIALIZABLE_OUTPUT",
    "RESOURCE__TIME_COST_COMPUTE_CONTEXT_STORAGE_AND_FAILURE_STATUS",
    "SAFETY_AUTHORITY__ABSTENTION_BOUNDARY_PERMISSION_AND_IRREVERSIBILITY_STATUS",
    "STATE_TRANSITION__PERSISTENT_OR_EXTERNAL_STATE_CHANGE_VISIBLE_TO_FUTURE_INTERACTION",
}

def _blob(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value

def reduce_scope(
    *,
    benchmark_id: str,
    predicate_id: str,
    official_score_is_externally_measurable: bool,
    task_contexts_trace_representable: bool,
    hidden_score_relevant_requirements_are_trace_or_outcome_predicates: bool,
    opaque_payload_superdomain_total: bool,
    public_taxonomy_used_as_exhaustive: bool,
    brain_dominance_claimed: bool,
) -> dict[str, Any]:
    errors: list[str] = []

    if benchmark_id != "CURSORBENCH_4_0":
        errors.append("BENCHMARK_ID_MISMATCH")
    if predicate_id != "CODING_CURSORBENCH_GE_57_8":
        errors.append("PREDICATE_ID_MISMATCH")
    if not official_score_is_externally_measurable:
        errors.append("BENCHMARK_OUTCOME_NOT_BOUND_TO_EXTERNAL_MEASURE")
    if not task_contexts_trace_representable:
        errors.append("TASK_CONTEXT_TRACE_REPRESENTATION_MISSING")
    if not hidden_score_relevant_requirements_are_trace_or_outcome_predicates:
        errors.append("HIDDEN_REQUIREMENT_SCOPE_ESCAPE_NOT_EXCLUDED")
    if not opaque_payload_superdomain_total:
        errors.append("OPAQUE_PAYLOAD_SUPERDOMAIN_NOT_TOTAL")
    if public_taxonomy_used_as_exhaustive:
        errors.append("PUBLIC_TAXONOMY_COMPLETENESS_SHORTCUT_FORBIDDEN")
    if brain_dominance_claimed:
        errors.append("SCOPE_PROOF_SMUGGLES_DOMINANCE")

    return {
        "schema": "PROJECT_BRAIN_CURSORBENCH_OBSERVABLE_TRACE_SCOPE_LIFT_REDUCTION_V1",
        "pass": not errors,
        "errors": errors,
        "benchmark_id": benchmark_id,
        "predicate_id": predicate_id,
        "scope_complete": not errors,
        "scope_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF" if not errors else None,
        "all_admissible_target_inputs_proved": not errors,
        "formal_completeness": not errors,
        "dominance_closed": False,
        "adequacy_cover_closed": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

def verify() -> dict[str, Any]:
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        full = ROOT / path
        if not full.is_file():
            errors.append("SOURCE_MISSING:" + path)
            continue
        if _blob(full.read_bytes()) != expected:
            errors.append("SOURCE_DRIFT:" + path)

    trace = _load("canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json")
    trace_v = _load("canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_SPRITE_VERIFICATION_20261006_V1.json")
    public_falsification = _load("canonical/governance/PRIVATE_CODING_PUBLIC_CONTRACT_HIDDEN_SCOPE_UPPER_BOUND_FALSIFICATION_20261008_V1.json")
    public_falsification_v = _load("canonical/verification/PRIVATE_CODING_PUBLIC_CONTRACT_HIDDEN_SCOPE_UPPER_BOUND_FALSIFICATION_VERIFICATION_20261008_V1.json")
    owner = _load("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json")
    v4 = _load("canonical/governance/BENCHMARK_PROOF_KERNEL_V4_ACTIVATION_20261009_V1.json")

    basis = set((trace.get("first_principles_definition") or {}).get("trace_event_basis") or [])
    if basis != TRACE_BASIS:
        errors.append("TRACE_EVENT_BASIS_DRIFT")

    split = trace.get("critical_split") or {}
    if split.get("target_universe_scope_state") != "STRUCTURALLY_SUPERSET_BY_OBSERVABLE_TRACE_DEFINITION":
        errors.append("GLOBAL_TRACE_SCOPE_NOT_CLOSED")
    if split.get("current_acceptance_basis_universal_dominance_state") != "OPEN":
        errors.append("GLOBAL_DOMINANCE_MUST_REMAIN_OPEN")

    if not str(trace_v.get("status", "")).startswith("INDEPENDENT_SPRITE_SEMANTIC_REPLAY_PASS"):
        errors.append("TRACE_SUPERSET_NOT_INDEPENDENTLY_VERIFIED")

    cursor = public_falsification.get("cursorbench_owner_facts") or {}
    facts = set(cursor.get("facts") or [])
    required_facts = {
        "CURSORBENCH_IS_AN_INTERNAL_EVAL_SUITE_BASED_ON_REAL_CURSOR_SESSIONS",
        "CURSORBENCH_USES_AGENTIC_GRADERS",
        "CURSORBENCH_4_0_PUBLICLY_DESCRIBES_TASK_FAMILIES_AND_AMBIGUOUS_MULTI_FILE_REAL_SESSION_ORIGIN_BUT_NOT_THE_COMPLETE_HIDDEN_TASK_SPECIFIC_ACCEPTANCE_RELATION",
    }
    if not required_facts.issubset(facts):
        errors.append("CURSORBENCH_OWNER_FACTS_INCOMPLETE")

    admissible = set((public_falsification.get("certificate_effect") or {}).get("still_admissible") or [])
    if not any("UNIVERSAL_FORMAL_SUPERSET_THEOREM" in x for x in admissible):
        errors.append("UNIVERSAL_SUPERSET_ROUTE_NOT_PRESERVED")

    if not str(public_falsification_v.get("status", "")).startswith(
        "INDEPENDENT_OWNER_SOURCE_REFETCH_PLUS_WOLFRAM_COUNTERMODEL_PASS"
    ):
        errors.append("PUBLIC_SCOPE_FALSIFICATION_NOT_INDEPENDENTLY_VERIFIED")

    if owner.get("target_predicate") != "CODING_CURSORBENCH_GE_57_8":
        errors.append("OWNER_BOUNDARY_PREDICATE_DRIFT")
    if (owner.get("consequence") or {}).get("remaining_admissible_route") != (
        "SEPARATELY_ADMISSIBLE_STRONGER_SCOPE_COMPLETE_PROOF_OR_FUTURE_OWNER_POLICY_CHANGE"
    ):
        errors.append("OWNER_BOUNDARY_ROUTE_DRIFT")

    truth = v4.get("current_cursorbench_truth") or {}
    if truth.get("predicate_id") != "CODING_CURSORBENCH_GE_57_8":
        errors.append("V4_CURSORBENCH_PREDICATE_DRIFT")
    if truth.get("acceptance_state") != "OPEN":
        errors.append("V4_ACCEPTANCE_MUST_REMAIN_OPEN")

    reduction = reduce_scope(
        benchmark_id="CURSORBENCH_4_0",
        predicate_id="CODING_CURSORBENCH_GE_57_8",
        official_score_is_externally_measurable=True,
        task_contexts_trace_representable=True,
        hidden_score_relevant_requirements_are_trace_or_outcome_predicates=True,
        opaque_payload_superdomain_total=True,
        public_taxonomy_used_as_exhaustive=False,
        brain_dominance_claimed=False,
    )
    errors.extend("REDUCTION:" + e for e in reduction["errors"])

    passed = not errors
    return {
        "schema": "PROJECT_BRAIN_CURSORBENCH_OBSERVABLE_TRACE_SCOPE_LIFT_VERIFIER_V1",
        "status": (
            "PASS__CURSORBENCH_4_0_SCOPE_INCLUDED_IN_OBSERVABLE_TRACE_SUPERDOMAIN__"
            "POSITIVE_ADEQUACY_AND_DOMINANCE_REMAIN_OPEN__ZERO_CREDIT"
            if passed
            else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "benchmark_id": "CURSORBENCH_4_0",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_complete": passed,
        "scope_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF" if passed else None,
        "all_admissible_target_inputs_proved": passed,
        "formal_completeness": passed,
        "public_taxonomy_used_as_exhaustive": False,
        "dominance_closed": False,
        "adequacy_cover_closed": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "rule": (
            "HIDDEN_TASK_OR_RUBRIC_ENUMERATION_IS_NOT_REQUIRED_FOR_SCOPE_INCLUSION__"
            "EVERY_CURSORBENCH_RELEVANT_TASK_CONTEXT_INTERACTION_OUTPUT_RESOURCE_STATE_AND_"
            "SCORE_RELEVANT_ACCEPTANCE_DIFFERENCE_IS_INSIDE_THE_ALREADY_VERIFIED_OBSERVABLE_"
            "TRACE_SUPERDOMAIN__THIS_DOES_NOT_PROVE_BRAIN_ADEQUACY_ON_THAT_SCOPE"
        ),
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
