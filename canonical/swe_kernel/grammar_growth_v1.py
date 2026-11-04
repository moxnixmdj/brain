"""A grammar that grows: unexplained edits accumulate into evidence for a missing shape.

THE FALSIFIER THIS ANSWERS
--------------------------
Pass twenty closed with a prediction against myself: the fitted grammar learns *within* a space I
authored, and nothing in it can invent a shape. The test was to hand it a world needing a shape it does
not contain -- `not (a < b)` -- and see whether it can do anything. It cannot: the proposer returns
nothing, correctly and uselessly.

WHY "INVENT A SHAPE" IS THE WRONG NEXT STEP
-------------------------------------------
The obvious move is to add a wrapper primitive. That is just authoring a fifth shape by hand, one level
up, and it teaches nothing: I would be the one noticing that negation exists. The honest prerequisite is
smaller and testable: **can the creature notice that its space has a hole, and say where the hole is?**

That distinction is the whole content of this module. Inventing a shape with no evidence is guessing.
Noticing a hole is observation, and it is the only thing that could ever justify a shape.

WHAT IS KEPT, AND WHY IT WAS BEING THROWN AWAY
---------------------------------------------
`synthesized_edit_grammar_v1.signature()` returns None for any edit its keys cannot explain, and
`observe()` drops those edits on the floor. That is the *same* mistake the awake loop made with rejected
candidates: a negative result was being discarded because the data structure had no slot for it.

An edit nobody can explain is not noise. It is a precise, machine-checkable claim:

    "these two expressions were observed to be a repair, and none of my 248 keys describes the step"

Six such claims that cluster -- all wrapping a comparison in `not`, always at the outermost node,
always with one operand -- are evidence for exactly one thing, and bad_data for almost everything else.
This module collects them, groups them by the *structural difference* between the two expressions, and
reports a hole only when the group is both large enough and tight enough to name.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not add the shape, and it does not propose a candidate using it. Reporting a hole is not
repairing one. Everything below is measurement; the next step (turning a named hole into a new
primitive that the fitter can then accept or reject) is deliberately still absent, because doing it
before the detection is measured would mean I had authored it.

Authority NONE, spend $0, `truth.achieved` false.
"""

from __future__ import annotations

import ast
import json
import pathlib
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_GRAMMAR_GROWTH_V1"

# How many unexplained edits must agree before a hole is reported, and how much of the group must share
# one structural description. Both are measurement thresholds, not knowledge: they are stated so a
# reader can disagree with them, and they are the only numbers here I chose.
MIN_EVIDENCE = 3
MIN_AGREEMENT = 0.75


def _shape_of(node: ast.AST | None) -> str:
    """A structural label for an expression, ignoring identifiers and literals.

    `not (a < b)` and `not (x > y)` get the same label; `not (a < b)` and `a < b + 1` do not. That is
    what "the same kind of edit" has to mean if a hole is to be named at all.
    """
    if node is None:
        return "none"
    if isinstance(node, ast.Compare):
        # `Compare(Lt)` and `Compare(Gt)` are the SAME kind of edit when both get wrapped in `not`, and
        # keying on the specific operator split one hole into four groups of one -- which is why the
        # first run named nothing. A hole is named by the CHANGE of form, so the form label must
        # abstract away the operator that the change does not touch.
        negated = any(isinstance(o, (ast.NotIn, ast.IsNot)) for o in node.ops)
        return f"Compare(negated={negated})"
    # One rule, applied consistently: a form label names the NODE KIND, never the specific operator,
    # because the operator is usually the thing the edit leaves alone. MEASURED 2026-11-05: keying on the
    # operator split "operator -> call" into Add/Mult/Sub groups of one and named nothing, the second time
    # this exact mistake appeared in this file. The exceptions are structural, not alphabetical:
    # `UnaryOp(Not)` is kept because negation IS the change; `Compare(negated=...)` is kept because
    # in/not-in vs </> is exactly the distinction that separates holes.
    if isinstance(node, ast.BoolOp):
        return "BoolOp"
    if isinstance(node, ast.BinOp):
        return "BinOp"
    if isinstance(node, ast.UnaryOp):
        return f"UnaryOp({type(node.op).__name__})"
    if isinstance(node, ast.Subscript):
        return "Subscript"
    if isinstance(node, ast.Name):
        return "Name"
    if isinstance(node, ast.Constant):
        return f"Const({type(node.value).__name__})"
    if isinstance(node, ast.Call):
        return "Call"
    if isinstance(node, ast.IfExp):
        return "IfExp"
    return type(node).__name__


def _returned(tree: ast.AST) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            return node.value
    return None


def describe_unexplained(before: str, after: str) -> dict[str, Any] | None:
    """Describe the structural step between two expressions, in terms that ignore names and values."""
    try:
        b, a = ast.parse(before), ast.parse(after)
    except SyntaxError:
        return None
    vb, va = _returned(b), _returned(a)
    if vb is None or va is None:
        return None
    # What is the OUTERMOST thing that changed about the root form?
    root_before, root_after = _shape_of(vb), _shape_of(va)
    if root_before == root_after:
        # Same shape -- the difference is inside. Record the operand shapes, which is what an edit that
        # swaps or shifts a component would look like.
        return {
            "root_before": root_before,
            "root_after": root_after,
            "inner_before": [_shape_of(n) for n in ast.walk(vb) if n is not vb][:6],
            "inner_after": [_shape_of(n) for n in ast.walk(va) if n is not va][:6],
            "wrapped": False,
            "key": f"{root_before}->inner",
        }
    # A different root shape: name it by (before, after). `Compare(..) -> UnaryOp(Not)` is the label a
    # human would call "negation", but the creature never needs that word -- it needs the pair.
    return {
        "root_before": root_before,
        "root_after": root_after,
        "wrapped": True,
        "key": f"{root_before}->{root_after}",
    }


class GrammarGrowth:
    """Accumulates the edits the grammar cannot explain, and names a hole when they agree."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        # key -> {"count": n, "examples": [[before, after], ...], "roots": [.., ..]}
        self.gaps: dict[str, dict[str, Any]] = {}
        self.load()

    # -- persistence ---------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "gaps": self.gaps}

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d.get("schema") == SCHEMA and isinstance(d.get("gaps"), dict):
                self.gaps = d["gaps"]
        except (ValueError, OSError, TypeError):
            return

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return

    # -- accumulation --------------------------------------------------------------------------
    def note_unexplained(self, before: str, after: str) -> dict[str, Any] | None:
        """Record an edit no key explains. Called only when `signature()` returned None."""
        desc = describe_unexplained(before, after)
        if desc is None:
            return None
        row = self.gaps.setdefault(desc["key"], {"count": 0, "examples": [], "roots": []})
        row["count"] = int(row.get("count") or 0) + 1
        pair = [before, after]
        if pair not in row["examples"] and len(row["examples"]) < 8:
            row["examples"].append(pair)
        if desc["root_after"] not in row["roots"]:
            row["roots"].append(desc["root_after"])
        self.save()
        return desc

    # -- reporting -----------------------------------------------------------------------------
    def holes(self) -> list[dict[str, Any]]:
        """Unexplained-edit groups that are large and tight enough to name as a missing shape."""
        out: list[dict[str, Any]] = []
        total = sum(int(r.get("count") or 0) for r in self.gaps.values())
        for key, row in self.gaps.items():
            n = int(row.get("count") or 0)
            if n < MIN_EVIDENCE:
                continue
            share = n / max(1, total)
            if share < MIN_AGREEMENT and len(self.gaps) > 1:
                # A hole is only believable if it is not simply "everything is unexplained".
                continue
            out.append({
                "hole": key,
                "evidence": n,
                "share": round(share, 3),
                "roots_seen": list(row.get("roots") or []),
                "examples": (row.get("examples") or [])[:3],
                "asks_for": self._asks_for(key, row),
            })
        out.sort(key=lambda h: (-h["evidence"], h["hole"]))
        return out

    @staticmethod
    def _asks_for(key: str, row: Mapping[str, Any]) -> str:
        """What the evidence would require the grammar to be able to express, in one sentence.

        This is a DESCRIPTION of the missing step, not a proposal. It is derived from the observation
        pair, and it deliberately does not name Python syntax unless the roots themselves do.
        """
        before, after = key.split("->", 1)
        if after.startswith("UnaryOp"):
            return (f"a way to express `{after}` applied to a `{before}` expression -- "
                    f"the edit is the same outer form every time and only the inner expression varies")
        if after == "inner":
            return (f"a way to change a component INSIDE a `{before}` expression "
                    f"(every example keeps the outer form and differs within it)")
        return (f"a rewrite from `{before}` to `{after}`, which no current key spans")

    def summary(self) -> Mapping[str, Any]:
        hs = self.holes()
        return {
            "schema": SCHEMA,
            "unexplained_groups": len(self.gaps),
            "unexplained_edits": sum(int(r.get("count") or 0) for r in self.gaps.values()),
            "holes": hs,
            "named": [h["hole"] for h in hs],
            "persisted_to": str(self.path) if self.path else None,
        }


_LIVE: GrammarGrowth | None = None


def live_growth(path: str | pathlib.Path | None = None) -> GrammarGrowth:
    global _LIVE
    p = pathlib.Path(path) if path else None
    if _LIVE is None or _LIVE.path != p:
        _LIVE = GrammarGrowth(p)
    return _LIVE
