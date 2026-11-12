#!/usr/bin/env python3
"""Does a one-shot learned rule actually hold when it is EXECUTED against a real spec?

THE QUESTION THIS ANSWERS
-------------------------
Every check in this tree so far has been honest but *cheap*: re-checking a stored rule
(`skill_recheck_v1`), noticing two rules cancel (`skill_sequence_verify_v1`), requiring the
defect to be present (`skill_precondition_presence_v1`), resolving the program a receipt names
(`receipt_program_identity_v1`). **None of them executes the learned edit against a
specification and asks whether the answer is right.** Passing all four says a rule behaves
consistently. It does not say the rule is good.

That gap is where the claim "experience it once, learn it permanently" actually lives or dies.
A rule induced from one edit is a hypothesis about *which* edits are equivalent. One example
identifies a *set* of rules consistent with it; re-checking the store tests membership in that
set, not correctness.

So this module takes a taught edit, induces the rule with the tree's own anti-unifier, applies
it to a **victim it was never taught on**, RUNS the result against an oracle spec, and asks the
only question that matters:

    does the edit preserve the behaviour the program already had?

FOUR VERDICTS, AND THE ONES THAT HAVE TO BE REACHABLE
-----------------------------------------------------
    HOLDS           edited victim agrees with the oracle on every probe
    BREAKS          it does not -- the rule was over-general and changed behaviour it never saw
    NOT_APPLICABLE  the rule does not fire on the victim at all; nothing was edited
    REFUSED         no oracle or no probes, so nothing was executed; not a pass

Refusal is deliberately loud. Three of the four checks this session shipped were never called
by the learn path at all -- they existed and measured nothing. A check whose success case is
"I didn't look" is the same failure in a new place.

Authority: NONE. HOLDS is evidence about one rule on one probe set. It is not a capability and
it does not extend to inputs the probes do not cover.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

SCHEMA = "PROJECT_BRAIN_RULE_GENERALIZATION_PROBE_V1"

HOLDS = "HOLDS"
BREAKS = "BREAKS"
NOT_APPLICABLE = "NOT_APPLICABLE"
REFUSED = "REFUSED"
NO_RULE = "NO_RULE"

#: Given the victim's source and a probe point, return the value the *correct* program
#: produces. The oracle states the spec; the probe never asks the program what it meant.
Oracle = Callable[[str, Any], Any]


def _function_name(source: str) -> str | None:
    """The last top-level ``def`` in the snippet, which is the edit's subject."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    return names[-1] if names else None


def run_snippet(source: str, arguments: Sequence[Any] = ()) -> Any:
    """Execute one function definition and return its value on ``arguments``.

    Sandboxing is *not* attempted and must not be implied: this runs project code in-process,
    as every other verification path in this tree does. The bounded guarantee is that only the
    named function is called, once, with the given arguments.
    """
    namespace: dict[str, Any] = {}
    exec(compile(source, "<probe>", "exec"), namespace)  # noqa: S102 - the artefact under test
    name = _function_name(source)
    if name is None:
        raise SyntaxError("NO_TOP_LEVEL_FUNCTION")
    return namespace[name](*arguments)


def probe_rule(
    before_snippet: str,
    after_snippet: str,
    *,
    oracle: Oracle | None,
    probes: Iterable[Any] | None = None,
    victim_snippet: str | None = None,
    rule: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Induce a rule from one taught edit, apply it to a victim, and execute against the oracle.

    ``victim_snippet`` defaults to the taught ``before_snippet`` (in which case the probe is
    only checking that the fix reproduces itself -- the weaker question). Passing a different
    victim is the actual generalization measurement.
    """
    if rule is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule

        rule = anti_unify_code_rule(before_snippet, after_snippet)
    if not rule:
        return {"schema": SCHEMA, "verdict": NO_RULE,
                "reason": "SNIPPET_PAIR_DID_NOT_GENERALIZE",
                "taught": {"before": before_snippet, "after": after_snippet}}

    from canonical.swe_kernel.verified_skill_crystallizer_v1 import apply_crystallized_code_rule

    victim = victim_snippet if victim_snippet is not None else before_snippet
    points = list(probes) if probes is not None else []

    if oracle is None or not points:
        return {"schema": SCHEMA, "verdict": REFUSED,
                "reason": "NO_ORACLE" if oracle is None else "NO_PROBES",
                "rule_fires_on_taught_before":
                    apply_crystallized_code_rule(before_snippet, rule) is not None,
                "note": "a refused probe is not a pass; nothing was executed"}

    edited = apply_crystallized_code_rule(victim, rule)
    if edited is None:
        return {"schema": SCHEMA, "verdict": NOT_APPLICABLE,
                "reason": "RULE_DOES_NOT_FIRE_ON_VICTIM",
                "victim": victim,
                "note": "nothing was edited, so nothing was verified"}

    observed: list[dict[str, Any]] = []
    for point in points:
        entry: dict[str, Any] = {"probe": point}
        try:
            entry["expected"] = oracle(victim, point)
        except Exception as exc:                       # the oracle cannot state the spec here
            entry.update({"outcome": "ORACLE_ERROR", "error": f"{type(exc).__name__}:{exc}"})
            observed.append(entry)
            continue
        try:
            entry["actual"] = run_snippet(edited, (point,))
        except Exception as exc:
            entry.update({"outcome": "EXECUTION_ERROR", "error": f"{type(exc).__name__}:{exc}"})
            observed.append(entry)
            continue
        entry["outcome"] = "AGREES" if entry["actual"] == entry["expected"] else "DISAGREES"
        observed.append(entry)

    disagreements = [o for o in observed if o["outcome"] != "AGREES"]
    verdict = BREAKS if disagreements else HOLDS
    return {"schema": SCHEMA, "verdict": verdict,
            "reason": None if verdict == HOLDS else f"{len(disagreements)}_OF_{len(observed)}_FAILED",
            "victim": victim, "edited": edited, "probes": observed,
            "authority": "NONE",
            "rule": {k: rule[k] for k in ("pattern_format", "language") if k in rule}}


# ---------------------------------------------------------------------------
# the concrete spec used by the CLI
# ---------------------------------------------------------------------------
def strict_boundary_oracle(_victim_source: str, point: Any) -> bool:
    """Spec: 'under 100' is a STRICT boundary. A program returning True at 100 is wrong."""
    return point < 100


def demonstrate() -> dict[str, Any]:
    """One rule, two victims: the same edit is right on one and wrong on the other."""
    honest = probe_rule(
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        oracle=strict_boundary_oracle,
        probes=(0, 99, 100, 101),
        victim_snippet="def tier(a):\n    return a <= 100\n",
    )
    overgeneral = probe_rule(
        "def classify(x):\n    return x < 100\n",
        "def classify(x):\n    return x <= 100\n",
        oracle=strict_boundary_oracle,
        probes=(0, 99, 100, 101),
        victim_snippet="def tier(a):\n    return a < 100\n",
    )
    refused = probe_rule(
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        oracle=None, probes=(0,),
    )
    return {"honest_rule_on_new_victim": honest,
            "overgeneral_rule_on_new_victim": overgeneral,
            "no_oracle": refused}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = demonstrate()
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        for label, outcome in result.items():
            print(f"{label:30} -> {outcome['verdict']}")
            if outcome.get("edited"):
                print(f"    victim : {outcome['victim']!r}")
                print(f"    edited : {outcome['edited']!r}")
            for probe in outcome.get("probes") or ():
                print(f"    {probe.get('probe'):>4}  expected={probe.get('expected')!r:6}"
                      f" actual={probe.get('actual')!r:6} {probe['outcome']}")
    # Exit 1 when the over-general rule visibly breaks behaviour: that is the finding.
    return 1 if result["overgeneral_rule_on_new_victim"]["verdict"] == BREAKS else 0


if __name__ == "__main__":
    raise SystemExit(main())
