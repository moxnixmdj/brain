from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_BENCHMARK_OUTPUT_INFORMATION_EQUIVALENCE_GATE_V1"

class GateError(ValueError):
    pass

TERMINAL_TYPES = {"CAPABILITY_RELATION", "EXACT_BENCHMARK_STATISTIC"}
ROUTE_TYPES = {
    "NATIVE_BENCHMARK",
    "EXACT_SUFFICIENT_STATISTIC",
    "PROOF_CARRYING_STRONGER_CERTIFICATE",
}

def evaluate_route(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise GateError("SPEC_NOT_OBJECT")

    terminal = spec.get("terminal_predicate")
    route = spec.get("route")
    if not isinstance(terminal, Mapping):
        raise GateError("TERMINAL_PREDICATE_MISSING")
    if not isinstance(route, Mapping):
        raise GateError("ROUTE_MISSING")

    terminal_type = terminal.get("type")
    if terminal_type not in TERMINAL_TYPES:
        raise GateError("TERMINAL_TYPE_INVALID")
    if not isinstance(terminal.get("decision_output"), str) or not terminal["decision_output"].strip():
        raise GateError("DECISION_OUTPUT_UNBOUND")
    if terminal.get("goal_substitution_allowed") is not False:
        raise GateError("GOAL_SUBSTITUTION_MUST_BE_FORBIDDEN")

    route_type = route.get("type")
    if route_type not in ROUTE_TYPES:
        raise GateError("ROUTE_TYPE_INVALID")

    if route.get("uses_target_output_leakage") is not False:
        raise GateError("TARGET_OUTPUT_LEAKAGE_NOT_EXCLUDED")
    if route.get("reconstructs_private_answers_or_hidden_task_identity") is not False:
        raise GateError("PRIVATE_TARGET_RECONSTRUCTION_NOT_EXCLUDED")
    if route.get("proxy_metric_substitution") is not False:
        raise GateError("PROXY_METRIC_SUBSTITUTION_NOT_EXCLUDED")

    if route_type == "NATIVE_BENCHMARK":
        if route.get("native_identity_bound") is not True:
            raise GateError("NATIVE_BENCHMARK_IDENTITY_UNBOUND")
        if route.get("native_scoring_semantics_bound") is not True:
            raise GateError("NATIVE_SCORING_SEMANTICS_UNBOUND")
        information_relation = "NATIVE_MEASUREMENT"
    else:
        exact_sufficient = route.get("decision_sufficient_statistic_proved") is True
        stronger = route.get("strictly_stronger_entailment_proved") is True
        if not (exact_sufficient or stronger):
            raise GateError("DECISION_INFORMATION_EQUIVALENCE_NOT_PROVED")
        information_relation = (
            "EXACT_SUFFICIENT_STATISTIC"
            if exact_sufficient
            else "STRICTLY_STRONGER_ENTAILMENT"
        )
        if terminal_type == "EXACT_BENCHMARK_STATISTIC":
            if route.get("exact_statistic_bridge_proved") is not True:
                raise GateError("EXACT_STATISTIC_BRIDGE_REQUIRED")
            if route.get("frozen_scorer_state_bound") is not True:
                raise GateError("FROZEN_SCORER_STATE_UNBOUND")

    if route.get("minimal_information_cut_proved") is not True:
        raise GateError("MINIMAL_INFORMATION_CUT_NOT_PROVED")

    delete_native = (
        terminal_type == "CAPABILITY_RELATION"
        and route_type != "NATIVE_BENCHMARK"
        and information_relation in {
            "EXACT_SUFFICIENT_STATISTIC",
            "STRICTLY_STRONGER_ENTAILMENT",
        }
    )

    return {
        "schema": SCHEMA,
        "status": "PASS__TERMINAL_DECISION_INFORMATION_PRESERVED",
        "terminal_type": terminal_type,
        "route_type": route_type,
        "information_relation": information_relation,
        "native_benchmark_deletable_for_this_terminal_predicate": delete_native,
        "exact_statistic_requires_native_or_exact_score_bridge": (
            terminal_type == "EXACT_BENCHMARK_STATISTIC"
        ),
        "rule": (
            "MINIMIZE_ACTIONS_AND_NEW_INFORMATION_NEEDED_TO_DETERMINE_THE_TERMINAL_"
            "DECISION_OUTPUT__BENCHMARK_PROCEDURE_HAS_NO_INTRINSIC_AUTHORITY"
        ),
        "hard_nonclaims": [
            "CAPABILITY_RELATION_DOES_NOT_IMPLY_EXACT_REALIZED_BENCHMARK_STATISTIC_WITHOUT_A_PROVED_BRIDGE",
            "NO_PROXY_METRIC_SUBSTITUTION",
            "NO_PRIVATE_TASK_OR_ANSWER_RECONSTRUCTION",
            "ZERO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_CREDIT",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
