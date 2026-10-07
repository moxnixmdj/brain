"""Executable checker for the canonical unbarred matched-parity protocol.

This module does not select cases, call a comparator, or grant terminal authority.
It only recomputes the predeclared paired-difference anytime-valid acceptance rule
from frozen, identity-matched Brain and exact-Opus-5.5 case scores.

Protocol source:
canonical/governance/UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_UNBARRED_MATCHED_PARITY_ACCEPTANCE_V1"
PROTOCOL_SCHEMA = "PROJECT_BRAIN_UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1"
EXPECTED_COMPARATOR = "Claude Opus 5.5"
FAMILY_ALPHA = 0.05


def _fail(errors: Sequence[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(str(x) for x in errors)),
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _score(x: Any, label: str, errors: list[str]) -> float | None:
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(float(x)):
        errors.append(label + "_INVALID")
        return None
    y = float(x)
    if not 0.0 <= y <= 1.0:
        errors.append(label + "_OUT_OF_RANGE")
        return None
    return y


def evaluate(data: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        return _fail(["INPUT_NOT_OBJECT"])

    errors: list[str] = []

    if data.get("protocol_schema") != PROTOCOL_SCHEMA:
        errors.append("PROTOCOL_SCHEMA_MISMATCH")
    if data.get("exact_comparator") != EXPECTED_COMPARATOR:
        errors.append("EXACT_COMPARATOR_MISMATCH")

    for key in (
        "family_behavior_frozen",
        "brain_package_frozen",
        "comparator_surface_frozen",
        "challenge_source_pool_frozen",
        "selection_after_candidate_freeze",
        "same_task_input",
        "same_visible_information",
        "same_jit_knowledge_sources",
        "same_tool_classes",
        "same_external_action_authority",
        "same_task_time_or_step_budget",
        "same_scoring_rubric",
        "identity_blinded_to_adjudicators",
        "zero_case_replacement",
        "zero_adaptive_tuning",
        "donor_capability_routes_blocked",
        "provenance_complete",
        "zero_incremental_spend",
    ):
        if data.get(key) is not True:
            errors.append(key.upper() + "_NOT_TRUE")

    scopes = data.get("required_scopes")
    if not isinstance(scopes, Sequence) or isinstance(scopes, (str, bytes)) or not scopes:
        errors.append("REQUIRED_SCOPES_INVALID_OR_EMPTY")
        scopes = []

    normalized: list[dict[str, Any]] = []
    seen_scope_ids: set[str] = set()
    for si, scope in enumerate(scopes):
        if not isinstance(scope, Mapping):
            errors.append(f"SCOPE_NOT_OBJECT:{si}")
            continue
        sid = str(scope.get("scope_id") or "").strip()
        if not sid:
            errors.append(f"SCOPE_ID_MISSING:{si}")
            continue
        if sid in seen_scope_ids:
            errors.append(f"SCOPE_ID_DUPLICATE:{sid}")
            continue
        seen_scope_ids.add(sid)

        if scope.get("required") is not True:
            errors.append(f"SCOPE_REQUIRED_NOT_TRUE:{sid}")
        if scope.get("scope_definition_frozen") is not True:
            errors.append(f"SCOPE_DEFINITION_NOT_FROZEN:{sid}")
        if scope.get("scorer_frozen") is not True:
            errors.append(f"SCOPE_SCORER_NOT_FROZEN:{sid}")
        if scope.get("case_scores_independent_conditionally_on_frozen_population") is not True:
            errors.append(f"SCOPE_INDEPENDENCE_NOT_BOUND:{sid}")

        rows = scope.get("paired_cases")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            errors.append(f"PAIRED_CASES_INVALID_OR_EMPTY:{sid}")
            continue

        seen_case_ids: set[str] = set()
        pairs: list[tuple[str, float, float]] = []
        for ri, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"CASE_NOT_OBJECT:{sid}:{ri}")
                continue
            cid = str(row.get("case_id") or "").strip()
            if not cid:
                errors.append(f"CASE_ID_MISSING:{sid}:{ri}")
                continue
            if cid in seen_case_ids:
                errors.append(f"CASE_ID_DUPLICATE:{sid}:{cid}")
                continue
            seen_case_ids.add(cid)
            if row.get("brain_case_id") != cid or row.get("opus_case_id") != cid:
                errors.append(f"CASE_IDENTITY_MISMATCH:{sid}:{cid}")
            b = _score(row.get("brain_score"), f"BRAIN_SCORE:{sid}:{cid}", errors)
            o = _score(row.get("opus_score"), f"OPUS_SCORE:{sid}:{cid}", errors)
            if b is not None and o is not None:
                pairs.append((cid, b, o))

        normalized.append({"scope_id": sid, "pairs": pairs})

    if errors:
        return _fail(errors)

    scope_count = len(normalized)
    if scope_count == 0:
        return _fail(["NO_VALID_REQUIRED_SCOPES"])

    sample_counts = {len(scope["pairs"]) for scope in normalized}
    if len(sample_counts) != 1:
        return _fail(["UNBALANCED_SCOPE_ROUND_COUNTS"])
    round_count = next(iter(sample_counts))
    if round_count <= 0:
        return _fail(["NO_MATCHED_ROUNDS"])

    if data.get("balanced_scope_rounds") is not True:
        return _fail(["BALANCED_SCOPE_ROUNDS_NOT_TRUE"])

    alpha_scope = FAMILY_ALPHA / scope_count
    scope_results: list[dict[str, Any]] = []
    all_pass = True

    for scope in normalized:
        sid = scope["scope_id"]
        pairs = scope["pairs"]
        ds = [b - o for _cid, b, o in pairs]
        running: list[dict[str, Any]] = []
        prefix_sum = 0.0
        first_pass_n: int | None = None
        for i, d in enumerate(ds, start=1):
            prefix_sum += d
            mean = prefix_sum / i
            alpha_n = 6.0 * alpha_scope / (math.pi ** 2 * i * i)
            epsilon = math.sqrt(2.0 * math.log(1.0 / alpha_n) / i)
            lcb = mean - epsilon
            passed = lcb >= 0.0
            running.append({
                "n": i,
                "mean_paired_difference": mean,
                "alpha_scope_n": alpha_n,
                "hoeffding_epsilon": epsilon,
                "one_sided_lcb": lcb,
                "pass": passed,
            })
            if passed and first_pass_n is None:
                first_pass_n = i

        final = running[-1]
        passed = bool(final["pass"])
        all_pass = all_pass and passed
        scope_results.append({
            "scope_id": sid,
            "sample_count": len(ds),
            "mean_paired_difference": final["mean_paired_difference"],
            "one_sided_lcb": final["one_sided_lcb"],
            "first_pass_n": first_pass_n,
            "pass": passed,
            "anytime_trace": running,
            "paired_case_ids": [cid for cid, _b, _o in pairs],
        })

    global_first_pass_n = None
    for n in range(1, round_count + 1):
        if all(row["anytime_trace"][n - 1]["pass"] for row in scope_results):
            global_first_pass_n = n
            break

    stop_rule_ok = (
        global_first_pass_n is None
        or global_first_pass_n == round_count
    )
    if not stop_rule_ok:
        return _fail([
            f"GLOBAL_STOP_RULE_VIOLATED:FIRST_ALL_SCOPE_PASS_N={global_first_pass_n}:FINAL_N={round_count}"
        ])

    return {
        "schema": SCHEMA,
        "status": "PASS" if all_pass else "FAIL_BOUND_NOT_MET",
        "pass": all_pass,
        "protocol_schema": PROTOCOL_SCHEMA,
        "exact_comparator": EXPECTED_COMPARATOR,
        "family_alpha": FAMILY_ALPHA,
        "required_scope_count": scope_count,
        "balanced_round_count": round_count,
        "alpha_scope": alpha_scope,
        "global_first_all_scope_pass_n": global_first_pass_n,
        "scope_results": scope_results,
        "rule": (
            "PASS_IFF_EVERY_REQUIRED_SCOPE_FINAL_ANYTIME_HOEFFDING_PAIRED_DIFFERENCE_"
            "LOWER_BOUND_IS_NONNEGATIVE_AND_ALL_FROZEN_MATCHED_PROTOCOL_INVARIANTS_HOLD"
        ),
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
