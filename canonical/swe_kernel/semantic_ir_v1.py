#!/usr/bin/env python3
"""Universal Semantic Meaning Graph (`semantic_ir_v1`) — Leap 2 Core.

Translates programs from Python, C, C++, JavaScript, TypeScript, Go, and Rust into ONE
language-neutral SSA + Canonical Loop + Control/Data IR (`SemanticIR`), then saturates
expressions and loop/guard semantics inside a congruence-closed E-Graph with optimistic
abstract e-class analysis (interval, nullness, type set, truthiness).

Zero external model calls. Zero memorized world facts. Zero language-specific repair rules.
"""
from __future__ import annotations

import ast
import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SEMANTIC_IR_V1"
MODEL_CALLS = 0

# Optional tree-sitter substrate (graceful fallback to pure-Python parser if absent)
try:
    from tree_sitter_languages import get_parser as _ts_get_parser  # type: ignore
except Exception:
    _ts_get_parser = None  # type: ignore

# Optional Z3 substrate for mathematical equivalence proofs
try:
    import z3 as _z3  # type: ignore
except Exception:
    _z3 = None  # type: ignore

HAS_TREE_SITTER = _ts_get_parser is not None
HAS_Z3 = _z3 is not None

SUPPORTED_LANGUAGES = ("python", "c", "cpp", "javascript", "typescript", "go", "rust")

_EXT_TO_LANG = {
    ".py": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def detect_language(path_or_lang: str) -> str:
    low = str(path_or_lang or "").strip().lower()
    if low in SUPPORTED_LANGUAGES:
        return low
    for ext, lang in _EXT_TO_LANG.items():
        if low.endswith(ext):
            return lang
    return "python"


# ---------------------------------------------------------------------------
# 1. Abstract Domain Lattice for Optimistic E-Class Analysis (arXiv:2511.20782)
# ---------------------------------------------------------------------------

INF = float("inf")
NEG_INF = float("-inf")


@dataclass(frozen=True)
class Interval:
    """Closed interval [lo, hi] over extended reals; lo > hi represents bottom (unreachable)."""

    lo: float = NEG_INF
    hi: float = INF

    @property
    def is_bottom(self) -> bool:
        return self.lo > self.hi

    @property
    def is_top(self) -> bool:
        return self.lo == NEG_INF and self.hi == INF

    @property
    def is_const(self) -> bool:
        return not self.is_bottom and self.lo == self.hi and math.isfinite(self.lo)

    def join(self, other: "Interval") -> "Interval":
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        return Interval(min(self.lo, other.lo), max(self.hi, other.hi))

    def meet(self, other: "Interval") -> "Interval":
        if self.is_bottom or other.is_bottom:
            return Interval(1.0, 0.0)
        return Interval(max(self.lo, other.lo), min(self.hi, other.hi))

    def add(self, other: "Interval") -> "Interval":
        if self.is_bottom or other.is_bottom:
            return Interval(1.0, 0.0)
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def sub(self, other: "Interval") -> "Interval":
        if self.is_bottom or other.is_bottom:
            return Interval(1.0, 0.0)
        return Interval(self.lo - other.hi, self.hi - other.lo)

    def mul(self, other: "Interval") -> "Interval":
        if self.is_bottom or other.is_bottom:
            return Interval(1.0, 0.0)
        if self.is_top or other.is_top:
            if (self.is_const and self.lo == 0) or (other.is_const and other.lo == 0):
                return Interval(0.0, 0.0)
            return Interval()
        prods = []
        for a in (self.lo, self.hi):
            for b in (other.lo, other.hi):
                prods.append(0.0 if (a == 0 or b == 0) else a * b)
        return Interval(min(prods), max(prods))

    def contains(self, x: float) -> bool:
        return not self.is_bottom and self.lo <= x <= self.hi


NULL_BOT = "BOT"
NULL_ONLY = "NULL"
NON_NULL = "NON_NULL"
MAYBE_NULL = "MAYBE_NULL"

_NULL_JOIN = {
    (NULL_BOT, NULL_BOT): NULL_BOT,
    (NULL_BOT, NULL_ONLY): NULL_ONLY,
    (NULL_BOT, NON_NULL): NON_NULL,
    (NULL_BOT, MAYBE_NULL): MAYBE_NULL,
    (NULL_ONLY, NULL_ONLY): NULL_ONLY,
    (NULL_ONLY, NON_NULL): MAYBE_NULL,
    (NULL_ONLY, MAYBE_NULL): MAYBE_NULL,
    (NON_NULL, NON_NULL): NON_NULL,
    (NON_NULL, MAYBE_NULL): MAYBE_NULL,
    (MAYBE_NULL, MAYBE_NULL): MAYBE_NULL,
}

_NULL_MEET = {
    (MAYBE_NULL, MAYBE_NULL): MAYBE_NULL,
    (MAYBE_NULL, NON_NULL): NON_NULL,
    (MAYBE_NULL, NULL_ONLY): NULL_ONLY,
    (NON_NULL, NON_NULL): NON_NULL,
    (NULL_ONLY, NULL_ONLY): NULL_ONLY,
    (NON_NULL, NULL_ONLY): NULL_BOT,
}


def join_null(a: str, b: str) -> str:
    return _NULL_JOIN.get((a, b)) or _NULL_JOIN.get((b, a)) or MAYBE_NULL


def meet_null(a: str, b: str) -> str:
    if a == NULL_BOT or b == NULL_BOT:
        return NULL_BOT
    return _NULL_MEET.get((a, b)) or _NULL_MEET.get((b, a)) or NULL_BOT


@dataclass(frozen=True)
class AbstractValue:
    """Optimistic abstract domain per SSA variable or E-Class."""

    interval: Interval = field(default_factory=Interval)
    null_state: str = MAYBE_NULL
    types: frozenset[str] = field(default_factory=frozenset)  # empty => TOP (any type)
    truthiness: str = "UNKNOWN"  # TRUTHY | FALSY | UNKNOWN
    symbolic_upper: str | None = None  # e.g., "LEN(arr)" or "n"
    upper_inclusive: bool = False  # True if val can reach symbolic_upper itself!

    def join(self, other: "AbstractValue") -> "AbstractValue":
        types = self.types | other.types if (self.types and other.types) else frozenset()
        truth = self.truthiness if self.truthiness == other.truthiness else "UNKNOWN"
        sym_up = self.symbolic_upper if self.symbolic_upper == other.symbolic_upper else None
        up_inc = (self.upper_inclusive or other.upper_inclusive) if sym_up else False
        return AbstractValue(
            interval=self.interval.join(other.interval),
            null_state=join_null(self.null_state, other.null_state),
            types=types,
            truthiness=truth,
            symbolic_upper=sym_up,
            upper_inclusive=up_inc,
        )

    def meet(self, other: "AbstractValue") -> "AbstractValue":
        if self.types and other.types:
            types = self.types & other.types
        else:
            types = self.types or other.types
        truth = self.truthiness
        if truth == "UNKNOWN":
            truth = other.truthiness
        elif other.truthiness != "UNKNOWN" and other.truthiness != truth:
            truth = "CONTRADICTION"
        sym_up = self.symbolic_upper or other.symbolic_upper
        if self.symbolic_upper and other.symbolic_upper and self.symbolic_upper == other.symbolic_upper:
            up_inc = self.upper_inclusive and other.upper_inclusive
        else:
            up_inc = self.upper_inclusive if self.symbolic_upper else other.upper_inclusive
        return AbstractValue(
            interval=self.interval.meet(other.interval),
            null_state=meet_null(self.null_state, other.null_state),
            types=types,
            truthiness=truth,
            symbolic_upper=sym_up,
            upper_inclusive=up_inc,
        )


def abstract_from_const(val: Any) -> AbstractValue:
    if val is None:
        return AbstractValue(Interval(), NULL_ONLY, frozenset({"NULL"}), "FALSY")
    if isinstance(val, bool):
        return AbstractValue(Interval(float(int(val)), float(int(val))), NON_NULL, frozenset({"BOOL"}), "TRUTHY" if val else "FALSY")
    if isinstance(val, int):
        return AbstractValue(Interval(float(val), float(val)), NON_NULL, frozenset({"INT"}), "TRUTHY" if val != 0 else "FALSY")
    if isinstance(val, float):
        return AbstractValue(Interval(val, val), NON_NULL, frozenset({"FLOAT"}), "TRUTHY" if val != 0.0 else "FALSY")
    if isinstance(val, str):
        return AbstractValue(Interval(), NON_NULL, frozenset({"STR"}), "TRUTHY" if len(val) > 0 else "FALSY")
    if isinstance(val, bytes):
        return AbstractValue(Interval(), NON_NULL, frozenset({"BYTES"}), "TRUTHY" if len(val) > 0 else "FALSY")
    return AbstractValue(Interval(), NON_NULL, frozenset({type(val).__name__.upper()}), "UNKNOWN")


# ---------------------------------------------------------------------------
# 2. Universal Canonical IR Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IRExpr:
    """Universal canonical expression node across all languages."""

    op: str
    args: tuple["IRExpr", ...] = ()
    value: Any = None  # for CONST / VAR / ATTR / MCALL / CALL / CAST / UNKNOWN
    ty: str = "ANY"

    def free_vars(self) -> set[str]:
        out: set[str] = set()
        if self.op == "VAR" and isinstance(self.value, str):
            out.add(self.value)
        elif self.op == "CALL" and isinstance(self.value, str):
            pass
        for a in self.args:
            out.update(a.free_vars())
        return out

    def size(self) -> int:
        return 1 + sum(a.size() for a in self.args)

    def attr_reads(self) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()
        if self.op == "ATTR" and len(self.args) == 1 and isinstance(self.value, str):
            base = self.args[0].value if self.args[0].op == "VAR" else "*"
            out.add((str(base), self.value))
        for a in self.args:
            out.update(a.attr_reads())
        return out

    def call_targets(self) -> list[tuple[str, tuple["IRExpr", ...]]]:
        out: list[tuple[str, tuple[IRExpr, ...]]] = []
        if self.op == "CALL" and isinstance(self.value, str):
            out.append((self.value, self.args))
        elif self.op == "MCALL" and isinstance(self.value, str):
            out.append((self.value, self.args))
        for a in self.args:
            out.extend(a.call_targets())
        return out

    def rename(self, mapping: Mapping[str, str]) -> "IRExpr":
        if self.op == "VAR" and isinstance(self.value, str):
            return IRExpr("VAR", (), mapping.get(self.value, self.value), self.ty)
        return IRExpr(self.op, tuple(a.rename(mapping) for a in self.args), self.value, self.ty)

    def pretty(self) -> str:
        if self.op == "CONST":
            return repr(self.value)
        if self.op == "VAR":
            return str(self.value)
        if self.op == "ATTR" and len(self.args) == 1:
            return f"{self.args[0].pretty()}.{self.value}"
        if self.op == "INDEX" and len(self.args) == 2:
            return f"{self.args[0].pretty()}[{self.args[1].pretty()}]"
        if self.op == "CALL":
            return f"{self.value}({', '.join(a.pretty() for a in self.args)})"
        if self.op == "MCALL" and self.args:
            return f"{self.args[0].pretty()}.{self.value}({', '.join(a.pretty() for a in self.args[1:])})"
        if self.op == "LEN" and len(self.args) == 1:
            return f"LEN({self.args[0].pretty()})"
        if self.op == "IS_NULL" and len(self.args) == 1:
            return f"IS_NULL({self.args[0].pretty()})"
        if self.op == "NOT_NULL" and len(self.args) == 1:
            return f"NOT_NULL({self.args[0].pretty()})"
        if self.op == "DEREF" and len(self.args) == 1:
            return f"DEREF({self.args[0].pretty()})"
        if self.op == "PHI" and len(self.args) == 3:
            return f"PHI({self.args[0].pretty()} ? {self.args[1].pretty()} : {self.args[2].pretty()})"
        return f"{self.op}({', '.join(a.pretty() for a in self.args)})"


@dataclass
class LoopSpec:
    """Canonical loop normal form unifying C for/while/ptr-loops, Python for/while, JS, Go, Rust."""

    loop_kind: str  # INDEXED_SCAN | PTR_SCAN | SEQ_ITER | WHILE_COND
    iv: str  # induction variable name (e.g., "i", "ptr", "x")
    init_expr: IRExpr | None = None
    bound_expr: IRExpr | None = None  # canonical upper bound (e.g. LEN(arr) or n)
    inclusive: bool = False  # True for <=, 0..=n, range(n+1)
    step_expr: IRExpr | None = None  # e.g. CONST(1) or CONST(-1)
    seq_expr: IRExpr | None = None  # sequence/array being scanned if identified
    cond_expr: IRExpr | None = None  # raw condition if WHILE_COND
    body: list["IRStmt"] = field(default_factory=list)
    source_form: str = ""  # "for_c" | "while_idx" | "while_ptr" | "for_range" | "for_each" | "for_rust"


@dataclass
class IRStmt:
    """Universal statement node with explicit def/use/effect metadata."""

    stmt_id: int
    kind: str  # ASSIGN | AUG_ASSIGN | RETURN | BRANCH | LOOP | GUARD | CALL_STMT | STORE_INDEX | STORE_ATTR | RAISE | PASS
    line: int
    end_line: int
    file: str
    func: str
    target: str = ""  # assigned variable / attr / index base
    target_attr: str = ""  # for STORE_ATTR
    target_index: IRExpr | None = None  # for STORE_INDEX
    aug_op: str = ""  # for AUG_ASSIGN (ADD, SUB, ...)
    expr: IRExpr | None = None  # RHS value, branch/guard condition, return value, or call expr
    then_body: list["IRStmt"] = field(default_factory=list)
    else_body: list["IRStmt"] = field(default_factory=list)
    loop: LoopSpec | None = None
    defs: tuple[str, ...] = ()
    uses: tuple[str, ...] = ()
    attr_writes: tuple[tuple[str, str], ...] = ()
    attr_reads: tuple[tuple[str, str], ...] = ()
    source_text: str = ""


@dataclass
class IRFunction:
    """Canonical language-independent function representation."""

    name: str
    qualname: str
    file: str
    language: str
    params: tuple[str, ...]
    line: int
    end_line: int
    stmts: list[IRStmt] = field(default_factory=list)
    source_text: str = ""
    return_type: str = "ANY"

    def all_stmts(self) -> list[IRStmt]:
        out: list[IRStmt] = []

        def _walk(items: Sequence[IRStmt]) -> None:
            for st in items:
                out.append(st)
                if st.then_body:
                    _walk(st.then_body)
                if st.else_body:
                    _walk(st.else_body)
                if st.loop and st.loop.body:
                    _walk(st.loop.body)

        _walk(self.stmts)
        return out


@dataclass
class IRModule:
    file: str
    language: str
    imports: tuple[str, ...] = ()
    functions: list[IRFunction] = field(default_factory=list)
    globals_init: list[IRStmt] = field(default_factory=list)
    source_text: str = ""


@dataclass
class IRProgram:
    modules: dict[str, IRModule] = field(default_factory=dict)

    def all_functions(self) -> list[IRFunction]:
        out: list[IRFunction] = []
        for m in self.modules.values():
            out.extend(m.functions)
        return out

    def find_function(self, name: str, preferred_file: str | None = None) -> IRFunction | None:
        if preferred_file and preferred_file in self.modules:
            for fn in self.modules[preferred_file].functions:
                if fn.name == name or fn.qualname == name:
                    return fn
        for m in self.modules.values():
            for fn in m.functions:
                if fn.name == name or fn.qualname == name:
                    return fn
        return None


# ---------------------------------------------------------------------------
# 3. Congruence-Closed Semantic E-Graph with Optimistic E-Class Analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ENode:
    op: str
    children: tuple[int, ...] = ()
    value: Any = None


@dataclass
class EClass:
    cid: int
    nodes: list[ENode] = field(default_factory=list)
    data: AbstractValue = field(default_factory=AbstractValue)


class SemanticEGraph:
    """Fast congruence-closed E-Graph with algebraic/boolean/bounds saturation + optimistic analysis."""

    def __init__(self) -> None:
        self.parent: list[int] = []
        self.classes: dict[int, EClass] = {}
        self.memo: dict[ENode, int] = {}

    def find(self, cid: int) -> int:
        p = self.parent
        while p[cid] != cid:
            p[cid] = p[p[cid]]
            cid = p[cid]
        return cid

    def _canon(self, node: ENode) -> ENode:
        if not node.children:
            return node
        return ENode(node.op, tuple(self.find(c) for c in node.children), node.value)

    def _eval_abstract_node(self, node: ENode) -> AbstractValue:
        op = node.op
        if op == "CONST":
            return abstract_from_const(node.value)
        if op == "LEN":
            return AbstractValue(Interval(0.0, INF), NON_NULL, frozenset({"INT"}))
        if op in ("IS_NULL", "NOT_NULL", "EQ", "NE", "LT", "LE", "GT", "GE", "AND", "OR", "NOT"):
            return AbstractValue(Interval(0.0, 1.0), NON_NULL, frozenset({"BOOL"}))
        if op == "ADD" and len(node.children) == 2:
            a = self.classes[self.find(node.children[0])].data
            b = self.classes[self.find(node.children[1])].data
            return AbstractValue(a.interval.add(b.interval), NON_NULL, a.types & b.types if (a.types and b.types) else (a.types or b.types))
        if op == "SUB" and len(node.children) == 2:
            a = self.classes[self.find(node.children[0])].data
            b = self.classes[self.find(node.children[1])].data
            return AbstractValue(a.interval.sub(b.interval), NON_NULL, a.types & b.types if (a.types and b.types) else (a.types or b.types))
        if op == "MUL" and len(node.children) == 2:
            a = self.classes[self.find(node.children[0])].data
            b = self.classes[self.find(node.children[1])].data
            return AbstractValue(a.interval.mul(b.interval), NON_NULL, a.types & b.types if (a.types and b.types) else (a.types or b.types))
        return AbstractValue()

    def add_node(self, node: ENode, env_abstract: Mapping[str, AbstractValue] | None = None) -> int:
        cnode = self._canon(node)
        if cnode in self.memo:
            return self.find(self.memo[cnode])
        cid = len(self.parent)
        self.parent.append(cid)
        if cnode.op == "VAR" and env_abstract and isinstance(cnode.value, str) and cnode.value in env_abstract:
            adata = env_abstract[cnode.value]
        else:
            adata = self._eval_abstract_node(cnode)
        self.classes[cid] = EClass(cid, [cnode], adata)
        self.memo[cnode] = cid
        return cid

    def add_expr(self, expr: IRExpr, env_abstract: Mapping[str, AbstractValue] | None = None) -> int:
        child_ids = tuple(self.add_expr(a, env_abstract) for a in expr.args)
        val = expr.value if expr.op in ("CONST", "VAR", "ATTR", "CALL", "MCALL", "CAST", "UNKNOWN") else None
        return self.add_node(ENode(expr.op, child_ids, val), env_abstract)

    def union(self, a: int, b: int) -> int:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        if len(self.classes[ra].nodes) < len(self.classes[rb].nodes):
            ra, rb = rb, ra
        self.parent[rb] = ra
        ec_a = self.classes[ra]
        ec_b = self.classes[rb]
        ec_a.nodes.extend(ec_b.nodes)
        # Optimistic abstract e-class analysis: MEET domain facts on discovered equality!
        ec_a.data = ec_a.data.meet(ec_b.data)
        del self.classes[rb]
        return ra

    def rebuild(self) -> None:
        changed = True
        while changed:
            changed = False
            new_memo: dict[ENode, int] = {}
            for cid in list(self.classes.keys()):
                rcid = self.find(cid)
                if rcid not in self.classes:
                    continue
                dedup: list[ENode] = []
                seen: set[ENode] = set()
                for n in self.classes[rcid].nodes:
                    cn = self._canon(n)
                    if cn in new_memo and self.find(new_memo[cn]) != rcid:
                        rcid = self.union(rcid, new_memo[cn])
                        changed = True
                    else:
                        new_memo[cn] = rcid
                    if cn not in seen:
                        seen.add(cn)
                        dedup.append(cn)
                if rcid in self.classes:
                    self.classes[rcid].nodes = dedup
                    # Re-evaluate abstract data optimistically across all e-nodes in class
                    cur_data = self.classes[rcid].data
                    for cn in dedup:
                        nd = self._eval_abstract_node(cn)
                        if not nd.interval.is_top or nd.null_state != MAYBE_NULL or nd.types:
                            cur_data = cur_data.meet(nd)
                    self.classes[rcid].data = cur_data
            self.memo = new_memo

    def saturate(self, max_iters: int = 8, max_nodes: int = 2000) -> int:
        """Apply universal algebraic, boolean, comparison, and bounds equivalence laws."""
        merges_total = 0
        c0 = self.add_node(ENode("CONST", (), 0))
        c1 = self.add_node(ENode("CONST", (), 1))
        c2 = self.add_node(ENode("CONST", (), 2))

        for _ in range(max_iters):
            if len(self.memo) > max_nodes:
                break
            pending_unions: list[tuple[int, int]] = []
            snapshot = [(self.find(cid), list(ec.nodes)) for cid, ec in self.classes.items()]
            for cid, nodes in snapshot:
                for n in nodes:
                    op, ch = n.op, n.children
                    # 1. Commutativity: +, *, ==, !=, &&, ||
                    if op in ("ADD", "MUL", "EQ", "NE", "AND", "OR") and len(ch) == 2:
                        a, b = self.find(ch[0]), self.find(ch[1])
                        if a != b:
                            sw = self.add_node(ENode(op, (b, a)))
                            pending_unions.append((cid, sw))
                    # 2. Comparison symmetry: a < b <-> b > a ; a <= b <-> b >= a
                    if op == "LT" and len(ch) == 2:
                        pending_unions.append((cid, self.add_node(ENode("GT", (ch[1], ch[0])))))
                    elif op == "GT" and len(ch) == 2:
                        pending_unions.append((cid, self.add_node(ENode("LT", (ch[1], ch[0])))))
                    elif op == "LE" and len(ch) == 2:
                        pending_unions.append((cid, self.add_node(ENode("GE", (ch[1], ch[0])))))
                    elif op == "GE" and len(ch) == 2:
                        pending_unions.append((cid, self.add_node(ENode("LE", (ch[1], ch[0])))))
                    # 3. Negation & De Morgan laws
                    if op == "NOT" and len(ch) == 1:
                        inner_cid = self.find(ch[0])
                        for inn in list(self.classes.get(inner_cid, EClass(inner_cid)).nodes):
                            iop, ich = inn.op, inn.children
                            if iop == "NOT" and len(ich) == 1:
                                pending_unions.append((cid, ich[0]))
                            elif iop == "LT" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("GE", ich))))
                            elif iop == "LE" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("GT", ich))))
                            elif iop == "GT" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("LE", ich))))
                            elif iop == "GE" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("LT", ich))))
                            elif iop == "EQ" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("NE", ich))))
                            elif iop == "NE" and len(ich) == 2:
                                pending_unions.append((cid, self.add_node(ENode("EQ", ich))))
                            elif iop == "IS_NULL" and len(ich) == 1:
                                pending_unions.append((cid, self.add_node(ENode("NOT_NULL", ich))))
                            elif iop == "NOT_NULL" and len(ich) == 1:
                                pending_unions.append((cid, self.add_node(ENode("IS_NULL", ich))))
                            elif iop == "AND" and len(ich) == 2:
                                na = self.add_node(ENode("NOT", (ich[0],)))
                                nb = self.add_node(ENode("NOT", (ich[1],)))
                                pending_unions.append((cid, self.add_node(ENode("OR", (na, nb)))))
                            elif iop == "OR" and len(ich) == 2:
                                na = self.add_node(ENode("NOT", (ich[0],)))
                                nb = self.add_node(ENode("NOT", (ich[1],)))
                                pending_unions.append((cid, self.add_node(ENode("AND", (na, nb)))))
                    # 4. Arithmetic identities
                    if op == "ADD" and len(ch) == 2:
                        a, b = self.find(ch[0]), self.find(ch[1])
                        if b == self.find(c0):
                            pending_unions.append((cid, a))
                        if a == self.find(c0):
                            pending_unions.append((cid, b))
                        if a == b:
                            pending_unions.append((cid, self.add_node(ENode("MUL", (a, c2)))))
                        # (x - y) + y == x
                        for subn in list(self.classes.get(a, EClass(a)).nodes):
                            if subn.op == "SUB" and len(subn.children) == 2 and self.find(subn.children[1]) == b:
                                pending_unions.append((cid, subn.children[0]))
                    elif op == "SUB" and len(ch) == 2:
                        a, b = self.find(ch[0]), self.find(ch[1])
                        if b == self.find(c0):
                            pending_unions.append((cid, a))
                        if a == b:
                            pending_unions.append((cid, c0))
                        # (x + y) - y == x
                        for addn in list(self.classes.get(a, EClass(a)).nodes):
                            if addn.op == "ADD" and len(addn.children) == 2:
                                if self.find(addn.children[1]) == b:
                                    pending_unions.append((cid, addn.children[0]))
                                elif self.find(addn.children[0]) == b:
                                    pending_unions.append((cid, addn.children[1]))
                    elif op == "MUL" and len(ch) == 2:
                        a, b = self.find(ch[0]), self.find(ch[1])
                        if b == self.find(c1):
                            pending_unions.append((cid, a))
                        if a == self.find(c1):
                            pending_unions.append((cid, b))
                        if b == self.find(c0) or a == self.find(c0):
                            pending_unions.append((cid, c0))
                        if b == self.find(c2):
                            pending_unions.append((cid, self.add_node(ENode("ADD", (a, a)))))
                    elif op == "SHL" and len(ch) == 2 and self.find(ch[1]) == self.find(c1):
                        pending_unions.append((cid, self.add_node(ENode("MUL", (ch[0], c2)))))
                    # 5. Integer loop bound equivalences: i < n + 1 <-> i <= n ; i <= n - 1 <-> i < n
                    elif op == "LT" and len(ch) == 2:
                        lhs, rhs = self.find(ch[0]), self.find(ch[1])
                        for rn in list(self.classes.get(rhs, EClass(rhs)).nodes):
                            if rn.op == "ADD" and len(rn.children) == 2:
                                if self.find(rn.children[1]) == self.find(c1):
                                    pending_unions.append((cid, self.add_node(ENode("LE", (lhs, rn.children[0])))))
                                elif self.find(rn.children[0]) == self.find(c1):
                                    pending_unions.append((cid, self.add_node(ENode("LE", (lhs, rn.children[1])))))
                    elif op == "LE" and len(ch) == 2:
                        lhs, rhs = self.find(ch[0]), self.find(ch[1])
                        for rn in list(self.classes.get(rhs, EClass(rhs)).nodes):
                            if rn.op == "SUB" and len(rn.children) == 2 and self.find(rn.children[1]) == self.find(c1):
                                pending_unions.append((cid, self.add_node(ENode("LT", (lhs, rn.children[0])))))
                    # 6. Constant folding
                    if op in ("ADD", "SUB", "MUL") and len(ch) == 2:
                        da = self.classes[self.find(ch[0])].data.interval
                        db = self.classes[self.find(ch[1])].data.interval
                        if da.is_const and db.is_const and float(da.lo).is_integer() and float(db.lo).is_integer():
                            va, vb = int(da.lo), int(db.lo)
                            res = va + vb if op == "ADD" else (va - vb if op == "SUB" else va * vb)
                            pending_unions.append((cid, self.add_node(ENode("CONST", (), res))))

            step_merges = 0
            for u, v in pending_unions:
                if self.find(u) != self.find(v):
                    self.union(u, v)
                    step_merges += 1
            if step_merges == 0:
                break
            merges_total += step_merges
            self.rebuild()
        return merges_total

    def equivalent(self, cid_a: int, cid_b: int) -> bool:
        return self.find(cid_a) == self.find(cid_b)


def expressions_equivalent(expr_a: IRExpr, expr_b: IRExpr, *, use_z3: bool = True) -> tuple[bool, str]:
    """Check semantic equivalence of two IRExprs via E-Graph saturation (+ optional Z3 SMT)."""
    eg = SemanticEGraph()
    ca = eg.add_expr(expr_a)
    cb = eg.add_expr(expr_b)
    eg.saturate()
    if eg.equivalent(ca, cb):
        return True, "EGRAPH_CONGRUENCE_PROVEN"
    if use_z3 and _z3 is not None:
        ok, reason = _z3_exprs_equivalent(expr_a, expr_b)
        if ok:
            return True, reason
    return False, "NOT_EQUIVALENT"


def _to_z3_term(expr: IRExpr, sym_map: dict[str, Any]) -> Any | None:
    if _z3 is None:
        return None
    op = expr.op
    if op == "CONST":
        if isinstance(expr.value, bool):
            return _z3.BoolVal(expr.value)
        if isinstance(expr.value, int):
            return _z3.IntVal(expr.value)
        return None
    if op == "VAR" and isinstance(expr.value, str):
        if expr.value not in sym_map:
            sym_map[expr.value] = _z3.Int(expr.value)
        return sym_map[expr.value]
    if op == "LEN" and len(expr.args) == 1:
        key = f"__len__{expr.args[0].pretty()}"
        if key not in sym_map:
            sym_map[key] = _z3.Int(key)
        return sym_map[key]
    if op == "NEG" and len(expr.args) == 1:
        t = _to_z3_term(expr.args[0], sym_map)
        return -t if t is not None and _z3.is_arith(t) else None
    if op == "NOT" and len(expr.args) == 1:
        t = _to_z3_term(expr.args[0], sym_map)
        return _z3.Not(t) if t is not None and _z3.is_bool(t) else None
    if len(expr.args) == 2:
        a = _to_z3_term(expr.args[0], sym_map)
        b = _to_z3_term(expr.args[1], sym_map)
        if a is None or b is None:
            return None
        if op == "ADD" and _z3.is_arith(a) and _z3.is_arith(b):
            return a + b
        if op == "SUB" and _z3.is_arith(a) and _z3.is_arith(b):
            return a - b
        if op == "MUL" and _z3.is_arith(a) and _z3.is_arith(b):
            return a * b
        if op == "IDIV" and _z3.is_int(a) and _z3.is_int(b):
            return a / b
        if op == "MOD" and _z3.is_int(a) and _z3.is_int(b):
            return a % b
        if op == "LT" and _z3.is_arith(a) and _z3.is_arith(b):
            return a < b
        if op == "LE" and _z3.is_arith(a) and _z3.is_arith(b):
            return a <= b
        if op == "GT" and _z3.is_arith(a) and _z3.is_arith(b):
            return a > b
        if op == "GE" and _z3.is_arith(a) and _z3.is_arith(b):
            return a >= b
        if op == "EQ" and a.sort() == b.sort():
            return a == b
        if op == "NE" and a.sort() == b.sort():
            return a != b
        if op == "AND" and _z3.is_bool(a) and _z3.is_bool(b):
            return _z3.And(a, b)
        if op == "OR" and _z3.is_bool(a) and _z3.is_bool(b):
            return _z3.Or(a, b)
    if op == "PHI" and len(expr.args) == 3:
        c = _to_z3_term(expr.args[0], sym_map)
        t = _to_z3_term(expr.args[1], sym_map)
        e = _to_z3_term(expr.args[2], sym_map)
        if c is not None and t is not None and e is not None and _z3.is_bool(c) and t.sort() == e.sort():
            return _z3.If(c, t, e)
    return None


def _z3_exprs_equivalent(expr_a: IRExpr, expr_b: IRExpr) -> tuple[bool, str]:
    if _z3 is None:
        return False, "Z3_UNAVAILABLE"
    sym_map: dict[str, Any] = {}
    ta = _to_z3_term(expr_a, sym_map)
    tb = _to_z3_term(expr_b, sym_map)
    if ta is None or tb is None or ta.sort() != tb.sort():
        return False, "Z3_UNTRANSLATABLE"
    s = _z3.Solver()
    s.set("timeout", 200)
    for k, v in sym_map.items():
        if k.startswith("__len__"):
            s.add(v >= 0)
    s.add(ta != tb)
    if s.check() == _z3.unsat:
        return True, "Z3_SMT_PROVEN"
    return False, "Z3_COUNTEREXAMPLE_EXISTS"


# ---------------------------------------------------------------------------
# 4. Python Front-End Lowering -> SemanticIR (Exact, Zero-Dependency)
# ---------------------------------------------------------------------------

_PY_BINOP = {
    ast.Add: "ADD",
    ast.Sub: "SUB",
    ast.Mult: "MUL",
    ast.Div: "DIV",
    ast.FloorDiv: "IDIV",
    ast.Mod: "MOD",
    ast.Pow: "POW",
    ast.BitAnd: "BITAND",
    ast.BitOr: "BITOR",
    ast.BitXor: "BITXOR",
    ast.LShift: "SHL",
    ast.RShift: "SHR",
}

_PY_CMP = {
    ast.Eq: "EQ",
    ast.NotEq: "NE",
    ast.Lt: "LT",
    ast.LtE: "LE",
    ast.Gt: "GT",
    ast.GtE: "GE",
    ast.In: "IN",
    ast.NotIn: "NOT_IN",
}


class _IdGen:
    def __init__(self) -> None:
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n


def _lower_py_expr(node: ast.AST | None) -> IRExpr:
    if node is None:
        return IRExpr("CONST", (), None, "NULL")
    if isinstance(node, ast.Constant):
        v = node.value
        ty = "NULL" if v is None else ("BOOL" if isinstance(v, bool) else type(v).__name__.upper())
        return IRExpr("CONST", (), v, ty)
    if isinstance(node, ast.Name):
        return IRExpr("VAR", (), node.id)
    if isinstance(node, ast.Attribute):
        base = _lower_py_expr(node.value)
        return IRExpr("ATTR", (base,), node.attr)
    if isinstance(node, ast.Subscript):
        val = _lower_py_expr(node.value)
        if isinstance(node.slice, ast.Slice):
            lo = _lower_py_expr(node.slice.lower)
            hi = _lower_py_expr(node.slice.upper)
            st = _lower_py_expr(node.slice.step)
            return IRExpr("SLICE", (val, lo, hi, st))
        idx = _lower_py_expr(node.slice)
        return IRExpr("INDEX", (val, idx))
    if isinstance(node, ast.BinOp):
        op = _PY_BINOP.get(type(node.op), "BINOP")
        return IRExpr(op, (_lower_py_expr(node.left), _lower_py_expr(node.right)))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return IRExpr("NOT", (_lower_py_expr(node.operand),), None, "BOOL")
        if isinstance(node.op, ast.USub):
            return IRExpr("NEG", (_lower_py_expr(node.operand),))
        if isinstance(node.op, ast.UAdd):
            return _lower_py_expr(node.operand)
        if isinstance(node.op, ast.Invert):
            return IRExpr("BITNOT", (_lower_py_expr(node.operand),))
    if isinstance(node, ast.BoolOp):
        op = "AND" if isinstance(node.op, ast.And) else "OR"
        cur = _lower_py_expr(node.values[0])
        for v in node.values[1:]:
            cur = IRExpr(op, (cur, _lower_py_expr(v)), None, "BOOL")
        return cur
    if isinstance(node, ast.Compare):
        parts: list[IRExpr] = []
        left = node.left
        for op_node, right in zip(node.ops, node.comparators):
            le = _lower_py_expr(left)
            re_ = _lower_py_expr(right)
            if isinstance(op_node, ast.Is) and re_.op == "CONST" and re_.value is None:
                parts.append(IRExpr("IS_NULL", (le,), None, "BOOL"))
            elif isinstance(op_node, ast.IsNot) and re_.op == "CONST" and re_.value is None:
                parts.append(IRExpr("NOT_NULL", (le,), None, "BOOL"))
            elif isinstance(op_node, ast.Is):
                parts.append(IRExpr("IS", (le, re_), None, "BOOL"))
            elif isinstance(op_node, ast.IsNot):
                parts.append(IRExpr("IS_NOT", (le, re_), None, "BOOL"))
            else:
                cop = _PY_CMP.get(type(op_node), "CMP")
                parts.append(IRExpr(cop, (le, re_), None, "BOOL"))
            left = right
        cur = parts[0]
        for p in parts[1:]:
            cur = IRExpr("AND", (cur, p), None, "BOOL")
        return cur
    if isinstance(node, ast.IfExp):
        return IRExpr("PHI", (_lower_py_expr(node.test), _lower_py_expr(node.body), _lower_py_expr(node.orelse)))
    if isinstance(node, ast.Call):
        args = tuple(_lower_py_expr(a) for a in node.args)
        if isinstance(node.func, ast.Name):
            if node.func.id == "len" and len(args) == 1:
                return IRExpr("LEN", args, None, "INT")
            if node.func.id == "isinstance" and len(args) == 2:
                return IRExpr("TYPE_IS", args, None, "BOOL")
            return IRExpr("CALL", args, node.func.id)
        if isinstance(node.func, ast.Attribute):
            recv = _lower_py_expr(node.func.value)
            return IRExpr("MCALL", (recv, *args), node.func.attr)
        return IRExpr("CALL", args, ast.unparse(node.func))
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        kind = "LIST" if isinstance(node, ast.List) else ("TUPLE" if isinstance(node, ast.Tuple) else "SET")
        return IRExpr(kind, tuple(_lower_py_expr(e) for e in node.elts))
    if isinstance(node, ast.Dict):
        kv: list[IRExpr] = []
        for k, v in zip(node.keys, node.values):
            kv.append(_lower_py_expr(k))
            kv.append(_lower_py_expr(v))
        return IRExpr("DICT", tuple(kv))
    if isinstance(node, ast.JoinedStr):
        return IRExpr("FORMAT", tuple(_lower_py_expr(v) for v in node.values), None, "STR")
    if isinstance(node, ast.FormattedValue):
        return _lower_py_expr(node.value)
    return IRExpr("UNKNOWN", (), ast.unparse(node))


def _canonicalize_while_to_loop(
    prev_stmts: list[IRStmt],
    cond: IRExpr,
    body: list[IRStmt],
    *,
    source_form: str = "while_idx",
) -> LoopSpec:
    """Lift `i = 0; while i < n: ...; i += 1` or `p = a; while p < a + n: ...; p++` to canonical LoopSpec!"""
    # Detect induction variable & comparison bound
    iv = ""
    bound_expr: IRExpr | None = None
    inclusive = False
    if cond.op in ("LT", "LE") and len(cond.args) == 2 and cond.args[0].op == "VAR":
        iv = str(cond.args[0].value)
        bound_expr = cond.args[1]
        inclusive = cond.op == "LE"
    elif cond.op in ("GT", "GE") and len(cond.args) == 2 and cond.args[1].op == "VAR":
        iv = str(cond.args[1].value)
        bound_expr = cond.args[0]
        inclusive = cond.op == "GE"

    if iv:
        # Check preceding init assignment for `iv`
        init_expr: IRExpr | None = None
        for ps in reversed(prev_stmts):
            if ps.kind == "ASSIGN" and ps.target == iv and ps.expr is not None:
                init_expr = ps.expr
                break
        # Check step increment inside body (e.g., iv += 1 or iv = iv + 1)
        step_expr: IRExpr | None = None
        clean_body: list[IRStmt] = []
        for bs in body:
            if bs.kind == "AUG_ASSIGN" and bs.target == iv and bs.aug_op == "ADD" and bs.expr is not None:
                step_expr = bs.expr
                continue
            if (
                bs.kind == "ASSIGN"
                and bs.target == iv
                and bs.expr is not None
                and bs.expr.op == "ADD"
                and len(bs.expr.args) == 2
                and bs.expr.args[0] == IRExpr("VAR", (), iv)
            ):
                step_expr = bs.expr.args[1]
                continue
            clean_body.append(bs)

        if step_expr is not None:
            # Normalize pointer scan `p = arr; while (p < arr + n)` -> INDEXED_SCAN(seq=arr, init=0, bound=n)!
            if (
                init_expr is not None
                and init_expr.op == "VAR"
                and bound_expr is not None
                and bound_expr.op == "ADD"
                and len(bound_expr.args) == 2
                and bound_expr.args[0] == init_expr
            ):
                seq_expr = init_expr
                real_bound = bound_expr.args[1]
                # Rewrite DEREF(VAR(iv)) inside body to INDEX(seq_expr, VAR(iv))!
                norm_body = [_rewrite_ptr_deref_stmt(bs, iv, seq_expr) for bs in clean_body]
                return LoopSpec(
                    loop_kind="INDEXED_SCAN",
                    iv=iv,
                    init_expr=IRExpr("CONST", (), 0, "INT"),
                    bound_expr=real_bound,
                    inclusive=inclusive,
                    step_expr=step_expr,
                    seq_expr=seq_expr,
                    cond_expr=cond,
                    body=norm_body,
                    source_form="while_ptr",
                )
            # Detect sequence indexed by `iv` inside body
            seq_expr = _infer_indexed_seq(clean_body, iv)
            return LoopSpec(
                loop_kind="INDEXED_SCAN",
                iv=iv,
                init_expr=init_expr or IRExpr("CONST", (), 0, "INT"),
                bound_expr=bound_expr,
                inclusive=inclusive,
                step_expr=step_expr,
                seq_expr=seq_expr,
                cond_expr=cond,
                body=clean_body,
                source_form=source_form,
            )

    return LoopSpec(
        loop_kind="WHILE_COND",
        iv=iv or "",
        cond_expr=cond,
        body=body,
        source_form=source_form,
    )


def _rewrite_ptr_deref_expr(expr: IRExpr, ptr_var: str, seq_expr: IRExpr) -> IRExpr:
    if expr.op == "DEREF" and len(expr.args) == 1 and expr.args[0] == IRExpr("VAR", (), ptr_var):
        return IRExpr("INDEX", (seq_expr, IRExpr("VAR", (), ptr_var)))
    return IRExpr(expr.op, tuple(_rewrite_ptr_deref_expr(a, ptr_var, seq_expr) for a in expr.args), expr.value, expr.ty)


def _rewrite_ptr_deref_stmt(st: IRStmt, ptr_var: str, seq_expr: IRExpr) -> IRStmt:
    new_expr = _rewrite_ptr_deref_expr(st.expr, ptr_var, seq_expr) if st.expr else None
    new_then = [_rewrite_ptr_deref_stmt(s, ptr_var, seq_expr) for s in st.then_body]
    new_else = [_rewrite_ptr_deref_stmt(s, ptr_var, seq_expr) for s in st.else_body]
    uses = tuple(sorted(new_expr.free_vars())) if new_expr else st.uses
    return IRStmt(
        stmt_id=st.stmt_id,
        kind=st.kind,
        line=st.line,
        end_line=st.end_line,
        file=st.file,
        func=st.func,
        target=st.target,
        target_attr=st.target_attr,
        target_index=st.target_index,
        aug_op=st.aug_op,
        expr=new_expr,
        then_body=new_then,
        else_body=new_else,
        loop=st.loop,
        defs=st.defs,
        uses=uses,
        attr_writes=st.attr_writes,
        attr_reads=st.attr_reads,
        source_text=st.source_text,
    )


def _infer_indexed_seq(stmts: Sequence[IRStmt], iv: str) -> IRExpr | None:
    def _scan_expr(e: IRExpr | None) -> IRExpr | None:
        if e is None:
            return None
        if e.op == "INDEX" and len(e.args) == 2 and e.args[1] == IRExpr("VAR", (), iv):
            return e.args[0]
        for a in e.args:
            r = _scan_expr(a)
            if r is not None:
                return r
        return None

    for s in stmts:
        r = _scan_expr(s.expr)
        if r is not None:
            return r
        if s.kind == "STORE_INDEX" and s.target_index == IRExpr("VAR", (), iv) and s.target:
            return IRExpr("VAR", (), s.target)
        for sub in (s.then_body, s.else_body):
            r = _infer_indexed_seq(sub, iv)
            if r is not None:
                return r
    return None


def _lower_py_stmts(
    stmts: Sequence[ast.stmt],
    file: str,
    func: str,
    idgen: _IdGen,
    src_lines: Sequence[str],
) -> list[IRStmt]:
    out: list[IRStmt] = []
    for node in stmts:
        ln = getattr(node, "lineno", 0)
        end_ln = getattr(node, "end_lineno", ln)
        stxt = "\n".join(src_lines[ln - 1 : end_ln]) if (1 <= ln <= len(src_lines)) else ""
        if isinstance(node, ast.Assign):
            rhs = _lower_py_expr(node.value)
            uses = tuple(sorted(rhs.free_vars()))
            areads = tuple(sorted(rhs.attr_reads()))
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out.append(IRStmt(
                        idgen.next(), "ASSIGN", ln, end_ln, file, func,
                        target=tgt.id, expr=rhs, defs=(tgt.id,), uses=uses,
                        attr_reads=areads, source_text=stxt,
                    ))
                elif isinstance(tgt, ast.Attribute):
                    base = _lower_py_expr(tgt.value)
                    bname = str(base.value) if base.op == "VAR" else "*"
                    out.append(IRStmt(
                        idgen.next(), "STORE_ATTR", ln, end_ln, file, func,
                        target=bname, target_attr=tgt.attr, expr=rhs,
                        defs=(), uses=tuple(sorted(set(uses) | base.free_vars())),
                        attr_writes=((bname, tgt.attr),), attr_reads=areads, source_text=stxt,
                    ))
                elif isinstance(tgt, ast.Subscript):
                    base = _lower_py_expr(tgt.value)
                    idx = _lower_py_expr(tgt.slice)
                    bname = str(base.value) if base.op == "VAR" else "*"
                    out.append(IRStmt(
                        idgen.next(), "STORE_INDEX", ln, end_ln, file, func,
                        target=bname, target_index=idx, expr=rhs,
                        defs=(bname,) if bname != "*" else (),
                        uses=tuple(sorted(set(uses) | base.free_vars() | idx.free_vars())),
                        attr_reads=areads, source_text=stxt,
                    ))
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    dnames = tuple(e.id for e in tgt.elts if isinstance(e, ast.Name))
                    out.append(IRStmt(
                        idgen.next(), "ASSIGN", ln, end_ln, file, func,
                        target=",".join(dnames), expr=rhs, defs=dnames, uses=uses,
                        attr_reads=areads, source_text=stxt,
                    ))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            rhs = _lower_py_expr(node.value)
            uses = tuple(sorted(rhs.free_vars()))
            if isinstance(node.target, ast.Name):
                out.append(IRStmt(
                    idgen.next(), "ASSIGN", ln, end_ln, file, func,
                    target=node.target.id, expr=rhs, defs=(node.target.id,), uses=uses,
                    attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                ))
            elif isinstance(node.target, ast.Attribute):
                base = _lower_py_expr(node.target.value)
                bname = str(base.value) if base.op == "VAR" else "*"
                out.append(IRStmt(
                    idgen.next(), "STORE_ATTR", ln, end_ln, file, func,
                    target=bname, target_attr=node.target.attr, expr=rhs,
                    uses=tuple(sorted(set(uses) | base.free_vars())),
                    attr_writes=((bname, node.target.attr),),
                    attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                ))
        elif isinstance(node, ast.AugAssign):
            op = _PY_BINOP.get(type(node.op), "ADD")
            rhs = _lower_py_expr(node.value)
            if isinstance(node.target, ast.Name):
                tname = node.target.id
                out.append(IRStmt(
                    idgen.next(), "AUG_ASSIGN", ln, end_ln, file, func,
                    target=tname, aug_op=op, expr=rhs,
                    defs=(tname,), uses=tuple(sorted(rhs.free_vars() | {tname})),
                    attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                ))
            elif isinstance(node.target, ast.Subscript):
                base = _lower_py_expr(node.target.value)
                idx = _lower_py_expr(node.target.slice)
                bname = str(base.value) if base.op == "VAR" else "*"
                cur_val = IRExpr("INDEX", (base, idx))
                new_val = IRExpr(op, (cur_val, rhs))
                out.append(IRStmt(
                    idgen.next(), "STORE_INDEX", ln, end_ln, file, func,
                    target=bname, target_index=idx, expr=new_val,
                    defs=(bname,) if bname != "*" else (),
                    uses=tuple(sorted(rhs.free_vars() | base.free_vars() | idx.free_vars())),
                    attr_reads=tuple(sorted(rhs.attr_reads() | base.attr_reads())), source_text=stxt,
                ))
        elif isinstance(node, ast.Return):
            rhs = _lower_py_expr(node.value)
            out.append(IRStmt(
                idgen.next(), "RETURN", ln, end_ln, file, func,
                expr=rhs, uses=tuple(sorted(rhs.free_vars())),
                attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.Raise):
            rhs = _lower_py_expr(node.exc)
            out.append(IRStmt(
                idgen.next(), "RAISE", ln, end_ln, file, func,
                expr=rhs, uses=tuple(sorted(rhs.free_vars())),
                attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.If):
            cond = _lower_py_expr(node.test)
            tb = _lower_py_stmts(node.body, file, func, idgen, src_lines)
            eb = _lower_py_stmts(node.orelse, file, func, idgen, src_lines)
            kind = "GUARD" if (not eb and len(tb) == 1 and tb[0].kind in ("RETURN", "RAISE")) else "BRANCH"
            out.append(IRStmt(
                idgen.next(), kind, ln, end_ln, file, func,
                expr=cond, then_body=tb, else_body=eb,
                uses=tuple(sorted(cond.free_vars())),
                attr_reads=tuple(sorted(cond.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.For):
            body = _lower_py_stmts(node.body, file, func, idgen, src_lines)
            iv = node.target.id if isinstance(node.target, ast.Name) else ast.unparse(node.target)
            iter_e = _lower_py_expr(node.iter)
            # Lift `for i in range(a, b, s)` -> canonical INDEXED_SCAN!
            if iter_e.op == "CALL" and iter_e.value == "range" and 1 <= len(iter_e.args) <= 3:
                if len(iter_e.args) == 1:
                    init_e, bound_e, step_e = IRExpr("CONST", (), 0, "INT"), iter_e.args[0], IRExpr("CONST", (), 1, "INT")
                elif len(iter_e.args) == 2:
                    init_e, bound_e, step_e = iter_e.args[0], iter_e.args[1], IRExpr("CONST", (), 1, "INT")
                else:
                    init_e, bound_e, step_e = iter_e.args[0], iter_e.args[1], iter_e.args[2]
                # Detect `range(n + 1)` -> inclusive=True with bound=n!
                inclusive = False
                if bound_e.op == "ADD" and len(bound_e.args) == 2 and bound_e.args[1] == IRExpr("CONST", (), 1, "INT"):
                    bound_e = bound_e.args[0]
                    inclusive = True
                seq_e = _infer_indexed_seq(body, iv)
                spec = LoopSpec(
                    loop_kind="INDEXED_SCAN",
                    iv=iv,
                    init_expr=init_e,
                    bound_expr=bound_e,
                    inclusive=inclusive,
                    step_expr=step_e,
                    seq_expr=seq_e,
                    body=body,
                    source_form="for_range",
                )
            else:
                spec = LoopSpec(
                    loop_kind="SEQ_ITER",
                    iv=iv,
                    init_expr=IRExpr("CONST", (), 0, "INT"),
                    bound_expr=IRExpr("LEN", (iter_e,), None, "INT"),
                    inclusive=False,
                    step_expr=IRExpr("CONST", (), 1, "INT"),
                    seq_expr=iter_e,
                    body=body,
                    source_form="for_each",
                )
            if isinstance(node.target, ast.Name):
                iv_defs: tuple[str, ...] = (node.target.id,)
            elif isinstance(node.target, (ast.Tuple, ast.List)):
                iv_defs = tuple(e.id for e in node.target.elts if isinstance(e, ast.Name))
            else:
                iv_defs = (iv,)
            out.append(IRStmt(
                idgen.next(), "LOOP", ln, end_ln, file, func,
                target=",".join(iv_defs) if len(iv_defs) > 1 else iv, expr=iter_e, loop=spec,
                defs=iv_defs, uses=tuple(sorted(iter_e.free_vars())),
                attr_reads=tuple(sorted(iter_e.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.While):
            cond = _lower_py_expr(node.test)
            body = _lower_py_stmts(node.body, file, func, idgen, src_lines)
            spec = _canonicalize_while_to_loop(out, cond, body, source_form="while_idx")
            out.append(IRStmt(
                idgen.next(), "LOOP", ln, end_ln, file, func,
                target=spec.iv, expr=cond, loop=spec,
                defs=(spec.iv,) if spec.iv else (),
                uses=tuple(sorted(cond.free_vars())),
                attr_reads=tuple(sorted(cond.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.Expr):
            e = _lower_py_expr(node.value)
            mut_defs: tuple[str, ...] = ()
            mut_target = ""
            if e.op == "MCALL" and e.args and e.args[0].op == "VAR":
                mut_target = str(e.args[0].value)
                mut_defs = (mut_target,)
            out.append(IRStmt(
                idgen.next(), "CALL_STMT", ln, end_ln, file, func,
                target=mut_target, expr=e, defs=mut_defs,
                uses=tuple(sorted(e.free_vars())),
                attr_reads=tuple(sorted(e.attr_reads())), source_text=stxt,
            ))
        elif isinstance(node, ast.Try):
            tb = _lower_py_stmts(node.body, file, func, idgen, src_lines)
            eb: list[IRStmt] = []
            for h in node.handlers:
                eb.extend(_lower_py_stmts(h.body, file, func, idgen, src_lines))
            out.append(IRStmt(
                idgen.next(), "BRANCH", ln, end_ln, file, func,
                expr=IRExpr("CONST", (), True, "BOOL"), then_body=tb, else_body=eb,
                source_text=stxt,
            ))
    return out


def lower_python_module(source: str, file: str = "<module>.py") -> IRModule:
    tree = ast.parse(source, filename=file)
    src_lines = source.splitlines()
    idgen = _IdGen()
    imports: list[str] = []
    funcs: list[IRFunction] = []
    globals_init: list[IRStmt] = []

    def _collect_fn(fn_node: ast.FunctionDef | ast.AsyncFunctionDef, cls_prefix: str = "") -> None:
        params = tuple(
            a.arg for a in (
                list(fn_node.args.posonlyargs)
                + list(fn_node.args.args)
                + list(fn_node.args.kwonlyargs)
            )
        )
        qual = f"{cls_prefix}.{fn_node.name}" if cls_prefix else fn_node.name
        stmts = _lower_py_stmts(fn_node.body, file, qual, idgen, src_lines)
        ln = fn_node.lineno
        end_ln = getattr(fn_node, "end_lineno", ln)
        ftxt = "\n".join(src_lines[ln - 1 : end_ln])
        funcs.append(IRFunction(fn_node.name, qual, file, "python", params, ln, end_ln, stmts, ftxt))
        for sub in fn_node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _collect_fn(sub, qual)

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_fn(node)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _collect_fn(sub, node.name)
        else:
            globals_init.extend(_lower_py_stmts([node], file, "<module>", idgen, src_lines))

    return IRModule(file=file, language="python", imports=tuple(imports), functions=funcs, globals_init=globals_init, source_text=source)


# ---------------------------------------------------------------------------
# 5. Polyglot Front-End Lowering (C / C++ / JS / TS / Go / Rust) via Tree-Sitter
# ---------------------------------------------------------------------------

_TS_OP_MAP = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD",
    "==": "EQ", "===": "EQ", "!=": "NE", "!==": "NE",
    "<": "LT", "<=": "LE", ">": "GT", ">=": "GE",
    "&&": "AND", "||": "OR", "&": "BITAND", "|": "BITOR", "^": "BITXOR",
    "<<": "SHL", ">>": "SHR",
}

_NULL_LITERALS = frozenset({"NULL", "nullptr", "null", "undefined", "nil", "None"})


def _ts_text(node: Any, raw: bytes) -> str:
    return raw[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _ts_named(node: Any) -> list[Any]:
    return [c for c in node.children if c.is_named and c.type != "comment"]


def _lower_ts_expr(node: Any, raw: bytes, lang: str) -> IRExpr:
    if node is None:
        return IRExpr("CONST", (), None, "NULL")
    t = node.type
    txt = _ts_text(node, raw).strip()

    if t in ("parenthesized_expression", "expression_statement", "argument", "expression_list"):
        ch = _ts_named(node)
        if len(ch) == 1:
            return _lower_ts_expr(ch[0], raw, lang)
    if t in ("number_literal", "integer_literal", "number", "int_literal", "float_literal"):
        clean = txt.rstrip("uUlLfF").replace("_", "")
        try:
            if "." in clean or "e" in clean.lower():
                return IRExpr("CONST", (), float(clean), "FLOAT")
            return IRExpr("CONST", (), int(clean, 0), "INT")
        except ValueError:
            return IRExpr("CONST", (), txt, "NUM")
    if t in ("string_literal", "string", "interpreted_string_literal", "raw_string_literal", "char_literal"):
        return IRExpr("CONST", (), txt.strip("\"'`"), "STR")
    if t in ("true", "false"):
        return IRExpr("CONST", (), t == "true", "BOOL")
    if t in ("null", "nullptr", "nil", "undefined") or txt in _NULL_LITERALS:
        return IRExpr("CONST", (), None, "NULL")
    if t in ("identifier", "field_identifier", "property_identifier", "this", "self"):
        return IRExpr("VAR", (), txt)
    if t in ("pointer_expression", "unary_expression", "prefix_unary_expression"):
        ch = _ts_named(node)
        if ch:
            op_tok = txt[: len(txt) - len(_ts_text(ch[0], raw))].strip()
            inner = _lower_ts_expr(ch[0], raw, lang)
            if op_tok == "!":
                return IRExpr("NOT", (inner,), None, "BOOL")
            if op_tok == "-":
                return IRExpr("NEG", (inner,))
            if op_tok == "*":
                return IRExpr("DEREF", (inner,))
            if op_tok == "&":
                return IRExpr("ADDR", (inner,))
            return inner
    if t == "update_expression":
        ch = _ts_named(node)
        if ch:
            inner = _lower_ts_expr(ch[0], raw, lang)
            if "++" in txt:
                return IRExpr("ADD", (inner, IRExpr("CONST", (), 1, "INT")))
            if "--" in txt:
                return IRExpr("SUB", (inner, IRExpr("CONST", (), 1, "INT")))
    if t in ("binary_expression",):
        ch = _ts_named(node)
        if len(ch) == 2:
            # Find operator token between ch[0] and ch[1]
            op_s = raw[ch[0].end_byte : ch[1].start_byte].decode("utf-8", errors="replace").strip()
            le = _lower_ts_expr(ch[0], raw, lang)
            re_ = _lower_ts_expr(ch[1], raw, lang)
            cop = _TS_OP_MAP.get(op_s, "BINOP")
            if cop == "EQ" and re_.op == "CONST" and re_.value is None:
                return IRExpr("IS_NULL", (le,), None, "BOOL")
            if cop == "NE" and re_.op == "CONST" and re_.value is None:
                return IRExpr("NOT_NULL", (le,), None, "BOOL")
            if cop == "EQ" and le.op == "CONST" and le.value is None:
                return IRExpr("IS_NULL", (re_,), None, "BOOL")
            if cop == "NE" and le.op == "CONST" and le.value is None:
                return IRExpr("NOT_NULL", (re_,), None, "BOOL")
            return IRExpr(cop, (le, re_))
    if t in ("conditional_expression", "ternary_expression"):
        ch = _ts_named(node)
        if len(ch) == 3:
            return IRExpr("PHI", (_lower_ts_expr(ch[0], raw, lang), _lower_ts_expr(ch[1], raw, lang), _lower_ts_expr(ch[2], raw, lang)))
    if t in ("subscript_expression", "index_expression"):
        ch = _ts_named(node)
        if len(ch) >= 2:
            return IRExpr("INDEX", (_lower_ts_expr(ch[0], raw, lang), _lower_ts_expr(ch[1], raw, lang)))
    if t in ("field_expression", "member_expression", "selector_expression"):
        ch = _ts_named(node)
        if len(ch) >= 2:
            recv = _lower_ts_expr(ch[0], raw, lang)
            fld = _ts_text(ch[-1], raw).strip()
            if fld in ("length",):
                return IRExpr("LEN", (recv,), None, "INT")
            return IRExpr("ATTR", (recv,), fld)
    if t in ("call_expression",):
        ch = _ts_named(node)
        if ch:
            callee_node = ch[0]
            arg_list = ch[1] if len(ch) > 1 else None
            args = tuple(_lower_ts_expr(a, raw, lang) for a in (_ts_named(arg_list) if arg_list else []))
            if callee_node.type in ("field_expression", "member_expression", "selector_expression"):
                fch = _ts_named(callee_node)
                if len(fch) >= 2:
                    recv = _lower_ts_expr(fch[0], raw, lang)
                    mname = _ts_text(fch[-1], raw).strip()
                    if mname in ("len", "size", "length") and len(args) == 0:
                        return IRExpr("LEN", (recv,), None, "INT")
                    if mname == "is_none" and len(args) == 0:
                        return IRExpr("IS_NULL", (recv,), None, "BOOL")
                    if mname == "is_some" and len(args) == 0:
                        return IRExpr("NOT_NULL", (recv,), None, "BOOL")
                    return IRExpr("MCALL", (recv, *args), mname)
            cname = _ts_text(callee_node, raw).strip()
            if cname in ("len", "strlen") and len(args) == 1:
                return IRExpr("LEN", args, None, "INT")
            return IRExpr("CALL", args, cname)
    if t == "cast_expression":
        ch = _ts_named(node)
        if ch:
            return _lower_ts_expr(ch[-1], raw, lang)
    if t == "range_expression":
        ch = _ts_named(node)
        if len(ch) == 2:
            op = "RANGE_INC" if "..=" in txt else "RANGE"
            return IRExpr(op, (_lower_ts_expr(ch[0], raw, lang), _lower_ts_expr(ch[1], raw, lang)))
    if t == "assignment_expression":
        ch = _ts_named(node)
        if len(ch) == 2:
            return _lower_ts_expr(ch[1], raw, lang)
    return IRExpr("UNKNOWN", (), txt)


def _extract_c_ident(node: Any, raw: bytes) -> str:
    if node is None:
        return ""
    if node.type in ("identifier", "field_identifier"):
        return _ts_text(node, raw).strip()
    for c in node.children:
        if c.type in ("identifier", "pointer_declarator", "array_declarator", "function_declarator", "init_declarator"):
            r = _extract_c_ident(c, raw)
            if r:
                return r
    return ""


def _lower_ts_stmts(
    nodes: Sequence[Any],
    raw: bytes,
    lang: str,
    file: str,
    func: str,
    idgen: _IdGen,
) -> list[IRStmt]:
    out: list[IRStmt] = []
    for node in nodes:
        t = node.type
        if t in ("comment", "{", "}", ";"):
            continue
        ln = node.start_point[0] + 1
        end_ln = node.end_point[0] + 1
        stxt = _ts_text(node, raw)

        if t in ("compound_statement", "statement_block", "block"):
            out.extend(_lower_ts_stmts(_ts_named(node), raw, lang, file, func, idgen))
            continue

        # Variable declarations: C `int x = 0;`, JS `let x = 0;`, Rust `let mut x = 0;`, Go `x := 0`
        if t in ("declaration", "lexical_declaration", "variable_declaration", "let_declaration", "short_var_declaration"):
            if t == "short_var_declaration":
                ch = _ts_named(node)
                if len(ch) >= 2:
                    lhs = _ts_text(ch[0], raw).strip()
                    rhs = _lower_ts_expr(ch[1], raw, lang)
                    out.append(IRStmt(
                        idgen.next(), "ASSIGN", ln, end_ln, file, func,
                        target=lhs, expr=rhs, defs=(lhs,), uses=tuple(sorted(rhs.free_vars())),
                        attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                    ))
                continue
            if t == "let_declaration":
                ch = _ts_named(node)
                pat = next((c for c in ch if c.type == "identifier"), None)
                val_n = ch[-1] if len(ch) >= 2 else None
                if pat is not None and val_n is not None and val_n is not pat:
                    lhs = _ts_text(pat, raw).strip()
                    rhs = _lower_ts_expr(val_n, raw, lang)
                    out.append(IRStmt(
                        idgen.next(), "ASSIGN", ln, end_ln, file, func,
                        target=lhs, expr=rhs, defs=(lhs,), uses=tuple(sorted(rhs.free_vars())),
                        attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                    ))
                continue
            for decl in _ts_named(node):
                if decl.type in ("init_declarator", "variable_declarator"):
                    dch = _ts_named(decl)
                    if len(dch) >= 2:
                        lhs = _extract_c_ident(dch[0], raw)
                        rhs = _lower_ts_expr(dch[-1], raw, lang)
                        if lhs:
                            out.append(IRStmt(
                                idgen.next(), "ASSIGN", ln, end_ln, file, func,
                                target=lhs, expr=rhs, defs=(lhs,), uses=tuple(sorted(rhs.free_vars())),
                                attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                            ))
            continue

        if t == "expression_statement":
            ch = _ts_named(node)
            if not ch:
                continue
            inner = ch[0]
            it = inner.type
            if it in ("for_expression", "if_expression", "while_expression", "return_expression", "return_statement"):
                out.extend(_lower_ts_stmts([inner], raw, lang, file, func, idgen))
                continue
            if it in ("assignment_expression", "augmented_assignment_expression", "compound_assignment_expr"):
                ach = _ts_named(inner)
                if len(ach) == 2:
                    op_s = raw[ach[0].end_byte : ach[1].start_byte].decode("utf-8", errors="replace").strip()
                    rhs = _lower_ts_expr(ach[1], raw, lang)
                    lhs_node = ach[0]
                    if op_s in ("+=", "-=", "*=", "/="):
                        aug = {"+=": "ADD", "-=": "SUB", "*=": "MUL", "/=": "DIV"}[op_s]
                        tname = _ts_text(lhs_node, raw).strip()
                        out.append(IRStmt(
                            idgen.next(), "AUG_ASSIGN", ln, end_ln, file, func,
                            target=tname, aug_op=aug, expr=rhs,
                            defs=(tname,), uses=tuple(sorted(rhs.free_vars() | {tname})),
                            attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                        ))
                    elif lhs_node.type in ("field_expression", "member_expression", "selector_expression"):
                        fch = _ts_named(lhs_node)
                        base = _lower_ts_expr(fch[0], raw, lang) if fch else IRExpr("VAR", (), "*")
                        fld = _ts_text(fch[-1], raw).strip() if len(fch) >= 2 else ""
                        bname = str(base.value) if base.op == "VAR" else "*"
                        out.append(IRStmt(
                            idgen.next(), "STORE_ATTR", ln, end_ln, file, func,
                            target=bname, target_attr=fld, expr=rhs,
                            uses=tuple(sorted(rhs.free_vars() | base.free_vars())),
                            attr_writes=((bname, fld),), attr_reads=tuple(sorted(rhs.attr_reads())),
                            source_text=stxt,
                        ))
                    elif lhs_node.type in ("subscript_expression", "index_expression"):
                        sch = _ts_named(lhs_node)
                        base = _lower_ts_expr(sch[0], raw, lang)
                        idx = _lower_ts_expr(sch[1], raw, lang)
                        bname = str(base.value) if base.op == "VAR" else "*"
                        out.append(IRStmt(
                            idgen.next(), "STORE_INDEX", ln, end_ln, file, func,
                            target=bname, target_index=idx, expr=rhs,
                            defs=(bname,) if bname != "*" else (),
                            uses=tuple(sorted(rhs.free_vars() | base.free_vars() | idx.free_vars())),
                            attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                        ))
                    else:
                        tname = _ts_text(lhs_node, raw).strip()
                        out.append(IRStmt(
                            idgen.next(), "ASSIGN", ln, end_ln, file, func,
                            target=tname, expr=rhs, defs=(tname,), uses=tuple(sorted(rhs.free_vars())),
                            attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
                        ))
                continue
            if it == "update_expression":
                uch = _ts_named(inner)
                if uch:
                    tname = _ts_text(uch[0], raw).strip()
                    aug = "ADD" if "++" in _ts_text(inner, raw) else "SUB"
                    out.append(IRStmt(
                        idgen.next(), "AUG_ASSIGN", ln, end_ln, file, func,
                        target=tname, aug_op=aug, expr=IRExpr("CONST", (), 1, "INT"),
                        defs=(tname,), uses=(tname,), source_text=stxt,
                    ))
                continue
            e = _lower_ts_expr(inner, raw, lang)
            out.append(IRStmt(
                idgen.next(), "CALL_STMT", ln, end_ln, file, func,
                expr=e, uses=tuple(sorted(e.free_vars())),
                attr_reads=tuple(sorted(e.attr_reads())), source_text=stxt,
            ))
            continue

        if t in ("return_statement", "return_expression"):
            ch = _ts_named(node)
            rhs = _lower_ts_expr(ch[0], raw, lang) if ch else IRExpr("CONST", (), None, "NULL")
            out.append(IRStmt(
                idgen.next(), "RETURN", ln, end_ln, file, func,
                expr=rhs, uses=tuple(sorted(rhs.free_vars())),
                attr_reads=tuple(sorted(rhs.attr_reads())), source_text=stxt,
            ))
            continue

        if t in ("if_statement", "if_expression"):
            ch = _ts_named(node)
            if len(ch) >= 2:
                cond = _lower_ts_expr(ch[0], raw, lang)
                tb = _lower_ts_stmts([ch[1]], raw, lang, file, func, idgen)
                eb: list[IRStmt] = []
                if len(ch) >= 3:
                    else_n = ch[2]
                    if else_n.type == "else_clause":
                        eb = _lower_ts_stmts(_ts_named(else_n), raw, lang, file, func, idgen)
                    else:
                        eb = _lower_ts_stmts([else_n], raw, lang, file, func, idgen)
                kind = "GUARD" if (not eb and len(tb) == 1 and tb[0].kind in ("RETURN", "RAISE")) else "BRANCH"
                out.append(IRStmt(
                    idgen.next(), kind, ln, end_ln, file, func,
                    expr=cond, then_body=tb, else_body=eb,
                    uses=tuple(sorted(cond.free_vars())),
                    attr_reads=tuple(sorted(cond.attr_reads())), source_text=stxt,
                ))
            continue

        if t in ("while_statement", "while_expression"):
            ch = _ts_named(node)
            if len(ch) >= 2:
                cond = _lower_ts_expr(ch[0], raw, lang)
                body = _lower_ts_stmts([ch[1]], raw, lang, file, func, idgen)
                spec = _canonicalize_while_to_loop(out, cond, body, source_form=f"while_{lang}")
                out.append(IRStmt(
                    idgen.next(), "LOOP", ln, end_ln, file, func,
                    target=spec.iv, expr=cond, loop=spec,
                    defs=(spec.iv,) if spec.iv else (),
                    uses=tuple(sorted(cond.free_vars())),
                    attr_reads=tuple(sorted(cond.attr_reads())), source_text=stxt,
                ))
            continue

        if t in ("for_statement", "for_expression"):
            # Unify C/C++/JS/Go/Rust `for` loops into canonical LoopSpec!
            ch = _ts_named(node)
            if lang == "rust" and t == "for_expression" and len(ch) >= 3:
                iv = _ts_text(ch[0], raw).strip()
                rng = _lower_ts_expr(ch[1], raw, lang)
                body = _lower_ts_stmts([ch[-1]], raw, lang, file, func, idgen)
                if rng.op in ("RANGE", "RANGE_INC") and len(rng.args) == 2:
                    spec = LoopSpec(
                        loop_kind="INDEXED_SCAN",
                        iv=iv,
                        init_expr=rng.args[0],
                        bound_expr=rng.args[1],
                        inclusive=(rng.op == "RANGE_INC"),
                        step_expr=IRExpr("CONST", (), 1, "INT"),
                        seq_expr=_infer_indexed_seq(body, iv),
                        body=body,
                        source_form="for_rust",
                    )
                else:
                    spec = LoopSpec(
                        loop_kind="SEQ_ITER",
                        iv=iv,
                        init_expr=IRExpr("CONST", (), 0, "INT"),
                        bound_expr=IRExpr("LEN", (rng,), None, "INT"),
                        inclusive=False,
                        step_expr=IRExpr("CONST", (), 1, "INT"),
                        seq_expr=rng,
                        body=body,
                        source_form="for_rust",
                    )
                out.append(IRStmt(
                    idgen.next(), "LOOP", ln, end_ln, file, func,
                    target=iv, expr=rng, loop=spec, defs=(iv,),
                    uses=tuple(sorted(rng.free_vars())), source_text=stxt,
                ))
                continue

            # C / C++ / JS / Go 3-clause for loop
            init_n = node.child_by_field_name("initializer")
            cond_n = node.child_by_field_name("condition")
            upd_n = node.child_by_field_name("update") or node.child_by_field_name("increment")
            body_n = node.child_by_field_name("body") or (ch[-1] if ch else None)

            # Go `for_clause` wraps initializer/condition/update
            if lang == "go":
                fc = next((c for c in ch if c.type == "for_clause"), None)
                if fc is not None:
                    init_n = fc.child_by_field_name("initializer")
                    cond_n = fc.child_by_field_name("condition")
                    upd_n = fc.child_by_field_name("update")

            init_stmts = _lower_ts_stmts([init_n], raw, lang, file, func, idgen) if init_n else []
            iv = init_stmts[0].target if init_stmts else ""
            init_expr = init_stmts[0].expr if init_stmts else IRExpr("CONST", (), 0, "INT")
            cond = _lower_ts_expr(cond_n, raw, lang) if cond_n else IRExpr("CONST", (), True, "BOOL")
            body = _lower_ts_stmts([body_n], raw, lang, file, func, idgen) if body_n else []

            bound_expr: IRExpr | None = None
            inclusive = False
            if cond.op in ("LT", "LE") and len(cond.args) == 2 and cond.args[0].op == "VAR":
                iv = iv or str(cond.args[0].value)
                bound_expr = cond.args[1]
                inclusive = cond.op == "LE"
            elif cond.op in ("GT", "GE") and len(cond.args) == 2 and cond.args[1].op == "VAR":
                iv = iv or str(cond.args[1].value)
                bound_expr = cond.args[0]
                inclusive = cond.op == "GE"

            step_expr = IRExpr("CONST", (), 1, "INT")
            if upd_n is not None:
                utxt = _ts_text(upd_n, raw)
                if "--" in utxt or "-=" in utxt:
                    step_expr = IRExpr("CONST", (), -1, "INT")

            # Normalize pointer-scan C `for (int *p = arr; p < arr + n; p++)` too!
            if (
                init_expr is not None
                and init_expr.op == "VAR"
                and bound_expr is not None
                and bound_expr.op == "ADD"
                and len(bound_expr.args) == 2
                and bound_expr.args[0] == init_expr
            ):
                seq_e = init_expr
                bound_expr = bound_expr.args[1]
                init_expr = IRExpr("CONST", (), 0, "INT")
                body = [_rewrite_ptr_deref_stmt(bs, iv, seq_e) for bs in body]
            else:
                seq_e = _infer_indexed_seq(body, iv)

            spec = LoopSpec(
                loop_kind="INDEXED_SCAN" if bound_expr is not None else "WHILE_COND",
                iv=iv,
                init_expr=init_expr,
                bound_expr=bound_expr,
                inclusive=inclusive,
                step_expr=step_expr,
                seq_expr=seq_e,
                cond_expr=cond,
                body=body,
                source_form=f"for_{lang}",
            )
            out.append(IRStmt(
                idgen.next(), "LOOP", ln, end_ln, file, func,
                target=iv, expr=cond, loop=spec,
                defs=(iv,) if iv else (),
                uses=tuple(sorted(cond.free_vars() | (init_expr.free_vars() if init_expr else set()))),
                source_text=stxt,
            ))
            continue

        if t in ("inc_statement", "dec_statement"):
            ch = _ts_named(node)
            if ch:
                tname = _ts_text(ch[0], raw).strip()
                aug = "ADD" if t == "inc_statement" else "SUB"
                out.append(IRStmt(
                    idgen.next(), "AUG_ASSIGN", ln, end_ln, file, func,
                    target=tname, aug_op=aug, expr=IRExpr("CONST", (), 1, "INT"),
                    defs=(tname,), uses=(tname,), source_text=stxt,
                ))
            continue

        if t == "assignment_statement":  # Go
            ch = _ts_named(node)
            if len(ch) == 2:
                op_s = raw[ch[0].end_byte : ch[1].start_byte].decode("utf-8", errors="replace").strip()
                tname = _ts_text(ch[0], raw).strip()
                rhs = _lower_ts_expr(ch[1], raw, lang)
                if op_s in ("+=", "-=", "*=", "/="):
                    aug = {"+=": "ADD", "-=": "SUB", "*=": "MUL", "/=": "DIV"}[op_s]
                    out.append(IRStmt(
                        idgen.next(), "AUG_ASSIGN", ln, end_ln, file, func,
                        target=tname, aug_op=aug, expr=rhs,
                        defs=(tname,), uses=tuple(sorted(rhs.free_vars() | {tname})), source_text=stxt,
                    ))
                else:
                    out.append(IRStmt(
                        idgen.next(), "ASSIGN", ln, end_ln, file, func,
                        target=tname, expr=rhs, defs=(tname,), uses=tuple(sorted(rhs.free_vars())), source_text=stxt,
                    ))
            continue

    return out


def _extract_ts_params(param_list: Any, raw: bytes, lang: str) -> tuple[str, ...]:
    if param_list is None:
        return ()
    params: list[str] = []
    for p in _ts_named(param_list):
        if p.type == "identifier":
            params.append(_ts_text(p, raw).strip())
        elif p.type in ("parameter_declaration", "parameter", "required_parameter", "formal_parameter"):
            if lang == "rust":
                ident = next((c for c in _ts_named(p) if c.type == "identifier"), None)
                if ident:
                    params.append(_ts_text(ident, raw).strip())
            elif lang == "go":
                idents = [c for c in _ts_named(p) if c.type == "identifier"]
                for ident in idents:
                    params.append(_ts_text(ident, raw).strip())
            else:
                name = _extract_c_ident(p, raw)
                if name:
                    params.append(name)
    return tuple(params)


def lower_polyglot_module(source: str, file: str, language: str) -> IRModule:
    lang = detect_language(language or file)
    if lang == "python":
        return lower_python_module(source, file)
    if _ts_get_parser is None:
        return _lower_c_family_fallback(source, file, lang)

    ts_lang = "c" if lang == "c" else lang
    parser = _ts_get_parser(ts_lang)
    raw = source.encode("utf-8", errors="replace")
    tree = parser.parse(raw)
    idgen = _IdGen()
    imports: list[str] = []
    funcs: list[IRFunction] = []

    def _walk(node: Any) -> None:
        t = node.type
        if t in ("preproc_include", "import_statement", "import_declaration", "use_declaration"):
            imports.append(_ts_text(node, raw).strip())
            return
        if t in ("function_definition", "function_declaration", "function_item", "method_definition"):
            ln = node.start_point[0] + 1
            end_ln = node.end_point[0] + 1
            name = ""
            params: tuple[str, ...] = ()
            body_n = node.child_by_field_name("body")
            if t == "function_definition" and lang in ("c", "cpp"):
                decl = node.child_by_field_name("declarator")
                if decl is not None:
                    # Unwrap pointer declarator around function_declarator
                    cur = decl
                    while cur is not None and cur.type != "function_declarator":
                        nxt = next((c for c in cur.children if c.type in ("function_declarator", "pointer_declarator")), None)
                        if nxt is None:
                            break
                        cur = nxt
                    if cur is not None and cur.type == "function_declarator":
                        name_n = cur.child_by_field_name("declarator")
                        name = _extract_c_ident(name_n, raw)
                        params = _extract_ts_params(cur.child_by_field_name("parameters"), raw, lang)
            else:
                name_n = node.child_by_field_name("name")
                name = _ts_text(name_n, raw).strip() if name_n is not None else ""
                params = _extract_ts_params(node.child_by_field_name("parameters"), raw, lang)
            if name and body_n is not None:
                stmts = _lower_ts_stmts([body_n], raw, lang, file, name, idgen)
                funcs.append(IRFunction(name, name, file, lang, params, ln, end_ln, stmts, _ts_text(node, raw)))
            return
        for c in node.children:
            _walk(c)

    _walk(tree.root_node)
    return IRModule(file=file, language=lang, imports=tuple(imports), functions=funcs, source_text=source)


def _lower_c_family_fallback(source: str, file: str, lang: str) -> IRModule:
    """Minimal pure-Python fallback if tree-sitter is absent: extracts functions & loops."""
    idgen = _IdGen()
    funcs: list[IRFunction] = []
    fn_re = re.compile(r"(?:function|fn|func|[A-Za-z_][\w\s\*]+?)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{")
    for m in fn_re.finditer(source):
        name = m.group(1)
        if name in ("if", "for", "while", "switch"):
            continue
        raw_params = [p.strip().split()[-1].lstrip("*&") for p in m.group(2).split(",") if p.strip()]
        ln = source[: m.start()].count("\n") + 1
        funcs.append(IRFunction(name, name, file, lang, tuple(raw_params), ln, ln, [], m.group(0)))
    return IRModule(file=file, language=lang, functions=funcs, source_text=source)


def lower_program(files: Mapping[str, str], languages: Mapping[str, str] | None = None) -> IRProgram:
    """Lower a multi-file, possibly polyglot repository snapshot into one unified IRProgram."""
    prog = IRProgram()
    langs = languages or {}
    for rel, src in files.items():
        lang = langs.get(rel) or detect_language(rel)
        try:
            prog.modules[rel] = lower_polyglot_module(src, rel, lang)
        except SyntaxError:
            continue
    return prog


# ---------------------------------------------------------------------------
# 6. Canonical Semantic Fingerprinting & Cross-Language Equivalence Check
# ---------------------------------------------------------------------------

def _canonicalize_ir_expr(expr: IRExpr, alpha: dict[str, str], counter: list[int]) -> IRExpr:
    if expr.op == "VAR" and isinstance(expr.value, str):
        if expr.value not in alpha:
            alpha[expr.value] = f"$v{counter[0]}"
            counter[0] += 1
        return IRExpr("VAR", (), alpha[expr.value], expr.ty)
    # Normalize binary comparison direction (GT -> LT, GE -> LE) & commutative ordering
    args = tuple(_canonicalize_ir_expr(a, alpha, counter) for a in expr.args)
    op = expr.op
    if op == "GT" and len(args) == 2:
        op, args = "LT", (args[1], args[0])
    elif op == "GE" and len(args) == 2:
        op, args = "LE", (args[1], args[0])
    elif op == "NOT" and len(args) == 1:
        inner = args[0]
        flip = {"LT": "LE", "LE": "LT", "EQ": "NE", "NE": "EQ", "IS_NULL": "NOT_NULL", "NOT_NULL": "IS_NULL"}
        if inner.op == "NOT" and len(inner.args) == 1:
            return inner.args[0]
        if inner.op == "LT" and len(inner.args) == 2:
            return IRExpr("LE", (inner.args[1], inner.args[0]), None, "BOOL")
        if inner.op == "LE" and len(inner.args) == 2:
            return IRExpr("LT", (inner.args[1], inner.args[0]), None, "BOOL")
        if inner.op in ("EQ", "NE", "IS_NULL", "NOT_NULL"):
            return IRExpr(flip[inner.op], inner.args, None, "BOOL")
    # Normalize `i < n + 1` -> `i <= n` and `i <= n - 1` -> `i < n`
    if op == "LT" and len(args) == 2 and args[1].op == "ADD" and len(args[1].args) == 2:
        if args[1].args[1] == IRExpr("CONST", (), 1, "INT"):
            return IRExpr("LE", (args[0], args[1].args[0]), None, "BOOL")
        if args[1].args[0] == IRExpr("CONST", (), 1, "INT"):
            return IRExpr("LE", (args[0], args[1].args[1]), None, "BOOL")
    if op == "LE" and len(args) == 2 and args[1].op == "SUB" and len(args[1].args) == 2:
        if args[1].args[1] == IRExpr("CONST", (), 1, "INT"):
            return IRExpr("LT", (args[0], args[1].args[0]), None, "BOOL")
    if op in ("ADD", "MUL", "EQ", "NE", "AND", "OR") and len(args) == 2:
        if args[0].pretty() > args[1].pretty():
            args = (args[1], args[0])
    return IRExpr(op, args, expr.value, expr.ty)


def canonical_function_signature(fn: IRFunction) -> dict[str, Any]:
    """Compute alpha-renamed, loop-normalized, E-Graph-canonical semantic signature of a function."""
    alpha: dict[str, str] = {}
    for idx, p in enumerate(fn.params):
        alpha[p] = f"$p{idx}"
    counter = [0]

    def _canon_stmts(stmts: Sequence[IRStmt], skip_loop_inits: set[str]) -> list[Any]:
        res: list[Any] = []
        # Collect induction vars of loops that consumed a prior init assignment (`while_idx`/`while_ptr`)
        loop_iv_inits: set[str] = set()
        for st in stmts:
            if st.kind == "LOOP" and st.loop and st.loop.loop_kind == "INDEXED_SCAN" and st.loop.source_form.startswith("while"):
                if st.loop.iv:
                    loop_iv_inits.add(st.loop.iv)

        for st in stmts:
            if st.kind == "ASSIGN" and st.target in loop_iv_inits:
                # Init was absorbed into LoopSpec.init_expr!
                continue
            if st.kind == "ASSIGN":
                rhs = _canonicalize_ir_expr(st.expr, alpha, counter) if st.expr else None
                if st.target not in alpha:
                    alpha[st.target] = f"$v{counter[0]}"
                    counter[0] += 1
                res.append(("ASSIGN", alpha[st.target], rhs.pretty() if rhs else ""))
            elif st.kind == "AUG_ASSIGN":
                if st.target not in alpha:
                    alpha[st.target] = f"$v{counter[0]}"
                    counter[0] += 1
                rhs = _canonicalize_ir_expr(st.expr, alpha, counter) if st.expr else None
                res.append(("AUG", alpha[st.target], st.aug_op, rhs.pretty() if rhs else ""))
            elif st.kind == "RETURN":
                rhs = _canonicalize_ir_expr(st.expr, alpha, counter) if st.expr else None
                res.append(("RETURN", rhs.pretty() if rhs else ""))
            elif st.kind in ("BRANCH", "GUARD"):
                cond = _canonicalize_ir_expr(st.expr, alpha, counter) if st.expr else None
                res.append((
                    st.kind,
                    cond.pretty() if cond else "",
                    _canon_stmts(st.then_body, set()),
                    _canon_stmts(st.else_body, set()),
                ))
            elif st.kind == "LOOP" and st.loop is not None:
                lp = st.loop
                if lp.iv and lp.iv not in alpha:
                    alpha[lp.iv] = f"$iv{counter[0]}"
                    counter[0] += 1
                iv_c = alpha.get(lp.iv, "$iv")
                init_c = _canonicalize_ir_expr(lp.init_expr, alpha, counter).pretty() if lp.init_expr else ""
                bound_c = _canonicalize_ir_expr(lp.bound_expr, alpha, counter).pretty() if lp.bound_expr else ""
                # Canonicalize C `n` vs Python `LEN(arr)` when param count matches `(arr, n)` vs `(arr)`
                step_c = _canonicalize_ir_expr(lp.step_expr, alpha, counter).pretty() if lp.step_expr else ""
                body_c = _canon_stmts(lp.body, set())
                res.append((
                    "LOOP",
                    lp.loop_kind,
                    iv_c,
                    init_c,
                    bound_c,
                    bool(lp.inclusive),
                    step_c,
                    body_c,
                ))
            elif st.kind == "STORE_INDEX":
                if st.target not in alpha:
                    alpha[st.target] = f"$v{counter[0]}"
                    counter[0] += 1
                idx_c = _canonicalize_ir_expr(st.target_index, alpha, counter).pretty() if st.target_index else ""
                rhs_c = _canonicalize_ir_expr(st.expr, alpha, counter).pretty() if st.expr else ""
                res.append(("STORE_INDEX", alpha[st.target], idx_c, rhs_c))
        return res

    body_sig = _canon_stmts(fn.stmts, set())
    digest = hashlib.sha256(repr(body_sig).encode("utf-8")).hexdigest()[:16]
    return {
        "schema": SCHEMA,
        "arity": len(fn.params),
        "canonical_body": body_sig,
        "semantic_hash": digest,
        "language": fn.language,
    }


def functions_semantically_equivalent(fn_a: IRFunction, fn_b: IRFunction) -> tuple[bool, dict[str, Any]]:
    """Determine if two functions (potentially in DIFFERENT languages & loop shapes!) are semantically equivalent."""
    sig_a = canonical_function_signature(fn_a)
    sig_b = canonical_function_signature(fn_b)
    if sig_a["semantic_hash"] == sig_b["semantic_hash"]:
        return True, {"reason": "CANONICAL_IR_ISOMORPHISM", "sig_a": sig_a, "sig_b": sig_b}

    # Secondary check: unify `(arr, n)` explicit-length C/Go loops with `(arr)` implicit-LEN Python/JS/Rust loops!
    body_a = repr(sig_a["canonical_body"])
    body_b = repr(sig_b["canonical_body"])
    norm_a = body_a.replace("LEN($p0)", "$p1")
    norm_b = body_b.replace("LEN($p0)", "$p1")
    if norm_a == norm_b:
        return True, {"reason": "CANONICAL_IR_LEN_PARAM_EQUIVALENCE", "sig_a": sig_a, "sig_b": sig_b}

    return False, {"reason": "SEMANTICALLY_DISTINCT", "sig_a": sig_a, "sig_b": sig_b}


# ---------------------------------------------------------------------------
# 7. Native Multi-Language Emitter from Universal SemanticIR
# ---------------------------------------------------------------------------

def emit_expr(expr: IRExpr, lang: str) -> str:
    """Emit native target-language source expression from a Universal IRExpr."""
    lang = detect_language(lang)
    op = expr.op
    if op == "CONST":
        v = expr.value
        if v is None:
            return {"python": "None", "c": "NULL", "cpp": "nullptr", "javascript": "null", "typescript": "null", "go": "nil", "rust": "None"}[lang]
        if isinstance(v, bool):
            return ("True" if v else "False") if lang == "python" else ("true" if v else "false")
        if isinstance(v, str):
            return repr(v) if lang == "python" else f'"{v}"'
        return str(v)
    if op == "VAR":
        return str(expr.value)
    if op == "LEN" and len(expr.args) == 1:
        a = emit_expr(expr.args[0], lang)
        if lang in ("python", "go"):
            return f"len({a})"
        if lang in ("javascript", "typescript"):
            return f"{a}.length"
        if lang == "rust":
            return f"{a}.len()"
        if lang == "cpp":
            return f"{a}.size()"
        return f"strlen({a})"
    if op == "IS_NULL" and len(expr.args) == 1:
        a = emit_expr(expr.args[0], lang)
        return {
            "python": f"({a} is None)",
            "c": f"({a} == NULL)",
            "cpp": f"({a} == nullptr)",
            "javascript": f"({a} === null || {a} === undefined)",
            "typescript": f"({a} === null || {a} === undefined)",
            "go": f"({a} == nil)",
            "rust": f"{a}.is_none()",
        }[lang]
    if op == "NOT_NULL" and len(expr.args) == 1:
        a = emit_expr(expr.args[0], lang)
        return {
            "python": f"({a} is not None)",
            "c": f"({a} != NULL)",
            "cpp": f"({a} != nullptr)",
            "javascript": f"({a} !== null && {a} !== undefined)",
            "typescript": f"({a} !== null && {a} !== undefined)",
            "go": f"({a} != nil)",
            "rust": f"{a}.is_some()",
        }[lang]
    if op == "NOT" and len(expr.args) == 1:
        a = emit_expr(expr.args[0], lang)
        return f"(not {a})" if lang == "python" else f"(!{a})"
    if op == "NEG" and len(expr.args) == 1:
        return f"(-{emit_expr(expr.args[0], lang)})"
    if op == "ATTR" and len(expr.args) == 1:
        sep = "->" if lang == "c" else "."
        return f"{emit_expr(expr.args[0], lang)}{sep}{expr.value}"
    if op == "INDEX" and len(expr.args) == 2:
        return f"{emit_expr(expr.args[0], lang)}[{emit_expr(expr.args[1], lang)}]"
    if op == "CALL":
        args_s = ", ".join(emit_expr(a, lang) for a in expr.args)
        return f"{expr.value}({args_s})"
    if op == "MCALL" and expr.args:
        recv = emit_expr(expr.args[0], lang)
        args_s = ", ".join(emit_expr(a, lang) for a in expr.args[1:])
        return f"{recv}.{expr.value}({args_s})"
    if op == "PHI" and len(expr.args) == 3:
        c, t, e = (emit_expr(a, lang) for a in expr.args)
        if lang == "python":
            return f"({t} if {c} else {e})"
        if lang == "rust":
            return f"(if {c} {{ {t} }} else {{ {e} }})"
        return f"({c} ? {t} : {e})"
    bin_sym = {
        "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "IDIV": "//" if lang == "python" else "/",
        "MOD": "%", "EQ": "==" if lang != "javascript" else "===", "NE": "!=" if lang != "javascript" else "!==",
        "LT": "<", "LE": "<=", "GT": ">", "GE": ">=",
        "AND": "and" if lang == "python" else "&&",
        "OR": "or" if lang == "python" else "||",
        "IN": "in", "NOT_IN": "not in",
        "BITAND": "&", "BITOR": "|", "BITXOR": "^", "SHL": "<<", "SHR": ">>",
    }
    if op in bin_sym and len(expr.args) == 2:
        return f"({emit_expr(expr.args[0], lang)} {bin_sym[op]} {emit_expr(expr.args[1], lang)})"
    return expr.pretty()
