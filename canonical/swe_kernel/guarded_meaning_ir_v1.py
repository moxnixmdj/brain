#!/usr/bin/env python3
"""Guarded Region-SSA Meaning IR + semi-persistent e-graph + delta simulator.

ONE part, not four.  Everything below is expressed in a single canonical term
language so that a Python comprehension, a C ``for`` loop and a JS
``.filter().map()`` chain become *the same term*, and so that the same term can
be (a) proved equal to another by an e-graph, (b) evaluated concretely in
microseconds, and (c) classified for the frame delta it would cause.

Canonical term language (language-neutral; ``#x`` / ``#acc`` are the element /
accumulator placeholders bound by ``map`` / ``filter`` / ``reduce``)::

    Lit(v)                       literal
    Term('var',  (name,))        SSA-ish value reference (free variable)
    Term('const',(v,))           frozen constant
    Term('add'|'sub'|'mul'|'div'|'floordiv'|'mod'|'pow', (a, b))
    Term('neg'|'pos'|'not_'|'invert', (a,))
    Term('and_'|'or_'|'eq'|'ne'|'lt'|'le'|'gt'|'ge'|'in_'|'contains', (a, b))
    Term('select',  (cond, then, else_))   ternary / C ?: / guard merge
    Term('slice',   (xs, lo, hi))          xs[lo:hi] / xs.slice(lo, hi)
    Term('index',   (xs, i))               xs[i] / a[i]
    Term('range',   (lo, hi))              range(lo,hi) / for(i=lo;i<hi;i++)
    Term('len',     (xs,))
    Term('map',     (xs, body))            body binds #x
    Term('filter',  (xs, pred))            pred binds #x
    Term('reduce',  (xs, init, body))      body binds #acc, #x
    Term('guard',   (cond, value))         value exists only under cond
    Term('call',    (fn, *args))
    Term('opaque',  (kind,))               explicitly not understood

The e-graph is an **undo-log** union-find: ``push()`` records one integer and
``pop()`` replays only the writes made since, so a speculative branch costs
O(changes) instead of O(graph).  That is what makes "try 64 candidate patches
in memory, keep the 2 that matter" affordable.

Authority: NONE.  No subprocess, no disk write, no network, no model call.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GUARDED_MEANING_IR_V1"

# --------------------------------------------------------------------------- #
# 0. Terms
# --------------------------------------------------------------------------- #


def _freeze(v: Any) -> Any:
    """Make ``v`` hashable without changing the meaning of scalars."""
    if v is None or isinstance(v, (str, int, float, bool, bytes)):
        return v
    if isinstance(v, (list, tuple)):
        return tuple(_freeze(x) for x in v)
    if isinstance(v, (set, frozenset)):
        return tuple(sorted((_freeze(x) for x in v), key=repr))
    if isinstance(v, dict):
        return tuple(sorted(((str(k), _freeze(x)) for k, x in v.items()), key=lambda kv: kv[0]))
    return repr(v)


@dataclass(frozen=True)
class Lit:
    v: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "v", _freeze(self.v))


@dataclass(frozen=True)
class Term:
    op: str
    args: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(
            a if isinstance(a, (Term, Lit)) else _freeze(a) for a in self.args))

    def __str__(self) -> str:
        if not self.args:
            return self.op
        return f"{self.op}({', '.join(str(a) for a in self.args)})"


#: placeholder names bound by the combinators
ELEM = "#x"
ACC = "#acc"


def var(name: str) -> Term:
    return Term("var", (str(name),))


def const(v: Any) -> Term:
    return Term("const", (Lit(v),))


# --------------------------------------------------------------------------- #
# 1. Semi-persistent e-graph (undo-log union-find + congruence)
# --------------------------------------------------------------------------- #

_SENTINEL = object()


class SemiPersistentEGraph:
    """Union-find e-graph with O(changes) ``push``/``pop`` and congruence.

    ``find`` never mutates, so a version is exactly the union of its recorded
    writes and ``pop()`` restores it byte-for-byte.
    """

    __slots__ = ("parent", "_nodes", "_memo", "_undo", "_marks")

    def __init__(self) -> None:
        self.parent: list[int] = []
        self._nodes: dict[int, list[tuple[str, tuple[int, ...], tuple]]] = {}
        self._memo: dict[tuple, int] = {}
        self._undo: list[tuple] = []
        self._marks: list[int] = []

    # -- versioning ------------------------------------------------------- #
    def push(self) -> int:
        self._marks.append(len(self._undo))
        return len(self._marks)

    def pop(self) -> bool:
        if not self._marks:
            return False
        mark = self._marks.pop()
        undo = self._undo
        while len(undo) > mark:
            rec = undo.pop()
            kind = rec[0]
            if kind == "p":
                self.parent[rec[1]] = rec[2]
            elif kind == "memo":
                if rec[2] is _SENTINEL:
                    self._memo.pop(rec[1], None)
                else:
                    self._memo[rec[1]] = rec[2]
            elif kind == "node":
                self._nodes[rec[1]].pop()
            elif kind == "newnode":
                self._nodes.pop(rec[1], None)
            elif kind == "moved":
                self._nodes[rec[1]] = list(rec[2])
            elif kind == "snapshot":
                self._nodes = {k: list(v) for k, v in rec[1].items()}
                self._memo = dict(rec[2])
            elif kind == "plen":
                del self.parent[rec[1]:]
        return True

    @property
    def depth(self) -> int:
        return len(self._marks)

    # -- union find (non-mutating) ---------------------------------------- #
    def find(self, i: int) -> int:
        p = self.parent
        root = i
        while p[root] != root:
            root = p[root]
        return root

    def _link(self, a: int, b: int) -> int:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        if len(self._nodes.get(ra, ())) < len(self._nodes.get(rb, ())):
            ra, rb = rb, ra
        self._undo.append(("p", rb, self.parent[rb]))
        self.parent[rb] = ra
        moved = self._nodes.pop(rb, ())
        self._undo.append(("moved", rb, tuple(moved)))
        tgt = self._nodes.setdefault(ra, [])
        self._undo.append(("node", ra, len(tgt)))
        tgt.extend(moved)
        return ra

    # -- construction ----------------------------------------------------- #
    def add(self, node: Any) -> int:
        """Add a ``Term`` / ``Lit`` recursively; return its e-class id."""
        if isinstance(node, Lit):
            return self._leaf(("lit", (), (node.v,)))
        if not isinstance(node, Term):
            node = const(node)
        if node.op == "const":
            v = node.args[0]
            v = v.v if isinstance(v, Lit) else v
            return self._leaf(("const", (), (_freeze(v),)))
        if node.op == "var":
            return self._leaf(("var", (), (str(node.args[0]),)))
        kids = tuple(self.add(a) for a in node.args)
        return self.add_canon(node.op, kids)

    def add_canon(self, op: str, child_ids: Sequence[int]) -> int:
        kids = tuple(self.find(c) for c in child_ids)
        return self._leaf((op, kids, ()))

    def _leaf(self, key: tuple) -> int:
        cid = self._memo.get(key)
        if cid is not None:
            return self.find(cid)
        new = len(self.parent)
        self._undo.append(("plen", new, None))
        self.parent.append(new)
        self._undo.append(("newnode", new, None))
        self._nodes[new] = [(key[0], key[1], key[2])]
        self._memo[key] = new
        return new

    def class_of(self, node: Any) -> int:
        return self.find(self.add(node))

    def equal(self, a: Any, b: Any) -> bool:
        return self.class_of(a) == self.class_of(b)

    def members(self, cid: int) -> list[tuple[str, tuple[int, ...], tuple]]:
        return list(self._nodes.get(self.find(cid), ()))

    def size(self) -> int:
        return len({self.find(i) for i in range(len(self.parent))})

    # -- rewriting -------------------------------------------------------- #
    def saturate(self, rules: Iterable[Any] | None = None, *, rounds: int = 6,
                 budget: int = 20000) -> int:
        """Apply rewrite rules to a bounded fixpoint.  Returns unions done."""
        from canonical.swe_kernel.guarded_meaning_ir_v1 import DEFAULT_RULES

        rule_list = list(rules if rules is not None else DEFAULT_RULES)
        unions = 0
        for _ in range(rounds):
            changed = False
            for cid in list(self._nodes.keys()):
                if unions >= budget:
                    return unions
                root = self.find(cid)
                for enode in list(self._nodes.get(root, ())):
                    if unions >= budget:
                        return unions
                    for new in _apply_rules(rule_list, enode, self):
                        other = self.add(new)
                        if self.find(other) != root:
                            self._link(root, other)
                            unions += 1
                            changed = True
                            root = self.find(root)
            if not changed:
                break
        self.rebuild()
        return unions

    def rebuild(self) -> int:
        """Congruence closure: re-canonicalise every enode after unions.

        Without this, ``add`` can mint a *fresh* class for an enode whose
        children were merged, and two equal meanings end up in different
        classes.  ``rebuild`` collapses them; it is called once at the end of
        :meth:`saturate` and records a whole-graph snapshot so ``pop()``
        stays exact.
        """
        self._undo.append(("snapshot", {k: list(v) for k, v in self._nodes.items()},
                           dict(self._memo)))
        merges = 0
        for _ in range(8):
            changed = False
            buckets: dict[tuple, int] = {}
            for cid in list(self._nodes.keys()):
                root = self.find(cid)
                for op, kids, payload in list(self._nodes.get(cid, ())):
                    key = (op, tuple(self.find(k) for k in kids), payload)
                    prev = buckets.get(key)
                    if prev is None:
                        buckets[key] = root
                    elif self.find(prev) != root:
                        self._link(root, prev)
                        merges += 1
                        changed = True
            if not changed:
                break
        new_nodes: dict[int, list[tuple]] = {}
        new_memo: dict[tuple, int] = {}
        for cid in list(self._nodes.keys()):
            root = self.find(cid)
            for op, kids, payload in self._nodes.get(cid, ()):
                key = (op, tuple(self.find(k) for k in kids), payload)
                if key in new_memo:
                    continue
                new_memo[key] = root
                new_nodes.setdefault(root, []).append((op, key[1], payload))
        self._nodes = new_nodes
        self._memo = new_memo
        return merges

    def extract(self, cid: int, *, prefer: Sequence[str] = ()) -> Any:
        return _extract(self, self.find(cid), frozenset(), prefer)


def _extract(g: SemiPersistentEGraph, cid: int, seen: frozenset, prefer: Sequence[str]) -> Any:
    cid = g.find(cid)
    if cid in seen:
        return Term("cycle", (cid,))
    nodes = g.members(cid)
    if not nodes:
        return Term("cycle", (cid,))
    op, kids, payload = min(nodes, key=lambda n: (len(n[1]), n[0] in ("opaque", "cycle"),
                                                  tuple(op_ != x for x in prefer), n[0]))
    if op in ("lit", "const"):
        return Lit(payload[0])
    if op == "var":
        return Term("var", (payload[0],))
    return Term(op, tuple(_extract(g, k, seen | {cid}, prefer) for k in kids))


Rule = Any  # (enode, graph) -> Iterable[Any]  (Term/Lit or (op, child_ids))


def _apply_rules(rules: Sequence[Rule], enode: tuple, g: SemiPersistentEGraph) -> Iterable[Any]:
    for r in rules:
        try:
            yield from r(enode, g)
        except Exception:  # noqa: BLE001 - a broken rule must not break the graph
            continue


# --------------------------------------------------------------------------- #
# 2. Rewrite rules (algebraic + control-flow)
# --------------------------------------------------------------------------- #

_COMMUTATIVE = frozenset({"add", "mul", "and_", "or_", "eq", "ne", "bitor", "bitxor"})
_IDENTITIES = {"add": 0, "mul": 1, "and_": True, "or_": False, "bitor": 0, "bitxor": 0}


def _is_const(g: SemiPersistentEGraph, cid: int, value: Any) -> bool:
    for op, _k, payload in g.members(cid):
        if op in ("const", "lit") and payload and payload[0] == value:
            return True
    return False


def _r_commutative(enode, g):
    op, kids, _ = enode
    if op in _COMMUTATIVE and len(kids) == 2:
        yield (op, (kids[1], kids[0]))


def _r_identity(enode, g):
    op, kids, _ = enode
    if op not in _IDENTITIES or len(kids) != 2:
        return
    ident = _IDENTITIES[op]
    if _is_const(g, kids[0], ident):
        yield (op, (kids[1],)) if False else ("copy", (kids[1],))
    elif _is_const(g, kids[1], ident):
        yield ("copy", (kids[0],))


def _r_double_neg(enode, g):
    op, kids, _ = enode
    if op == "not_" and kids:
        for n_op, n_kids, _p in g.members(kids[0]):
            if n_op == "not_" and n_kids:
                yield ("copy", (n_kids[0],))


def _r_select_same(enode, g):
    op, kids, _ = enode
    if op == "select" and len(kids) == 3 and g.find(kids[1]) == g.find(kids[2]):
        yield ("copy", (kids[1],))


def _r_guard_true(enode, g):
    op, kids, _ = enode
    if op == "guard" and len(kids) == 2 and _is_const(g, kids[0], True):
        yield ("copy", (kids[1],))


def _r_map_identity(enode, g):
    op, kids, _ = enode
    if op == "map" and len(kids) == 2:
        for n_op, _k, payload in g.members(kids[1]):
            if n_op == "var" and payload and payload[0] == ELEM:
                yield ("copy", (kids[0],))
                return


def _r_filter_true(enode, g):
    op, kids, _ = enode
    if op == "filter" and len(kids) == 2 and _is_const(g, kids[1], True):
        yield ("copy", (kids[0],))


def _r_guard_of_select(enode, g):
    """``guard(c, select(c, a, b))`` == ``guard(c, a)``."""
    op, kids, _ = enode
    if op == "guard" and len(kids) == 2:
        for n_op, n_kids, _p in g.members(kids[1]):
            if (n_op == "select" and len(n_kids) == 3
                    and g.find(n_kids[0]) == g.find(kids[0])):
                yield ("guard", (kids[0], n_kids[1]))
                return


DEFAULT_RULES: tuple[Rule, ...] = (
    _r_commutative, _r_identity, _r_double_neg, _r_select_same,
    _r_guard_true, _r_map_identity, _r_filter_true, _r_guard_of_select,
)


# ``copy`` / ``canon`` are pseudo-ops resolved by ``add`` below.
_ORIGINAL_ADD = SemiPersistentEGraph.add


def _add_with_pseudo(self: SemiPersistentEGraph, node: Any) -> int:
    if isinstance(node, tuple) and len(node) == 2 and isinstance(node[0], str) and node[0] == "copy":
        return self.find(node[1][0])
    if isinstance(node, tuple) and len(node) == 2 and isinstance(node[0], str) \
            and isinstance(node[1], tuple):
        return self.add_canon(node[0], node[1])
    return _ORIGINAL_ADD(self, node)


SemiPersistentEGraph.add = _add_with_pseudo  # type: ignore[method-assign]


# --------------------------------------------------------------------------- #
# 3. Anti-unification modulo the e-graph
# --------------------------------------------------------------------------- #

def anti_unify(a: Any, b: Any, g: SemiPersistentEGraph) -> dict[str, Any]:
    """Least general generalisation of two terms, modulo e-graph rewrites.

    Two subterms are *identical* when their e-classes are equal after
    saturation, so ``a + 0`` and ``0 + a`` anti-unify to ``a`` with zero holes
    rather than to a fresh variable.
    """
    ca, cb = g.class_of(a), g.class_of(b)
    if ca == cb:
        return {"schema": g.extract(ca), "holes": [], "equal": True}
    if (isinstance(a, Term) and isinstance(b, Term) and a.op == b.op
            and len(a.args) == len(b.args)):
        parts: list[Any] = []
        holes: list[dict[str, Any]] = []
        for x, y in zip(a.args, b.args):
            sub = anti_unify(x, y, g)
            if sub["equal"]:
                parts.append(sub["schema"])
            else:
                idx = len(holes)
                holes.extend(sub["holes"])
                holes.append({"i": idx, "a": _plain(x), "b": _plain(y)})
                parts.append(Term("hole", (Lit(idx),)))
        if not holes:
            return {"schema": Term(a.op, tuple(parts)), "holes": [], "equal": True}
        return {"schema": Term(a.op, tuple(parts)), "holes": holes, "equal": False}
    return {"schema": Term("hole", (Lit(0),)),
            "holes": [{"i": 0, "a": _plain(a), "b": _plain(b)}], "equal": False}


def _plain(x: Any) -> Any:
    if isinstance(x, Lit):
        return {"lit": x.v}
    if isinstance(x, Term):
        return {"op": x.op, "args": [_plain(a) for a in x.args]}
    if isinstance(x, (str, int, float, bool)) or x is None:
        return {"lit": x}
    return {"raw": repr(x)}


def terms_equal(a: Any, b: Any, *, rounds: int = 6) -> bool:
    g = SemiPersistentEGraph()
    g.add(a)
    g.add(b)
    g.saturate(rounds=rounds)
    return g.equal(a, b)


# --------------------------------------------------------------------------- #
# 4. Shared module container
# --------------------------------------------------------------------------- #

@dataclass
class Region:
    rid: str
    guards: tuple[str, ...] = ()
    parent: str | None = None
    kind: str = "block"


@dataclass
class Effect:
    kind: str          # read | write | destroy | call | raise | ret | bind
    target: str
    region: str
    detail: str = ""


@dataclass
class DefEvent:
    """An SSA definition: ``function`` binds ``name`` to ``term`` under ``guards``."""

    function: str
    name: str
    term: Term
    region: str
    guards: tuple[str, ...] = ()


@dataclass
class CallEvent:
    """A call site: ``function`` calls ``callee`` at ``region``."""

    function: str
    callee: str
    region: str
    args: tuple[Term, ...] = ()
    guards: tuple[str, ...] = ()


@dataclass
class MirModule:
    """A lowered unit: term table, regions, effects, function metadata."""

    lang: str
    file: str
    #: every lowered term, in discovery order (the e-graph's input)
    terms: list[Term] = field(default_factory=list)
    regions: dict[str, Region] = field(default_factory=dict)
    effects: list[Effect] = field(default_factory=list)
    functions: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: SSA definitions and call sites -- the input to the producer-lineage graph
    defs: list[DefEvent] = field(default_factory=list)
    calls: list[CallEvent] = field(default_factory=list)
    _rid: int = 0

    def put(self, t: Term) -> Term:
        """Record ``t`` in discovery order and return it (so it composes)."""
        self.terms.append(t)
        return t

    def new_region(self, kind: str, guards: Sequence[str] = (), parent: str | None = None) -> str:
        self._rid += 1
        rid = f"r{self._rid}"
        self.regions[rid] = Region(rid, tuple(guards), parent, kind)
        return rid

    def effect(self, kind: str, target: str, region: str, detail: str = "") -> None:
        self.effects.append(Effect(kind, target, region, detail))

    def def_event(self, function: str, name: str, term: Term, region: str,
                  guards: Sequence[str] = ()) -> None:
        self.defs.append(DefEvent(function, name, term, region, tuple(guards)))

    def call_event(self, function: str, callee: str, region: str,
                   args: Sequence[Term] = (), guards: Sequence[str] = ()) -> None:
        self.calls.append(CallEvent(function, callee, region, tuple(args), tuple(guards)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "lang": self.lang, "file": self.file,
            "term_count": len(self.terms), "region_count": len(self.regions),
            "effect_count": len(self.effects),
            "functions": {k: {"params": list(v.get("params") or []),
                              "value": str(v.get("value")),
                              "returns": v.get("returns") or []}
                          for k, v in self.functions.items()},
        }


# --------------------------------------------------------------------------- #
# 5. Lowering: Python ``ast``
# --------------------------------------------------------------------------- #

_BINOPS = {
    ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div",
    ast.FloorDiv: "floordiv", ast.Mod: "mod", ast.Pow: "pow",
    ast.LShift: "lshift", ast.RShift: "rshift", ast.BitOr: "bitor",
    ast.BitAnd: "bitand", ast.BitXor: "bitxor", ast.MatMult: "matmul",
}
_CMPOPS = {
    ast.Eq: "eq", ast.NotEq: "ne", ast.Lt: "lt", ast.LtE: "le",
    ast.Gt: "gt", ast.GtE: "ge", ast.Is: "is", ast.IsNot: "is_not",
    ast.In: "in_", ast.NotIn: "not_in",
}
_UNARY = {ast.USub: "neg", ast.UAdd: "pos", ast.Not: "not_", ast.Invert: "invert"}


class _PyLowerer:
    """``ast`` -> Meaning IR.  ``expr`` returns a ``Term`` so terms compose."""

    def __init__(self, mod: MirModule) -> None:
        self.mod = mod
        self.scopes: list[dict[str, Term]] = [{}]
        self.returns: list[tuple[tuple[Term, ...], Term]] = []
        self.guards: list[Term] = []
        self.region_stack: list[str] = []
        self.current_function = "<module>"

    # -- helpers ---------------------------------------------------------- #
    def cur_region(self) -> str:
        return self.region_stack[-1] if self.region_stack else "r0"

    def bind(self, name: str, t: Term, *, effect: bool = True) -> Term:
        self.scopes[-1][name] = t
        if effect:
            self.mod.effect("bind", name, self.cur_region())
            self.mod.def_event(self.current_function, name, t, self.cur_region(),
                               [str(g) for g in self.guards])
        return t

    def lookup(self, name: str) -> Term:
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return self.bind(name, self.mod.put(var(name)), effect=False)

    # -- module ----------------------------------------------------------- #
    def lower(self, tree: ast.AST) -> None:
        self.mod.regions["r0"] = Region("r0", (), None, "module")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.lower_function(node, prefix="")
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.lower_function(sub, prefix=node.name + ".")

    def lower_function(self, node: Any, *, prefix: str) -> Term | None:
        qname = prefix + node.name
        self.scopes.append({})
        saved = (self.returns, self.guards, self.region_stack)
        self.returns, self.guards, self.region_stack = [], [], []
        freg = self.mod.new_region("function")
        self.region_stack = [freg]
        params = [a.arg for a in node.args.args]
        for p in params:
            self.bind(p, self.mod.put(var(p)), effect=False)
        saved_fn = self.current_function
        self.current_function = qname
        for stmt in node.body:
            self.stmt(stmt)
        value = self._merge_returns()
        self.current_function = saved_fn
        self.mod.functions[qname] = {
            "params": params, "value": value, "region": freg,
            "returns": [[[str(g) for g in guards], str(val)] for guards, val in self.returns],
        }
        self.returns, self.guards, self.region_stack = saved
        self.scopes.pop()
        return value

    def _merge_returns(self) -> Term | None:
        """Fold multiple ``return`` sites into one ``select`` chain.

        An early return under guard ``c`` is ``select(c, a, rest)`` -- the
        control-flow guard becomes a value, which is what lets a C ``?:`` and a
        Python ``if/return`` occupy the same e-class.
        """
        if not self.returns:
            return None
        if len(self.returns) == 1:
            return self.returns[0][1]
        out = self.returns[-1][1]
        for guards, val in reversed(self.returns[:-1]):
            if not guards:
                out = val          # an unguarded return dominates the rest
                continue
            out = self.mod.put(Term("select", (self._conj(guards), val, out)))
        return out

    def _conj(self, guards: Sequence[Term]) -> Term:
        if not guards:
            return self.mod.put(const(True))
        tid = guards[0]
        for g in guards[1:]:
            tid = self.mod.put(Term("and_", (tid, g)))
        return tid

    # -- statements ------------------------------------------------------- #
    def stmt(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Return):
            v = self.expr(node.value) if node.value is not None else self.mod.put(const(None))
            self.returns.append((tuple(self.guards), v))
            self.mod.effect("ret", "", self.cur_region())
            return
        if isinstance(node, ast.Assign):
            t = self.expr(node.value)
            for tgt in node.targets:
                self._assign(tgt, t)
            return
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                self._assign(node.target, self.expr(node.value))
            return
        if isinstance(node, ast.AugAssign):
            name = node.target.id if isinstance(node.target, ast.Name) else None
            cur = self.lookup(name) if name else self.expr(node.target)
            rhs = self.expr(node.value)
            op = _BINOPS.get(type(node.op), "add")
            t = self.mod.put(Term(op, (cur, rhs)))
            if name:
                self.bind(name, t)
            return
        if isinstance(node, ast.If):
            self._if(node)
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            self._for(node)
            return
        if isinstance(node, ast.While):
            self._while(node)
            return
        if isinstance(node, ast.Expr):
            t = self.expr(node.value)
            if isinstance(node.value, ast.Call):
                self.mod.effect("call", _call_name(node.value), self.cur_region(), str(t))
            return
        if isinstance(node, ast.Raise):
            if node.exc is not None:
                self.expr(node.exc)
            self.mod.effect("raise", _call_name(node.exc) if node.exc else "", self.cur_region())
            return
        if isinstance(node, ast.Try):
            self._try(node)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.lower_function(node, prefix="")
            return
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.lower_function(sub, prefix=node.name + ".")
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                self.bind(a.asname or a.name,
                          self.mod.put(Term("opaque", ("import:" + a.name,))), effect=False)
            return
        if isinstance(node, ast.With):
            for it in node.items:
                t = self.expr(it.context_expr)
                if it.optional_vars is not None:
                    self._assign(it.optional_vars, t)
            for s in node.body:
                self.stmt(s)
            return
        if isinstance(node, ast.Delete):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.mod.effect("destroy", t.id, self.cur_region())
            return
        if isinstance(node, ast.Assert):
            self.expr(node.test)
            self.mod.effect("call", "assert", self.cur_region())
            return
        if isinstance(node, (ast.Pass, ast.Break, ast.Continue, ast.Global, ast.Nonlocal)):
            return
        self.mod.effect("call", f"opaque:{type(node).__name__}", self.cur_region())

    def _assign(self, tgt: ast.expr, t: Term) -> None:
        if isinstance(tgt, ast.Name):
            self.bind(tgt.id, t)
        elif isinstance(tgt, ast.Tuple):
            for i, el in enumerate(tgt.elts):
                self._assign(el, self.mod.put(Term("index", (t, self.mod.put(const(i))))))
        elif isinstance(tgt, ast.Subscript):
            base = self.expr(tgt.value)
            idx = self.expr(_slice_of(tgt.slice))
            self.mod.effect("write", _call_name(tgt.value), self.cur_region(),
                            f"{base}[{idx}]")
        elif isinstance(tgt, ast.Attribute):
            self.mod.effect("write", _attr_path(tgt), self.cur_region())
        else:
            self.mod.effect("write", type(tgt).__name__, self.cur_region())

    def _if(self, node: ast.If) -> None:
        cond = self.expr(node.test)
        reg_t = self.mod.new_region("then", [str(g) for g in self.guards], self.cur_region())
        reg_e = self.mod.new_region("else", [str(g) for g in self.guards], self.cur_region())
        before = dict(self.scopes[-1])
        self.region_stack.append(reg_t)
        self.guards.append(cond)
        for s in node.body:
            self.stmt(s)
        after_t = dict(self.scopes[-1])
        self.guards.pop()
        self.region_stack.pop()
        self.scopes[-1] = dict(before)
        self.region_stack.append(reg_e)
        self.guards.append(self.mod.put(Term("not_", (cond,))))
        for s in node.orelse:
            self.stmt(s)
        after_e = dict(self.scopes[-1])
        self.guards.pop()
        self.region_stack.pop()
        self.scopes[-1] = dict(before)
        for name in set(after_t) | set(after_e):
            tv, ev = after_t.get(name), after_e.get(name)
            if tv is ev:
                if tv is not None:
                    self.bind(name, tv, effect=False)
            elif ev is None:
                self.bind(name, tv, effect=False)
            elif tv is None:
                self.bind(name, ev, effect=False)
            else:
                self.bind(name, self.mod.put(Term("select", (cond, tv, ev))), effect=False)

    def _while(self, node: ast.While) -> None:
        cond = self.expr(node.test)
        reg = self.mod.new_region("loop", [str(g) for g in self.guards + [cond]], self.cur_region())
        self.region_stack.append(reg)
        self.guards.append(cond)
        for s in node.body:
            self.stmt(s)
        self.guards.pop()
        self.region_stack.pop()
        for s in node.orelse:
            self.stmt(s)

    def _for(self, node: Any) -> None:
        src = self.expr(node.iter)
        src_name = _call_name(node.iter)
        names = _target_names(node.target)

        # ---- 1. accumulation:  acc <op>= expr(x) ----
        acc = self._acc_pattern(node, names)
        if acc is not None:
            op, acc_name, init, value = acc
            t = self.mod.put(Term("reduce", (src, init,
                                             Term(op, (var(ACC), self._elem_body(value, names))))))
            self.bind(acc_name, t)
            self.mod.effect("read", src_name, self.cur_region())
            return

        # ---- 2/3. map / filter / map+filter ----
        #   out = [] ; out.append(f(x))            -> map(xs, f)
        #   out = [] ; if p(x): out.append(x)      -> filter(xs, p)
        #   out = [] ; if p(x): out.append(f(x))   -> map(filter(xs, p), f)
        mf = self._mapfilter_pattern(node, names)
        if mf is not None:
            out_name, pred, body = mf
            inner = src if pred is None else self.mod.put(Term("filter", (src, pred)))
            if (isinstance(body, Term) and body.op == "var" and body.args
                    and body.args[0] == ELEM and pred is not None):
                t = inner                      # append(x) itself: a pure filter
            else:
                t = self.mod.put(Term("map", (inner, body)))
            self.bind(out_name, t)
            self.mod.effect("read", src_name, self.cur_region())
            return

        # ---- 4. generic loop ----
        reg = self.mod.new_region("loop", [str(g) for g in self.guards], self.cur_region())
        self.region_stack.append(reg)
        for n in names:
            self.bind(n, self.mod.put(var(n)), effect=False)
        self.mod.effect("read", src_name, reg)
        for s in node.body:
            self.stmt(s)
        self.region_stack.pop()
        for s in node.orelse:
            self.stmt(s)

    def _elem_body(self, value: ast.expr, names: Sequence[str]) -> Term:
        """Lower ``value`` with the loop variables replaced by ``#x``."""
        t = self.expr(value)
        if not names:
            return t
        return _substitute(t, {n: var(ELEM) for n in names})

    def _acc_pattern(self, node: Any, names: Sequence[str]):
        if len(node.body) != 1:
            return None
        st = node.body[0]
        if not isinstance(st, ast.AugAssign) or not isinstance(st.target, ast.Name):
            return None
        op = _BINOPS.get(type(st.op))
        acc = st.target.id
        if op is None or acc in names:
            return None
        init = self.scopes[-1].get(acc)
        if init is None:
            init = self.mod.put(const(_IDENTITIES.get(op, 0)))
        return op, acc, init, st.value

    def _mapfilter_pattern(self, node: Any, names: Sequence[str]):
        """``out = []`` before the loop, then ``out.append(...)`` in the body.

        Returns ``(out_name, guard_predicate_or_None, appended_expression)``.
        """
        body = list(node.body)
        if len(body) != 1:
            return None
        st = body[0]
        pred = None
        # ``if p(x): out.append(f(x))`` is ONE statement in the AST: the call
        # lives inside the If body, not beside it.
        if isinstance(st, ast.If):
            if len(st.orelse) != 0 or len(st.body) != 1:
                return None
            pred = self._elem_body(st.test, names)
            st = st.body[0]
        if not isinstance(st, ast.Expr) or not isinstance(st.value, ast.Call):
            return None
        call = st.value
        f = call.func
        if not (isinstance(f, ast.Attribute) and f.attr == "append"
                and isinstance(f.value, ast.Name) and call.args):
            return None
        out = f.value.id
        if out in names:
            return None
        return out, pred, self._elem_body(call.args[0], names)

    def _try(self, node: ast.Try) -> None:
        reg = self.mod.new_region("try", [str(g) for g in self.guards], self.cur_region())
        self.region_stack.append(reg)
        for s in node.body:
            self.stmt(s)
        self.region_stack.pop()
        for h in node.handlers:
            hreg = self.mod.new_region("except", [str(g) for g in self.guards], self.cur_region())
            self.region_stack.append(hreg)
            if h.name:
                self.bind(h.name, self.mod.put(Term("opaque", ("exc",))), effect=False)
            self.mod.effect("raise", h.type.id if isinstance(h.type, ast.Name) else "", hreg)
            for s in h.body:
                self.stmt(s)
            self.region_stack.pop()

    # -- expressions ------------------------------------------------------ #
    def expr(self, node: ast.expr) -> Term:
        if node is None:
            return self.mod.put(const(None))
        if isinstance(node, ast.Constant):
            return self.mod.put(const(node.value))
        if isinstance(node, ast.Name):
            return self.lookup(node.id)
        if isinstance(node, ast.BinOp):
            op = _BINOPS.get(type(node.op), "add")
            return self.mod.put(Term(op, (self.expr(node.left), self.expr(node.right))))
        if isinstance(node, ast.Compare):
            out = self.expr(node.left)
            for op, cmp in zip(node.ops, node.comparators):
                out = self.mod.put(Term(_CMPOPS.get(type(op), "eq"), (out, self.expr(cmp))))
            return out
        if isinstance(node, ast.BoolOp):
            op = "and_" if isinstance(node.op, ast.And) else "or_"
            out = self.expr(node.values[0])
            for v in node.values[1:]:
                out = self.mod.put(Term(op, (out, self.expr(v))))
            return out
        if isinstance(node, ast.UnaryOp):
            return self.mod.put(Term(_UNARY.get(type(node.op), "not_"),
                                     (self.expr(node.operand),)))
        if isinstance(node, ast.IfExp):
            return self.mod.put(Term("select", (self.expr(node.test),
                                                self.expr(node.body), self.expr(node.orelse))))
        if isinstance(node, ast.Subscript):
            base = self.expr(node.value)
            sl = _slice_of(node.slice)
            if isinstance(sl, ast.Slice):
                lo = self.expr(sl.lower) if sl.lower else self.mod.put(const(0))
                hi = self.expr(sl.upper) if sl.upper else self.mod.put(const(None))
                return self.mod.put(Term("slice", (base, lo, hi)))
            return self.mod.put(Term("index", (base, self.expr(sl))))
        if isinstance(node, ast.Attribute):
            return self.mod.put(Term("getattr",
                                     (self.expr(node.value), self.mod.put(const(node.attr)))))
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return self._comprehension(node)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return self.mod.put(Term("list", tuple(self.expr(e) for e in node.elts)))
        if isinstance(node, ast.Dict):
            return self.mod.put(Term("list", tuple(self.expr(v) for v in node.values)))
        if isinstance(node, ast.Lambda):
            params = tuple(a.arg for a in node.args.args)
            self.scopes.append({p: self.mod.put(var(p)) for p in params})
            body = self.expr(node.body)
            self.scopes.pop()
            return self.mod.put(Term("lambda", (params, body)))
        if isinstance(node, ast.NamedExpr):
            t = self.expr(node.value)
            if isinstance(node.target, ast.Name):
                self.bind(node.target.id, t)
            return t
        if isinstance(node, (ast.Starred, ast.Await)):
            return self.expr(node.value)
        self.mod.effect("call", f"opaque:{type(node).__name__}", self.cur_region())
        return self.mod.put(Term("opaque", (type(node).__name__,)))

    def _call(self, node: ast.Call) -> Term:
        name = _call_name(node)
        args = tuple(self.expr(a) for a in node.args)
        if name in {"sum", "math.fsum"} and args:
            init = args[1] if len(args) > 1 else self.mod.put(const(0))
            return self.mod.put(Term("reduce", (args[0], init, Term("add", (var(ACC), var(ELEM))))))
        if name == "len" and len(args) == 1:
            return self.mod.put(Term("len", (args[0],)))
        if name == "range" and len(args) in (1, 2, 3):
            # range(n) == range(0, n); a third arg is a step we do not model,
            # so the term stays honest as an opaque call instead of a lie.
            if len(args) == 3:
                return self.mod.put(Term("call", (var("range"),) + args))
            lo = args[0] if len(args) == 2 else self.mod.put(const(0))
            hi = args[1] if len(args) == 2 else args[0]
            return self.mod.put(Term("range", (lo, hi)))
        if name in {"min", "max", "sorted", "reversed", "list", "tuple", "set"} and len(args) == 1:
            return self.mod.put(Term(name, (args[0],)))
        if name in {"all", "any"} and args:
            op = "and_" if name == "all" else "or_"
            return self.mod.put(Term("reduce", (args[0], self.mod.put(const(name == "all")),
                                                Term(op, (var(ACC), var(ELEM))))))
        if name in {"map", "filter"} and len(args) >= 2:
            body = self._lambda_body(args[0])
            if body is not None:
                return self.mod.put(Term(name, (args[1], body)))
        if name in {"functools.reduce", "reduce"} and len(args) >= 2:
            body = self._lambda_body(args[0], acc=True)
            if body is not None:
                init = args[2] if len(args) > 2 else self.mod.put(const(0))
                return self.mod.put(Term("reduce", (args[1], init, body)))
        self.mod.call_event(self.current_function, name, self.cur_region(), args,
                            [str(g) for g in self.guards])
        return self.mod.put(Term("call", (var(name),) + args))

    def _lambda_body(self, t: Term, *, acc: bool = False) -> Term | None:
        if not isinstance(t, Term) or t.op != "lambda" or len(t.args) < 2:
            return None
        params, body = t.args[0], t.args[1]
        if not isinstance(params, tuple) or not isinstance(body, Term):
            return None
        subs: dict[str, Term] = {}
        if acc:
            if params:
                subs[str(params[0])] = var(ACC)
            if len(params) > 1:
                subs[str(params[1])] = var(ELEM)
        elif params:
            subs[str(params[0])] = var(ELEM)
        return _substitute(body, subs)

    def _comprehension(self, node: Any) -> Term:
        gens = node.generators
        if not gens:
            return self.mod.put(Term("list", ()))
        gen = gens[0]
        src = self.expr(gen.iter)
        names = _target_names(gen.target)
        pred = None
        for cond in gen.ifs:
            c = self.expr(cond)
            pred = c if pred is None else self.mod.put(Term("and_", (pred, c)))
        if pred is not None:
            pred_t = _substitute(pred, {n: var(ELEM) for n in names})
            src = self.mod.put(Term("filter", (src, pred_t)))
        if isinstance(node, ast.DictComp):
            return self.mod.put(Term("map", (src, Term("opaque", ("dictcomp",)))))
        body = _substitute(self.expr(node.elt), {n: var(ELEM) for n in names})
        if isinstance(body, Term) and body.op == "var" and body.args and body.args[0] == ELEM:
            if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
                return src
        return self.mod.put(Term("map", (src, body)))


def _slice_of(sl: Any) -> Any:
    return sl.value if sl.__class__.__name__ == "Index" else sl


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _attr_path(node)
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Subscript):
        return _call_name(node.value)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    return type(node).__name__


def _attr_path(node: ast.expr) -> str:
    parts: list[str] = []
    cur: ast.expr | None = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return ".".join(reversed(parts))


def _target_names(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        out: list[str] = []
        for e in node.elts:
            out.extend(_target_names(e))
        return out
    return []


def _substitute(t: Any, subs: Mapping[str, Term]) -> Any:
    if not isinstance(t, Term):
        return t
    if t.op == "var" and t.args and str(t.args[0]) in subs:
        return subs[str(t.args[0])]
    if t.op == "lambda":
        return t
    return Term(t.op, tuple(_substitute(a, subs) for a in t.args))


def lower_python(src: str, *, filename: str = "<string>") -> MirModule:
    mod = MirModule("python", filename)
    _PyLowerer(mod).lower(ast.parse(src, filename=filename))
    return mod


# --------------------------------------------------------------------------- #
# 6. Lowering: tree-sitter (C / C++ / JS / TS / Go / Rust)
# --------------------------------------------------------------------------- #

_TS_OPS = {
    "+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod",
    "==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge",
    "&&": "and_", "||": "or_", "and": "and_", "or": "or_",
    "+=": "add", "-=": "sub", "*=": "mul", "/=": "div", "%=": "mod",
    "**": "pow", "//": "floordiv", "<<": "lshift", ">>": "rshift",
    "|": "bitor", "&": "bitand", "^": "bitxor",
}
_TS_EXT = {
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".go": "go", ".rs": "rust", ".java": "java",
}


class LoweringError(RuntimeError):
    pass


class _TSLowerer:
    """Structural lowering for tree-sitter grammars sharing the C-family shape.

    ``expr`` returns a ``Term`` so the result composes with the Python lowerer's
    output -- which is the whole point: the same algorithm in C, JS/TS and
    Python must land in the same e-class.
    """

    def __init__(self, mod: MirModule, src: bytes) -> None:
        self.mod = mod
        self.src = bytes(src)
        self.scopes: list[dict[str, Term]] = [{}]
        self.returns: list[tuple[tuple[Term, ...], Term]] = []
        self.guards: list[Term] = []
        self.region_stack: list[str] = []
        self.current_function = "<module>"
        self.mod.regions["r0"] = Region("r0", (), None, "module")

    # -- node helpers ----------------------------------------------------- #
    def text(self, node: Any) -> str:
        return self.src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def named(self, node: Any) -> list[Any]:
        return [c for c in node.children if c.is_named]

    def field(self, node: Any, name: str) -> Any:
        try:
            return node.child_by_field_name(name)
        except Exception:  # noqa: BLE001
            return None

    def op_text(self, node: Any, default: str = "") -> str:
        c = self.field(node, "operator")
        if c is not None:
            return self.text(c).strip()
        for ch in node.children:
            if not ch.is_named and ch.type not in ("(", ")", "[", "]", "{", "}", ",", ";", "?", ":"):
                return ch.type.strip()
        return default

    # -- dispatch --------------------------------------------------------- #
    def lower(self, root: Any) -> None:
        for node in self.named(root):
            self.dispatch(node)

    def dispatch(self, node: Any) -> None:
        t = node.type
        if t in ("function_definition", "method_definition", "function_declaration",
                 "generator_function_declaration", "abstract_method_declaration",
                 "function_item", "method_declaration", "constructor_declaration"):
            self.function(node)
        elif t in ("class_declaration", "class_specifier", "struct_specifier", "impl_item",
                   "trait_item", "namespace_definition", "declaration_list", "export_statement"):
            for c in self.named(node):
                self.dispatch(c)
        elif t == "expression_statement":
            self.expr_stmt(node)
        elif t in ("variable_declaration", "lexical_declaration", "const_item", "let_declaration",
                   "var_declaration", "field_declaration", "init_declarator", "var_declarator",
                   "variable_declarator", "local_variable_declaration", "const_declaration"):
            self.decl(node)
        elif t == "if_statement":
            self.if_stmt(node)
        elif t in ("for_statement", "for_range_loop", "for_in_statement", "foreach_statement",
                   "while_statement", "do_statement"):
            self.loop(node)
        elif t == "return_statement":
            self.return_stmt(node)
        elif t in ("comment", "line_comment", "block_comment", "preproc_def", "preproc_include",
                   "preproc_function_def", "preproc_ifdef", "preproc_call", "preproc_if",
                   "preproc_else", "preproc_endif", "preproc_directive", "attribute_item",
                   "attribute", "decorator", "empty_statement", "macro_invocation", ";"):
            return
        else:
            for c in self.named(node):
                self.dispatch(c)

    # -- functions -------------------------------------------------------- #
    def function(self, node: Any) -> None:
        declarator = self.field(node, "declarator")
        name = self._decl_name(declarator) if declarator is not None else None
        if name is None:
            nm = self.field(node, "name")
            name = self.text(nm).strip() if nm is not None else None
        if name is None:
            name = f"anon{len(self.mod.functions)}"
        body = self.field(node, "body")
        if body is None:
            for c in self.named(node):
                if c.type in ("compound_statement", "statement_block", "block"):
                    body = c
                    break
        if body is None:
            return
        self.scopes.append({})
        saved = (self.returns, self.guards, self.region_stack)
        self.returns, self.guards, self.region_stack = [], [], []
        freg = self.mod.new_region("function")
        self.region_stack = [freg]
        params = self.field(node, "parameters") or self.field(node, "parameter_declaration")
        plist: list[str] = []
        if params is not None:
            for p in self.named(params):
                nm2 = self._decl_name(p) or (self.text(p).split(":")[0].strip()
                                             or f"arg{len(plist)}")
                plist.append(nm2)
                self.bind(nm2, self.mod.put(var(nm2)), effect=False)
        saved_fn = self.current_function
        self.current_function = name
        for st in self.named(body):
            self.dispatch(st)
        self.current_function = saved_fn
        self.mod.functions[name] = {
            "params": plist, "value": self._merge_returns(), "region": freg,
            "returns": [[[str(g) for g in guards], str(val)] for guards, val in self.returns],
        }
        self.returns, self.guards, self.region_stack = saved
        self.scopes.pop()

    def _decl_name(self, node: Any) -> str | None:
        if node is None:
            return None
        if node.type in ("identifier", "property_identifier", "field_identifier",
                         "type_identifier", "scoped_identifier", "shorthand_property_identifier"):
            return self.text(node).strip()
        for f in ("declarator", "name", "value", "pattern"):
            c = self.field(node, f)
            if c is not None:
                n = self._decl_name(c)
                if n:
                    return n
        for c in self.named(node):
            if c.type in ("identifier", "property_identifier", "field_identifier",
                          "type_identifier", "scoped_identifier"):
                return self.text(c).strip()
            if c.type in ("function_declarator", "pointer_declarator", "array_declarator",
                          "init_declarator", "parenthesized_declarator", "qualified_identifier",
                          "reference_declarator"):
                n = self._decl_name(c)
                if n:
                    return n
        return None

    def cur_region(self) -> str:
        return self.region_stack[-1] if self.region_stack else "r0"

    def bind(self, name: str, t: Term, *, effect: bool = True) -> Term:
        self.scopes[-1][name] = t
        if effect:
            self.mod.effect("bind", name, self.cur_region())
            self.mod.def_event(self.current_function, name, t, self.cur_region(),
                               [str(g) for g in self.guards])
        return t

    def lookup(self, name: str) -> Term:
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return self.bind(name, self.mod.put(var(name)), effect=False)

    def _merge_returns(self) -> Term | None:
        if not self.returns:
            return None
        out = self.returns[-1][1]
        for guards, val in reversed(self.returns[:-1]):
            if not guards:
                out = val
                continue
            tid = guards[0]
            for g in guards[1:]:
                tid = self.mod.put(Term("and_", (tid, g)))
            out = self.mod.put(Term("select", (tid, val, out)))
        return out

    # -- statements ------------------------------------------------------- #
    def expr_stmt(self, node: Any) -> None:
        kids = self.named(node)
        if kids:
            self.expr(kids[-1])

    def decl(self, node: Any) -> None:
        for d in self.named(node):
            if d.type in ("variable_declarator", "init_declarator", "var_declarator",
                          "const_item", "let_declaration", "field_declaration"):
                nm = self._decl_name(d)
                val = self.field(d, "value") or self.field(d, "init")
                if nm:
                    self.bind(nm, self.expr(val) if val is not None else self.mod.put(var(nm)))
                    return
        nm = self._decl_name(node)
        val = self.field(node, "value") or self.field(node, "init")
        if nm:
            self.bind(nm, self.expr(val) if val is not None else self.mod.put(var(nm)))

    def if_stmt(self, node: Any) -> None:
        cond = self.expr(self.field(node, "condition"))
        cons = self.field(node, "consequence")
        alt = self.field(node, "alternative")
        before = dict(self.scopes[-1])
        reg_t = self.mod.new_region("then", [str(g) for g in self.guards], self.cur_region())
        self.region_stack.append(reg_t)
        self.guards.append(cond)
        if cons is not None:
            self.dispatch(cons)
        after_t = dict(self.scopes[-1])
        self.guards.pop()
        self.region_stack.pop()
        self.scopes[-1] = dict(before)
        after_e: dict[str, Term] = {}
        if alt is not None:
            reg_e = self.mod.new_region("else", [str(g) for g in self.guards], self.cur_region())
            self.region_stack.append(reg_e)
            self.guards.append(self.mod.put(Term("not_", (cond,))))
            self.dispatch(alt)
            self.guards.pop()
            self.region_stack.pop()
            after_e = dict(self.scopes[-1])
        self.scopes[-1] = dict(before)
        for name in set(after_t) | set(after_e):
            tv, ev = after_t.get(name), after_e.get(name)
            if tv is ev:
                if tv is not None:
                    self.bind(name, tv, effect=False)
            elif ev is None:
                self.bind(name, tv, effect=False)
            elif tv is None:
                self.bind(name, ev, effect=False)
            else:
                self.bind(name, self.mod.put(Term("select", (cond, tv, ev))), effect=False)

    def loop(self, node: Any) -> None:
        t = node.type
        body = self.field(node, "body")
        if body is None:
            for c in self.named(node):
                if c.type in ("compound_statement", "statement_block", "block"):
                    body = c
                    break
        if body is None:
            return
        if t == "for_statement":
            init = self.field(node, "initializer")
            cond = self.field(node, "condition")
            loop_var = self._declared_name(init) if init is not None else None
            if init is not None:
                self.dispatch(init)
            hi = self._bound_of(cond) if cond is not None else None
            src = self.mod.put(Term("range", (self.mod.put(const(0)),
                                              hi if hi is not None else self.mod.put(const(0)))))
            self._loop_body(body, src, loop_var)
            return
        it = (self.field(node, "right") or self.field(node, "iterable")
              or self.field(node, "sequence") or self.field(node, "value"))
        if it is not None:
            left = self.field(node, "left")
            loop_var = self.text(left).strip() if (left is not None and left.type == "identifier") else None
            if loop_var:
                self.bind(loop_var, self.mod.put(var(ELEM)), effect=False)
            src = self.expr(it)
        else:
            cond = self.field(node, "condition")
            src = self.mod.put(Term("range", (self.mod.put(const(0)),
                                              self._bound_of(cond) if cond is not None
                                              else self.mod.put(const(0)))))
            loop_var = None
        self._loop_body(body, src, loop_var)

    def _bound_of(self, cond: Any) -> Term | None:
        """Extract ``n`` from ``i < n`` / ``i <= n`` / ``i < xs.length``."""
        if cond is None:
            return None
        if cond.type in ("expression_statement", "parenthesized_expression", "expression"):
            kids = self.named(cond)
            if kids:
                cond = kids[-1]
        txt = self.text(cond).strip().rstrip(";").strip()
        for opn in ("<=", "<", "!=", ">=", ">"):
            if opn not in txt:
                continue
            rhs = txt.split(opn, 1)[1].strip().strip("()").strip()
            if rhs.endswith(".length"):
                base = rhs[: -len(".length")].strip()
                if base and all(ch.isalnum() or ch in "._[]" for ch in base):
                    return self.mod.put(Term("len", (self.mod.put(var(base)),)))
            if rhs and all(ch.isalnum() or ch in "._[]" for ch in rhs):
                return self.mod.put(var(rhs))
        return None

    def _declared_name(self, node: Any) -> str | None:
        """Name introduced by a ``for`` initializer (``let i = 0`` / ``int i=0``)."""
        if node is None:
            return None
        for d in self.named(node):
            if d.type in ("variable_declarator", "init_declarator", "var_declarator",
                          "const_item", "let_declaration"):
                nm = self._decl_name(d)
                if nm:
                    return nm
        nm = self._decl_name(node)
        return nm

    def _loop_body(self, body: Any, src: Term, loop_var: str | None = None) -> None:
        stmts = self.named(body)
        if loop_var:
            # the loop variable *is* the element: this is what makes C's a[i],
            # JS's a[i] and Python's a[i] the same term.
            self.bind(loop_var, self.mod.put(var(ELEM)), effect=False)
        acc = self._acc_pattern(stmts)
        if acc is not None:
            op, init, acc_name, rhs = acc
            self.bind(acc_name, self.mod.put(Term("reduce", (src, init,
                                                              Term(op, (var(ACC), self.expr(rhs)))))))
            self.mod.effect("read", "", self.cur_region())
            return
        reg = self.mod.new_region("loop", [str(g) for g in self.guards], self.cur_region())
        self.region_stack.append(reg)
        for st in stmts:
            self.dispatch(st)
        self.region_stack.pop()

    def _acc_pattern(self, stmts: Sequence[Any]) -> tuple[str, Term, str, Any] | None:
        """``s += expr`` / ``s = s + expr`` -> ``(op, init, acc_name, rhs_node)``."""
        if len(stmts) != 1:
            return None
        st = stmts[0]
        if st.type != "expression_statement":
            return None
        inner = self.named(st)
        if not inner:
            return None
        e = inner[-1]
        if e.type not in ("assignment_expression", "augmented_assignment_expression",
                          "assignment"):
            return None
        op = self.op_text(e, "=")
        left = self.field(e, "left")
        right = self.field(e, "right")
        if left is None or right is None:
            return None
        lname = self.text(left).strip()
        if op == "=":
            if right.type != "binary_expression":
                return None
            bop = self.op_text(right, "+")
            mop = _TS_OPS.get(bop, "add")
            rl = self.field(right, "left")
            if rl is None or self.text(rl).strip() != lname:
                return None
        else:
            mop = _TS_OPS.get(op)
            if mop is None:
                return None
            if self.text(right).strip() == lname:
                return None
        init = self.scopes[-1].get(lname)
        if init is None:
            init = self.mod.put(const(0))
        return mop, init, lname, right

    def return_stmt(self, node: Any) -> None:
        kids = self.named(node)
        t = self.expr(kids[0]) if kids else self.mod.put(const(None))
        self.returns.append((tuple(self.guards), t))
        self.mod.effect("ret", "", self.cur_region())

    # -- expressions ------------------------------------------------------ #
    def expr(self, node: Any) -> Term:
        if node is None:
            return self.mod.put(const(None))
        t = node.type
        if t in ("identifier", "property_identifier", "field_identifier", "scoped_identifier",
                 "type_identifier", "shorthand_property_identifier"):
            return self.lookup(self.text(node).strip())
        if t in ("number_literal", "int_literal", "float_literal", "decimal_integer_literal",
                 "decimal_floating_point_literal", "hex_integer_literal",
                 "octal_integer_literal", "number", "integer", "float"):
            txt = self.text(node).replace("_", "").rstrip("luLU")
            try:
                v: Any = int(txt, 0)
            except ValueError:
                try:
                    v = float(txt)
                except ValueError:
                    v = txt
            return self.mod.put(const(v))
        if t in ("string_literal", "string", "raw_string_literal", "character_literal"):
            return self.mod.put(const(self.text(node).strip("\"'`")))
        if t == "true":
            return self.mod.put(const(True))
        if t == "false":
            return self.mod.put(const(False))
        if t in ("null", "nil", "None", "undefined"):
            return self.mod.put(const(None))
        if t == "binary_expression":
            mop = _TS_OPS.get(self.op_text(node, "+"), "add")
            return self.mod.put(Term(mop, (self.expr(self.field(node, "left")),
                                           self.expr(self.field(node, "right")))))
        if t == "unary_expression":
            op = self.op_text(node, "-")
            mop = "not_" if op in ("!", "not") else "neg"
            return self.mod.put(Term(mop, (self.expr(self.field(node, "argument")),)))
        if t in ("conditional_expression", "ternary_expression"):
            cond = self.field(node, "condition")
            cons = self.field(node, "consequence")
            alt = self.field(node, "alternative")
            if cond is None or cons is None or alt is None:
                kids = [c for c in node.children if c.is_named]
                if len(kids) >= 3:
                    cond, cons, alt = kids[0], kids[1], kids[2]
            return self.mod.put(Term("select", (self.expr(cond), self.expr(cons), self.expr(alt))))
        if t in ("assignment_expression", "augmented_assignment_expression", "assignment"):
            op = self.op_text(node, "=")
            left = self.field(node, "left")
            right = self.field(node, "right")
            rt = self.expr(right)
            if left is not None and left.type in ("identifier", "property_identifier",
                                                  "field_identifier"):
                lname = self.text(left).strip()
                mop = _TS_OPS.get(op)
                if mop and op != "=":
                    rt = self.mod.put(Term(mop, (self.lookup(lname), rt)))
                self.bind(lname, rt)
            elif left is not None:
                self.mod.effect("write", self.text(left).strip(), self.cur_region())
            return rt
        if t in ("call_expression", "call", "macro_invocation", "object_creation_expression"):
            fn = self.field(node, "function")
            args_node = self.field(node, "arguments")
            args = tuple(self.expr(a) for a in (self.named(args_node) if args_node is not None else ()))
            fname = self._call_name(fn)
            if fname in ("sum", "math.sum", "math.fsum") and args:
                return self.mod.put(Term("reduce", (args[0], self.mod.put(const(0)),
                                                    Term("add", (var(ACC), var(ELEM))))))
            if fname in ("len", "strlen", "length", "count") and len(args) == 1:
                return self.mod.put(Term("len", (args[0],)))
            recv = None
            if fn is not None and fn.type in ("member_expression", "field_expression"):
                recv = self.field(fn, "object") or self.field(fn, "argument")
            method = fname.rsplit(".", 1)[-1] if "." in fname else ""
            if method == "reduce" and args:
                src_t = self.expr(recv) if recv is not None else args[0]
                return self.mod.put(Term("reduce", (src_t,
                                                    args[1] if len(args) > 1
                                                    else self.mod.put(const(0)),
                                                    self._arrow_body(node, acc=True)
                                                    or Term("add", (var(ACC), var(ELEM))))))
            if method in ("map", "filter") and args:
                b = self._arrow_body(node)
                if b is not None:
                    src_t = self.expr(recv) if recv is not None else args[0]
                    return self.mod.put(Term(method, (src_t, b)))
            if method == "slice" and recv is not None:
                src_t = self.expr(recv)
                lo = args[0] if len(args) > 0 else self.mod.put(const(0))
                hi = args[1] if len(args) > 1 else self.mod.put(const(None))
                return self.mod.put(Term("slice", (src_t, lo, hi)))
            self.mod.call_event(self.current_function, fname, self.cur_region(), args,
                                [str(g) for g in self.guards])
            return self.mod.put(Term("call", (var(fname),) + args))
        if t in ("subscript_expression", "subscript"):
            base = self.expr(self.field(node, "object") or self.field(node, "argument"))
            idx = self.field(node, "index") or self.field(node, "subscript")
            if idx is None:
                # tree-sitter-cpp gives ``subscript_expression`` only an
                # ``argument`` field; the index is the second named child.
                nk = self.named(node)
                if len(nk) >= 2:
                    idx = nk[1]
            if idx is not None and idx.type in ("slice", "slice_expression", "subscript_pattern"):
                kids = self.named(idx)
                lo = self.expr(kids[0]) if len(kids) > 0 else self.mod.put(const(0))
                hi = self.expr(kids[1]) if len(kids) > 1 else self.mod.put(const(None))
                return self.mod.put(Term("slice", (base, lo, hi)))
            return self.mod.put(Term("index", (base, self.expr(idx))))
        if t in ("member_expression", "field_expression", "attribute"):
            obj = self.expr(self.field(node, "object") or self.field(node, "argument"))
            prop = self.field(node, "property") or self.field(node, "field")
            pname = self.text(prop).strip() if prop is not None else ""
            if pname in ("length", "size", "len"):
                return self.mod.put(Term("len", (obj,)))
            return self.mod.put(Term("getattr", (obj, self.mod.put(const(pname)))))
        if t == "pointer_expression":
            return self.mod.put(Term("index",
                                     (self.expr(self.field(node, "argument")),
                                      self.mod.put(const(0)))))
        if t in ("parenthesized_expression", "expression"):
            kids = self.named(node)
            return self.expr(kids[0]) if kids else self.mod.put(const(None))
        if t in ("arrow_function", "function_expression", "lambda_expression"):
            params = self.field(node, "parameters")
            plist: list[str] = []
            if params is not None:
                for p in self.named(params):
                    plist.append(self._decl_name(p) or f"a{len(plist)}")
            else:
                for c in self.named(node):
                    if c.type == "identifier":
                        plist.append(self.text(c).strip())
                    elif c.type in ("binary_expression", "ternary_expression"):
                        break
            body_node = self.field(node, "body")
            self.scopes.append({p: self.mod.put(var(p)) for p in plist})
            saved = self.region_stack
            self.region_stack = [self.cur_region()]
            if body_node is not None:
                if body_node.type in ("statement_block", "block", "compound_statement"):
                    for st in self.named(body_node):
                        self.dispatch(st)
                else:
                    self.expr(body_node)
            self.region_stack = saved
            self.scopes.pop()
            return self.mod.put(Term("lambda", (tuple(plist), var(ELEM))))
        if t in ("array", "array_expression", "list", "object"):
            return self.mod.put(Term("list", tuple(self.expr(c) for c in self.named(node))))
        if t in ("template_string", "template_literal"):
            return self.mod.put(Term("concat", tuple(self.expr(c) for c in self.named(node)
                                                      if c.type != "string_fragment")))
        kids = self.named(node)
        if len(kids) == 1:
            return self.expr(kids[0])
        if kids:
            return self.expr(kids[-1])
        return self.mod.put(Term("opaque", (t,)))

    def _arrow_body(self, call_node: Any, *, acc: bool = False) -> Term | None:
        """Body of the callback passed to ``.map`` / ``.filter`` / ``.reduce``."""
        args_node = self.field(call_node, "arguments")
        if args_node is None:
            return None
        for a in self.named(args_node):
            if a.type not in ("arrow_function", "function_expression", "lambda_expression"):
                continue
            params = self.field(a, "parameters")
            names: list[str] = []
            if params is not None:
                for p in self.named(params):
                    names.append(self._decl_name(p) or f"a{len(names)}")
            else:
                for c in self.named(a):
                    if c.type == "identifier":
                        names.append(self.text(c).strip())
                    elif c.type in ("binary_expression", "ternary_expression", "statement_block"):
                        break
            body_node = self.field(a, "body")
            if body_node is None:
                return None
            saved = self.region_stack
            self.region_stack = [self.cur_region()]
            self.scopes.append({})
            for i, n in enumerate(names):
                self.bind(n, self.mod.put(var(ACC if (acc and i == 0) else ELEM)), effect=False)
            tid: Term | None = None
            if body_node.type in ("statement_block", "block", "compound_statement"):
                for st in self.named(body_node):
                    if st.type == "return_statement":
                        kids = self.named(st)
                        tid = self.expr(kids[0]) if kids else self.mod.put(const(None))
            else:
                tid = self.expr(body_node)
            self.scopes.pop()
            self.region_stack = saved
            return tid
        return None

    def _call_name(self, node: Any) -> str:
        if node is None:
            return ""
        if node.type in ("identifier", "property_identifier", "field_identifier"):
            return self.text(node).strip()
        if node.type in ("member_expression", "field_expression"):
            obj = self.field(node, "object") or self.field(node, "argument")
            prop = self.field(node, "property") or self.field(node, "field")
            return f"{self._call_name(obj)}.{self.text(prop).strip() if prop is not None else ''}"
        if node.type == "call_expression":
            return self._call_name(self.field(node, "function"))
        if node.type == "parenthesized_expression":
            kids = self.named(node)
            return self._call_name(kids[0]) if kids else ""
        return self.text(node).strip()


_ACC_NAME = "__acc__"


def lower_tree_sitter(src: bytes, language: str, *, filename: str = "<ts>") -> MirModule:
    from tree_sitter_languages import get_parser

    parser = get_parser(language)
    tree = parser.parse(bytes(src))
    mod = MirModule(language, filename)
    if tree.root_node.has_error:
        mod.effect("call", "parse_error", "r0", tree.root_node.type)
    _TSLowerer(mod, bytes(src)).lower(tree.root_node)
    return mod


def lower_file(path: str | pathlib.Path) -> MirModule:
    p = pathlib.Path(path)
    suffix = p.suffix.lower()
    # refuse an unsupported extension BEFORE opening anything: a caller must not
    # be able to probe the filesystem with a lowering request
    if suffix != ".py" and suffix not in _TS_EXT:
        raise LoweringError(f"UNSUPPORTED_EXTENSION:{suffix}")
    raw = p.read_bytes()
    if suffix == ".py":
        return lower_python(raw.decode("utf-8", errors="replace"), filename=str(p))
    return lower_tree_sitter(raw, _TS_EXT[suffix], filename=str(p))


def lower_sources(sources: Mapping[str, str]) -> dict[str, MirModule]:
    out: dict[str, MirModule] = {}
    for name, src in sources.items():
        suffix = pathlib.Path(name).suffix.lower()
        if suffix == ".py":
            out[name] = lower_python(src, filename=name)
            continue
        lang = _TS_EXT.get(suffix)
        if lang is None:
            raise LoweringError(f"UNSUPPORTED_EXTENSION:{suffix}")
        out[name] = lower_tree_sitter(src.encode("utf-8"), lang, filename=name)
    return out


# --------------------------------------------------------------------------- #
# 7. Concrete evaluator over the Meaning IR
# --------------------------------------------------------------------------- #

class EvalBudgetExceeded(RuntimeError):
    pass


_EVAL_BUDGET = 20000

#: terms compiled to Python closures, keyed by the (hashable) term itself.
#: One compile, then every evaluation is a plain closure call -- that is what
#: puts concrete simulation in the microsecond range instead of the tens.
_EVAL_CACHE: dict[Any, Any] = {}

_BIN = {
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b,
    "div": lambda a, b: a / b, "floordiv": lambda a, b: a // b, "mod": lambda a, b: a % b,
    "pow": lambda a, b: a ** b, "lshift": lambda a, b: a << b, "rshift": lambda a, b: a >> b,
    "bitor": lambda a, b: a | b, "bitand": lambda a, b: a & b, "bitxor": lambda a, b: a ^ b,
    "matmul": lambda a, b: a @ b,
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b, "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b, "gt": lambda a, b: a > b, "ge": lambda a, b: a >= b,
    "in_": lambda a, b: a in b, "contains": lambda a, b: b in a,
    "is": lambda a, b: a is b, "is_not": lambda a, b: a is not b,
    "not_in": lambda a, b: a not in b,
}
_UN = {"not_": lambda a: not a, "neg": lambda a: -a, "pos": lambda a: +a,
       "invert": lambda a: ~a}
_WRAP = {"list": list, "tuple": tuple, "set": set}
_REDUCE1 = {"sorted": sorted, "reversed": lambda v: list(reversed(v)),
            "min": min, "max": max}


def compile_term(t: Any) -> Any:
    """Compile a Meaning-IR term into a closure ``(env, steps) -> value``.

    The step budget is only charged inside ``map``/``filter``/``reduce`` --
    the only unbounded constructs -- so straight-line arithmetic stays fast.
    """
    fn = _EVAL_CACHE.get(t)
    if fn is not None:
        return fn
    if isinstance(t, Lit):
        def fn(e, steps, _v=t.v):
            return _v
    elif not isinstance(t, Term):
        def fn(e, steps, _v=t):
            return _v
    else:
        op, args = t.op, t.args
        if op == "const":
            v = args[0].v if isinstance(args[0], Lit) else args[0]

            def fn(e, steps, _v=v):
                return _v
        elif op == "var":
            name = str(args[0])

            def fn(e, steps, _n=name):
                try:
                    return e[_n]
                except KeyError:
                    raise NameError(f"UNBOUND_VARIABLE:{_n}") from None
        elif op in _BIN:
            f, g, o = compile_term(args[0]), compile_term(args[1]), _BIN[op]

            def fn(e, steps, _f=f, _g=g, _o=o):
                return _o(_f(e, steps), _g(e, steps))
        elif op in _UN:
            f, o = compile_term(args[0]), _UN[op]

            def fn(e, steps, _f=f, _o=o):
                return _o(_f(e, steps))
        elif op == "and_":
            f, g = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _f=f, _g=g):
                return _f(e, steps) and _g(e, steps)
        elif op == "or_":
            f, g = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _f=f, _g=g):
                return _f(e, steps) or _g(e, steps)
        elif op == "select":
            c, a, b = (compile_term(args[0]), compile_term(args[1]), compile_term(args[2]))

            def fn(e, steps, _c=c, _a=a, _b=b):
                return _a(e, steps) if _c(e, steps) else _b(e, steps)
        elif op == "guard":
            c, a = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _c=c, _a=a):
                return _a(e, steps) if _c(e, steps) else None
        elif op == "slice":
            x, lo, hi = (compile_term(args[0]), compile_term(args[1]), compile_term(args[2]))

            def fn(e, steps, _x=x, _lo=lo, _hi=hi):
                return _x(e, steps)[_lo(e, steps):_hi(e, steps)]
        elif op == "index":
            x, i = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _x=x, _i=i):
                return _x(e, steps)[_i(e, steps)]
        elif op == "range":
            lo, hi = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _lo=lo, _hi=hi):
                return list(range(int(_lo(e, steps)), int(_hi(e, steps))))
        elif op == "len":
            x = compile_term(args[0])

            def fn(e, steps, _x=x):
                return len(_x(e, steps))
        elif op == "getattr":
            x = compile_term(args[0])
            attr = args[1].v if isinstance(args[1], Lit) else args[1]

            def fn(e, steps, _x=x, _a=attr):
                return getattr(_x(e, steps), str(_a))
        elif op == "concat":
            a, b = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _a=a, _b=b):
                return _a(e, steps) + _b(e, steps)
        elif op == "list":
            kids = tuple(compile_term(a) for a in args)

            def fn(e, steps, _k=kids):
                return [c(e, steps) for c in _k]
        elif op == "tuple":
            kids = tuple(compile_term(a) for a in args)

            def fn(e, steps, _k=kids):
                return tuple(c(e, steps) for c in _k)
        elif op in _WRAP:
            x, w = compile_term(args[0]), _WRAP[op]

            def fn(e, steps, _x=x, _w=w):
                return _w(_x(e, steps))
        elif op in _REDUCE1:
            x, w = compile_term(args[0]), _REDUCE1[op]

            def fn(e, steps, _x=x, _w=w):
                return _w(_x(e, steps))
        elif op == "map":
            x, b = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _x=x, _b=b):
                out = []
                had, old = ELEM in e, e.get(ELEM)
                try:
                    for item in _x(e, steps):
                        steps[0] += 1
                        if steps[0] > steps[1]:
                            raise EvalBudgetExceeded(f"EVAL_BUDGET_EXCEEDED:{steps[1]}")
                        e[ELEM] = item
                        out.append(_b(e, steps))
                finally:
                    if had:
                        e[ELEM] = old
                    else:
                        e.pop(ELEM, None)
                return out
        elif op == "filter":
            x, b = compile_term(args[0]), compile_term(args[1])

            def fn(e, steps, _x=x, _b=b):
                out = []
                had, old = ELEM in e, e.get(ELEM)
                try:
                    for item in _x(e, steps):
                        steps[0] += 1
                        if steps[0] > steps[1]:
                            raise EvalBudgetExceeded(f"EVAL_BUDGET_EXCEEDED:{steps[1]}")
                        e[ELEM] = item
                        if _b(e, steps):
                            out.append(item)
                finally:
                    if had:
                        e[ELEM] = old
                    else:
                        e.pop(ELEM, None)
                return out
        elif op == "reduce":
            x, i, b = (compile_term(args[0]), compile_term(args[1]), compile_term(args[2]))

            def fn(e, steps, _x=x, _i=i, _b=b):
                acc = _i(e, steps)
                had_e, old_e = ELEM in e, e.get(ELEM)
                had_a, old_a = ACC in e, e.get(ACC)
                try:
                    for item in _x(e, steps):
                        steps[0] += 1
                        if steps[0] > steps[1]:
                            raise EvalBudgetExceeded(f"EVAL_BUDGET_EXCEEDED:{steps[1]}")
                        e[ACC] = acc
                        e[ELEM] = item
                        acc = _b(e, steps)
                finally:
                    if had_e:
                        e[ELEM] = old_e
                    else:
                        e.pop(ELEM, None)
                    if had_a:
                        e[ACC] = old_a
                    else:
                        e.pop(ACC, None)
                return acc
        elif op == "call":
            kids = tuple(compile_term(a) for a in args)

            def fn(e, steps, _k=kids):
                target = _k[0](e, steps)
                argv = [c(e, steps) for c in _k[1:]]
                if isinstance(target, tuple) and target and target[0] == "lambda":
                    sub = dict(e)
                    for pname, val in zip(target[1], argv):
                        sub[str(pname)] = val
                    return compile_term(target[2])(sub, steps)
                if callable(target):
                    return target(*argv)
                raise TypeError(f"NOT_CALLABLE:{type(target).__name__}")
        elif op == "lambda":
            def fn(e, steps, _t=t):
                return ("lambda", _t.args[0], _t.args[1])
        elif op == "hole":
            def fn(e, steps):
                raise ValueError("HOLE_IS_NOT_A_VALUE")
        elif op == "cycle":
            def fn(e, steps):
                raise ValueError("CYCLIC_TERM")
        else:
            detail = args[0] if args else ""

            def fn(e, steps, _d=detail):
                raise ValueError(f"OPAQUE_IS_NOT_A_VALUE:{_d}")
    _EVAL_CACHE[t] = fn
    return fn


def eval_term(t: Any, env: Mapping[str, Any] | None = None, *,
              budget: int = _EVAL_BUDGET) -> Any:
    """Evaluate a pure Meaning-IR term concretely.  Microseconds, no subprocess.

    Raises ``EvalBudgetExceeded`` when the loop-iteration budget is exhausted
    rather than looping, and propagates the guest's own exceptions so a
    crashing branch is observable as a crash instead of being swallowed.
    """
    return compile_term(t)(dict(env or {}), [0, int(budget)])


# --------------------------------------------------------------------------- #
# 8. Delta mental simulator (frames, push/pop, witness purity, pruning)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Action:
    """A candidate step.  ``effects`` is an abstract summary; ``apply`` is an
    optional in-memory concrete transition (never a subprocess)."""

    name: str
    effects: tuple[tuple[str, str], ...] = ()   # (kind, target)
    raises: bool = False
    apply: Any = None                            # Callable[[Mapping], Mapping] | None
    cost: float = 1.0
    detail: str = ""


@dataclass
class Delta:
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    destroys: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    raises: bool = False
    noop: bool = True

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class DeltaSim:
    """Fast in-memory frame simulator with semi-persistent snapshots.

    A *frame* is a mapping ``name -> value``.  ``push``/``pop`` are O(1) and
    ``apply`` is O(effects).  Nothing here touches disk, a subprocess, or the
    network, which is exactly why it can afford to try every candidate.

    ``invariants`` are predicates over the frame that must hold after every
    step; a step that breaks one is reported as ``INVARIANT_VIOLATION`` and is
    pruned before anything is executed for real.
    """

    def __init__(self, frame: Mapping[str, Any] | None = None, *,
                 invariants: Sequence[tuple[str, Any]] = ()) -> None:
        self._frames: list[dict[str, Any]] = [dict(frame or {})]
        self._marks: list[int] = []
        self.invariants = list(invariants)
        self.log: list[dict[str, Any]] = []

    # -- frame access ----------------------------------------------------- #
    @property
    def frame(self) -> dict[str, Any]:
        return self._frames[-1]

    def __getitem__(self, k: str) -> Any:
        return self._frames[-1][k]

    def get(self, k: str, default: Any = None) -> Any:
        return self._frames[-1].get(k, default)

    # -- snapshots -------------------------------------------------------- #
    def push(self) -> int:
        self._marks.append(len(self._frames))
        self._frames.append(dict(self._frames[-1]))
        return len(self._marks)

    def pop(self) -> bool:
        if not self._marks:
            return False
        self._frames.pop()
        self._marks.pop()
        return True

    @property
    def depth(self) -> int:
        return len(self._marks)

    # -- transitions ------------------------------------------------------ #
    def apply(self, action: Action) -> Delta:
        reads: list[str] = []
        writes: list[str] = []
        destroys: list[str] = []
        for kind, target in action.effects:
            if kind == "read":
                reads.append(target)
            elif kind == "write":
                writes.append(target)
            elif kind == "destroy":
                destroys.append(target)
        before = dict(self._frames[-1])
        raises = bool(action.raises)
        if not raises and action.apply is not None:
            try:
                out = action.apply(dict(before))
                if not isinstance(out, Mapping):
                    raise TypeError("APPLY_MUST_RETURN_A_MAPPING")
            except EvalBudgetExceeded:
                raises = True
            except Exception:  # noqa: BLE001 - a crashing branch is a result
                raises = True
            else:
                self._frames[-1] = dict(out)
        if not raises:
            for d in destroys:
                self._frames[-1].pop(d, None)
            after = self._frames[-1]
            changed = sorted(k for k in set(before) | set(after)
                             if before.get(k, _SENTINEL) != after.get(k, _SENTINEL))
        else:
            changed = []
        delta = Delta(reads=tuple(sorted(set(reads))), writes=tuple(sorted(set(writes))),
                      destroys=tuple(sorted(set(destroys))), changed=tuple(changed),
                      raises=raises, noop=(not changed and not raises))
        self.log.append({"action": action.name, "delta": delta.as_dict()})
        return delta

    def restore(self) -> None:
        while self._marks:
            self.pop()

    # -- goal-directed pruning -------------------------------------------- #
    def prune(self, actions: Sequence[Action], *, goal: Any = None,
              witness: Any = None, invariants: Sequence[tuple[str, Any]] = ()) -> dict[str, Any]:
        """Partition candidates into SAFE / NOOP / CRASH / DESTRUCTIVE.

        An action whose delta is the identity (NOOP), which raises (CRASH), or
        which destroys without a witness (DESTRUCTIVE_UNWITNESSED) is removed
        from the live queue.  A witness is a predicate ``delta -> bool``
        certifying that the destructive effect is *required* for the goal;
        absent a witness every destructive action is pruned -- fail closed,
        exactly like the ``shred -v`` law.
        """
        invs = list(self.invariants) + list(invariants)
        safe: list[dict[str, Any]] = []
        pruned: list[dict[str, Any]] = []
        for act in actions:
            self.push()
            try:
                d = self.apply(act)
                # snapshot BEFORE pop(): the goal must be scored on the frame the
                # action actually produced, not on the restored one
                after = dict(self.frame)
                bad = [n for n, fn in invs if not _safe_call(fn, self.frame)]
            finally:
                self.pop()
            row = {"action": act.name, "cost": act.cost, "detail": act.detail,
                   "delta": d.as_dict()}
            if d.raises:
                row["verdict"] = "CRASH"
                pruned.append(row)
            elif d.destroys and not (witness is not None and _safe_call(witness, d)):
                row["verdict"] = "DESTRUCTIVE_UNWITNESSED"
                pruned.append(row)
            elif d.noop and not d.reads and not d.destroys:
                # A declared write that changes nothing is dead code -- prune it.
                # A destroy is never a no-op (the key may simply be absent), and
                # a pure read is a legitimate observation, so both stay.
                row["verdict"] = "NOOP"
                pruned.append(row)
            elif bad:
                row["verdict"] = "INVARIANT_VIOLATION"
                row["violated"] = bad
                pruned.append(row)
            else:
                row["verdict"] = "SAFE"
                row["goal_score"] = (_safe_call(goal, after, default=0.0)
                                     if goal is not None else 0.0)
                safe.append(row)
        safe.sort(key=lambda r: (-float(r.get("goal_score") or 0.0), float(r["cost"])))
        total = len(safe) + len(pruned)
        return {
            "schema": SCHEMA, "total": total, "safe": safe, "pruned": pruned,
            "pruned_fraction": round(len(pruned) / total, 6) if total else 0.0,
        }

    def simulate_plan(self, steps: Sequence[Action], *, goal: Any = None,
                      witness: Any = None) -> dict[str, Any]:
        """Run a candidate plan in memory and report whether it is viable."""
        self.push()
        try:
            rows: list[dict[str, Any]] = []
            for i, act in enumerate(steps):
                d = self.apply(act)
                rows.append({"i": i, "action": act.name, "delta": d.as_dict()})
                if d.raises:
                    return {"schema": SCHEMA, "viable": False, "reason": "CRASH",
                            "at_step": i, "rows": rows}
                if d.destroys and not (witness is not None and _safe_call(witness, d)):
                    return {"schema": SCHEMA, "viable": False,
                            "reason": "DESTRUCTIVE_UNWITNESSED", "at_step": i, "rows": rows}
                bad = [n for n, fn in self.invariants if not _safe_call(fn, self.frame)]
                if bad:
                    return {"schema": SCHEMA, "viable": False, "reason": "INVARIANT_VIOLATION",
                            "violated": bad, "at_step": i, "rows": rows}
            score = _safe_call(goal, self.frame, default=0.0) if goal is not None else 0.0
            return {"schema": SCHEMA, "viable": True, "reason": "SIMULATED_OK",
                    "goal_score": score, "rows": rows}
        finally:
            self.pop()


def _safe_call(fn: Any, *args: Any, default: Any = False) -> Any:
    try:
        return fn(*args)
    except Exception:  # noqa: BLE001 - a witness that raises certifies nothing
        return default


# --------------------------------------------------------------------------- #
# 9. Witness-certified observation purity for CLI-shaped actions
# --------------------------------------------------------------------------- #

#: Programs whose *only* effect is to read.  Anything not listed here is
#: treated as potentially mutating -- fail closed.
_READ_ONLY_PROGRAMS = frozenset({
    "ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "ag",
    "pwd", "whoami", "id", "groups", "stat", "file", "du", "df", "which",
    "type", "true", "false", "sort", "uniq", "cut", "tr", "rev", "nl",
    "basename", "dirname", "realpath", "readlink", "printf", "echo", "test",
    "expr", "env", "printenv", "date", "uname", "arch", "nproc", "free",
    "jq", "yq", "xmllint", "column", "fold", "fmt", "expand",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "cksum", "b2sum",
    "cmp", "comm", "diff", "diff3", "seq", "yes", "tsort", "pr", "tac",
})

#: Programs that mutate even when asked for help in a non-standard way.
#: ``shred -v`` and ``split -v`` are the measured examples.
_NEVER_PURE = frozenset({
    "shred", "split", "dd", "tee", "mv", "cp", "rm", "rmdir", "mkdir", "ln",
    "chmod", "chown", "chgrp", "touch", "truncate", "install", "tar", "gzip",
    "gunzip", "zip", "unzip", "rsync", "scp", "wget", "curl", "git", "sed",
    "awk", "perl", "python", "python3", "node", "sh", "bash", "zsh", "dash",
    "xargs", "find", "sqlite3", "psql", "mysql", "mongo", "redis-cli",
})

#: Flags that are always a pure request for information.
_HELP_FLAGS = frozenset({"-h", "--help", "-?", "/?", "--usage", "-V", "--version",
                         "--copyright", "--license"})


def classify_cli(argv: Sequence[str]) -> dict[str, Any]:
    """Classify an argv as a read / write effect summary.  Fail closed.

    An unknown program, an unknown flag, or any shell metacharacter is
    ``write``-or-worse.  ``shred -v`` is the canonical counter-example to the
    "``-v`` is harmless" intuition, so it is classified non-pure.
    """
    argv = [str(a) for a in argv if str(a).strip()]
    if not argv:
        return {"schema": SCHEMA, "program": "", "effects": [], "pure": False,
                "verdict": "REFUSED__EMPTY_ARGV"}
    prog = pathlib.PurePosixPath(argv[0]).name
    rest = argv[1:]
    reasons: list[str] = []
    if prog in _NEVER_PURE:
        if not (rest and all(a in _HELP_FLAGS for a in rest)):
            reasons.append(f"MUTATING_PROGRAM:{prog}")
    elif prog not in _READ_ONLY_PROGRAMS:
        reasons.append(f"UNKNOWN_PROGRAM:{prog}")
    for a in rest:
        if not a.startswith("-") and any(ch in a for ch in ("|", ";", ">", "<", "&", "\n")):
            reasons.append(f"SHELL_METACHARACTER:{a[:24]}")
            break
    if reasons:
        return {"schema": SCHEMA, "program": prog, "effects": [("write", "")],
                "pure": False, "verdict": "NOT_PURE", "reasons": sorted(set(reasons))}
    return {"schema": SCHEMA, "program": prog, "effects": [("read", "")],
            "pure": True, "verdict": "OBSERVATION_PURE", "reasons": []}


def cli_action(argv: Sequence[str], *, cost: float = 1.0) -> Action:
    c = classify_cli(argv)
    return Action(name=" ".join(str(a) for a in argv), effects=tuple(c["effects"]),
                  raises=False, cost=cost, detail=c["verdict"])


# --------------------------------------------------------------------------- #
# 10. Cross-language equivalence + summary
# --------------------------------------------------------------------------- #

def build_graph(mods: Mapping[str, MirModule] | None = None, *,
                terms: Sequence[Any] = ()) -> SemiPersistentEGraph:
    g = SemiPersistentEGraph()
    for m in (mods or {}).values():
        for t in m.terms:
            g.add(t)
    for t in terms:
        g.add(t)
    return g


def function_term(mod: MirModule, qname: str) -> Any:
    """The canonical Meaning-IR term computing ``qname``'s return value."""
    f = mod.functions.get(qname)
    if not f:
        return None
    return f.get("value")


def cross_language_equivalence(a: Any, b: Any, *, rounds: int = 6) -> dict[str, Any]:
    g = SemiPersistentEGraph()
    g.add(a)
    g.add(b)
    unions = g.saturate(rounds=rounds)
    ca, cb = g.class_of(a), g.class_of(b)
    return {
        "schema": SCHEMA, "equal": ca == cb, "unions": unions,
        "a_canonical": str(g.extract(ca)), "b_canonical": str(g.extract(cb)),
        "anti_unification": anti_unify(a, b, g),
    }


def summarize(mods: Mapping[str, MirModule]) -> dict[str, Any]:
    g = build_graph(mods)
    g.saturate()
    return {
        "schema": SCHEMA,
        "files": {k: v.as_dict() for k, v in mods.items()},
        "e_classes": g.size(),
        "total_terms": sum(len(m.terms) for m in mods.values()),
        "total_effects": sum(len(m.effects) for m in mods.values()),
        "total_regions": sum(len(m.regions) for m in mods.values()),
    }


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=repr).encode()).hexdigest()


__all__ = [
    "SCHEMA", "Lit", "Term", "ELEM", "ACC", "var", "const",
    "SemiPersistentEGraph", "Rule", "DEFAULT_RULES", "anti_unify", "terms_equal",
    "Region", "Effect", "DefEvent", "CallEvent", "MirModule", "LoweringError",
    "lower_python", "lower_tree_sitter", "lower_file", "lower_sources",
    "eval_term", "EvalBudgetExceeded",
    "Action", "Delta", "DeltaSim", "classify_cli", "cli_action",
    "build_graph", "function_term", "cross_language_equivalence", "summarize",
    "digest", "_freeze",
]
