"""Recompute current sound GDPval public-220 semantic-localization counts.

Truth-repair audit after bounded predicate lexicon hardening. The audit preserves
the independently source-bound imperative-directive channel and recomputes the
modal/compound channel on current runtime bytes.

No absence, whole-task semantic membership, policy adequacy, GDPval acceptance,
or terminal authority is granted by these one-sided counts.
"""
from __future__ import annotations

import json
from typing import Any

from canonical.runtime.gdpval_semantic_complement_localizer_v2 import (
    load_public_rows,
    localize_rows,
)
from canonical.runtime.bounded_imperative_directive_semantics_v2 import (
    parse_directive,
    segment_task_text,
)

SCHEMA = "PROJECT_BRAIN_GDPVAL_PUBLIC_220_SEMANTIC_TRUTH_REPLAY_V2"
EXPECTED = {
    "task_count": 220,
    "population_manifest_sha256": "b86c134c72f911f7170206b30bc7b31742a92f5f9fb3cbd667320993963d3905",
    "baseline_explicit_obligation_count": 29,
    "baseline_unresolved_segment_count": 5206,
    "modal_segment_count": 536,
    "compound_candidate_counts": {
        "DECOMPOSED_BUT_REPARSE_UNRESOLVED": 12,
        "NO_SAFE_COMPOUND_DECOMPOSITION": 524,
    },
    "imperative_directive_count": 421,
    "tasks_with_imperative_directives": 173,
    "tasks_with_modal_obligations": 26,
    "tasks_with_any_modal_or_imperative": 178,
    "tasks_without_any_modal_or_imperative": 42,
    "whole_task_semantic_membership_proved_count": 0,
}


def evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    localized = localize_rows(rows)
    if localized.get("status") != "PASS__COMPLETE_PUBLIC_220_STRUCTURAL_RELOCALIZATION__ZERO_PROMOTION_CREDIT":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["LOCALIZER_NOT_PASS"],
            "terminal_authority": False,
        }

    modal_tasks = {
        int(x["row_idx"])
        for x in localized["tasks"]
        if int(x.get("baseline_explicit_obligation_count") or 0) > 0
    }
    imperative_tasks: set[int] = set()
    imperative_count = 0
    for item in rows:
        idx = int(item["row_idx"])
        row = dict(item.get("row") or {})
        prompt = str(row.get("prompt") or "")
        count = 0
        for segment in segment_task_text(prompt):
            parsed = parse_directive(segment)
            if parsed.get("status") == "RESOLVED_DIRECTIVE":
                count += 1
        imperative_count += count
        if count:
            imperative_tasks.add(idx)

    observed = {
        "task_count": int(localized["population"]["task_count"]),
        "population_manifest_sha256": localized["population"]["population_manifest_sha256"],
        "baseline_explicit_obligation_count": int(
            localized["aggregate"]["baseline_explicit_obligation_count"]
        ),
        "baseline_unresolved_segment_count": int(
            localized["aggregate"]["baseline_unresolved_segment_count"]
        ),
        "modal_segment_count": int(localized["aggregate"]["modal_segment_count"]),
        "compound_candidate_counts": dict(localized["compound_candidate_counts"]),
        "imperative_directive_count": imperative_count,
        "tasks_with_imperative_directives": len(imperative_tasks),
        "tasks_with_modal_obligations": len(modal_tasks),
        "tasks_with_any_modal_or_imperative": len(modal_tasks | imperative_tasks),
        "tasks_without_any_modal_or_imperative": 220 - len(modal_tasks | imperative_tasks),
        "whole_task_semantic_membership_proved_count": 0,
    }
    errors = []
    for key, expected in EXPECTED.items():
        if observed.get(key) != expected:
            errors.append(f"DRIFT:{key}:{observed.get(key)!r}!={expected!r}")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_SOUND_PUBLIC_220_SEMANTIC_COUNTS__ZERO_CREDIT"
            if not errors
            else "FAIL_CLOSED"
        ),
        "pass": not errors,
        "errors": errors,
        "observed": observed,
        "superseded_counts": {
            "baseline_explicit_obligation_count": 154,
            "tasks_with_modal_obligations": 93,
            "baseline_unresolved_segment_count": 5081,
            "tasks_with_any_modal_or_imperative": 194,
            "tasks_without_any_modal_or_imperative": 26,
        },
        "truth_repair": {
            "root_cause": (
                "OLD_MODAL_PARSER_ACCEPTED_ARBITRARY_ALPHABETIC_TOKEN_AS_PREDICATE"
            ),
            "historical_examples_of_invalid_predicate_tokens": [
                "accurately",
                "also",
                "strongly",
                "the",
                "visually",
            ],
            "imperative_channel_recomputed_independently": True,
            "old_modal_counts_authoritative": False,
        },
        "soundness": {
            "one_sided_positive_semantics_only": True,
            "absence_proves_irrelevance": False,
            "whole_task_semantic_membership_proved": False,
            "policy_adequacy_proved": False,
            "gdpval_acceptance_proved": False,
            "terminal_authority": False,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "fresh_target_model_queries": 0,
            "terminal_credit_delta": 0,
        },
    }


def evaluate() -> dict[str, Any]:
    return evaluate_rows(load_public_rows())


def main() -> None:
    result = evaluate()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
