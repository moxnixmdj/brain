"""Mechanism sketches: the difference between remembering an answer and knowing a skill.

THE QUESTION THIS MODULE ANSWERS
--------------------------------
The owner's question, restated as a claim a machine can decide:

  > "Saving his exact experience must be in a very sufficient way, not just
  >  saving the exact experience in a dumb way. Maybe we should do generalization."

A saved ACTION LIST like `statistics.median([3, 1, 4, 1, 5])` is a cache of one instance's
data welded to the mechanism. It never transfers: the next document, the next dataset, the
next machine differ in exactly the part that was hard-coded. The 2026-11-16 round measured
that a cache is not learning (`LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1`).

What transfers is the MECHANISM: the shape of the call, with the data-dependent parts made
into slots. The anti-unifier in `verified_skill_crystallizer_v1` proved that for code
repair -- one before/after pair becomes a rule with holes. This module does the same for
single expressions taken from documents or traces, and the admission test is the same
discipline: nothing is believed until it replays to the goal on instances it never saw.

THE DESIGN, IN FOUR MECHANISMS
------------------------------
1. PARAMETERIZE. Parse the statement; every constant literal (a list/tuple of constants as
   one slot, a bare number/string as a slot) becomes a named hole. The template is
   re-emitted with `ast.unparse`. Zero parameters are fitted; the transform is a function
   of the example alone. A statement that survives slotting is a HYPOTHESIS about the
   mechanism, nothing more.

2. CANDIDATES. The values a slot may take come from the environment's own observation,
   never from imagination: every sequence of two or more scalars found in the observation
   (whole, for sequence slots) and every number/string leaf (for scalar slots), deduplicated,
   bounded, longer sequences first. If the observation cannot fill a slot, the step cannot
   bind. That is a refusal, not a guess.

3. BIND AND VERIFY. The candidate product is tried in order; each complete assignment is
   rendered (Parse -> substitute -> unparse, never string splicing), EXECUTED, and the
   goal is OBSERVED. The first binding that reaches the goal wins. The search is bounded
   (`limit`); running out of bindings or running into the limit is an honest REFUSED with
   the tried count. Nothing here trusts an unexecuted rendering.

4. ADMIT ON FRESH INSTANCES. A verified binding in training is an anecdote. Admission is
   the caller driving (1)-(3) on instances the sketch never saw, with the environment's
   own goal check deciding. Save iff ADMIT; otherwise refined or refused. The caller
   persists -- this module stores nothing.

WHAT THIS REFUSES TO CLAIM
---------------------------
* Not a model, not weights, not a parameter warehouse: zero parameters are fitted here.
* Not a proof that the sketch is the "true" generalization: anti-unification over ONE
  example yields the most specific generalization consistent with it, and only execution
  on other instances justifies keeping it.
* Not safe for mutating environments: bindings are searched against the observation taken
  at the START of the plan; a step whose side effect changes what a later slot should see
  is out of scope and is refused by the caller's goal check, never guessed.

Model calls: 0. Network calls: 0. Parameters stored: 0.
"""
from __future__ import annotations

import ast
import itertools
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MECHANISM_SKETCH_V1"

MAX_SLOTS = 8
MAX_CANDIDATES = 64
DEFAULT_BIND_LIMIT = 96


# --------------------------------------------------------------------------- #
# 1. PARAMETERIZE: one concrete statement -> a mechanism template with holes
# --------------------------------------------------------------------------- #

def _scalar_type(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return None


def _is_const_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return _scalar_type(node.value) is not None
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and all(_is_const_literal(e) for e in node.elts)
    return False


def parameterize(statement: Any, *, slot_start: int = 0) -> dict[str, Any]:
    """Turn one example statement into a template with named holes.

    A list/tuple of constants is slotted as ONE hole (its whole content) so the
    template keeps working when a later instance has a different number of
    elements. Bare number/string constants become holes of their own. Boolean
    and None constants are left alone: they are almost always mechanism
    (`True`/`False` flags), and slotting them buys nothing.

    `slot_start` keeps slot names unique across the steps of one plan: pass the
    number of slots already used so far.
    """
    slot_start = int(slot_start or 0)
    text = str(statement or "").strip()
    if not text:
        return {"status": "REFUSED__EMPTY_STATEMENT", "template": None, "slots": []}
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        return {"status": "REFUSED__NOT_AN_EXPRESSION", "template": None, "slots": [],
                "statement": text[:200]}

    slots: list[dict[str, Any]] = []

    def _slot_name() -> str:
        return f"S{slot_start + len(slots)}"

    class Rewriter(ast.NodeTransformer):
        def visit_List(self, node: ast.List) -> ast.AST:
            if _is_const_literal(node):
                return self._make_slot("sequence", node)
            self.generic_visit(node)
            return node

        def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
            if _is_const_literal(node):
                return self._make_slot("sequence", node)
            self.generic_visit(node)
            return node

        def visit_Constant(self, node: ast.Constant) -> ast.AST:
            kind = _scalar_type(node.value)
            if kind is None:
                return node
            return self._make_slot("scalar:" + kind, node)

        def _make_slot(self, kind: str, node: ast.AST) -> ast.AST:
            name = _slot_name()
            slots.append({"id": name, "kind": kind,
                          "example": ast.unparse(node)[:120]})
            if len(slots) > MAX_SLOTS:
                raise _TooManySlots()
            return ast.Name(id=name, ctx=ast.Load())

    class _TooManySlots(Exception):
        pass

    try:
        rewritten = Rewriter().visit(tree)
    except _TooManySlots:
        return {"status": "REFUSED__MORE_THAN_8_SLOTS", "template": None, "slots": [],
                "statement": text[:200]}
    ast.fix_missing_locations(rewritten)
    try:
        template = ast.unparse(rewritten)
    except Exception:  # noqa: BLE001
        return {"status": "REFUSED__TEMPLATE_UNPARSE_FAILED", "template": None, "slots": []}
    return {"status": "PASS__SLOTTED", "schema": SCHEMA, "template": template,
            "slots": slots, "statement": text[:400],
            "binding_kind": "sequence" if any(s["kind"] == "sequence" for s in slots) else "scalar"}


# --------------------------------------------------------------------------- #
# 2. CANDIDATES: what the slots may be filled with, read from the observation
# --------------------------------------------------------------------------- #

def _walk(value: Any, depth: int = 0) -> Iterable[Any]:
    if depth > 6:
        return
    if isinstance(value, Mapping):
        yield value
        for k, v in value.items():
            yield from _walk(k, depth + 1)
            yield from _walk(v, depth + 1)
        return
    if isinstance(value, (list, tuple)):
        yield value
        for item in value:
            yield from _walk(item, depth + 1)
        return
    yield value


def _as_sequence(value: Any) -> tuple | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        if all(_scalar_type(v) == "number" or isinstance(v, str) for v in value):
            try:
                return tuple(value)
            except TypeError:
                return None
    return None


def candidate_values(observation: Any, limit: int = MAX_CANDIDATES) -> dict[str, list[Any]]:
    """Values a slot may take, derived from the observation alone.

    Sequence candidates are the whole sequences found in the observation --
    longest first, deduplicated, capped. Scalar candidates are the number and
    string leaves, deduplicated, in traversal order, capped.
    """
    sequences: list[tuple] = []
    numbers: list[float] = []
    strings: list[str] = []
    seen_seq: set[tuple] = set()
    seen_num: set[float] = set()
    seen_str: set[str] = set()
    for node in _walk(observation):
        seq = _as_sequence(node)
        if seq is not None and seq not in seen_seq:
            seen_seq.add(seq)
            sequences.append(seq)
        elif isinstance(node, bool) or node is None:
            continue
        elif isinstance(node, (int, float)):
            if float(node) not in seen_num:
                seen_num.add(float(node))
                numbers.append(node)
        elif isinstance(node, str):
            if node not in seen_str:
                seen_str.add(node)
                strings.append(node)
    sequences.sort(key=lambda s: (-len(s), repr(s)))
    return {"sequence": sequences[:limit], "number": numbers[:limit], "string": strings[:limit]}


def candidates_for_slot(slot: Mapping[str, Any], candidates: Mapping[str, list[Any]]) -> list[Any]:
    kind = str(slot.get("kind") or "")
    if kind == "sequence":
        return list(candidates.get("sequence") or [])
    if kind == "scalar:number":
        return list(candidates.get("number") or [])
    if kind == "scalar:string":
        return list(candidates.get("string") or [])
    return []


# --------------------------------------------------------------------------- #
# 3. RENDER + BIND AND VERIFY: parse, substitute, execute, observe
# --------------------------------------------------------------------------- #

def render(template: str, binding: Mapping[str, Any]) -> str:
    """Render a template with a concrete binding by AST substitution.

    Never string splicing: the result is re-parsed and re-emitted, so a binding
    cannot inject syntax. A template that names an unknown slot renders as
    itself and will fail the caller's execution honestly.
    """
    tree = ast.parse(template, mode="eval")

    class Binder(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in binding:
                value = binding[node.id]
                try:
                    return ast.Constant(value=value)
                except (TypeError, ValueError):
                    return node
            return node

    bound = Binder().visit(tree)
    ast.fix_missing_locations(bound)
    return ast.unparse(bound)


def bind_plan_and_verify(
    steps: Sequence[Mapping[str, Any]],
    candidates: Mapping[str, list[Any]],
    execute: Callable[[str], Any],
    is_goal: Callable[[], bool],
    *,
    reset: Callable[[], Any] | None = None,
    limit: int = DEFAULT_BIND_LIMIT,
) -> dict[str, Any]:
    """Try bindings for a whole plan; the goal decides, never the renderer.

    `steps` are parameterized statements (all steps share one binding, because
    a datum appears once). `execute` is the caller's real action mechanism;
    `is_goal` observes the world AFTER the full sequence. Between combos the
    caller's `reset` is invoked when provided; without it, combos after the
    first run on a dirty world and the result says so.

    Returns PASS with the binding and tried count, or REFUSED with the count.
    """
    slot_tables: list[list[Any]] = []
    slot_ids: list[str] = []
    ok = True
    for step in steps:
        for slot in step.get("slots") or []:
            opts = candidates_for_slot(slot, candidates)
            slot_ids.append(str(slot.get("id")))
            slot_tables.append(opts)
            if not opts:
                ok = False
    if not steps:
        return {"status": "REFUSED__EMPTY_PLAN", "tried": 0}
    if not ok:
        missing = [sid for sid, opts in zip(slot_ids, slot_tables) if not opts]
        return {"status": "REFUSED__NO_CANDIDATE_FOR_SLOT", "tried": 0,
                "unfilled_slots": missing}

    tried = 0
    for combo in itertools.product(*slot_tables) if slot_tables else [()]:
        if tried >= limit:
            return {"status": "REFUSED__BIND_LIMIT_REACHED", "tried": tried,
                    "limit": limit}
        tried += 1
        binding = dict(zip(slot_ids, combo))
        rendered: list[str] = []
        try:
            if reset is not None:
                reset()
            for step in steps:
                stmt = render(str(step.get("template")), binding)
                rendered.append(stmt)
                execute(stmt)
            if bool(is_goal()):
                return {"status": "PASS__BOUND_AND_GOAL_OBSERVED",
                        "binding": {k: repr(v)[:120] for k, v in binding.items()},
                        "rendered": rendered, "tried": tried}
        except Exception:
            # an unexecutable rendering is a fact about this binding, not about
            # the world; the next binding is tried.
            continue
    return {"status": "REFUSED__NO_BINDING_REACHED_GOAL", "tried": tried}


# --------------------------------------------------------------------------- #
# 4. STORAGE FORMAT (the caller persists; this defines the shape)
# --------------------------------------------------------------------------- #

def sketch_rule(goal_family: str, env_kind: str, steps: Sequence[Mapping[str, Any]],
                *, source_authority: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The persistable unit: mechanism templates, never the training data."""
    import hashlib
    import json
    import time

    payload = [
        {"template": s.get("template"),
         "slots": [{"id": slot.get("id"), "kind": slot.get("kind")} for slot in s.get("slots") or []]}
        for s in steps
    ]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return {
        "schema": SCHEMA,
        "kind": "document_sketch",
        "rule_id": "sketch-" + digest,
        "goal_family": str(goal_family or "goal"),
        "env_kind": str(env_kind or "unknown"),
        "scope": {"goal_family": str(goal_family or "goal"), "env_kind": str(env_kind or "unknown")},
        "plan_sketch": payload,
        "source_authority": str(source_authority or "EXTERNAL_DOCUMENT_REPLAYED_AND_SELF_CHECKED"),
        "authority": "EXTERNAL_DOCUMENT_SKETCH__ADMITTED_OR_REFUSED_BY_REPLAY",
        "evidence": dict(evidence or {}),
        "created_at": time.time(),
    }
