#!/usr/bin/env python3
"""Goal-directed sufficient knowing V1.

This is a zero-model, zero-network decision kernel. It implements the smallest
useful quotient of the owner's "perfect algorithm" idea:

    goal -> decision-relevant action partition -> smallest K1 query that can
    change the partition -> recomputed relation -> relation-only memory.

It never calls a model, never fetches the web, never executes an environment
action, never stores world facts in parameters, and never saves an exact action
trajectory as knowledge. External facts are non-authoritative K1 records that
must be authenticated, scoped, source-bound and unable to choose policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_KNOWING_V1"
STORE_SCHEMA = "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_KNOWLEDGE_STORE_V1"
RELATION_SCHEMA = "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_RELATION_V1"

K1_QUERY_REQUIRED = "K1_QUERY_REQUIRED__ASK_ONLY_THE_DECIDING_QUESTION"
READY_FOR_DISTINCT_VERIFIER = "READY_FOR_DISTINCT_VERIFIER__NO_LOCAL_EXECUTION_AUTHORITY"
REFUSED_PREFIX = "REFUSED__"

APPROVED_SOURCE_CLASSES = {
    "official_primary",
    "code_registry",
    "direct_probe",
    "independent_verifier",
    "local_guide",
    "authenticated_observation",
}
FORBIDDEN_SOURCE_CLASSES = {
    "runtime_model",
    "model_output",
    "unauthenticated",
    "ready_made_plan",
    "ready_made_answer",
    "unknown",
}
FORBIDDEN_EXPERIENCE_KEYS = {
    "action_trace",
    "actions",
    "trajectory",
    "raw_trajectory",
    "expected_answer",
    "answer",
    "policy",
    "executable_predicate",
    "lambda",
    "world_fact",
    "model_output",
}

REQUIRED_RELATION_KEYS = (
    "environment_class",
    "goal_effect",
    "relation",
    "variables",
    "preconditions",
    "falsifier",
    "evidence_hash",
    "verifier_id",
)


def _canon(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _terms(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        out: set[str] = set()
        for child in value.values():
            out |= _terms(child)
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        out: set[str] = set()
        for child in value:
            out |= _terms(child)
        return out
    text = _canon(value).casefold()
    if not text:
        return set()
    normalized = "".join(ch if ch.isalnum() else " " for ch in text)
    return {text} | set(part for part in normalized.split() if part)


def _scope_matches(scope: Mapping[str, Any], goal: Mapping[str, Any], environment: Mapping[str, Any]) -> bool:
    goal_effect = _canon(goal.get("effect")).casefold()
    env_class = _canon(environment.get("environment_class")).casefold()
    env_id = _canon(environment.get("id")).casefold()
    scope_goal = _canon(scope.get("goal_effect")).casefold()
    scope_env_class = _canon(scope.get("environment_class")).casefold()
    scope_env_ids = {_canon(x).casefold() for x in (scope.get("environment_ids") or []) if _canon(x)}
    if scope_goal and scope_goal != goal_effect:
        return False
    if scope_env_class and scope_env_class != env_class:
        return False
    if scope_env_ids and env_id not in scope_env_ids:
        return False
    return True


def _fact_is_usable(
    fact: Mapping[str, Any],
    unknown_id: str,
    goal: Mapping[str, Any],
    environment: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _canon(fact.get("unknown_id")) != _canon(unknown_id):
        reasons.append("FACT_UNKNOWN_ID_MISMATCH")
    if fact.get("authenticated") is not True:
        reasons.append("FACT_NOT_AUTHENTICATED")
    if fact.get("source_bound") is not True:
        reasons.append("FACT_NOT_SOURCE_BOUND")
    if not _canon(fact.get("evidence_hash")):
        reasons.append("FACT_EVIDENCE_HASH_MISSING")
    if fact.get("policy_authority") is not False:
        reasons.append("FACT_ASSERTS_POLICY_AUTHORITY")
    if fact.get("answer_authority") is not False:
        reasons.append("FACT_ASSERTS_ANSWER_AUTHORITY")
    if int(fact.get("capability_credit_delta", 0) or 0) != 0:
        reasons.append("FACT_ASSERTS_CAPABILITY_CREDIT")
    source_class = _canon(fact.get("source_class")).casefold()
    if source_class in FORBIDDEN_SOURCE_CLASSES or source_class not in APPROVED_SOURCE_CLASSES:
        reasons.append("FACT_SOURCE_CLASS_NOT_K1")
    if fact.get("freshness_ok") is not True:
        reasons.append("FACT_FRESHNESS_NOT_PROVEN")
    if fact.get("completeness_required") is True and fact.get("bounded_enumeration") is not True:
        reasons.append("OPEN_WORLD_COMPLETENESS_NOT_PROVEN")
    if not _scope_matches(dict(fact.get("scope") or {}), goal, environment):
        reasons.append("FACT_SCOPE_MISMATCH")
    return not reasons, reasons


def _affected_actions(unknown_id: str, actions: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        _canon(a.get("id"))
        for a in actions
        if unknown_id in {_canon(x) for x in (a.get("requires") or [])}
    ]


def _synthesize_question(
    unknown_id: str,
    goal: Mapping[str, Any],
    environment: Mapping[str, Any],
    affected: Sequence[str],
) -> str:
    """Derive a canonical K1 query from the undecided action partition."""
    return (
        "Resolve " + unknown_id + " for " + _canon(goal.get("effect"))
        + " in " + _canon(environment.get("environment_class"))
        + "; deciding actions: " + ", ".join(affected)
    )


def _query_value(
    unknown: Mapping[str, Any],
    goal: Mapping[str, Any],
    actions: Sequence[Mapping[str, Any]],
) -> tuple[float, str, list[str], list[str]]:
    """Compute exact EVPI when a scoped probability model is supplied.

    Without probabilities, the decision-contrast bound is a conservative
    worst-case value, not a Bayesian information value. The returned basis is
    part of the receipt so the two quantities cannot be conflated.
    """
    unknown_id = _canon(unknown.get("id"))
    affected = _affected_actions(unknown_id, actions)
    reasons: list[str] = []
    if not affected:
        return 0.0, "NO_DECISION_CHANGE", affected, reasons
    goal_scale = float(goal.get("value", 1) or 1) * float(goal.get("risk", 1) or 1)
    cost = float(unknown.get("cost", 0) or 0)
    hypotheses = unknown.get("hypotheses")
    if hypotheses is not None:
        if not isinstance(hypotheses, Sequence) or isinstance(hypotheses, (str, bytes)) or not hypotheses:
            return 0.0, "INVALID_HYPOTHESIS_MODEL", affected, ["HYPOTHESIS_MODEL_INVALID"]
        total = 0.0
        expected_with_information = 0.0
        expected_by_action = {action_id: 0.0 for action_id in affected}
        for i, row in enumerate(hypotheses):
            if not isinstance(row, Mapping):
                reasons.append("HYPOTHESIS_ROW_INVALID:" + str(i))
                continue
            try:
                probability = float(row.get("probability"))
            except (TypeError, ValueError):
                reasons.append("HYPOTHESIS_PROBABILITY_INVALID:" + str(i))
                continue
            if probability < 0 or probability > 1:
                reasons.append("HYPOTHESIS_PROBABILITY_OUT_OF_RANGE:" + str(i))
                continue
            utilities = row.get("utilities") or {}
            if not isinstance(utilities, Mapping):
                reasons.append("HYPOTHESIS_UTILITIES_INVALID:" + str(i))
                continue
            values = []
            for action_id in affected:
                if action_id not in utilities:
                    reasons.append("HYPOTHESIS_UTILITY_MISSING:" + str(i) + ":" + action_id)
                    continue
                try:
                    values.append(float(utilities[action_id]))
                except (TypeError, ValueError):
                    reasons.append("HYPOTHESIS_UTILITY_INVALID:" + str(i) + ":" + action_id)
            if len(values) != len(affected):
                continue
            total += probability
            expected_with_information += probability * max(values)
            for action_id, value in zip(affected, values):
                expected_by_action[action_id] += probability * value
        if reasons:
            return 0.0, "INVALID_HYPOTHESIS_MODEL", affected, sorted(set(reasons))
        if abs(total - 1.0) > 1e-6:
            return 0.0, "INVALID_HYPOTHESIS_MODEL", affected, ["HYPOTHESIS_PROBABILITIES_NOT_NORMALIZED"]
        best_without = max(expected_by_action.values())
        score = goal_scale * (expected_with_information - best_without) - cost
        return score, "EXACT_EVPI", affected, []
    action_values = unknown.get("action_values") or {}
    values = []
    for action_id in affected:
        try:
            values.append(float(action_values.get(action_id, 0) or 0))
        except (TypeError, ValueError):
            reasons.append("ACTION_VALUE_INVALID:" + action_id)
            values.append(0.0)
    contrast = max(values) - min(values) if values else 0.0
    score = goal_scale * contrast - cost
    return score, "WORST_CASE_CONTRAST_BOUND", affected, reasons


def _query_is_admissible(
    unknown: Mapping[str, Any],
    score: float,
    basis: str,
    value_reasons: Sequence[str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = list(value_reasons)
    if score <= 0:
        reasons.append("VOI_NOT_POSITIVE")
    if basis in {"INVALID_HYPOTHESIS_MODEL", "NO_DECISION_CHANGE"}:
        reasons.append("QUERY_VALUE_NOT_COMPUTED")
    if not _canon(unknown.get("falsifier")):
        reasons.append("FALSIFIER_MISSING")
    source_class = _canon(unknown.get("source_class")).casefold()
    if source_class in FORBIDDEN_SOURCE_CLASSES or source_class not in APPROVED_SOURCE_CLASSES:
        reasons.append("SOURCE_CLASS_NOT_K1")
    if unknown.get("completeness_required") is True and unknown.get("bounded_enumeration") is not True:
        reasons.append("OPEN_WORLD_COMPLETENESS_NOT_PROVEN")
    if unknown.get("ready_made_plan") is True or unknown.get("ready_made_answer") is True:
        reasons.append("K1_MAY_NOT_SUPPLY_PLAN_OR_ANSWER")
    if unknown.get("model_call_required") is True:
        reasons.append("MODEL_CALL_REQUIRED")
    return not reasons, sorted(set(reasons))


def evaluate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one goal packet without any runtime model or network call."""
    goal = dict(packet.get("goal") or {})
    environment = dict(packet.get("environment") or {})
    store = dict(packet.get("store") or {})
    actions = [dict(x) for x in (packet.get("actions") or []) if isinstance(x, Mapping)]
    unknowns = {_canon(x.get("id")): dict(x) for x in (packet.get("unknowns") or []) if isinstance(x, Mapping)}
    facts = [dict(x) for x in (store.get("facts") or []) if isinstance(x, Mapping)]
    max_queries = int(packet.get("max_queries", 1) or 1)

    failed: list[str] = []
    if not _canon(goal.get("effect")):
        failed.append("GOAL_EFFECT_MISSING")
    if not _canon(goal.get("success_predicate")):
        failed.append("GOAL_SUCCESS_PREDICATE_MISSING")
    if not _canon(environment.get("environment_class")):
        failed.append("ENVIRONMENT_CLASS_MISSING")
    if not actions:
        failed.append("ACTION_PARTITION_MISSING")
    if packet.get("independent_verifier_present") is not True:
        failed.append("DISTINCT_VERIFIER_MISSING")
    if _canon(packet.get("producer_id")) == _canon(packet.get("verifier_id")):
        failed.append("VERIFIER_NOT_DISTINCT_FROM_PRODUCER")
    if max_queries < 1:
        failed.append("MAX_QUERIES_INVALID")
    if store.get("schema") and _canon(store.get("schema")) != STORE_SCHEMA:
        failed.append("EXTERNAL_STORE_SCHEMA_MISMATCH")
    if store.get("parameters") or store.get("weights") or store.get("model_calls"):
        failed.append("PARAMETER_WAREHOUSE_OR_MODEL_DEPENDENCY_PRESENT")
    for fact in facts:
        if any(key in fact for key in FORBIDDEN_EXPERIENCE_KEYS):
            failed.append("STORE_CONTAINS_FORBIDDEN_EXPERIENCE_OR_POLICY")
            break

    goal_terms = _terms(goal)
    decision_relevant_unknowns = [
        unknown
        for unknown_id, unknown in unknowns.items()
        if _affected_actions(unknown_id, actions)
    ]
    decision_terms = goal_terms | _terms(actions) | _terms(decision_relevant_unknowns)
    scan = [dict(x) for x in (packet.get("scan") or []) if isinstance(x, Mapping)]
    relevant_scan = []
    deleted_scan = []
    for atom in scan:
        atom_terms = _terms(atom) | {_canon(x).casefold() for x in (atom.get("decision_terms") or []) if _canon(x)}
        if atom_terms & decision_terms:
            relevant_scan.append(atom)
        else:
            deleted_scan.append(_canon(atom.get("id")))

    known_by_unknown: dict[str, str] = {}
    fact_failures: dict[str, list[str]] = {}
    for unknown_id in unknowns:
        usable_fact_ids = []
        local_failures: list[str] = []
        for fact in facts:
            ok, reasons = _fact_is_usable(fact, unknown_id, goal, environment)
            if ok:
                usable_fact_ids.append(_canon(fact.get("id")))
            else:
                local_failures.extend(reasons)
        if len(usable_fact_ids) == 1:
            known_by_unknown[unknown_id] = usable_fact_ids[0]
        elif len(usable_fact_ids) > 1:
            failed.append("AMBIGUOUS_KNOWLEDGE:" + unknown_id)
        else:
            fact_failures[unknown_id] = sorted(set(local_failures)) or ["NO_BOUND_K1_FACT"]

    query_candidates: list[dict[str, Any]] = []
    for unknown_id, unknown in unknowns.items():
        if unknown_id in known_by_unknown:
            continue
        score, basis, affected, value_reasons = _query_value(unknown, goal, actions)
        ok, reasons = _query_is_admissible(unknown, score, basis, value_reasons)
        supplied_question = _canon(unknown.get("question"))
        synthesized_question = _synthesize_question(unknown_id, goal, environment, affected)
        query_candidates.append({
            "unknown_id": unknown_id,
            "question": supplied_question or synthesized_question,
            "question_source": "SUPPLIED_K1_TEMPLATE" if supplied_question else "DERIVED_FROM_ACTION_PARTITION",
            "source_class": _canon(unknown.get("source_class")).casefold(),
            "scope": {
                "goal_effect": _canon(goal.get("effect")),
                "environment_class": _canon(environment.get("environment_class")),
                "environment_id": _canon(environment.get("id")),
            },
            "falsifier": _canon(unknown.get("falsifier")),
            "bounded_enumeration": bool(unknown.get("bounded_enumeration")),
            "value_of_information": round(score, 6),
            "value_of_information_basis": basis,
            "affected_actions": affected,
            "admissible": ok,
            "reasons": reasons,
        })

    admissible_queries = [q for q in query_candidates if q["admissible"]]
    admissible_queries.sort(key=lambda q: (-q["value_of_information"], q["unknown_id"]))
    selected_queries = admissible_queries[:max_queries]
    unresolved_unknowns = sorted(set(unknowns) - set(known_by_unknown))
    open_world_failures = sorted({
        reason
        for q in query_candidates
        if not q["admissible"]
        for reason in q["reasons"]
        if reason.startswith("OPEN_WORLD") or reason.startswith("MODEL_") or reason.startswith("K1_MAY")
    })
    failed.extend(open_world_failures)

    if failed:
        decision = REFUSED_PREFIX + "_".join(sorted(set(failed)))[:220]
    elif selected_queries:
        decision = K1_QUERY_REQUIRED
    elif unresolved_unknowns:
        decision = REFUSED_PREFIX + "NO_ADMISSIBLE_DECIDING_QUESTION"
    else:
        decision = READY_FOR_DISTINCT_VERIFIER

    return {
        "schema": SCHEMA,
        "decision": decision,
        "goal_id": _canon(goal.get("id")),
        "environment_id": _canon(environment.get("id")),
        "goal_terms": sorted(goal_terms),
        "decision_terms": sorted(decision_terms),
        "relevant_scan": relevant_scan,
        "deleted_scan_atoms": deleted_scan,
        "known_unknowns": dict(sorted(known_by_unknown.items())),
        "unknown_unknowns": unresolved_unknowns,
        "fact_failures": {k: v for k, v in sorted(fact_failures.items())},
        "query_candidates": query_candidates,
        "selected_queries": selected_queries,
        "selected_query_count": len(selected_queries),
        "exhaustive_scan_rejected": len(deleted_scan) > 0,
        "learn_everything_rejected": True,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "knowledge_written_to_weights": 0,
        "environment_action_executed": False,
        "execution_authority": False,
        "distinct_verifier_present": bool(packet.get("independent_verifier_present") is True),
        "producer_id": _canon(packet.get("producer_id")),
        "verifier_id": _canon(packet.get("verifier_id")),
        "benchmark_score_authority": False,
        "capability_credit_delta": 0,
        "section_6_verifications": 0,
        "truth": {"achieved": False, "section_6": "NOT_MET"},
        "rule": "ASK_ONLY_FOR_A_DECISION_RELEVANT_CONTRAST__VERIFY_AND_RECOMPUTE__SAVE_TYPED_RELATIONS_NOT_TRAJECTORIES",
        "packet_hash": stable_hash({
            "goal": goal,
            "environment": environment,
            "actions": actions,
            "unknowns": unknowns,
            "scan": scan,
            "store": {"facts": facts, "relations": store.get("relations") or []},
        }),
    }


def distill(experience: Mapping[str, Any], contrast: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Distill one executed experience into a scoped external relation.

    A single experience may write a scoped relation with a falsifier. It may not
    declare universal generalization. A second, independently verified contrast
    in a different environment with the same typed relation is required before
    a generalization license is written.
    """
    failed: list[str] = []
    for key in REQUIRED_RELATION_KEYS:
        if not _canon(experience.get(key)) and not isinstance(experience.get(key), (list, tuple, dict)):
            failed.append("RELATION_FIELD_MISSING:" + key)
    for key in FORBIDDEN_EXPERIENCE_KEYS:
        if key in experience:
            failed.append("FORBIDDEN_EXACT_EXPERIENCE_KEY:" + key)
    if experience.get("independent_verifier") is not True:
        failed.append("DISTINCT_VERIFIER_MISSING")
    if _canon(experience.get("producer_id")) == _canon(experience.get("verifier_id")):
        failed.append("VERIFIER_NOT_DISTINCT_FROM_PRODUCER")
    if int(experience.get("model_calls", 0) or 0) != 0:
        failed.append("MODEL_DEPENDENCY_PRESENT")
    if int(experience.get("runtime_network_calls", 0) or 0) != 0:
        failed.append("RUNTIME_NETWORK_DEPENDENCY_PRESENT")
    if int(experience.get("parameters_written", 0) or 0) != 0:
        failed.append("PARAMETERS_WRITTEN")
    if not isinstance(experience.get("variables"), (list, tuple, dict)):
        failed.append("VARIABLES_NOT_TYPED_STRUCTURE")
    if not isinstance(experience.get("preconditions"), (list, tuple, dict)):
        failed.append("PRECONDITIONS_NOT_TYPED_STRUCTURE")

    generalization_license = False
    contrast_hash = None
    if contrast is not None:
        contrast_hash = stable_hash(dict(contrast))
        if _canon(contrast.get("relation")) != _canon(experience.get("relation")):
            failed.append("CONTRAST_RELATION_SHAPE_MISMATCH")
        if _canon(contrast.get("environment_class")) == _canon(experience.get("environment_class")):
            failed.append("CONTRAST_NOT_CROSS_ENVIRONMENT")
        if _canon(contrast.get("verifier_id")) == _canon(experience.get("verifier_id")):
            failed.append("CONTRAST_VERIFIER_NOT_DISTINCT")
        if _canon(contrast.get("evidence_hash")) == _canon(experience.get("evidence_hash")):
            failed.append("CONTRAST_EVIDENCE_NOT_DISTINCT")
        if contrast.get("independent_verifier") is not True:
            failed.append("CONTRAST_DISTINCT_VERIFIER_MISSING")
        if not failed:
            generalization_license = True

    relation = {
        "schema": RELATION_SCHEMA,
        "relation_id": stable_hash({
            "environment_class": experience.get("environment_class"),
            "goal_effect": experience.get("goal_effect"),
            "relation": experience.get("relation"),
            "variables": experience.get("variables"),
        }),
        "environment_class": _canon(experience.get("environment_class")),
        "goal_effect": _canon(experience.get("goal_effect")),
        "relation": _canon(experience.get("relation")),
        "variables": experience.get("variables"),
        "preconditions": experience.get("preconditions"),
        "falsifier": _canon(experience.get("falsifier")),
        "evidence_hash": _canon(experience.get("evidence_hash")),
        "producer_id": _canon(experience.get("producer_id")),
        "verifier_id": _canon(experience.get("verifier_id")),
        "generalization_license": generalization_license,
        "contrast_hash": contrast_hash,
        "single_experience_scope": not generalization_license,
        "exact_action_trajectory_saved": False,
        "world_fact_saved_in_weights": False,
        "executable_predicate_saved": False,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "capability_credit_delta": 0,
        "section_6_verifications": 0,
        "truth": {"achieved": False, "section_6": "NOT_MET"},
    }
    if failed:
        relation["decision"] = REFUSED_PREFIX + "_".join(sorted(set(failed)))[:220]
        relation["generalization_license"] = False
    else:
        relation["decision"] = "RELATION_ADMITTED__SCOPE_BOUND"
    return {
        "schema": STORE_SCHEMA,
        "facts": [],
        "relations": [] if failed else [relation],
        "decision": relation["decision"],
        "failed": sorted(set(failed)),
        "relation": relation,
        "knowledge_lives_outside_weights": True,
        "editable_without_retraining": True,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "capability_credit_delta": 0,
        "section_6_verifications": 0,
        "truth": {"achieved": False, "section_6": "NOT_MET"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    packet = json.loads(pathlib.Path(args.packet).read_text(encoding="utf-8"))
    result = evaluate(packet)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["decision"])


if __name__ == "__main__":
    main()
