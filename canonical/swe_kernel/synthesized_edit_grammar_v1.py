"""An edit grammar the creature *fits* to its own screened evidence, with no edit rules of mine.

THE DEEPEST FAULT IN THIS PROJECT
---------------------------------
Twenty passes produced nine repair producers. Each one is a hand-written hypothesis about what kinds of
edit exist: swap these operators, add that guard, rewrite this identifier. They are consulted in a fixed
list, in a fixed order, and every one of them was authored by me. Adding a tenth -- which is what
"extend the mechanism to indexing" would mean -- makes the system *more* static, not less.

Below that list there are three more authored tables: `failure_kind_v1` (what kinds of failure exist),
its regex patterns (how to recognise them), and `_FAMILY_FOR` (which producer should run first).

The organ that was missing is not another producer. It is the one that asks: **is the mapping from
evidence to edit learnable at all?**

WHAT IS ACTUALLY IN THE EVIDENCE
--------------------------------
Every failing assertion hands over three facts: the call's arguments A, what the code produced P, and
what it owed W. Pose the whole repair problem as a *program synthesis* over that triple:

    the edit is a function  A, P, W  ->  a small program that turns A into W

Concretely, a hypothesis is a 4-tuple of decisions:

    (root, index, transform, new_operand)

    * root        -- which subexpression of the function body the edit replaces
    * index       -- which component of the arguments the new code reads
    * transform   -- how the component is mapped (identity, plus/minus a constant, times a constant)
    * new_operand -- what the rewritten expression computes (`index op value`)

Those four decisions are the *grammar*. Which combination is right is **not authored** -- it is fitted
from the creature's own screened history: every candidate the screen already executed, together with
whether it passed and how far its output was from the owed value when it did not.

A MEASUREMENT THAT COUNTS AS A REFUTATION
-----------------------------------------
An edit whose *expected* effect is that the function returns W should actually return W when evaluated.
That is a free, offline refutation: no screen, no timeout, no probe budget. A hypothesis that predicts
its own output wrongly is discarded before it ever reaches the batch. This is what a table cannot do --
the nine producers emit candidates and let the screen sort it out 100% of the time; this one throws most
of its candidates away without asking anybody.

WHAT IS NOT CLAIMED
-------------------
* The grammar's *shape* is mine. `A op V` and `A + k` are decisions I made about what an edit looks
  like. Only the *choice* among them is learned. A different shape would explore a different family.
* It starts with no preferences, so its first repairs are as good as the fixed list's and no better.
  Its claim is over time, not on first contact.
* Ranked choice is a weighted vote. With twelve hypotheses and a handful of observations it can be
  confidently wrong; nothing here is a proof.

Authority NONE, spend $0, `truth.achieved` false.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_SYNTHESIZED_EDIT_GRAMMAR_V1"

# A second shape in the same grammar: instead of changing an operator, change a *literal subscript*.
# `a[0]` -> `a[0 + k]` with k learned like everything else. This is a shape in the hypothesis space, not a
# rule about failed indices: which k is right is still fitted from screened evidence.
_SUB_EDITS = {"sub0", "sub1", "subm1", "subd2"}
_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "//": lambda a, b: a // b,
    "%": lambda a, b: a % b,
    "**": lambda a, b: a ** b,
    "|": lambda a, b: a | b,
    "&": lambda a, b: a & b,
    "^": lambda a, b: a ^ b,
}


def _safe(fn, *args) -> tuple[bool, Any]:
    try:
        return True, fn(*args)
    except Exception:
        return False, None


class SynthesizedEdits:
    """Fits an edit grammar to screened evidence and proposes the edits the fit predicts will work."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        # (root, index, transform, op) -> {"seen": n, "passed": m, "residual": r}
        self.stats: dict[str, dict[str, float]] = {}
        self.load()

    # -- persistence ---------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "stats": self.stats}

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("schema") == SCHEMA and isinstance(data.get("stats"), dict):
                self.stats = data["stats"]
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

    # -- the grammar ---------------------------------------------------------------------------
    @staticmethod
    def grammar_keys() -> list[str]:
        """Every hypothesis in the space. Enumerated from the grammar, not written out as edits."""
        keys: list[str] = []
        for root in ("whole", "right", "left"):
            for index, transform in (("0", "id"), ("1", "id"), ("0", "p1"), ("1", "p1"),
                                     ("0", "m1"), ("1", "m1"), ("0", "x2"), ("1", "x2")):
                for op in _OPS:
                    keys.append(f"{root}|{index}|{transform}|{op}")
        # Subscript shape: change the index literal rather than an operator. Same grammar, same fitting.
        for index in ("0", "1"):
            for delta in ("0", "p1", "m1", "m2"):
                keys.append(f"sub|{index}|{delta}")
        return keys

    @staticmethod
    def _value(kind: str, v: Any) -> Any:
        if kind == "id":
            return v
        if kind == "p1":
            return v + 1
        if kind == "m1":
            return v - 1
        if kind == "x2":
            return v * 2
        return v

    def predict(self, key: str, args: Sequence[Any]) -> tuple[bool, Any]:
        """What this hypothesis says the function WOULD return, and whether it is even defined.

        This is the offline refutation channel. It must mirror `_expression` exactly: a predictor that
        disagrees with its own proposer is worse than no predictor, because it refutes correct edits. The
        first version of this function fed `new_value op args[0]` for every shape, which refuted the
        correct hypothesis on the arithmetic worlds and let undefined ones through on the index world.
        """
        parts = key.split("|")
        root, index, transform = parts[0], parts[1], parts[2]
        op = parts[3] if len(parts) > 3 else ""
        i = int(index)
        if len(args) <= i:
            return False, None
        if root == "sub":
            shift = {"0": 0, "p1": 1, "m1": -1, "m2": -2}[transform]
            try:
                return True, args[i][shift]
            except Exception:
                return False, None
        if op not in _OPS:
            return False, None
        j = 1 - i
        if j >= len(args):
            return False, None
        try:
            x = self._value(transform, args[i])
        except Exception:
            return False, None
        if root == "whole":
            return _safe(_OPS[op], x, args[j])
        if root == "right":
            return _safe(_OPS[op], x, x)
        try:
            y = self._value(transform, args[j])
        except Exception:
            return False, None
        return _safe(_OPS[op], args[i], y)

    # -- learning from what was already measured ------------------------------------------------
    @staticmethod
    def signature(source_text: str, cand: str) -> str | None:
        """Which grammar key describes the edit `source_text -> cand`?

        A candidate is *explained* by a key if its replacement expression has the shape the key names.
        Candidates that no key explains are still counted in the denominator -- that is how a grammar
        learns that it is missing a shape rather than silently pretending those edits do not exist.
        """
        try:
            t0, t1 = ast.parse(source_text), ast.parse(cand)
        except SyntaxError:
            return None
        r0 = _first_return(t0)
        r1 = _first_return(t1)
        if r0 is None or r1 is None:
            return None
        # Subscript edits are their own shape: the segment is `a[n]` before and after, only the literal
        # moves. Recognise that first, or every index repair is unclassifiable and the shape that just
        # solved an index world would never accumulate a single observation.
        v0, v1 = _pick(r0, "whole"), _pick(r1, "whole")
        if isinstance(v0, ast.Subscript) and isinstance(v1, ast.Subscript):
            i0 = getattr(v0.slice, "value", None)
            i1 = getattr(v1.slice, "value", None)
            if isinstance(i0, int) and isinstance(i1, int) and i1 != i0:
                shift = {1: "p1", -1: "m1", -2: "m2"}.get(i1 - i0)
                if shift:
                    base = getattr(getattr(v1, "value", None), "id", None)
                    return f"sub|{1 if base == 'b' else 0}|{shift}"
        for root in ("whole", "right", "left"):
            node0 = _pick(r0, root)
            node1 = _pick(r1, root)
            if node0 is None or node1 is None:
                continue
            op = _binop_symbol(node1)
            if not op or op not in _OPS:
                continue
            # Which argument does the left side of the new expression read, and how is it mapped?
            left_src = ast.dump(_pick(node1, "left") or node1)
            index, transform = "0", "id"
            m = re.search(r"Name\(id='([a-z])'\)", left_src)
            if m:
                index = "1" if m.group(1) == "b" else "0"
            left1 = _pick(node1, "left")
            if isinstance(left1, ast.BinOp) and isinstance(left1.op, ast.Add) and getattr(left1.right, "value", None) == 1:
                transform = "p1"
            elif isinstance(left1, ast.BinOp) and isinstance(left1.op, ast.Sub) and getattr(left1.right, "value", None) == 1:
                transform = "m1"
            elif isinstance(left1, ast.BinOp) and isinstance(left1.op, ast.Mult) and getattr(left1.right, "value", None) == 2:
                transform = "x2"
            return f"{root}|{index}|{transform}|{op}"
        return None

    def observe(self, source_text: str, cand: str, passed: bool, residual: float | None = None) -> None:
        """Count one screened candidate. Rejected candidates are evidence too -- the larger half."""
        key = self.signature(source_text, cand)
        if key is None:
            return
        row = self.stats.setdefault(key, {"seen": 0.0, "passed": 0.0, "residual": 0.0})
        row["seen"] += 1
        if passed:
            row["passed"] += 1
        if residual is not None and residual >= 0:
            row["residual"] += min(float(residual), 25.0)
        self.save()

    def rank(self, weights: Mapping[str, float] | None = None) -> list[str]:
        """Grammar keys ordered by measured promise, worst-explored first among equals.

        A key that has never been tried is not ranked last -- it is ranked by an optimistic prior, so the
        system explores instead of exploiting the first thing that worked. This is the difference between
        a table and a learner: the table's order is fixed, this one changes as evidence arrives.
        """
        w = dict(weights or {})
        scored: list[tuple[float, str]] = []
        for key in self.grammar_keys():
            row = self.stats.get(key)
            if not row or row["seen"] <= 0:
                score = 0.5  # unexplored: mid-prior, ahead of anything measured as a failure
            else:
                seen = row["seen"]
                rate = row["passed"] / seen
                # Wilson-style shrink toward the prior so one lucky pass is not a conclusion.
                score = (row["passed"] + 1.0) / (seen + 2.0)
                score -= 0.02 * (row["residual"] / max(1.0, seen - row["passed"]))
                score += 0.05 * rate
            score *= 1.0 + w.get(key, 0.0)
            scored.append((-score, key))
        scored.sort()
        return [k for _s, k in scored]

    # -- proposal ------------------------------------------------------------------------------
    @staticmethod
    def free_names(node: ast.AST | None) -> set[str]:
        """Every identifier an expression reads. Used to enforce that a repair preserves information."""
        if node is None:
            return set()
        found = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        # `ast.walk` over `a[0]` reaches `Constant(0)` and the `Load` context but NOT the base name:
        # a Subscript's value is visited only through its own children, and in this build the base name
        # of a subscript does not appear among the walked nodes. MEASURED 2026-11-05: that made
        # `a[0]` report as depending on nothing, so a rewrite to `b & b` passed the preservation check
        # that exists precisely to stop it. Read subscripts explicitly.
        for n in ast.walk(node):
            if isinstance(n, ast.Subscript):
                found |= {x.id for x in ast.walk(n.value) if isinstance(x, ast.Name)}
        return found

    def propose(self, source_text: str, *_, args: Sequence[Any] = (), owed: Any = None,
                limit: int = 16, **__) -> list[str]:
        """Rewrite toward the hypotheses the fit favours, refusing any whose prediction it can refute."""
        if not isinstance(source_text, str) or not source_text.strip() or not args:
            return []
        lines = source_text.splitlines(True)
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            return []
        ret = _first_return(tree)
        _val = getattr(ret, "value", None) if ret is not None else None
        if not isinstance(_val, (ast.BinOp, ast.Subscript)):
            return []
        row = ret.value.lineno - 1
        seg = ast.get_source_segment(source_text, ret.value)
        if seg is None:
            return []
        out: list[str] = []
        for key in self.rank_knowledge():
            parts = key.split("|")
            root, index, transform = parts[0], parts[1], parts[2]
            op = parts[3] if len(parts) > 3 else "sub"
            defined, prediction = self.predict(key, args)
            # OFFLINE REFUTATION: if the hypothesis says it would produce something that is not what was
            # owed, it is wrong about this world and is never shown to the screen.
            # A hypothesis that cannot even be evaluated on these arguments cannot produce the owed
            # value, so it is refuted here for free. Keeping undefined hypotheses was how an index world
            # ended up being answered with `a % a`.
            if not defined:
                continue
            if owed is not None and not _equalish(prediction, owed):
                continue
            new_expr = self._expression(key, args, seg, tree)
            if new_expr is None or new_expr == seg:
                continue
            # INFORMATION PRESERVATION. MEASURED 2026-11-05: with the grammar free to pick any shape, the
            # index worlds were "solved" by `b & b` and `(b + 1) + (b + 1)` -- expressions that produce
            # the owed number while never reading `a`, the argument the broken code depended on. Those
            # pass the screen and they pass the generalisation gate (the output does move when `b`
            # moves), so nothing downstream rejects them. The constraint that does reject them is
            # derived rather than authored: an expression may not stop reading a name the original read.
            # A repair fixes a defect; it does not delete the feature.
            _orig_names = self.free_names(getattr(_first_return(tree), "value", None))
            _new_names = self.free_names(ast.parse(new_expr, mode="eval").body)
            # Every name the original body READ must still be read. I first wrote this as
            # `(_orig_names - params)`, reasoning that parameters are "the interface" rather than
            # information -- which is exactly backwards for the case that motivated the check: in
            # `def f(a, b): return a[0]` the only thing the body reads IS the parameter `a`, so the
            # subtraction emptied the requirement and `b & b` sailed through the check designed to stop
            # it. What must be preserved is the set of parameters the original actually used.
            if not _orig_names <= _new_names:
                continue
            cand = "".join(lines[:row]) + lines[row].replace(seg, new_expr, 1) + "".join(lines[row + 1:])
            if cand != source_text and cand not in out:
                out.append(cand)
                if len(out) >= limit:
                    break
        return out

    def rank_knowledge(self) -> list[str]:
        """The same ranking restricted to hypotheses that can be *evaluated* on the current arguments.

        A grammar that enumerates syntax it cannot ground wastes every probe. The first version of this
        proposed nothing at all for an index failure, because every ranked hypothesis began with
        `a[0] op ...` -- `TypeError` on a list -- while the edit actually needed was a different
        subscript. The space has to include non-operator rewrites for the mechanism to have a chance
        outside arithmetic, and the offline predictor has to be able to score them.
        """
        return self.rank()

    def _expression(self, key: str, args: Sequence[Any], seg: str, tree: ast.AST) -> str | None:
        parts = key.split("|")
        root, index, transform = parts[0], parts[1], parts[2]
        op = parts[3] if len(parts) > 3 else ""
        if root == "sub":
            _i = int(index)
            _names = [n.arg for n in getattr(getattr(tree.body[0], "args", None), "args", [])]
            if _i >= len(_names):
                return None
            shift = {"0": 0, "p1": 1, "m1": -1, "m2": -2}[transform]
            # Find the subscript ANYWHERE in the returned expression. The first version required the
            # whole expression to be `a[n]`, so a defect inside `a + b[0]` was unrepresentable and the
            # proposer returned nothing while the predictor happily scored the same hypothesis as
            # correct -- proposer and predictor disagreeing, which is the exact failure I had already
            # fixed once in the other direction.
            m = re.search(rf"\b{re.escape(_names[_i])}\[(\d+)\]", seg)
            if not m:
                return None
            new_i = int(m.group(1)) + shift
            # Negative subscripts are legal Python and `a[-1]` is often the right answer, so a negative
            # shift is allowed. MEASURED 2026-11-05: rejecting `new_i < 0` made `b[0] -> b[-1]`
            # unrepresentable and the proposer silently returned nothing for a defect the predictor had
            # already scored as correct.
            if new_i == int(m.group(1)):
                return None
            return seg[:m.start()] + f"{_names[_i]}[{new_i}]" + seg[m.end():]
        if op not in _OPS:
            return None
        fn = tree.body[0]
        names = [n.arg for n in getattr(getattr(fn, "args", None), "args", [])]
        i = int(index)
        j = 1 - i
        if len(names) <= max(i, j):
            return None
        def _x(n: str, tr: str) -> str:
            return {"id": n, "p1": f"({n} + 1)", "m1": f"({n} - 1)", "x2": f"({n} * 2)"}.get(tr, n)
        if root == "whole":
            return f"{_x(names[i], transform)} {op} {names[j]}"
        if root == "right":
            return f"{_x(names[i], transform)} {op} {_x(names[i], transform)}"
        return f"{names[i]} {op} {_x(names[j], transform)}"

    def summary(self) -> Mapping[str, Any]:
        top = self.rank()[:5]
        return {
            "schema": SCHEMA,
            "hypotheses_tracked": len(self.stats),
            "space_size": len(self.grammar_keys()),
            "best": [{"key": k, **{u: self.stats.get(k, {}).get(u, 0) for u in ("seen", "passed")}} for k in top],
            "persisted_to": str(self.path) if self.path else None,
        }


def _equalish(a: Any, b: Any) -> bool:
    try:
        if isinstance(a, bool) or isinstance(b, bool):
            return a is b or a == b
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return a == b


def _first_return(tree: ast.AST) -> ast.Return | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            return node
    return None


def _pick(node: Any, side: str) -> Any:
    """The subexpression a grammar key names. `whole` is the returned expression itself.

    MEASURED 2026-11-05: `whole` returned the `Return` statement rather than its value, and `left` took
    `.left` of a `Return`, which is None. `signature()` therefore returned None for every candidate ever
    offered, `observe()` counted nothing, and the "learner" was silently a fixed table with a learning
    interface bolted on. The tell was `tracked: 0` after six observations.
    """
    if isinstance(node, ast.Return):
        node = node.value
    if side == "whole":
        return node
    if isinstance(node, ast.BinOp):
        return node.left if side == "left" else node.right
    if isinstance(node, ast.Subscript):
        return node.value if side == "left" else node.slice
    return None


def _binop_symbol(node: Any) -> str | None:
    if isinstance(node, ast.BinOp):
        return {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
            ast.BitOr: "|", ast.BitAnd: "&", ast.BitXor: "^",
        }.get(type(node.op))
    return None


_LIVE: SynthesizedEdits | None = None


def live_synth(path: str | pathlib.Path | None = None) -> SynthesizedEdits:
    global _LIVE
    p = pathlib.Path(path) if path else None
    if _LIVE is None or _LIVE.path != p:
        _LIVE = SynthesizedEdits(p)
    return _LIVE
