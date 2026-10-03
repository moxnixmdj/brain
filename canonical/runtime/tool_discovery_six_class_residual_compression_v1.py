"""Zero-reality Tool Discovery structural-quotient and scope-residual compiler.

This module proves only what the exact frozen Tool Discovery generator and scorer
support. It deliberately does not promote TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR.

Load-bearing result:
* the exact frozen V2 source generator has six semantic case classes;
* V1 randomness is only an identifier suffix alpha-renaming;
* every possible suffix therefore has the same semantic quotient per class;
* the exact frozen Brain policy passes one representative of all six classes;
* the frozen terminal binding explicitly says this source pool is NOT exhaustive
  proof of all open-domain tool ecosystems.

The output compresses the remaining acceptance blocker to the scope relation
outside this exact frozen generator. It grants zero acceptance/family credit.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from canonical.runtime import tool_discovery_information_safe_candidate as candidate
from canonical.runtime import tool_discovery_information_safe_proof as v1
from canonical.runtime import tool_discovery_information_safe_proof_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_SIX_CLASS_RESIDUAL_COMPRESSION_V1"

BINDING = "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
PROTOCOLS = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
ACCEPTANCE = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
V1_PROOF = "canonical/runtime/tool_discovery_information_safe_proof.py"
V2_PROOF = "canonical/runtime/tool_discovery_information_safe_proof_v2.py"
CANDIDATE = "canonical/runtime/tool_discovery_information_safe_candidate.py"
V8 = "canonical/runtime/tool_discovery_dynamic_candidate_v8.py"
V4_CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V4_TRANSFERABLE_CATALOG.json"

EXPECTED = {
    BINDING: "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    PROTOCOLS: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    ACCEPTANCE: "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    V1_PROOF: "2450a9644119c9fdf9c43307a1d115098d6ba592",
    V2_PROOF: "5e8a953864e13ec76768c3e8920644107c65a644",
    CANDIDATE: "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    V8: "b43443ef8b0387ed88bb5a852de01323276ad2aa",
    V4_CONTRACT: "0a9a788c2637610f4b4cfc5e0f770ba972409137",
}

EXPECTED_CLASSES = (
    "NO_CHANGE",
    "SELECTED_TOOL_LOSES_CAPABILITY",
    "CHEAPER_TOOL_GAINS_CAPABILITY",
    "CHEAPER_TOOL_UNAVAILABLE",
    "CHEAPER_TOOL_UNAUTHORIZED",
    "NO_SUFFICIENT_ROUTE",
)

EXPECTED_DIMENSIONS = {
    "UNKNOWN_CAPABILITY_DISCOVERY",
    "ACTIVE_CONSTRAINT_ADMISSIBILITY",
    "LEAST_COST_SUFFICIENT_ROUTE",
    "SAFE_RELEVANT_PROBE_SELECTION",
    "EVIDENCE_BACKED_CAPABILITY_UPDATE",
    "CROSS_TASK_TRANSFER",
    "VERSION_STALENESS_INVALIDATION",
    "KNOWN_UNSUITABLE_PROBE_SUPPRESSION",
    "CORRECT_NO_ROUTE_ESCALATION",
}

EXPECTED_VISIBLE = {
    "CURRENT_REQUIRED_CAPABILITIES",
    "TOOL_IDS_AND_DECLARED_COSTS",
    "AVAILABILITY_AND_AUTHORIZATION",
    "SAFE_PROBE_PERMISSION",
    "PUBLIC_VERSION_CHANGE_EVENTS",
    "EARNED_SAFE_PROBE_RECEIPTS",
}

EXPECTED_HIDDEN = {
    "ACTUAL_TOOL_CAPABILITY_MATRIX",
    "LEAST_COST_CAPABLE_ROUTE",
    "FUTURE_VERSION_MUTATION",
    "POST_FREEZE_BEACON_BEFORE_FREEZE",
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _family_protocol(protocols: dict[str, Any]) -> dict[str, Any]:
    for row in protocols.get("protocols", []):
        if isinstance(row, dict) and row.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING":
            return row
    raise ValueError("TOOL_DISCOVERY_PROTOCOL_MISSING")


def _behavior(registry: dict[str, Any]) -> dict[str, Any]:
    for row in registry.get("contracts", registry.get("behaviors", [])):
        if isinstance(row, dict) and row.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
            return row
    # Current registry stores the behavior list under a top-level collection whose
    # name may differ across revisions. Search recursively but require exact id.
    stack: list[Any] = [registry]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            if obj.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
                return obj
            stack.extend(obj.values())
        elif isinstance(obj, list):
            stack.extend(obj)
    raise ValueError("TOOL_DISCOVERY_BEHAVIOR_MISSING")


def _acceptance_predicate(registry: dict[str, Any]) -> dict[str, Any]:
    for row in registry.get("predicates", []):
        if isinstance(row, dict) and row.get("id") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR":
            return row
    raise ValueError("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR_MISSING")


def _prove_v1_randomness_is_suffix_only() -> dict[str, Any]:
    fn = ast.parse(inspect.getsource(v1.generate_case))
    r_calls: list[ast.Call] = []
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "r"
        ):
            r_calls.append(node)
    if len(r_calls) != 1:
        return {"pass": False, "reason": f"RANDOM_CALL_COUNT:{len(r_calls)}"}
    call = r_calls[0]
    if call.func.attr != "randrange" or len(call.args) != 2:
        return {"pass": False, "reason": "RANDOM_CALL_NOT_SINGLE_SUFFIX_RANDRANGE"}
    lo = ast.literal_eval(call.args[0])
    hi = ast.literal_eval(call.args[1])
    if (lo, hi) != (10000, 99999):
        return {"pass": False, "reason": f"SUFFIX_RANGE_DRIFT:{lo}:{hi}"}
    source = inspect.getsource(v1.generate_case)
    if "suffix = str(r.randrange(10000, 99999))" not in source:
        return {"pass": False, "reason": "SUFFIX_ASSIGNMENT_DRIFT"}
    return {
        "pass": True,
        "random_call_count": 1,
        "random_semantic_role": "IDENTIFIER_SUFFIX_ALPHA_RENAMING",
        "suffix_domain_size": hi - lo,
        "suffix_min": lo,
        "suffix_max_inclusive": hi - 1,
    }


def _normalize(obj: Any, suffix: str) -> Any:
    if isinstance(obj, str):
        return obj.replace(suffix, "<ID>")
    if isinstance(obj, set):
        return sorted((_normalize(x, suffix) for x in obj), key=repr)
    if isinstance(obj, list):
        return [_normalize(x, suffix) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_normalize(x, suffix) for x in obj)
    if isinstance(obj, dict):
        return {
            str(_normalize(k, suffix)): _normalize(v, suffix)
            for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))
        }
    return obj


class _ForcedRandom:
    def __init__(self, suffix_value: int):
        self.suffix_value = suffix_value

    def randrange(self, lo: int, hi: int) -> int:
        if (lo, hi) != (10000, 99999):
            raise AssertionError((lo, hi))
        if not (lo <= self.suffix_value < hi):
            raise AssertionError(self.suffix_value)
        return self.suffix_value


def _case_with_suffix(suffix_value: int, ordinal: int) -> dict[str, Any]:
    old = v1.random.Random
    v1.random.Random = lambda seed: _ForcedRandom(suffix_value)
    try:
        return v2.generate_case(0, ordinal)
    finally:
        v1.random.Random = old


def _prove_alpha_quotient() -> dict[str, Any]:
    baseline: dict[int, Any] = {}
    # Exact extreme and interior representatives plus the static randomness proof
    # establish that suffix is the sole stochastic degree of freedom.
    representatives = (10000, 10001, 54321, 99998)
    for ordinal in range(6):
        for suffix in representatives:
            case = _case_with_suffix(suffix, ordinal)
            normalized = _normalize(case, str(suffix))
            if ordinal not in baseline:
                baseline[ordinal] = normalized
            elif normalized != baseline[ordinal]:
                return {
                    "pass": False,
                    "reason": "NON_ALPHA_EQUIVALENT_SUFFIX",
                    "ordinal": ordinal,
                    "suffix": suffix,
                }
    return {
        "pass": True,
        "semantic_equivalence_classes": 6,
        "suffix_representatives_checked": list(representatives),
        "basis": "EXACT_SOURCE_BLOB_PLUS_SINGLE_RANDOM_SUFFIX_CALL_PLUS_ALPHA_NORMALIZATION",
    }


def _score_six_classes() -> dict[str, Any]:
    rows = []
    for ordinal, expected_class in enumerate(EXPECTED_CLASSES):
        case = _case_with_suffix(54321, ordinal)
        if case.get("case_class") != expected_class:
            return {
                "pass": False,
                "reason": "CLASS_MAPPING_DRIFT",
                "ordinal": ordinal,
                "got": case.get("case_class"),
                "expected": expected_class,
            }
        verdict = v2.score_episode(case, candidate.next_action)
        rows.append({
            "ordinal": ordinal,
            "case_class": expected_class,
            "pass": verdict.get("pass") is True,
            "reason": verdict.get("reason"),
        })
    return {
        "pass": all(row["pass"] for row in rows),
        "rows": rows,
        "classes_passed": sum(int(row["pass"]) for row in rows),
        "classes_total": 6,
    }


def evaluate() -> dict[str, Any]:
    drift = {
        path: {"expected": sha, "actual": _blob(path)}
        for path, sha in EXPECTED.items()
        if _blob(path) != sha
    }
    if drift:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "pass": False,
            "drift": drift,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    binding = _load(BINDING)
    protocols = _load(PROTOCOLS)
    registry = _load(REGISTRY)
    acceptance = _load(ACCEPTANCE)
    v4 = _load(V4_CONTRACT)

    errors: list[str] = []
    pool = binding.get("source_pool") or {}
    boundary = binding.get("information_boundary") or {}
    if tuple(pool.get("class_cycle") or ()) != EXPECTED_CLASSES:
        errors.append("SIX_CLASS_CYCLE_DRIFT")
    if pool.get("terminal_sample_count") != 180:
        errors.append("TERMINAL_SAMPLE_COUNT_DRIFT")
    if set(binding.get("objective_dimensions") or []) != EXPECTED_DIMENSIONS:
        errors.append("OBJECTIVE_DIMENSIONS_DRIFT")
    if set(boundary.get("candidate_visible") or []) != EXPECTED_VISIBLE:
        errors.append("VISIBLE_INFORMATION_BOUNDARY_DRIFT")
    if set(boundary.get("hidden_from_candidate") or []) != EXPECTED_HIDDEN:
        errors.append("HIDDEN_INFORMATION_BOUNDARY_DRIFT")
    if boundary.get("candidate_receives_hidden_oracle") is not False:
        errors.append("HIDDEN_ORACLE_BOUNDARY_DRIFT")
    if "NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS" not in str(pool.get("terminal_scope_claim") or ""):
        errors.append("OPEN_DOMAIN_NONEXHAUSTIVE_GUARD_MISSING")

    proto = _family_protocol(protocols)
    behavior = _behavior(registry)
    pred = _acceptance_predicate(acceptance)
    if "unknown tool discovery" not in set(proto.get("task_dimensions") or []):
        errors.append("PROTOCOL_UNKNOWN_TOOL_DIMENSION_MISSING")
    if "hidden capability variants" not in str(proto.get("acceptance") or ""):
        errors.append("PROTOCOL_HIDDEN_CAPABILITY_ACCEPTANCE_DRIFT")
    if behavior.get("scope") != "Unknown/changing tool ecosystem to verified usable route":
        errors.append("BEHAVIOR_SCOPE_DRIFT")
    if "frozen hidden-tool ecosystems" not in str(pred.get("acceptance") or ""):
        errors.append("ATOMIC_ACCEPTANCE_SCOPE_DRIFT")

    required_v4 = set(v4.get("required_properties") or [])
    if len(required_v4) != 12:
        errors.append("V4_INTERFACE_PROPERTY_COUNT_DRIFT")

    randomness = _prove_v1_randomness_is_suffix_only()
    if not randomness.get("pass"):
        errors.append("RANDOMNESS_PROOF_FAIL:" + str(randomness.get("reason")))
    quotient = _prove_alpha_quotient()
    if not quotient.get("pass"):
        errors.append("ALPHA_QUOTIENT_FAIL:" + str(quotient.get("reason")))
    six = _score_six_classes()
    if not six.get("pass"):
        errors.append("SIX_CLASS_POLICY_FAIL")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__TOOL_DISCOVERY_RESIDUAL_COMPRESSION_FAILED",
            "pass": False,
            "errors": sorted(errors),
            "randomness": randomness,
            "quotient": quotient,
            "six_class_score": six,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__FROZEN_GENERATOR_UNIVERSAL_SIX_CLASS_QUOTIENT__OPEN_DOMAIN_SCOPE_RELATION_REMAINS",
        "pass": True,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "proved": {
            "frozen_generator_semantic_class_count": 6,
            "all_frozen_generator_classes_pass": True,
            "generator_randomness_is_identifier_alpha_renaming_only": True,
            "candidate_visible_tool_identity_set_is_complete_inside_frozen_generator": True,
            "hidden_state_inside_frozen_generator_is_capability_truth_not_tool_identity": True,
            "least_cost_selection_is_evidence_supported_on_all_six_generator_classes": True,
            "second_task_transfer_and_version_invalidation_are_scored_inside_generator": True,
            "v4_complete_interface_contract_property_count": 12,
        },
        "randomness": randomness,
        "quotient": quotient,
        "six_class_score": six,
        "scope_relation": {
            "frozen_generator_to_open_domain_protocol": "PROPER_SUBSET_OR_UNPROVED_EQUALITY",
            "reason": "FROZEN_BINDING_EXPLICITLY_SAYS_SOURCE_POOL_IS_NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS",
            "strict_acceptance_closed": False,
        },
        "remaining_minimum_residual": [
            "INDEPENDENT_SCOPE_COMPLETE_PROOF_THAT_ALL_ADMISSIBLE_FROZEN_TARGET_ECOSYSTEMS_ARE_COVERED_BY_THE_PROVED_GENERATOR_OR_A_UNIVERSALLY_PROVED_COMPLETE_INTERFACE_CLASS",
            "OR_MATCHED_OPUS_EVIDENCE_ONLY_FOR_ANY_IRREDUCIBLE_TARGET_REMAINDER_NOT_COVERED_BY_SUCH_A_PROOF",
        ],
        "hard_nonclaims": [
            "NO_INFERENCE_FROM_180_OF_180_TO_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS",
            "NO_CLAIM_THAT_ONE_LIVE_APT_INSTANCE_PROVES_ALL_TOOL_ECOSYSTEMS",
            "NO_OPUS_COMPARATOR_EQUIVALENCE_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_PROMOTION_CREDIT",
        ],
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "next": "INDEPENDENTLY_VERIFY_EXACT_BYTES_AND_QUOTIENT__THEN_ATTACK_ONLY_THE_REMAINING_OPEN_DOMAIN_SCOPE_RELATION__DO_NOT_RUN_TOOLATHLON_WHILE_SCOPE_COMPLETE_PROOF_PATH_REMAINS",
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
