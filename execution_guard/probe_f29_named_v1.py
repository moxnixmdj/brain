#!/usr/bin/env python3
"""EXPERIMENT: F29 - a request must NAME the capability it selects.

The retrieval path can be decisive for a request that named NOTHING.  Measured: "Run the
thing." selects `run_long_horizon_continuity_v1`, because "run" is the only capability name
in the registry that contains it, so the margin is 1.0 against no competitor.  The machine
then reports success on a request that described no task.  The base commit does the same, so
this is a pre-existing hole.

The rule: a capability's NAME is how the caller refers to it.  A request that contains no
word of that name - other than the verbs any request is made of ("run", "execute", "do") -
did not name this capability, whatever the lexical score says.  The score matched a verb.

This measures the rule in both directions, with the name split on every separator the
inventory uses (`.`, `_`, `-`; the earlier attempt split on only two of them and so failed to
see `bson-modern` in "the bson modern python library").

Read-only.  Writes /tmp/f29_named.json.  Authority: NONE.  Credit: 0.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

_SUFFIX = re.compile(r"\.py\.auto\.v\d+$")
_VERBS = {"run", "runs", "running", "execute", "executes", "perform", "performs", "do", "does",
          "make", "makes", "invoke", "invokes", "call", "calls", "start", "starts", "trigger",
          "triggers", "launch", "launches", "apply", "applies", "produce", "produces",
          "generate", "generates", "create", "creates", "compute", "computes", "evaluate",
          "evaluates", "use", "uses", "the", "a", "an"}
_ADVERSARIAL = [
    "Do the needful thing.", "Run the thing.", "Run the v1.", "Run the canonical runtime py auto v1.",
    "Run the auto canonical runtime.", "Please handle it as usual.", "Run the.",
    "Run the v2.", "Do what is right.", "Run the capability.", "Run the 1.", "Run the v.",
    "Run the auto.", "Run the py auto v1 canonical runtime.", "Run it.", "Do it.", "Execute.",
    "Just run it.", "Run the task.", "Perform the operation.", "Go ahead and run it.",
]


def name_words(cid: str) -> set[str]:
    """The capability's NAME words: its last path segment, split on every separator."""
    stem = _SUFFIX.sub("", cid.rsplit("/", 1)[-1])
    return {w.lower() for w in re.split(r"[._\-]+", stem) if len(w) > 1 and not w.isdigit()}


def request_words(goal: str) -> set[str]:
    return {t for t in gc._tokens(goal) if t not in gc.GENERIC_MATCH_TOKENS}


def stem_sentence(cid: str) -> str:
    stem = _SUFFIX.sub("", cid.rsplit("/", 1)[-1])
    return "Run the " + " ".join(w for w in stem.split("_") if len(w) > 1) + "."


def names_it(goal: str, cid: str) -> bool:
    """True when the request contains a word of the capability's name that is not a verb."""
    shared = (name_words(cid) & request_words(goal)) - _VERBS
    return bool(shared)


def main() -> int:
    reg = gc._platform_admissible_registry(dict(load_verified_registry()))
    zero = {c: e for c, e in reg.items() if not front.is_plain_goal_routable(e)}

    # 1. the 296 that must still be reached
    lost, reached = [], 0
    for cid, entry in sorted(zero.items()):
        goal = stem_sentence(cid)
        if not names_it(goal, cid):
            lost.append(cid)
            continue
        try:
            c = front.compile_goal(goal, reg, ROOT)
            if c.get("selected_capability") == cid:
                reached += 1
        except gc.GoalCompilationFailure:
            pass
    print(f"296 zero-input capabilities: {reached} still reached; {len(lost)} would be lost")
    for cid in lost[:8]:
        print("   LOST:", cid[:76])

    # 2. the adversarial requests
    print("\nadversarial requests:")
    refused = 0
    for goal in _ADVERSARIAL:
        cap = None
        try:
            c = front.compile_goal(goal, reg, ROOT)
            cap = c.get("selected_capability")
        except gc.GoalCompilationFailure:
            pass
        ok = cap is None or not names_it(goal, cap)
        refused += ok
        print(f"   {'REFUSED' if ok else 'ANSWERED':<9} {goal[:42]:<44} -> {str(cap)[:40]}")
    print(f"   refused: {refused}/{len(_ADVERSARIAL)}")

    # 3. the real family sentences must not be blocked
    from execution_guard.live_solver_end_to_end_measurement_v1 import all_generators
    work = ROOT / "canonical/astra_runtime/tmp/probe_f29"
    work.mkdir(parents=True, exist_ok=True)
    rng = random.Random(11)
    allowed, blocked = 0, []
    for family, gen in all_generators().items():
        if family == "OUT_OF_SCOPE_MUST_FAIL_CLOSED":
            continue
        for i in range(8):
            case = gen(rng, work, i)
            cap = None
            try:
                c = front.compile_goal(case.goal, reg, ROOT)
                cap = c.get("selected_capability")
            except gc.GoalCompilationFailure:
                pass
            if cap is None:
                continue
            if names_it(case.goal, cap):
                allowed += 1
            else:
                blocked.append((family, case.goal[:88], cap))
    print(f"\nreal family sentences: allowed {allowed}, blocked {len(blocked)}")
    for family, goal, cap in blocked[:12]:
        print(f"   BLOCKED {family:<34} {goal[:66]} -> {cap[:34]}")

    Path("/tmp/f29_named.json").write_text(json.dumps(
        {"lost": lost, "blocked": blocked}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
