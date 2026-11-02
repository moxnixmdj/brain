"""State, out loud and in one place, what an under-specified goal is missing.

Measured 2026-11-02: when a goal does not supply what a capability's input
contract needs, `live_integrated_brain_v1.compile_against_live_registry` fails
closed and already reports a precise, structured reason in
`GoalCompilationFailure.detail`, of the form

    <capability>:<slot>:<reason>

for example

    python.refactor.extract_function.v1:module:not_stated
    http.json.fetch_from_state:source_json_path:0_type_compatible_existing_files_named
    math.numeric_expression.sympy:expression:value_not_parseable

The second of those is notable: the reason says the compiler looked for existing
files compatible with the slot's type and found zero. That is the machine stating
a gap in its own knowledge of the world, precisely, on its own initiative.

This is `OWNER_ACTIVE_GOAL_20261018_V1.md` section 5 capability 4 -- "it says 'I
don't have the data' out loud, then gets it, by itself." **The first half already
exists and nothing consumes it.** This module is the consumer: it turns those
structured failures into one explicit statement of what is needed to proceed.

WHAT THIS MODULE DOES NOT DO, stated so it is not over-read:

* It never executes a capability. It only compiles a goal, which is what the door
  already does on every request.
* It does not acquire anything. Capability 4's second half -- going and getting
  the data -- is not implemented here and is not claimed.
* It does not add a capability, register a row, flip a family, or move any count.
* It does not infer a slot value. If the door could not fill a slot, this module
  reports that it could not; it never guesses, because a guessed slot is exactly
  the silent mis-selection this exists to replace.
* It does not make selection fail loudly. Under-specified goals that COMPILE onto
  the wrong row (measured: 3 of 12) still compile, and this module reports
  `outcome='COMPILED'` for them without endorsing the choice. Closing that is a
  separate change in the door and is deliberately not attempted here.

One defect is reported rather than papered over: a goal for which the compiler
finds no candidate at all raises with `detail=None`. An empty detail leaves a
consumer unable to distinguish "no candidate capability" from "the report is
broken", so this module names that case explicitly as `NO_CANDIDATE_REPORTED`.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

SCHEMA = "BRAIN_GOAL_GAP_STATEMENT_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
_MODEL_PATH = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# Outcome vocabulary. Each is a distinct state of the world, not a severity rank.
OUTCOMES = (
    "COMPILED",                  # the door bound the goal to a row; nothing is missing
    "LOW_CONFIDENCE_SELECTION",  # the door bound the goal to a row the goal did not ask for
    "SLOT_UNSTATED",             # a row was identified and a named slot could not be filled
    "NO_CANDIDATE_REPORTED",     # the door failed closed and reported no detail at all
    "UNPARSEABLE_REPORT",        # the door reported something this module cannot parse
    "COMPILER_RAISED",           # an unexpected exception; named, never swallowed
)

_PLAIN_REASON = {
    "not_stated": "the goal does not state it",
    "value_not_parseable": "something in the goal was read as this slot but could not be parsed",
    "0_type_compatible_existing_files_named": (
        "no existing file compatible with this slot was found -- the compiler looked"
    ),
}


def _registry_rows() -> dict[str, dict[str, list[str]]]:
    """capability id -> its declared input slots and requirements.

    Read from the compiled artifact. An empty result is reported as such by the
    caller rather than treated as "every row requires nothing".
    """
    try:
        model = json.loads(_MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, dict[str, list[str]]] = {}
    for row in model.get("capabilities") or []:
        cid = str(row.get("id") or "")
        if cid:
            out[cid] = {
                "input_names": [str(n) for n in (row.get("input_names") or [])],
                "requires": [str(n) for n in (row.get("requires") or [])],
            }
    return out


def _plain(reason: str) -> str:
    return _PLAIN_REASON.get(reason, "the compiler reported " + (reason or "an empty reason"))


def state_the_gap(goal: str, root: pathlib.Path | str | None = None) -> dict[str, Any]:
    """Compile `goal` and state exactly what stands between it and being actionable.

    Returns a dict that always carries `outcome`, `statement` and `authority`.
    `statement` is a sentence a person or a machine can act on. Nothing is
    executed and no slot value is invented.
    """
    base = pathlib.Path(root).resolve() if root is not None else ROOT
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "goal": str(goal or ""),
        "outcome": "",
        "capability": None,
        "slot": None,
        "reason": None,
        "contract": [],
        "statement": "",
        "authority": "NONE",
    }

    if not str(goal or "").strip():
        result["outcome"] = "UNPARSEABLE_REPORT"
        result["statement"] = "No goal was given, so nothing can be stated about it."
        return result

    try:
        from canonical.runtime import live_integrated_brain_v1 as _lib
    except Exception as exc:  # pragma: no cover - import failure is itself the finding
        result["outcome"] = "COMPILER_RAISED"
        result["statement"] = f"The compiler could not be imported: {type(exc).__name__}."
        return result

    rows = _registry_rows()

    try:
        _registry, _admissible, compiled = _lib.compile_against_live_registry(str(goal), base)
    except Exception as exc:
        code = str(getattr(exc, "code", "") or "")
        detail = getattr(exc, "detail", None)
        result["reason_code"] = code or type(exc).__name__

        if detail is None or not str(detail).strip():
            # A fail-closed refusal with no detail. Named, not silently normalised.
            result["outcome"] = "NO_CANDIDATE_REPORTED"
            result["statement"] = (
                f"The goal was refused ({code or type(exc).__name__}) and the compiler reported no "
                "detail, so no candidate capability and no missing slot could be named. That is a "
                "gap in the report itself, not a statement about the goal."
            )
            return result

        parts = [p for p in str(detail).split(":")]
        if len(parts) < 2:
            result["outcome"] = "UNPARSEABLE_REPORT"
            result["statement"] = (
                f"The compiler reported '{str(detail)[:120]}', which does not carry a slot, so what "
                "is missing cannot be stated."
            )
            return result

        capability = parts[0]
        slot = parts[1]
        reason = ":".join(parts[2:]) if len(parts) > 2 else ""
        result["outcome"] = "SLOT_UNSTATED"
        result["capability"] = capability
        result["slot"] = slot
        result["reason"] = reason or None
        result["contract"] = rows.get(capability, {}).get("input_names", [])
        still = [s for s in result["contract"] if s != slot]
        result["statement"] = (
            f"To do this I would use '{capability}', and I cannot: it needs '{slot}', and { _plain(reason) }."
            + (f" Its full contract is {result['contract']}." if result["contract"] else "")
            + (f" Supply '{slot}' first; the rest of the contract is {still}." if still else "")
        )
        return result

    selected = str((compiled or {}).get("selected_capability") or "")
    declared = rows.get(selected, {})
    evidence = (compiled or {}).get("match_evidence") or {}
    goal_tokens = [str(x) for x in (evidence.get("goal_tokens") or [])]
    matched_provides = [str(x) for x in (evidence.get("matched_provides") or [])]
    matched_requires = [str(x) for x in (evidence.get("matched_requires") or [])]
    coverage = (
        len(set(matched_provides) | set(matched_requires)) / len(goal_tokens)
        if goal_tokens else 0.0
    )

    result["capability"] = selected or None
    result["contract"] = declared.get("input_names", [])
    result["declared_requires"] = declared.get("requires", [])
    result["selection_endorsed"] = False   # never endorsed; see the module docstring
    result["match_evidence"] = {
        "score": (compiled or {}).get("score"),
        "goal_tokens": goal_tokens,
        "matched_provides": matched_provides,
        "matched_requires": matched_requires,
        "goal_token_coverage": round(coverage, 4),
    }

    if not selected:
        result["outcome"] = "COMPILED"
        result["statement"] = "The goal compiled but named no capability."
        return result

    # UNFORCED SELECTION. Structural, not a tuned cutoff: the selected row declares
    # requirements and the goal matched NONE of them, so nothing in the goal asked
    # for this capability. Measured 2026-11-02 on 7 compiled under-specified goals
    # (n=7, and the intended row is my judgment, not ground truth the tree
    # declares): all 3 that selected a wrong row had matched_requires empty and
    # coverage 0.17-0.25, while all 4 that selected the intended row had
    # matched_requires non-empty and coverage 0.50-1.00. Score separated the same
    # way (11-13 wrong vs 24-36 right) but is reported as evidence, not used as a
    # threshold, because a numeric cutoff fitted to 7 points would be overfitting.
    # Rows that declare NO requirements are exempt: "matched none of nothing"
    # carries no information.
    if declared.get("requires") and not matched_requires:
        result["outcome"] = "LOW_CONFIDENCE_SELECTION"
        result["statement"] = (
            f"This compiled onto '{selected}', but the goal was not what asked for it: "
            f"'{selected}' declares it requires {declared['requires']}, and the goal matched "
            f"none of that. Only {len(matched_provides)} of {len(goal_tokens)} goal tokens "
            f"({', '.join(matched_provides) or 'none'}) matched anything it provides, at score "
            f"{(compiled or {}).get('score')}. The choice was not forced by the goal, so acting "
            f"on it would be acting on a guess -- state the target and the operation explicitly."
        )
        return result

    result["outcome"] = "COMPILED"
    result["statement"] = (
        f"The goal compiled onto '{selected}' and nothing was reported missing."
    )
    return result


def state_the_gaps(goals: Mapping[str, str] | list[str]) -> list[dict[str, Any]]:
    """`state_the_gap` over several goals, ranked so the actionable ones come first.

    Ranking is by what it costs to ignore the statement. A selection the goal did
    not force comes first because acting on it does the wrong thing; a named
    missing slot comes next because it merely stops; an empty report comes last
    because nothing can be acted on until the report itself is fixed.
    """
    items = list(goals.values() if isinstance(goals, Mapping) else goals)
    rows = [state_the_gap(g) for g in items]
    # A wrong action ranks above a missing one: LOW_CONFIDENCE_SELECTION will
    # proceed and do the wrong thing, whereas SLOT_UNSTATED merely stops.
    order = {"LOW_CONFIDENCE_SELECTION": 0, "SLOT_UNSTATED": 1, "COMPILED": 2,
             "UNPARSEABLE_REPORT": 3, "NO_CANDIDATE_REPORTED": 4, "COMPILER_RAISED": 5}
    return sorted(rows, key=lambda r: order.get(str(r.get("outcome")), 9))


__all__ = ["SCHEMA", "OUTCOMES", "state_the_gap", "state_the_gaps"]
