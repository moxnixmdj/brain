#!/usr/bin/env python3
"""A failure is a context, not a ban.

`macro_v1` remembers a plan under the shape of the goal and counts successes and failures against
it. Its own docstring records four sightings of the same error: a memory that generalised past the
situation that made it true. Counting was the response, and counting is still the wrong unit -- a
count can only argue against the plan EVERYWHERE, so "fails on a freshly copied .docx" and "fails
on every .docx" are indistinguishable evidence.

This probe runs the real store, twice, on the same experience:

  A. the historical counter-only path (`note_failure(key)` with no context);
  B. the same outcomes with the STATE they happened in (`note_failure(key, context=...)`).

and asks what each can still do afterwards. It also runs the two controls that make the claim
falsifiable rather than flattering:

  * a success-only store must report UNDETERMINED, and its most general boundary must admit the
    state where the plan actually fails -- the over-generalisation the owner's "learn it once and
    keep it permanently" would freeze in place;
  * a failure in the SAME context as the success must NOT produce a boundary. If it did, this
    module would be the fifth sighting of the error it exists to fix.

Authority NONE. The store is redirected to a temporary file; the repository's own macro state is
never read or written. Zero model dependency, $0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as APP  # noqa: E402
from canonical.runtime import macro_v1  # noqa: E402

SCHEMA = "PROJECT_BRAIN_A_FAILURE_IS_A_CONTEXT_NOT_A_BAN_V1"

#: The .docx case from `macro_v1.note_failure`'s docstring, made concrete. The plan works when the
#: sidecar is present and fails when it is not. Both states present the SAME goal shape, so both
#: hit the same macro key -- which is exactly why a counter cannot separate them.
CLAUSES = ["verify report.docx", "audit main.py"]
STEPS = [{"capability_id": "docx.verify", "verified": True},
         {"capability_id": "python.audit", "verified": True}]

HAS_SIDECAR = frozenset({"docx_intent_sidecar_present", "python_source_present"})
NO_SIDECAR = frozenset({"python_source_present"})


def _plan(key: str) -> list[dict[str, Any]]:
    return [{"capability_id": "docx.verify", "clause": CLAUSES[0]},
            {"capability_id": "python.audit", "clause": CLAUSES[1]}]


def measure_counter_only() -> dict[str, Any]:
    """A: the historical path. Two failures in the no-sidecar context erase a plan that works."""
    assert macro_v1.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = macro_v1.signature(CLAUSES)
    drops = [macro_v1.note_failure(key), macro_v1.note_failure(key)]
    survived = macro_v1.lookup(CLAUSES) is not None
    return {
        "arm": "COUNTER_ONLY__NO_CONTEXT",
        "successes_in_working_context": 1,
        "failures_in_other_context": 2,
        "dropped_on_call": drops,
        "plan_still_available": survived,
        "usable_in_the_context_where_it_works": survived,
        "usable_in_the_context_where_it_fails": survived,
    }


def measure_context_aware() -> dict[str, Any]:
    """B: the same outcomes with their states. The failure is scoped, the plan survives."""
    assert macro_v1.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = macro_v1.signature(CLAUSES)
    drops = [macro_v1.note_failure(key, context=NO_SIDECAR),
             macro_v1.note_failure(key, context=NO_SIDECAR)]
    survived = macro_v1.lookup(CLAUSES) is not None
    boundary = macro_v1.applicability(key)
    return {
        "arm": "CONTEXT_AWARE",
        "successes_in_working_context": 1,
        "failures_in_other_context": 2,
        "dropped_on_call": drops,
        "plan_still_available": survived,
        "usable_in_the_context_where_it_works": survived and macro_v1.applicable(key, HAS_SIDECAR),
        "usable_in_the_context_where_it_fails": survived and macro_v1.applicable(key, NO_SIDECAR),
        "boundary": boundary.as_row(),
    }


def measure_identification_needs_contrast() -> dict[str, Any]:
    """One success + one failure leaves TWO requirements; a contrasting success pins it to one.

    After a success with {sidecar, python} and a failure with {python}, both `{sidecar}` and
    `{sidecar, python}` explain every outcome. That is not a defect: it is the honest size of the
    version space, and it is why "one demonstration teaches the condition permanently" is false.
    A second success in a state that has the sidecar but NOT the other fact removes the stricter
    hypothesis and identifies the requirement exactly.
    """
    assert macro_v1.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = macro_v1.signature(CLAUSES)
    macro_v1.note_failure(key, context=NO_SIDECAR)
    before = macro_v1.applicability(key)
    assert macro_v1.record(CLAUSES, STEPS, context=frozenset({"docx_intent_sidecar_present"}))
    after = macro_v1.applicability(key)
    return {
        "arm": "IDENTIFICATION_NEEDS_CONTRAST",
        "survivors_after_one_success_one_failure": before.survivor_count,
        "status_before": before.status,
        "survivors_after_a_contrasting_success": after.survivor_count,
        "status_after": after.status,
        "required": None if after.required is None else list(after.required),
    }


def measure_success_only() -> dict[str, Any]:
    """Control 1: one success cannot license a boundary, and the default admits the failing state."""
    assert macro_v1.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = macro_v1.signature(CLAUSES)
    boundary = macro_v1.applicability(key)
    return {
        "arm": "SUCCESS_ONLY",
        "boundary": boundary.as_row(),
        "reports_undetermined": boundary.status == APP.UNDETERMINED,
        "most_general_boundary_admits_the_failing_state": APP.admits(
            boundary.most_general, NO_SIDECAR
        ),
        "withholds_the_plan_anywhere": not macro_v1.applicable(key, NO_SIDECAR),
    }


def measure_same_context_failure() -> dict[str, Any]:
    """Control 2: a failure in the SAME state as the success must not invent a boundary.

    Nothing observed distinguishes the two outcomes, so no conjunction of observed facts can
    explain them. The learner must say INCONSISTENT and the store must fall back to the existing
    e-process rule rather than manufacturing a ban. This is the guard against repeating the error.
    """
    assert macro_v1.record(CLAUSES, STEPS, context=HAS_SIDECAR)
    key = macro_v1.signature(CLAUSES)
    first = macro_v1.note_failure(key, context=HAS_SIDECAR)
    boundary = macro_v1.applicability(key)
    entry = (macro_v1._load().get("macros") or {}).get(key) or {}
    return {
        "arm": "SAME_CONTEXT_FAILURE",
        "boundary": boundary.as_row(),
        "invents_a_boundary": boundary.identified,
        "counted_against_the_plan": int(entry.get("failures") or 0),
        "scoped_failures": int(entry.get("scoped_failures") or 0),
        "dropped_on_first_failure": first,
    }


def measure_no_context_is_unchanged() -> dict[str, Any]:
    """Control 3: a caller passing no context must see the historical behaviour exactly."""
    assert macro_v1.record(CLAUSES, STEPS)
    key = macro_v1.signature(CLAUSES)
    entry = (macro_v1._load().get("macros") or {}).get(key) or {}
    before = {"failures": int(entry.get("failures") or 0), "evidence": entry.get("evidence")}
    first = macro_v1.note_failure(key)
    second = macro_v1.note_failure(key)
    return {
        "arm": "NO_CONTEXT_IS_UNCHANGED",
        "evidence_written": before["evidence"] is not None,
        "dropped_on_first_failure": first,
        "dropped_on_second_failure": second,
        "plan_still_available": macro_v1.lookup(CLAUSES) is not None,
    }


ARMS = (
    measure_counter_only,
    measure_context_aware,
    measure_identification_needs_contrast,
    measure_success_only,
    measure_same_context_failure,
    measure_no_context_is_unchanged,
)


def run() -> dict[str, Any]:
    records = []
    original = macro_v1.STATE
    try:
        for arm in ARMS:
            with tempfile.TemporaryDirectory(prefix="macro_scope_") as tmp:
                macro_v1.STATE = pathlib.Path(tmp) / "chain_macros_v1.json"
                records.append(arm())
    finally:
        macro_v1.STATE = original
    counter, scoped = records[0], records[1]
    return {
        "schema": SCHEMA,
        "probe": "a_failure_is_a_context_not_a_ban",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "records": records,
        "summary": {
            "counter_only_loses_a_plan_that_works": (
                counter["plan_still_available"] is False
                and counter["successes_in_working_context"] == 1
            ),
            "context_aware_keeps_it": scoped["plan_still_available"] is True,
            "context_aware_offers_it_where_it_works": scoped["usable_in_the_context_where_it_works"],
            "context_aware_withholds_it_where_it_fails": (
                scoped["usable_in_the_context_where_it_fails"] is False
            ),
            "boundary_status": scoped["boundary"]["status"],
            "survivors_after_one_success_one_failure": records[2][
                "survivors_after_one_success_one_failure"
            ],
            "identification_status_after_contrast": records[2]["status_after"],
            "required_after_contrast": records[2]["required"],
            "success_only_is_undetermined": records[3]["reports_undetermined"],
            "success_only_admits_the_failing_state": records[3][
                "most_general_boundary_admits_the_failing_state"
            ],
            "same_context_invents_no_boundary": records[4]["invents_a_boundary"] is False,
            "no_context_writes_no_evidence": records[5]["evidence_written"] is False,
        },
        "hard_nonclaims": [
            "ONE_CONSTRUCTED_REQUIREMENT_CLASS__NOT_A_MEASURE_OF_ARBITRARY_ENVIRONMENTS",
            "FACTS_MUST_BE_OBSERVED__BLIND_PREMISES_ARE_NOT_CREATED_BY_THIS",
            "SELECTION_ONLY__VERIFICATION_IS_UNCHANGED",
            "NO_CAPABILITY_REGISTERED",
            "NO_TRUTH_ACHIEVED",
        ],
    }


def render(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "A failure is a context, not a ban",
        "=" * 72,
        f"  counter-only loses a plan that works elsewhere   {s['counter_only_loses_a_plan_that_works']}",
        f"  context-aware keeps the plan                     {s['context_aware_keeps_it']}",
        f"  ...offers it where it works                      {s['context_aware_offers_it_where_it_works']}",
        f"  ...withholds it where it fails                   {s['context_aware_withholds_it_where_it_fails']}",
        f"  boundary status                                  {s['boundary_status']}",
        f"  survivors after ONE success + ONE failure        {s['survivors_after_one_success_one_failure']}",
        f"  status after a contrasting success               {s['identification_status_after_contrast']}",
        f"  required facts then                              {s['required_after_contrast']}",
        "",
        "Controls",
        "-" * 72,
        f"  one success reports UNDETERMINED                 {s['success_only_is_undetermined']}",
        f"  ...and its default admits the failing state      {s['success_only_admits_the_failing_state']}",
        f"  same-context failure invents no boundary         {s['same_context_invents_no_boundary']}",
        f"  no-context callers write no evidence             {s['no_context_writes_no_evidence']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
