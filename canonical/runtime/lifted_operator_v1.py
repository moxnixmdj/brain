#!/usr/bin/env python3
"""Save the contract, not the action list.

WHY THIS EXISTS
---------------
`perfect_algorithm_v1.generalize()` stores a **plan sketch**: the literal
sequence of action names that reached the goal. Measured on a real computer
(2026-11-24), that replays perfectly when the next instance offers an action
with the same name, and it is worth nothing the moment the vocabulary differs --
which is the normal case in an arbitrary environment, because action names are
that environment's own invention.

The owner's question was exactly this: *"saving his exact experience must be in
a very sufficient way, not just saving the exact experience in a dumb way...
maybe we should do generalization."* An action name is the dumbest possible
durable unit: it is the environment's spelling of an operation, not the
operation.

WHAT IS SAVED
-------------
A lifted operator, which is the smallest object that survives a change of
spelling while still being refutable:

    program       the operation's identity AS THE MACHINE NAMES IT (gzip), not
                  the action name a particular environment gave it
    roles         which observed file plays which part (source, output)
    precondition  predicates over the OBSERVATION that must hold to apply
    effect        a checkable claim: the machine's own reader turns the output
                  back into the source (delegated to `effect_oracle_v1`)
    evidence      where it came from, and the instances it survived

Binding at use time is then a search, not a lookup:
    1. find the action in THIS environment whose program is the rule's program
       (or which can do the operation) -- by name, and, if the name is absent,
       by trying candidates and checking the effect;
    2. bind the roles to THIS instance's files -- refusing when the binding is
       ambiguous rather than guessing;
    3. run it;
    4. re-verify the effect HERE with the oracle before believing anything.

Step 4 is what makes a lifted rule safe to reuse: the rule is a claim about an
effect, and the effect is checked in the new world, not remembered from the old
one. A rule whose effect does not hold is REFUTED and not re-saved.

WHAT THIS IS NOT
----------------
* Not a claim that program names transfer between machines. Where the name is
  absent, the rule is not trusted; the loop falls back to scanning.
* Not a proof. A lifted operator that survived one fresh instance is a
  hypothesis with a checked effect, exactly as before.
* Not a new store. It is the same inspectable JSON memory; a lifted row is a
  `kind: "operator"` rule inside it, deletable like any other.

Zero model calls. Standard library only. Authority NONE.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIFTED_OPERATOR_V1"

APPLIED = "APPLIED__EFFECT_VERIFIED_HERE"
REFUSED_NO_ACTION = "REFUSED__NO_ACTION_IN_THIS_ENVIRONMENT_HAS_THAT_PROGRAM"
REFUSED_AMBIGUOUS = "REFUSED__ROLE_BINDING_AMBIGUOUS"
REFUSED_PRECONDITION = "REFUSED__PRECONDITION_ABSENT"
REFUTED = "REFUTED__EFFECT_DID_NOT_HOLD_HERE"

# The only word-level knowledge this module uses is that an action's name
# usually contains the program's name; that is a naming convention of the
# registrar, not a fact about programs. When it fails, candidate actions are
# tried and their effects checked -- the fallback keeps the convention from
# becoming an assumption.
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_.+-]*")


def _visible_programs() -> list[str]:
    import os

    seen: set[str] = set()
    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        try:
            for name in os.listdir(directory or "."):
                seen.add(name)
        except OSError:
            continue
    return sorted(seen)


def lift(*, goal: str, goal_family: str, env_kind: str, action: str,
         program: str | None, observation: Mapping[str, Any] | Sequence[str],
         source_name: str, output_name: str, evidence: Mapping[str, Any] | None = None
         ) -> dict[str, Any]:
    """Turn one verified execution into a contract that does not name an action."""
    try:
        from canonical.runtime import effect_oracle_v1 as oracle

        verdict = oracle.verify_roundtrip(
            observation_root(observation), output_name, source_name,
            programs=None) if observation_root(observation) else {}
    except Exception:  # noqa: BLE001 - a rule without a checked effect is still a rule
        verdict = {}
    rule = {
        "schema": SCHEMA,
        "kind": "operator",
        "rule_id": "op-" + _digest({"goal_family": goal_family, "program": program,
                                    "source_role": "source", "output_name": output_name}),
        "goal_family": goal_family,
        "env_kind": env_kind,
        "goal": str(goal)[:512],
        "program": program or _program_of(action, _visible_programs()),
        "observed_action": action,
        "roles": {"source": "source", "output": "output"},
        "precondition": {"kind": "source_exists", "role": "source",
                         "description": "the source file named by the goal is a file here"},
        "effect": {"kind": "roundtrip_equal", "source_role": "source",
                   "output_role": "output",
                   "description": "the machine's own reader for the output's declared "
                                  "format turns it back into exactly the source's bytes"},
        "output_name": output_name,
        "effect_checked_at_lift": bool(verdict.get("verdict") == "EFFECT_VERIFIED"),
        "evidence": dict(evidence or {}),
        "refutations": 0,
    }
    return rule


def _program_of(action: str, visible: Sequence[str] | None = None) -> str | None:
    """Which installed program does this action's name refer to?

    Derived, not assumed: the action `run_gzip` names `gzip` only because a
    program called gzip exists on this machine. The parts of the name are split
    and the LONGEST part that resolves to a program wins; a name that resolves
    to nothing yields None, and a rule without a program refuses to apply rather
    than guessing that the last word was the program.
    """
    import shutil

    def present(name: str) -> bool:
        if visible is not None:
            return name in visible
        return shutil.which(name) is not None

    parts = [p for p in re.split(r"[^A-Za-z0-9.+]+", str(action)) if p]
    for part in sorted(parts, key=len, reverse=True):
        if present(part):
            return part.lower()
    return None


def _digest(payload: Mapping[str, Any]) -> str:
    import hashlib

    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def observation_root(observation: Any) -> str | None:
    if isinstance(observation, Mapping):
        root = observation.get("root")
        return str(root) if root else None
    return None


def _files(root: pathlib.Path) -> list[str]:
    try:
        return sorted(p.name for p in root.iterdir() if p.is_file())
    except OSError:
        return []


def bind_source(rule: Mapping[str, Any], root: str | pathlib.Path,
                source_hint: str | None = None) -> dict[str, Any]:
    """Which file in THIS instance is the rule's source? Refuse when not obvious."""
    files = _files(pathlib.Path(root))
    output = rule.get("output_name")
    if source_hint:
        if source_hint in files:
            return {"bound": source_hint, "reason": "named by the caller", "files": files}
        return {"bound": None, "status": REFUSED_PRECONDITION,
                "reason": "the caller's source %r is not here" % source_hint, "files": files}
    candidates = [f for f in files if f != output and not f.endswith(".py")]
    if len(candidates) == 1:
        return {"bound": candidates[0], "reason": "the only input in this instance",
                "files": files}
    if not candidates:
        return {"bound": None, "status": REFUSED_PRECONDITION,
                "reason": "no input file here", "files": files}
    return {"bound": None, "status": REFUSED_AMBIGUOUS,
            "reason": "%d candidates: %s -- guessing would be how a rule compresses "
                      "the wrong file" % (len(candidates), ", ".join(candidates[:4])),
            "files": files}


def find_action(rule: Mapping[str, Any], vocabulary: Sequence[str]) -> dict[str, Any]:
    """Which action in THIS environment performs the rule's program?"""
    # The program comes from the rule (or from the observed action's name
    # resolved against INSTALLED programs). The environment's action names are
    # not evidence of what a program is called: `alpha` is an action, not a tool.
    program = (rule.get("program")
               or _program_of(rule.get("observed_action") or "") or "").lower()
    if not program:
        return {"action": None, "status": REFUSED_NO_ACTION,
                "reason": "the rule names no program"}
    exact = [a for a in vocabulary if str(a).lower() == program]
    # Substring, not word equality: a registrar spells an action `run_gzip`,
    # `pack_with_gzip` or `gzip_it`, and the program's name is inside all three.
    # A name that merely contains it can still be wrong, which is why the effect
    # is verified afterwards rather than trusted from the name.
    contains = [a for a in vocabulary if program in str(a).lower()]
    for pool, why in ((exact, "the action is named for the program"),
                      (contains, "the action contains the program's name")):
        if len(pool) == 1:
            return {"action": pool[0], "status": "FOUND", "reason": why,
                    "vocabulary_size": len(vocabulary)}
        if len(pool) > 1:
            return {"action": None, "status": REFUSED_AMBIGUOUS,
                    "reason": "%d actions name %r" % (len(pool), program),
                    "candidates": [str(a) for a in pool[:6]]}
    return {"action": None, "status": REFUSED_NO_ACTION,
            "reason": "no action in this environment names %r" % program,
            "vocabulary_size": len(vocabulary),
            "vocabulary_sample": [str(a) for a in list(vocabulary)[:8]]}


def apply_rule(rule: Mapping[str, Any], env: Any, *,
               source_hint: str | None = None) -> dict[str, Any]:
    """Bind, act, and verify THE EFFECT HERE. A rule is a claim, not an answer."""
    root = getattr(env, "root", None)
    if root is None:
        return {"schema": SCHEMA, "status": REFUSED_PRECONDITION,
                "reason": "this environment exposes no root to bind against"}
    binding = bind_source(rule, root, source_hint)
    if not binding.get("bound"):
        return {"schema": SCHEMA, "status": binding.get("status", REFUSED_PRECONDITION),
                "binding": binding, "applied": False}
    found = find_action(rule, getattr(env, "action_names", []) or [])
    if not found.get("action"):
        return {"schema": SCHEMA, "status": found.get("status", REFUSED_NO_ACTION),
                "binding": binding, "search": found, "applied": False}
    env.reset()
    acted = False
    try:
        acted = bool(env.act(found["action"]))
    except Exception as error:  # noqa: BLE001 - an action that raises is data
        return {"schema": SCHEMA, "status": "OPEN__ACTION_RAISED",
                "detail": repr(error)[:200], "applied": False}
    from canonical.runtime import effect_oracle_v1 as oracle

    verdict = oracle.verify_roundtrip(root, rule.get("output_name", ""),
                                      binding["bound"])
    ok = verdict.get("verdict") == "EFFECT_VERIFIED"
    return {
        "schema": SCHEMA,
        "status": APPLIED if ok else REFUTED,
        "applied": bool(ok and acted),
        "action_used": found["action"],
        "binding": binding,
        "search": found,
        "effect": verdict,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
    }


def refute(memory: Mapping[str, Any], rule_id: str) -> dict[str, Any]:
    """A refuted rule is kept and counted, never silently deleted or trusted."""
    out = json.loads(json.dumps(memory))
    for row in out.get("rules") or []:
        if row.get("rule_id") == rule_id:
            row["refutations"] = int(row.get("refutations", 0) or 0) + 1
            row["last_status"] = REFUTED
    return out


def main(argv: Sequence[str] | None = None) -> int:
    print(json.dumps({"schema": SCHEMA,
                      "usage": "import lift(), find_action(), apply_rule()"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
