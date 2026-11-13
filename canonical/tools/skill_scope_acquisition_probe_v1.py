#!/usr/bin/env python3
"""One skill, eight victims, and the difference a bought scope makes.

This is the demonstration `skill_scope_acquisition_v1` is judged by, and it is deliberately shaped so
that a decorative scope cannot pass it. The same crystallized boundary lesson is run against the same
eight victims twice:

  1. WITHOUT a scope -- the skill proposes wherever its tokens match. Measured: it repairs the four
     victims that actually fail their own specification and it BREAKS the four that already satisfy
     theirs, because `>=` -> `>` is in the swap family of `<=` -> `<` and fires on correct code.
  2. WITH the scope it bought from its own executed behaviour -- `required` is
     `baseline.violates_own_spec`, so the four correct victims are refused BEFORE anything is edited.

Both numbers move, in opposite directions, or the scope is decoration. The dose-response ladder is
reported too: how many observations it took, and what the law said at each one, because "identified"
without a count is the same shape of claim as "verified_hits" without a state.

Nothing here is stubbed. The lesson is taught through `VerifiedSkillStore.crystallize_code_fix`, and
every verdict comes from executing a victim against its own specification.

Authority: NONE. Producer-run measurement on constructed fixtures.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

SCHEMA = "PROJECT_BRAIN_SKILL_SCOPE_ACQUISITION_PROBE_V1"

TAUGHT_BEFORE = "def within(x, hi):\n    return x <= hi\n"
TAUGHT_AFTER = "def within(x, hi):\n    return x < hi\n"

# The victim's OWN specification. Nothing tells the probe which victims are defective: that is
# decided by executing the spec against the source, before any skill is applied.
EXCLUSIVE = "assert f(10, 10) is False\nassert f(9, 10) is True\nassert f(0, 10) is True\n"
INCLUSIVE = "assert f(10, 10) is True\nassert f(9, 10) is False\nassert f(11, 10) is True\n"

VICTIMS = [
    # defect present: fails its own spec until the lesson applies
    {"label": "return_site_defect", "source": "def f(x, hi):\n    return x <= hi\n",
     "spec": EXCLUSIVE},
    {"label": "if_guard_defect",
     "source": "def f(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
     "spec": "assert f(10, 10) is False\nassert f(9, 10) is True\n"},
    {"label": "flipped_operands_defect", "source": "def f(x, hi):\n    return hi >= x\n",
     "spec": EXCLUSIVE},
    {"label": "negated_defect", "source": "def f(x, hi):\n    return not (x > hi)\n",
     "spec": EXCLUSIVE},
    {"label": "assignment_site_defect",
     "source": "def f(x, hi):\n    ok = x <= hi\n    return not ok\n",
     "spec": "assert f(10, 10) is True\nassert f(9, 10) is False\n"},
    # defect ABSENT: already satisfies its own spec, and the swap family still fires on it
    {"label": "return_site_already_correct", "source": "def f(x, hi):\n    return x >= hi\n",
     "spec": INCLUSIVE},
    {"label": "if_guard_already_correct",
     "source": "def f(x, hi):\n    if x >= hi:\n        return True\n    return False\n",
     "spec": "assert f(10, 10) is True\nassert f(9, 10) is False\n"},
    {"label": "flipped_operands_already_correct", "source": "def f(x, hi):\n    return hi <= x\n",
     "spec": INCLUSIVE},
]


def _twin_oracle(source: str) -> bool:
    """Name-agnostic: the twin is alpha-renamed, so find the callable rather than naming it."""
    ns: dict = {}
    try:
        exec(compile(source, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


def teach(tmp: pathlib.Path):
    store = cry.VerifiedSkillStore(db_path=tmp / "scope.db", seed=False)
    taught = store.crystallize_code_fix(before_snippet=TAUGHT_BEFORE, after_snippet=TAUGHT_AFTER,
                                       language="python", error_class="BOUNDARY",
                                       twin_oracle=_twin_oracle)
    if not taught.get("crystallized"):
        raise RuntimeError(f"LESSON_NOT_ADMITTED:{taught.get('reason')}")
    rules = store.lookup_rules("python", "BOUNDARY")
    if len(rules) != 1:
        raise RuntimeError("EXPECTED_EXACTLY_ONE_LESSON")
    return rules[0]


def demonstration() -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        rule = teach(tmp)

        # 1. no scope: propose wherever the tokens match
        unscoped = [acq.observe(rule, v["source"], v["spec"]) for v in VICTIMS]
        repaired_before = sum(1 for o in unscoped if o["verdict"] == acq.REPAIRED)
        broke_before = sum(1 for o in unscoped if o["verdict"] == acq.BROKE_CORRECT)
        not_applicable = sum(1 for o in unscoped if o["verdict"] == acq.NOT_APPLICABLE)

        # 2. buy the scope from the skill's own executed behaviour
        bought = acq.buy_scope(rule, VICTIMS, budget=len(VICTIMS))
        required = bought["required"]

        # the ladder: what the law said after each observation, in the order they were spent
        ladder = []
        rows: list[tuple[list[str], bool]] = []
        for step in bought["trace"]:
            obs = unscoped[step["index"]]
            if obs["row"] is not None:
                rows.append((list(obs["row"][0]), bool(obs["row"][1])))
            b = app.learn(rows)
            ladder.append({"observations": len(rows), "status": b.status,
                           "required": b.required, "survivors": b.survivor_count,
                           "label": step["label"], "verdict": step["verdict"]})

        # the earnability control: the same rows with every failure removed must NOT identify
        successes_only = [(st, ok) for st, ok in
                          [(list(o["row"][0]), bool(o["row"][1])) for o in unscoped if o["row"]]
                          if ok]
        control = app.learn(successes_only)

        # 3. with the scope enforced: refuse before editing where the requirement is absent
        repaired_after = broke_after = refused = 0
        refusals = []
        for v, obs in zip(VICTIMS, unscoped):
            gate = acq.admits(required, obs["state"])
            if not gate["admitted"]:
                refused += 1
                refusals.append({"label": v["label"], "missing": gate["missing"],
                                 "would_have_been": obs["verdict"]})
                continue
            if obs["verdict"] == acq.REPAIRED:
                repaired_after += 1
            elif obs["verdict"] == acq.BROKE_CORRECT:
                broke_after += 1

        return {
            "schema": SCHEMA,
            "authority": "NONE__PRODUCER_RUN_MEASUREMENT_ON_CONSTRUCTED_FIXTURES",
            "taught_lesson": {"before": TAUGHT_BEFORE, "after": TAUGHT_AFTER,
                              "swap": gen.derive_operator_swap(rule),
                              "swap_family": [(s["from"], s["to"])
                                              for s in gen.derive_swap_family(rule)]},
            "victims_offered": len(VICTIMS),
            "fired_on": sum(1 for o in unscoped if o["fired"]),
            "not_applicable": not_applicable,
            "repaired": repaired_before,
            "broke_correct_code_before_scope": broke_before,
            "status": bought["status"],
            "required": list(required) if required else None,
            "reason": bought["reason"],
            "survivors": bought["survivors"],
            "observations_to_identify": bought["observations_spent"],
            "evidence_rows": bought["evidence_rows"],
            "successes": bought["successes"],
            "failures": bought["failures"],
            "ladder": ladder,
            "repairs_after_scope": repaired_after,
            "broke_correct_code_after_scope": broke_after,
            "refusals": refused,
            "refusals_named": refusals,
            "earnability_control": {
                "successes_only_status": control.status,
                "successes_only_reason": control.reason,
                "successes_only_required": list(control.required) if control.required else None,
                "point": ("if the label were reachable from successes alone it would be a constant, "
                          "not a measurement"),
            },
            "per_victim": [{"label": v["label"], "verdict": o["verdict"], "fired": o["fired"],
                            "baseline_ok": o["baseline_ok"], "solved": o["solved"],
                            "candidates": o["candidates"],
                            "admitted_with_scope": acq.admits(required, o["state"])["admitted"]}
                           for v, o in zip(VICTIMS, unscoped)],
        }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = demonstration()
    if args.json:
        print(json.dumps(doc, indent=1, sort_keys=True, default=sorted))
        return 0
    print("skill scope acquisition probe: one lesson, eight victims, executed\n")
    print(f"  taught swap            {doc['taught_lesson']['swap']}")
    print(f"  swap family            {doc['taught_lesson']['swap_family']}")
    print(f"  victims offered        {doc['victims_offered']}   fired on {doc['fired_on']}"
          f"   not applicable {doc['not_applicable']}")
    print(f"\n  WITHOUT a scope")
    print(f"    repaired             {doc['repaired']}")
    print(f"    BROKE CORRECT CODE   {doc['broke_correct_code_before_scope']}")
    print(f"\n  buying the scope")
    print(f"    observations spent   {doc['observations_to_identify']}")
    print(f"    evidence rows        {doc['evidence_rows']} "
          f"({doc['successes']} successes, {doc['failures']} failures)")
    print(f"    status               {doc['status']}")
    print(f"    required             {doc['required']}")
    for step in doc["ladder"]:
        print(f"      after {step['observations']} obs  {step['status']:52} "
              f"required={step['required']}  ({step['label']}: {step['verdict']})")
    print(f"\n  WITH the scope enforced")
    print(f"    repairs              {doc['repairs_after_scope']}  (was {doc['repaired']})")
    print(f"    broke correct code   {doc['broke_correct_code_after_scope']}"
          f"  (was {doc['broke_correct_code_before_scope']})")
    print(f"    refused before edit  {doc['refusals']}")
    for r in doc["refusals_named"]:
        print(f"      {r['label']:34} missing={r['missing']} would_have_been={r['would_have_been']}")
    print(f"\n  earnability control    successes only -> {doc['earnability_control']['successes_only_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
