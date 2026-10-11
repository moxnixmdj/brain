#!/usr/bin/env python3
"""Exact-commit HLE semantic certificate scorer.

This module is deliberately narrower than the older HLE strict-reference scorer.
It does not parse prose, strip whitespace, normalize case, apply numeric tolerance,
or call an LLM judge. A slot succeeds iff the solver's already-committed final
answer string is exactly identical to the hidden official gold answer string.

The solver must run in a separate phase that cannot read the reference file.
This scorer is post-commit only.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

POPULATION_SIZE = 2500
TRIALS = 5
TOTAL_SLOTS = POPULATION_SIZE * TRIALS
TARGET_NUMERATOR = 8463
TARGET_DENOMINATOR = TOTAL_SLOTS


@dataclass(frozen=True)
class ExactCommitVerdict:
    task_id: str
    trial: int
    correct: bool
    answer_sha256: str


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_references(references: Sequence[Mapping[str, object]]) -> dict[str, str]:
    if len(references) != POPULATION_SIZE:
        raise ValueError(f"REFERENCE_COUNT_MUST_EQUAL_{POPULATION_SIZE}")
    out: dict[str, str] = {}
    for row in references:
        task_id = row.get("id")
        answer = row.get("answer")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("REFERENCE_ID_MUST_BE_NONEMPTY_STRING")
        if task_id in out:
            raise ValueError("REFERENCE_IDS_MUST_BE_UNIQUE")
        if not isinstance(answer, str):
            raise ValueError("REFERENCE_ANSWER_MUST_BE_STRING")
        out[task_id] = answer
    return out


def validate_commitments(commitments: Sequence[Mapping[str, object]], reference_ids: set[str]) -> None:
    if len(commitments) != TOTAL_SLOTS:
        raise ValueError(f"COMMITMENT_COUNT_MUST_EQUAL_{TOTAL_SLOTS}")
    seen: set[tuple[str, int]] = set()
    per_trial = Counter()
    for row in commitments:
        task_id = row.get("id")
        trial = row.get("trial")
        answer = row.get("final_answer")
        answer_sha256 = row.get("final_answer_sha256")
        if not isinstance(task_id, str) or task_id not in reference_ids:
            raise ValueError("COMMITMENT_ID_NOT_IN_REFERENCE_POPULATION")
        if not isinstance(trial, int) or not (1 <= trial <= TRIALS):
            raise ValueError(f"TRIAL_MUST_BE_INTEGER_1_TO_{TRIALS}")
        key = (task_id, trial)
        if key in seen:
            raise ValueError("DUPLICATE_TASK_TRIAL_SLOT")
        seen.add(key)
        per_trial[trial] += 1
        if not isinstance(answer, str):
            raise ValueError("FINAL_ANSWER_MUST_BE_STRING")
        if not isinstance(answer_sha256, str) or answer_sha256 != _sha256_text(answer):
            raise ValueError("FINAL_ANSWER_COMMITMENT_HASH_MISMATCH")
    for trial in range(1, TRIALS + 1):
        if per_trial[trial] != POPULATION_SIZE:
            raise ValueError(f"TRIAL_{trial}_MUST_CONTAIN_{POPULATION_SIZE}_TASKS")


def score_exact_commitments(
    commitments: Sequence[Mapping[str, object]],
    references: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    reference_by_id = validate_references(references)
    validate_commitments(commitments, set(reference_by_id))

    correct = 0
    per_trial_correct = Counter()
    verdicts: list[ExactCommitVerdict] = []
    for row in commitments:
        task_id = str(row["id"])
        trial = int(row["trial"])
        final_answer = str(row["final_answer"])
        hit = final_answer == reference_by_id[task_id]
        correct += int(hit)
        per_trial_correct[trial] += int(hit)
        verdicts.append(
            ExactCommitVerdict(
                task_id=task_id,
                trial=trial,
                correct=hit,
                answer_sha256=str(row["final_answer_sha256"]),
            )
        )

    result = {
        "schema": "PROJECT_BRAIN_HLE_EXACT_COMMIT_SEMANTIC_CERTIFICATE_RESULT_V1",
        "correct_exact_gold_identities": correct,
        "total_slots": TOTAL_SLOTS,
        "certified_fraction": correct / TOTAL_SLOTS,
        "certified_percent": 100.0 * correct / TOTAL_SLOTS,
        "threshold_numerator": TARGET_NUMERATOR,
        "threshold_denominator": TARGET_DENOMINATOR,
        "threshold_met": correct >= TARGET_NUMERATOR,
        "per_trial_correct": {str(t): per_trial_correct[t] for t in range(1, TRIALS + 1)},
        "commitments_manifest_sha256": _canonical_sha256(list(commitments)),
        "references_manifest_sha256": _canonical_sha256(list(references)),
        "verdict_manifest_sha256": _canonical_sha256(
            [
                {
                    "id": v.task_id,
                    "trial": v.trial,
                    "correct": v.correct,
                    "answer_sha256": v.answer_sha256,
                }
                for v in verdicts
            ]
        ),
        "grader_equivalence_claimed": False,
        "semantic_certificate_role": "EXACT_HIDDEN_GOLD_IDENTITY_ONLY",
        "required_external_condition": "REFERENCES_WERE_INACCESSIBLE_TO_SOLVER_UNTIL_ALL_FINAL_ANSWER_COMMITMENTS_WERE_IRREVOCABLY_SEALED",
    }
    return result


def self_test() -> None:
    refs = [{"id": f"q{i}", "answer": f"a{i}"} for i in range(POPULATION_SIZE)]
    commits = []
    for trial in range(1, TRIALS + 1):
        for i in range(POPULATION_SIZE):
            ans = f"a{i}"
            commits.append(
                {
                    "id": f"q{i}",
                    "trial": trial,
                    "final_answer": ans,
                    "final_answer_sha256": _sha256_text(ans),
                }
            )
    out = score_exact_commitments(commits, refs)
    assert out["correct_exact_gold_identities"] == TOTAL_SLOTS
    assert out["threshold_met"] is True

    bad = [dict(x) for x in commits]
    bad[0]["final_answer"] = " a0"
    bad[0]["final_answer_sha256"] = _sha256_text(" a0")
    out2 = score_exact_commitments(bad, refs)
    assert out2["correct_exact_gold_identities"] == TOTAL_SLOTS - 1


if __name__ == "__main__":
    self_test()
    print("SELF_TEST_PASS")
