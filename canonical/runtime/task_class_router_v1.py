"""One gate that decides WHICH KIND of problem a task is, before attempting it.

Three instruments existed separately after r87 and each knew one thing:

    goal_shape_v1        what WRITES does the goal require?      (arity / spread / transform)
    addressability_v1    can the terminal state be OBSERVED?     (state / hybrid / render / unobservable)
    multi_bind_v1        can those writes be BOUND?              (SOLVED / AMBIGUOUS / NO_FIELD)

Separately they are diagnostics. Together they answer the only question worth asking
before spending an episode:

    should this be executed, demonstrated, or refused?

That question matters because the three classes need three different mechanisms and only
one of them is cheap:

    A  token in the goal + an addressable effect    -> EXECUTE      (zero model calls)
    B  tokens + an addressable effect, multi-write  -> EXECUTE      (the binder, r87: 5/7)
    C  a predicate referent ("the shortest one")    -> DEMONSTRATE  (only a demonstration
                                                                     can name the object)
    D  a terminal state nothing can observe         -> REFUSE

r68's law applies to the router itself: one that cannot tell two classes apart must
refuse. So every ambiguous case here resolves to DEMONSTRATE or REFUSE, never to a guess.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.addressability_probe_v1 import (
    DOM_ONLY_UNOBSERVABLE, HYBRID, RENDER_ONLY, STATE_ADDRESSABLE, classify_source,
    referent_is_predicate,
)
from canonical.runtime.goal_arity_v1 import goal_shape
from canonical.runtime.multi_bind_v1 import plan_multi_bind

# TWO ORTHOGONAL VERDICTS. My first design collapsed them and refused 114 of 130 tasks,
# two of which the executor actually wins. "Can a reusable skill be compiled?" and "how
# should the agent attempt this now?" are different questions, and answering the first
# with REFUSE must never imply refusing the second. -- a_r88

# verdict 1: skill compilability
SKILL_YES = "SKILL_COMPILABLE"
SKILL_NO = "SKILL_NOT_COMPILABLE"

# verdict 2: how to attempt the task now
ATTEMPT_EXECUTE = "ATTEMPT_EXECUTE"        # deterministic, zero model calls
ATTEMPT_BINDER = "ATTEMPT_BINDER"          # deterministic multi-write binder
ATTEMPT_PIXEL = "ATTEMPT_PIXEL"            # the pixel/accessibility loop
ATTEMPT_DEMONSTRATE = "ATTEMPT_DEMONSTRATE"  # only a demonstration can name the referent
ATTEMPT_REFUSE = "ATTEMPT_REFUSE"          # nothing observable to check, and nothing to bind

EXECUTE_SIMPLE = "EXECUTE_SIMPLE"          # one literal, one control
EXECUTE_BINDER = "EXECUTE_BINDER"          # several literals / spread / transform
DEMONSTRATE = "DEMONSTRATE"                # the referent cannot be named in text
REFUSE = "REFUSE"                          # nothing observable to check

# Which classes the executor actually claims.
EXECUTABLE = {EXECUTE_SIMPLE, EXECUTE_BINDER}


def route(goal: str, html: str, state: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Decide the class. Pure: no clicks, no model calls, no side effects."""
    shape = goal_shape(goal or "")
    addr = classify_source(html or "")
    predicate = referent_is_predicate(goal or "")

    decision: str
    why: str

    # 1. Is there anything to bind at all? This must come FIRST. My first version tested
    #    addressability before literals and REFUSED all 130 MiniWob tasks -- including the
    #    eight the executor actually wins. A gate that refuses everything is not a decision,
    #    it is a stub wearing a verdict. -- a_r88
    #
    # A token the goal names explicitly is a target the ACTOR can address directly, so the
    # question "is the terminal state observable to a compiled skill" is not the right test
    # for it: MiniWob reports the terminal state in a JS global, which is a code-readable
    # channel (r85), and the executor demonstrably wins 5/7 binder tasks on such pages.
    has_bindable_literal = bool(shape["literals"]) and addr["kind"] != RENDER_ONLY
    if not has_bindable_literal and addr["kind"] in (RENDER_ONLY, DOM_ONLY_UNOBSERVABLE):
        decision = REFUSE
        why = ("the terminal state is a rendered result; no code path observes it, so a "
               "compiled skill could not be verified (r84/r85)")
        if addr["kind"] == DOM_ONLY_UNOBSERVABLE:
            why = ("no code-readable channel was found for the terminal state; it may exist "
                   "at runtime, so this is 'not observed', not 'not observable'")
    # 2. Is the target named by a property rather than a token? Only a demonstration can
    #    say which object a predicate picked.
    elif predicate and not shape["literals"]:
        decision = DEMONSTRATE
        why = ("the referent is a predicate ('the shortest one'); no token exists to bind, "
               "so the choice must be shown once")
    # 3. No literal at all and no predicate: the goal names nothing writable.
    elif not shape["literals"]:
        decision = DEMONSTRATE
        why = "the goal contains no literal to bind and no observable predicate referent"
    # 4. Literals exist. Can they be bound to controls?
    else:
        plan = plan_multi_bind(goal, list(state or []))
        if plan["status"] == "SOLVED":
            mode = plan.get("mode", "")
            decision = EXECUTE_SIMPLE if mode in ("one_value_one_field",
                                                  "one_value_named_single_field") else EXECUTE_BINDER
            why = f"bound {len(plan['writes'])} write(s) via {mode}"
        elif plan["status"] == "AMBIGUOUS":
            decision = DEMONSTRATE
            why = plan.get("why") or "several controls could take this value; refuse to guess"
        else:
            # NO_FIELD / TOO_FEW_FIELDS / NO_LITERAL with no readable controls: the page did
            # not expose enough to decide. That is not a licence to click.
            decision = DEMONSTRATE
            why = f"binder says {plan['status']}; the target must be shown once"

    # The second verdict, which the first must not silently dictate.
    if decision in EXECUTABLE:
        attempt = ATTEMPT_EXECUTE if decision == EXECUTE_SIMPLE else ATTEMPT_BINDER
    elif addr["kind"] in (RENDER_ONLY, DOM_ONLY_UNOBSERVABLE):
        # Neither kind is compilable into a verified skill, but the agent can still act on
        # pixels, and "unobservable" means the state was not FOUND -- not that the task is
        # impossible. The pixel loop demonstrably wins on this kind of page. Returning
        # REFUSE here for dom_only_unobservable was the same collapse, one level down.
        attempt = ATTEMPT_DEMONSTRATE if predicate else ATTEMPT_PIXEL
    elif decision == DEMONSTRATE:
        attempt = ATTEMPT_DEMONSTRATE
    else:
        attempt = ATTEMPT_REFUSE

    skill_ok = decision in EXECUTABLE

    return {
        "decision": decision,
        "skill": SKILL_YES if skill_ok else SKILL_NO,
        "attempt": attempt,
        "why": why,
        "task_kind": addr["kind"],
        "referent_is_predicate": predicate,
        "goal_shape": shape,
        "executable": decision in EXECUTABLE,
        "confidence": "high" if decision == REFUSE else ("medium" if decision == EXECUTE_SIMPLE else "low"),
    }
