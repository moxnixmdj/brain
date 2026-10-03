#!/usr/bin/env python3
"""Deterministic strict-reference lower-bound scorer for Chartography.

The official public scorer asks a model judge whether the submitted final answer
matches all parts of the golden answer. This scorer intentionally grants credit
only when the entire submitted response, after outer whitespace normalization,
is exactly the dataset golden answer. It therefore gives up all official rubric
leniency for acceptable ranges, equivalent notation, formatting, and wording.

This is a scorer-only proof mechanism. The candidate never receives the golden
answer. No official judge-output equivalence is claimed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

@dataclass(frozen=True)
class StrictChartographyVerdict:
    correct: bool
    reason: str

def normalize_outer_whitespace(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("VALUE_NOT_STRING")
    return value.replace("\r\n","\n").replace("\r","\n").strip()

def strict_reference_verdict(response: str, golden_answer: str) -> StrictChartographyVerdict:
    if not isinstance(response, str):
        return StrictChartographyVerdict(False,"RESPONSE_NOT_STRING")
    if not isinstance(golden_answer, str):
        return StrictChartographyVerdict(False,"REFERENCE_NOT_STRING")
    reference=normalize_outer_whitespace(golden_answer)
    if not reference:
        return StrictChartographyVerdict(False,"REFERENCE_EMPTY")
    submitted=normalize_outer_whitespace(response)
    if submitted == reference:
        return StrictChartographyVerdict(True,"EXACT_GOLDEN_ANSWER_MATCH")
    return StrictChartographyVerdict(False,"NOT_EXACT_GOLDEN_ANSWER_MATCH")

def score_predictions(prediction_by_id: Mapping[str,str], references: Sequence[Mapping[str,str]]) -> dict:
    total=len(references); correct=0; rows=[]; seen=set()
    for ref in references:
        qid=ref.get("id"); gold=ref.get("golden_answer")
        if not isinstance(qid,str) or not qid or qid in seen:
            raise ValueError("REFERENCE_IDS_MUST_BE_UNIQUE_NONEMPTY_STRINGS")
        seen.add(qid)
        response=prediction_by_id.get(qid)
        verdict = StrictChartographyVerdict(False,"MISSING_PREDICTION") if response is None else strict_reference_verdict(response,gold)
        correct += int(verdict.correct)
        rows.append({"id":qid,"correct":verdict.correct,"reason":verdict.reason})
    accuracy=(100.0*correct/total) if total else 0.0
    return {
      "schema":"PROJECT_BRAIN_CHARTOGRAPHY_STRICT_REFERENCE_LOWER_BOUND_RESULT_V1",
      "correct":correct,"total":total,"accuracy_percent":accuracy,"rows":rows,
      "official_judge_output_equivalence_claimed":False,
      "scorer_role":"STRICT_OBJECTIVE_LOWER_BOUND_ON_WRITTEN_GOLDEN_ANSWER_MATCH_CRITERION"
    }

def self_test():
    assert strict_reference_verdict("42","42").correct
    assert strict_reference_verdict(" 42\n","42").correct
    assert not strict_reference_verdict("42.0","42").correct
    assert not strict_reference_verdict("The answer is 42","42").correct
    r=score_predictions({"a":"x","b":"wrong"},[{"id":"a","golden_answer":"x"},{"id":"b","golden_answer":"y"}])
    assert r["accuracy_percent"]==50.0 and r["official_judge_output_equivalence_claimed"] is False

if __name__=="__main__":
    self_test()
    print("SELF_TEST_PASS")
