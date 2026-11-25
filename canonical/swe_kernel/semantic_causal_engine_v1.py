#!/usr/bin/env python3
"""Semantic-Causal Program Understanding, Universal Meaning E-Graph & Angelic CEGIS Engine.

Implements the four architectural leaps from local syntax skeletons to first-principles
semantic and causal program understanding with zero external model calls ($0, K3 = 0)
and zero memorized world-knowledge weights:

  1. Polyglot Code Property Graph (CPG) & Cross-File Causal Data-Flow Lineage:
     Builds AST + Control-Flow Guards (CFG) + Intra/Inter-Procedural Def-Use Data-Flow
     Edges (DFG) across multi-file projects in Python, C, C++, JavaScript/TypeScript,
     Rust, and Go. Traces backward value provenance from crash/symptom sites in
     consumer files to root-cause definitions and guards in upstream producer files.

  2. Universal Semantic Meaning IR (UIR) + Equality-Saturated E-Graph (egg algorithm):
     Lowers syntactically distinct constructs across languages and styles -- e.g.
     `for (int i = 0; i <= n; i++)`, `while (ptr <= base + n)`, `for i in range(n + 1)`,
     `while idx <= len(xs):`, early-return guards vs ternary/if-else branches, and
     truthiness coercion vs explicit nullability -- into one canonical Universal IR.
     Uses deferred-rebuild congruence closure + e-matching equality saturation so
     semantically equivalent programs collapse into the same e-class regardless of
     spelling or language.

  3. Goal-Directed Invention via Angelic Abduction + Z3 SMT & Observational STUN CEGIS:
     Infers frame-local angelic specifications {(sigma_k -> v_k*)} at upstream causal
     sites across files without requiring outer test assertions to share the internal
     site's type. Synthesizes new expressions, multi-branch guards, loop-bound/step
     repairs, state initializations, and cross-module helper calls over the project's
     CPG symbol vocabulary (never laundering test literals), using Z3 SMT + boundary
     counterexample generation to prove safety and termination.

  4. Fast Dual-Speed Verification & Quotiented Causal Law Store:
     Evaluates angelic probes in microseconds/milliseconds via in-memory Python AST
     code objects, single-compile `/dev/shm` C/C++ ASan/UBSan hooks, and Node runners,
     then verifies clean patches against full project suites. Crystallizes generalized,
     path-free, variable-name-free UIR causal laws deduplicated modulo e-graph equality.

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Stored world facts: 0.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
from dataclasses import dataclass, field
import hashlib
import itertools
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tree_sitter_swe_kernel_v1 as tsk  # noqa: E402

try:
    import z3  # type: ignore
    _HAS_Z3 = True
except Exception:  # pragma: no cover
    z3 = None  # type: ignore
    _HAS_Z3 = False

SCHEMA = "PROJECT_BRAIN_SEMANTIC_CAUSAL_ENGINE_V1"
LAW_STORE_SCHEMA = "PROJECT_BRAIN_UIR_CAUSAL_LAW_STORE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

SUPPORTED_LANGUAGES = ("python", "c", "cpp", "javascript", "typescript", "rust", "go")


# =========================================================================== #
# 1. Universal Semantic IR (UIR) + Deferred-Rebuild Equality Saturation (egg) #
# =========================================================================== #

@dataclass(frozen=True)
class UIRTerm:
    """Language-neutral semantic tree node.

    Operators represent computational MEANING rather than surface spelling:
      - Leaves: VAR(slot), CONST_INT(n), CONST_BOOL(b), CONST_STR(s), NULL_VAL()
      - Arithmetic: ADD, SUB, MUL, DIV, MOD, NEG
      - Logic & Comparison: AND, OR, NOT, LT, LE, EQ, NE
      - Nullability vs Truthiness: IS_NULL(x), NOT_NULL(x), TRUTHY(x)
      - Memory / Containers: CAPACITY(seq), INDEX(seq, idx), DEREF(ptr),
                             FIELD(obj, name), CONTAINS(seq, item)
      - Control & State: ITER_RANGE(idx_slot, start, excl_bound, step, body),
                         GUARD(cond, then_term, else_term),
                         ASSIGN(slot, val), RETURN(val), SEQ(items...),
                         CLAMP(val, lo, hi), CALL_FN(name, args...)
    """
    op: str
    args: tuple[Any, ...] = ()

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "args": [a.canonical_dict() if isinstance(a, UIRTerm) else a for a in self.args],
        }

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "UIRTerm":
        return UIRTerm(
            op=str(d["op"]),
            args=tuple(
                UIRTerm.from_dict(x) if isinstance(x, Mapping) and "op" in x else x
                for x in (d.get("args") or ())
            ),
        )

    def digest(self) -> str:
        blob = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def u_var(slot: str) -> UIRTerm:
    return UIRTerm("VAR", (slot,))


def u_int(val: int) -> UIRTerm:
    return UIRTerm("CONST_INT", (int(val),))


def u_bool(val: bool) -> UIRTerm:
    return UIRTerm("CONST_BOOL", (bool(val),))


def u_str(val: str) -> UIRTerm:
    return UIRTerm("CONST_STR", (str(val),))


def u_null() -> UIRTerm:
    return UIRTerm("NULL_VAL", ())


@dataclass(frozen=True)
class PVar:
    """Pattern hole variable `?x` for e-graph matching and UIR anti-unification."""
    name: str


@dataclass(frozen=True)
class PTerm:
    """Pattern term over UIR operators and `PVar` holes."""
    op: str
    args: tuple[Any, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out_args: list[Any] = []
        for a in self.args:
            if isinstance(a, PTerm):
                out_args.append(a.to_dict())
            elif isinstance(a, PVar):
                out_args.append({"pvar": a.name})
            else:
                out_args.append(a)
        return {"op": self.op, "args": out_args}

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> Any:
        if "pvar" in d:
            return PVar(str(d["pvar"]))
        return PTerm(
            op=str(d["op"]),
            args=tuple(
                PTerm.from_dict(x) if isinstance(x, Mapping) else x
                for x in (d.get("args") or ())
            ),
        )


@dataclass(frozen=True)
class ENode:
    op: str
    children: tuple[int, ...] = ()
    payload: tuple[Any, ...] = ()


@dataclass
class EClass:
    cid: int
    nodes: list[ENode] = field(default_factory=list)
    parents: list[tuple[ENode, int]] = field(default_factory=list)


@dataclass(frozen=True)
class RewriteLaw:
    name: str
    lhs: PTerm
    rhs: PTerm | PVar


class SemanticEGraph:
    """Willsey et al. (POPL 2021) equality-saturation e-graph with deferred rebuild & e-matching."""

    def __init__(self) -> None:
        self.uf: list[int] = []
        self.classes: dict[int, EClass] = {}
        self.memo: dict[ENode, int] = {}
        self.worklist: list[int] = []

    def find(self, cid: int) -> int:
        root = cid
        while self.uf[root] != root:
            root = self.uf[root]
        cur = cid
        while cur != root:
            nxt = self.uf[cur]
            self.uf[cur] = root
            cur = nxt
        return root

    def canonicalize(self, node: ENode) -> ENode:
        if not node.children:
            return node
        return ENode(node.op, tuple(self.find(c) for c in node.children), node.payload)

    def add_node(self, node: ENode) -> int:
        cnode = self.canonicalize(node)
        existing = self.memo.get(cnode)
        if existing is not None:
            return self.find(existing)
        cid = len(self.uf)
        self.uf.append(cid)
        ec = EClass(cid=cid, nodes=[cnode])
        self.classes[cid] = ec
        for ch in cnode.children:
            self.classes[self.find(ch)].parents.append((cnode, cid))
        self.memo[cnode] = cid
        return cid

    def add_term(self, term: UIRTerm) -> int:
        child_ids: list[int] = []
        payload: list[Any] = []
        for arg in term.args:
            if isinstance(arg, UIRTerm):
                child_ids.append(self.add_term(arg))
            else:
                payload.append(arg)
        return self.add_node(ENode(term.op, tuple(child_ids), tuple(payload)))

    def union(self, a: int, b: int) -> int:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        if len(self.classes[ra].parents) < len(self.classes[rb].parents):
            ra, rb = rb, ra
        self.uf[rb] = ra
        ca, cb = self.classes[ra], self.classes[rb]
        ca.nodes.extend(cb.nodes)
        ca.parents.extend(cb.parents)
        del self.classes[rb]
        self.worklist.append(ra)
        return ra

    def rebuild(self) -> None:
        while self.worklist:
            todo = {self.find(c) for c in self.worklist}
            self.worklist.clear()
            for cid in todo:
                self._repair(cid)

    def _repair(self, cid: int) -> None:
        ec = self.classes.get(cid)
        if ec is None:
            return
        for pnode, pclass in ec.parents:
            self.memo.pop(pnode, None)
            cp = self.canonicalize(pnode)
            self.memo[cp] = self.find(pclass)
        dedup_parents: dict[ENode, int] = {}
        for pnode, pclass in ec.parents:
            cp = self.canonicalize(pnode)
            prev = dedup_parents.get(cp)
            if prev is not None:
                self.union(prev, pclass)
            dedup_parents[cp] = self.find(pclass)
        ec.parents = [(n, c) for n, c in dedup_parents.items()]
        seen_nodes: set[ENode] = set()
        uniq_nodes: list[ENode] = []
        for n in ec.nodes:
            cn = self.canonicalize(n)
            if cn not in seen_nodes:
                seen_nodes.add(cn)
                uniq_nodes.append(cn)
        ec.nodes = uniq_nodes

    def _match_pattern_at(self, pat: Any, cid: int, subst: dict[str, int]) -> list[dict[str, int]]:
        cid = self.find(cid)
        if isinstance(pat, PVar):
            bound = subst.get(pat.name)
            if bound is not None:
                return [subst] if self.find(bound) == cid else []
            nxt = dict(subst)
            nxt[pat.name] = cid
            return [nxt]
        if not isinstance(pat, PTerm):
            return []
        ec = self.classes.get(cid)
        if ec is None:
            return []
        child_pats = [a for a in pat.args if isinstance(a, (PTerm, PVar))]
        lit_pats = tuple(a for a in pat.args if not isinstance(a, (PTerm, PVar)))
        results: list[dict[str, int]] = []
        for node in ec.nodes:
            if node.op != pat.op or node.payload != lit_pats or len(node.children) != len(child_pats):
                continue
            cur_substs = [subst]
            for ch_pat, ch_cid in zip(child_pats, node.children):
                next_substs: list[dict[str, int]] = []
                for s in cur_substs:
                    next_substs.extend(self._match_pattern_at(ch_pat, ch_cid, s))
                cur_substs = next_substs
                if not cur_substs:
                    break
            results.extend(cur_substs)
        return results

    def ematch(self, pat: PTerm) -> list[tuple[int, dict[str, int]]]:
        matches: list[tuple[int, dict[str, int]]] = []
        for cid in list(self.classes.keys()):
            rcid = self.find(cid)
            for s in self._match_pattern_at(pat, rcid, {}):
                matches.append((rcid, s))
        return matches

    def instantiate(self, pat: PTerm | PVar, subst: Mapping[str, int]) -> int:
        if isinstance(pat, PVar):
            return self.find(subst[pat.name])
        child_ids: list[int] = []
        payload: list[Any] = []
        for a in pat.args:
            if isinstance(a, (PTerm, PVar)):
                child_ids.append(self.instantiate(a, subst))
            else:
                payload.append(a)
        return self.add_node(ENode(pat.op, tuple(child_ids), tuple(payload)))

    def _fold_constants(self) -> bool:
        """Constant-folding e-class pass so `ADD(CONST_INT(0), CONST_INT(1))` simplifies cleanly."""
        int_val: dict[int, int] = {}
        for cid, ec in list(self.classes.items()):
            for n in ec.nodes:
                if n.op == "CONST_INT" and len(n.payload) == 1 and isinstance(n.payload[0], int):
                    int_val[self.find(cid)] = n.payload[0]
        changed = False
        to_merge: list[tuple[int, UIRTerm]] = []
        for cid, ec in list(self.classes.items()):
            rcid = self.find(cid)
            for n in list(ec.nodes):
                if len(n.children) == 2:
                    a, b = self.find(n.children[0]), self.find(n.children[1])
                    if a in int_val and b in int_val:
                        va, vb = int_val[a], int_val[b]
                        if n.op == "ADD":
                            to_merge.append((rcid, u_int(va + vb)))
                        elif n.op == "SUB":
                            to_merge.append((rcid, u_int(va - vb)))
                        elif n.op == "MUL":
                            to_merge.append((rcid, u_int(va * vb)))
        for target_cid, folded in to_merge:
            fcid = self.add_term(folded)
            if self.find(target_cid) != self.find(fcid):
                self.union(target_cid, fcid)
                changed = True
        return changed

    def saturate(
        self,
        laws: Sequence[RewriteLaw] | None = None,
        *,
        max_iters: int = 6,
        node_limit: int = 3000,
    ) -> int:
        active_laws = laws if laws is not None else UNIVERSAL_SEMANTIC_LAWS
        iters = 0
        for _ in range(max_iters):
            if sum(len(ec.nodes) for ec in self.classes.values()) > node_limit:
                break
            iters += 1
            pending: list[tuple[RewriteLaw, int, dict[str, int]]] = []
            for law in active_laws:
                for cid, subst in self.ematch(law.lhs):
                    pending.append((law, cid, subst))
            merged_any = False
            for law, cid, subst in pending:
                rhs_cid = self.instantiate(law.rhs, subst)
                if self.find(cid) != self.find(rhs_cid):
                    self.union(cid, rhs_cid)
                    merged_any = True
            if self._fold_constants():
                merged_any = True
            self.rebuild()
            if not merged_any:
                break
        return iters

    def extract_canonical(self, root_cid: int) -> UIRTerm:
        """Cost-guided canonical UIR extraction preferring normalized exclusive bounds & flat algebra."""
        op_cost = {
            "VAR": 1, "CONST_INT": 1, "CONST_BOOL": 1, "CONST_STR": 1, "NULL_VAL": 1,
            "CAPACITY": 2, "IS_NULL": 2, "NOT_NULL": 2, "TRUTHY": 3,
            "ADD": 3, "SUB": 3, "MUL": 3, "DIV": 4, "MOD": 4, "NEG": 2,
            "LT": 2, "LE": 4, "EQ": 2, "NE": 2,
            "AND": 3, "OR": 3, "NOT": 3,
            "INDEX": 3, "DEREF": 3, "FIELD": 2, "CONTAINS": 3,
            "ITER_RANGE": 4, "GUARD": 4, "ASSIGN": 3, "RETURN": 2, "SEQ": 2,
            "CLAMP": 3, "CALL_FN": 4,
        }
        best: dict[int, tuple[tuple[int, str], ENode]] = {}
        changed = True
        while changed:
            changed = False
            for cid, ec in self.classes.items():
                rcid = self.find(cid)
                for node in ec.nodes:
                    if any(self.find(ch) not in best for ch in node.children):
                        continue
                    c_sum = op_cost.get(node.op, 5) + sum(best[self.find(ch)][0][0] for ch in node.children)
                    tie = f"{node.op}:{node.payload!r}:" + ",".join(best[self.find(ch)][0][1] for ch in node.children)
                    cand_key = (c_sum, tie)
                    cur = best.get(rcid)
                    if cur is None or cand_key < cur[0]:
                        best[rcid] = (cand_key, node)
                        changed = True

        def _build(cid: int, visiting: frozenset[int]) -> UIRTerm:
            rcid = self.find(cid)
            if rcid in visiting or rcid not in best:
                ec = self.classes[rcid]
                leaf = ec.nodes[0]
                return UIRTerm(leaf.op, leaf.payload)
            _, chosen = best[rcid]
            child_terms = tuple(_build(ch, visiting | {rcid}) for ch in chosen.children)
            return UIRTerm(chosen.op, child_terms + chosen.payload)

        return _build(root_cid, frozenset())


# Pure mathematical & semantic equivalence laws (zero bug-specific heuristics!)
UNIVERSAL_SEMANTIC_LAWS: tuple[RewriteLaw, ...] = (
    # Additive & multiplicative identities + inverse cancellation
    RewriteLaw("add_zero_r", PTerm("ADD", (PVar("?x"), PTerm("CONST_INT", (0,)))), PVar("?x")),
    RewriteLaw("add_zero_l", PTerm("ADD", (PTerm("CONST_INT", (0,)), PVar("?x"))), PVar("?x")),
    RewriteLaw("sub_zero", PTerm("SUB", (PVar("?x"), PTerm("CONST_INT", (0,)))), PVar("?x")),
    RewriteLaw("mul_one_r", PTerm("MUL", (PVar("?x"), PTerm("CONST_INT", (1,)))), PVar("?x")),
    RewriteLaw("mul_one_l", PTerm("MUL", (PTerm("CONST_INT", (1,)), PVar("?x"))), PVar("?x")),
    RewriteLaw("add_sub_cancel", PTerm("SUB", (PTerm("ADD", (PVar("?x"), PVar("?k"))), PVar("?k"))), PVar("?x")),
    RewriteLaw("sub_add_cancel", PTerm("ADD", (PTerm("SUB", (PVar("?x"), PVar("?k"))), PVar("?k"))), PVar("?x")),
    # Commutativity on symmetric operators
    RewriteLaw("add_comm", PTerm("ADD", (PVar("?a"), PVar("?b"))), PTerm("ADD", (PVar("?b"), PVar("?a")))),
    RewriteLaw("eq_comm", PTerm("EQ", (PVar("?a"), PVar("?b"))), PTerm("EQ", (PVar("?b"), PVar("?a")))),
    RewriteLaw("ne_comm", PTerm("NE", (PVar("?a"), PVar("?b"))), PTerm("NE", (PVar("?b"), PVar("?a")))),
    # Integer strict/non-strict bound equivalence: `a <= b` <-> `a < b + 1`
    RewriteLaw(
        "le_to_lt_succ",
        PTerm("LE", (PVar("?a"), PVar("?b"))),
        PTerm("LT", (PVar("?a"), PTerm("ADD", (PVar("?b"), PTerm("CONST_INT", (1,)))))),
    ),
    RewriteLaw(
        "lt_succ_to_le",
        PTerm("LT", (PVar("?a"), PTerm("ADD", (PVar("?b"), PTerm("CONST_INT", (1,)))))),
        PTerm("LE", (PVar("?a"), PVar("?b"))),
    ),
    # Boolean & Nullability equivalences
    RewriteLaw("double_neg", PTerm("NOT", (PTerm("NOT", (PVar("?x"),)),)), PVar("?x")),
    RewriteLaw("not_is_null", PTerm("NOT", (PTerm("IS_NULL", (PVar("?x"),)),)), PTerm("NOT_NULL", (PVar("?x"),))),
    RewriteLaw("not_not_null", PTerm("NOT", (PTerm("NOT_NULL", (PVar("?x"),)),)), PTerm("IS_NULL", (PVar("?x"),))),
    RewriteLaw("eq_null_r", PTerm("EQ", (PVar("?x"), PTerm("NULL_VAL", ()))), PTerm("IS_NULL", (PVar("?x"),))),
    RewriteLaw("ne_null_r", PTerm("NE", (PVar("?x"), PTerm("NULL_VAL", ()))), PTerm("NOT_NULL", (PVar("?x"),))),
    RewriteLaw("not_lt", PTerm("NOT", (PTerm("LT", (PVar("?a"), PVar("?b"))),)), PTerm("LE", (PVar("?b"), PVar("?a")))),
    RewriteLaw("not_le", PTerm("NOT", (PTerm("LE", (PVar("?a"), PVar("?b"))),)), PTerm("LT", (PVar("?b"), PVar("?a")))),
    # Control-flow guard inversion: `if (!c) A else B` == `if (c) B else A`
    RewriteLaw(
        "guard_neg_flip",
        PTerm("GUARD", (PTerm("NOT", (PVar("?c"),)), PVar("?t"), PVar("?e"))),
        PTerm("GUARD", (PVar("?c"), PVar("?e"), PVar("?t"))),
    ),
    RewriteLaw(
        "guard_null_flip",
        PTerm("GUARD", (PTerm("IS_NULL", (PVar("?x"),)), PVar("?t"), PVar("?e"))),
        PTerm("GUARD", (PTerm("NOT_NULL", (PVar("?x"),)), PVar("?e"), PVar("?t"))),
    ),
)


def canonicalize_uir(term: UIRTerm) -> UIRTerm:
    """Saturate `term` in `SemanticEGraph` and extract its canonical semantic normal form."""
    eg = SemanticEGraph()
    root = eg.add_term(term)
    eg.saturate()
    return eg.extract_canonical(root)


def semantically_equivalent(a: UIRTerm, b: UIRTerm) -> bool:
    """True iff `a` and `b` belong to the same e-class after equality saturation."""
    eg = SemanticEGraph()
    ca = eg.add_term(a)
    cb = eg.add_term(b)
    eg.saturate()
    return eg.find(ca) == eg.find(cb)


# =========================================================================== #
# 2. Bidirectional Polyglot Lowering & Target-Language Emission               #
# =========================================================================== #

@dataclass
class LoweringContext:
    """Maps concrete language identifiers onto role-normalized semantic slots."""
    language: str
    seq_cap_pairs: dict[str, str] = field(default_factory=dict)   # e.g. C `arr` -> `n`
    cap_to_seq: dict[str, str] = field(default_factory=dict)      # e.g. C `n` -> `arr`
    ptr_bases: dict[str, str] = field(default_factory=dict)       # e.g. C `ptr` -> `arr`
    arrow_bases: set[str] = field(default_factory=set)            # C/C++ pointer receivers using `->`
    slot_to_ident: dict[str, str] = field(default_factory=dict)   # `$v0` -> concrete ident
    ident_to_slot: dict[str, str] = field(default_factory=dict)   # concrete ident -> `$v0`

    def bind(self, ident: str, role_prefix: str = "$v") -> str:
        existing = self.ident_to_slot.get(ident)
        if existing is not None:
            return existing
        idx = sum(1 for k in self.slot_to_ident if k.startswith(role_prefix))
        slot = f"{role_prefix}{idx}"
        self.ident_to_slot[ident] = slot
        self.slot_to_ident[slot] = ident
        return slot


def _infer_c_capacity_pairs(params: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Infer `(pointer_or_array_param -> length_param)` from C/C++ parameter signatures.

    Derived structurally from parameter types (`T*` / `T[]` paired with `int` / `size_t`),
    not from hard-coded function names.
    """
    ptr_params = [name for ptype, name in params if "*" in ptype or "[" in ptype]
    int_params = [
        name for ptype, name in params
        if "*" not in ptype and "[" not in ptype
        and any(t in ptype for t in ("int", "size_t", "ssize_t", "long", "unsigned"))
    ]
    pairs: dict[str, str] = {}
    if len(ptr_params) == 1 and len(int_params) == 1:
        pairs[ptr_params[0]] = int_params[0]
    elif ptr_params and int_params:
        for pp in ptr_params:
            for ip in int_params:
                if ip in ("n", "len", "length", "count", "size", "cap", f"{pp}_len", f"n_{pp}"):
                    pairs[pp] = ip
                    break
    return pairs


# --- Python AST -> UIR ---

def _lower_py_expr(node: ast.AST, ctx: LoweringContext) -> UIRTerm:
    if isinstance(node, ast.Constant):
        if node.value is None:
            return u_null()
        if isinstance(node.value, bool):
            return u_bool(node.value)
        if isinstance(node.value, int):
            return u_int(node.value)
        if isinstance(node.value, str):
            return u_str(node.value)
        return UIRTerm("CONST_OTHER", (repr(node.value),))
    if isinstance(node, ast.Name):
        if node.id in ctx.cap_to_seq:
            seq_slot = ctx.bind(ctx.cap_to_seq[node.id], "$seq")
            return UIRTerm("CAPACITY", (u_var(seq_slot),))
        return u_var(ctx.bind(node.id))
    if isinstance(node, ast.UnaryOp):
        sub = _lower_py_expr(node.operand, ctx)
        if isinstance(node.op, ast.Not):
            return UIRTerm("NOT", (sub,))
        if isinstance(node.op, ast.USub):
            if sub.op == "CONST_INT":
                return u_int(-int(sub.args[0]))
            return UIRTerm("NEG", (sub,))
        if isinstance(node.op, ast.UAdd):
            return sub
    if isinstance(node, ast.BinOp):
        l, r = _lower_py_expr(node.left, ctx), _lower_py_expr(node.right, ctx)
        op_map = {
            ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL",
            ast.FloorDiv: "DIV", ast.Div: "DIV", ast.Mod: "MOD",
        }
        uop = op_map.get(type(node.op), "BINOP_OTHER")
        return UIRTerm(uop, (l, r))
    if isinstance(node, ast.BoolOp):
        uop = "AND" if isinstance(node.op, ast.And) else "OR"
        cur = _lower_py_expr(node.values[0], ctx)
        for v in node.values[1:]:
            cur = UIRTerm(uop, (cur, _lower_py_expr(v, ctx)))
        return cur
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        op = node.ops[0]
        left_raw, right_raw = node.left, node.comparators[0]
        if isinstance(op, ast.Is) and isinstance(right_raw, ast.Constant) and right_raw.value is None:
            return UIRTerm("IS_NULL", (_lower_py_expr(left_raw, ctx),))
        if isinstance(op, ast.IsNot) and isinstance(right_raw, ast.Constant) and right_raw.value is None:
            return UIRTerm("NOT_NULL", (_lower_py_expr(left_raw, ctx),))
        l, r = _lower_py_expr(left_raw, ctx), _lower_py_expr(right_raw, ctx)
        if isinstance(op, ast.Lt):
            return UIRTerm("LT", (l, r))
        if isinstance(op, ast.LtE):
            return UIRTerm("LE", (l, r))
        if isinstance(op, ast.Gt):
            return UIRTerm("LT", (r, l))
        if isinstance(op, ast.GtE):
            return UIRTerm("LE", (r, l))
        if isinstance(op, ast.Eq):
            return UIRTerm("EQ", (l, r))
        if isinstance(op, ast.NotEq):
            return UIRTerm("NE", (l, r))
        if isinstance(op, ast.In):
            return UIRTerm("CONTAINS", (r, l))
        if isinstance(op, ast.NotIn):
            return UIRTerm("NOT", (UIRTerm("CONTAINS", (r, l)),))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1:
            arg_node = node.args[0]
            if isinstance(arg_node, ast.Name):
                seq_slot = ctx.bind(arg_node.id, "$seq")
                return UIRTerm("CAPACITY", (u_var(seq_slot),))
            return UIRTerm("CAPACITY", (_lower_py_expr(arg_node, ctx),))
        if isinstance(node.func, ast.Name) and node.func.id == "min" and len(node.args) == 2:
            a, b = _lower_py_expr(node.args[0], ctx), _lower_py_expr(node.args[1], ctx)
            return UIRTerm("GUARD", (UIRTerm("LT", (a, b)), a, b))
        if isinstance(node.func, ast.Name) and node.func.id == "max" and len(node.args) == 2:
            a, b = _lower_py_expr(node.args[0], ctx), _lower_py_expr(node.args[1], ctx)
            return UIRTerm("GUARD", (UIRTerm("LT", (b, a)), a, b))
        fname = ast.unparse(node.func)
        return UIRTerm("CALL_FN", (u_str(fname), *(_lower_py_expr(a, ctx) for a in node.args)))
    if isinstance(node, ast.Subscript):
        seq_node = node.value
        seq_t = u_var(ctx.bind(seq_node.id, "$seq")) if isinstance(seq_node, ast.Name) else _lower_py_expr(seq_node, ctx)
        return UIRTerm("INDEX", (seq_t, _lower_py_expr(node.slice, ctx)))
    if isinstance(node, ast.Attribute):
        return UIRTerm("FIELD", (_lower_py_expr(node.value, ctx), u_str(node.attr)))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return UIRTerm("NOT", (_lower_py_expr(node.operand, ctx),))
    if isinstance(node, ast.BoolOp):
        uop = "AND" if isinstance(node.op, ast.And) else "OR"
        cur = _lower_py_expr(node.values[0], ctx)
        for v in node.values[1:]:
            cur = UIRTerm(uop, (cur, _lower_py_expr(v, ctx)))
        return cur
    if isinstance(node, ast.IfExp):
        cond = _lower_py_cond(node.test, ctx)
        return UIRTerm("GUARD", (cond, _lower_py_expr(node.body, ctx), _lower_py_expr(node.orelse, ctx)))
    return UIRTerm("RAW_PY", (ast.unparse(node),))


def _lower_py_cond(node: ast.AST, ctx: LoweringContext) -> UIRTerm:
    """Lower a boolean test expression, making implicit truthiness explicit (`TRUTHY`)."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = node.operand
        if isinstance(inner, (ast.Name, ast.Attribute, ast.Subscript, ast.Call)):
            low = _lower_py_expr(inner, ctx)
            if low.op not in ("LT", "LE", "EQ", "NE", "IS_NULL", "NOT_NULL", "CONTAINS", "AND", "OR"):
                return UIRTerm("NOT", (UIRTerm("TRUTHY", (low,)),))
        return UIRTerm("NOT", (_lower_py_cond(inner, ctx),))
    if isinstance(node, ast.BoolOp):
        uop = "AND" if isinstance(node.op, ast.And) else "OR"
        cur = _lower_py_cond(node.values[0], ctx)
        for v in node.values[1:]:
            cur = UIRTerm(uop, (cur, _lower_py_cond(v, ctx)))
        return cur
    expr = _lower_py_expr(node, ctx)
    if expr.op in ("LT", "LE", "EQ", "NE", "IS_NULL", "NOT_NULL", "CONTAINS", "AND", "OR", "NOT", "CONST_BOOL"):
        return expr
    return UIRTerm("TRUTHY", (expr,))


def _extract_excl_bound(idx_slot: str, cond: UIRTerm) -> UIRTerm | None:
    """Convert `idx < B` -> `B` and `idx <= B` -> `ADD(B, 1)`."""
    if cond.op == "LT" and cond.args[0] == u_var(idx_slot):
        return cond.args[1]
    if cond.op == "LE" and cond.args[0] == u_var(idx_slot):
        return UIRTerm("ADD", (cond.args[1], u_int(1)))
    return None


def _lower_py_stmts(stmts: Sequence[ast.stmt], ctx: LoweringContext) -> UIRTerm:
    out: list[UIRTerm] = []
    i = 0
    n = len(stmts)
    while i < n:
        st = stmts[i]
        # Recognize `idx = start; while idx < bound: body; idx += step` -> `ITER_RANGE`
        if (
            isinstance(st, ast.Assign)
            and len(st.targets) == 1
            and isinstance(st.targets[0], ast.Name)
            and i + 1 < n
            and isinstance(stmts[i + 1], ast.While)
        ):
            idx_ident = st.targets[0].id
            wh = stmts[i + 1]
            assert isinstance(wh, ast.While)
            if wh.body:
                last = wh.body[-1]
                step_term: UIRTerm | None = None
                if isinstance(last, ast.AugAssign) and isinstance(last.target, ast.Name) and last.target.id == idx_ident and isinstance(last.op, ast.Add):
                    step_term = _lower_py_expr(last.value, ctx)
                elif (
                    isinstance(last, ast.Assign)
                    and len(last.targets) == 1
                    and isinstance(last.targets[0], ast.Name)
                    and last.targets[0].id == idx_ident
                    and isinstance(last.value, ast.BinOp)
                    and isinstance(last.value.op, ast.Add)
                    and isinstance(last.value.left, ast.Name)
                    and last.value.left.id == idx_ident
                ):
                    step_term = _lower_py_expr(last.value.right, ctx)
                if step_term is not None:
                    idx_slot = ctx.bind(idx_ident, "$idx")
                    start_t = _lower_py_expr(st.value, ctx)
                    cond_t = _lower_py_cond(wh.test, ctx)
                    excl = _extract_excl_bound(idx_slot, cond_t)
                    if excl is not None:
                        body_t = _lower_py_stmts(wh.body[:-1], ctx)
                        out.append(UIRTerm("ITER_RANGE", (u_var(idx_slot), start_t, excl, step_term, body_t)))
                        i += 2
                        continue

        # Recognize `for idx in range(...): body` -> `ITER_RANGE`
        if (
            isinstance(st, ast.For)
            and isinstance(st.target, ast.Name)
            and isinstance(st.iter, ast.Call)
            and isinstance(st.iter.func, ast.Name)
            and st.iter.func.id == "range"
            and 1 <= len(st.iter.args) <= 3
        ):
            idx_slot = ctx.bind(st.target.id, "$idx")
            rargs = [_lower_py_expr(a, ctx) for a in st.iter.args]
            if len(rargs) == 1:
                start_t, excl_t, step_t = u_int(0), rargs[0], u_int(1)
            elif len(rargs) == 2:
                start_t, excl_t, step_t = rargs[0], rargs[1], u_int(1)
            else:
                start_t, excl_t, step_t = rargs[0], rargs[1], rargs[2]
            body_t = _lower_py_stmts(st.body, ctx)
            out.append(UIRTerm("ITER_RANGE", (u_var(idx_slot), start_t, excl_t, step_t, body_t)))
            i += 1
            continue

        # Recognize early-return guard `if cond: return A; return B` -> `RETURN(GUARD(cond, A, B))`
        if (
            isinstance(st, ast.If)
            and not st.orelse
            and len(st.body) == 1
            and isinstance(st.body[0], ast.Return)
            and st.body[0].value is not None
            and i + 1 < n
            and isinstance(stmts[i + 1], ast.Return)
            and stmts[i + 1].value is not None
        ):
            ret_next = stmts[i + 1]
            assert isinstance(ret_next, ast.Return) and ret_next.value is not None
            cond_t = _lower_py_cond(st.test, ctx)
            then_v = _lower_py_expr(st.body[0].value, ctx)
            else_v = _lower_py_expr(ret_next.value, ctx)
            out.append(UIRTerm("RETURN", (UIRTerm("GUARD", (cond_t, then_v, else_v)),)))
            i += 2
            continue

        if isinstance(st, ast.If):
            cond_t = _lower_py_cond(st.test, ctx)
            if (
                len(st.body) == 1
                and len(st.orelse) == 1
                and isinstance(st.body[0], ast.Return)
                and isinstance(st.orelse[0], ast.Return)
                and st.body[0].value is not None
                and st.orelse[0].value is not None
            ):
                out.append(UIRTerm("RETURN", (UIRTerm(
                    "GUARD",
                    (cond_t, _lower_py_expr(st.body[0].value, ctx), _lower_py_expr(st.orelse[0].value, ctx)),
                ),)))
            else:
                then_b = _lower_py_stmts(st.body, ctx)
                else_b = _lower_py_stmts(st.orelse, ctx) if st.orelse else UIRTerm("NOP", ())
                out.append(UIRTerm("GUARD", (cond_t, then_b, else_b)))
            i += 1
            continue

        if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
            slot = ctx.bind(st.target.id)
            op_map = {ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL", ast.FloorDiv: "DIV"}
            uop = op_map.get(type(st.op), "ADD")
            out.append(UIRTerm("ASSIGN", (u_var(slot), UIRTerm(uop, (u_var(slot), _lower_py_expr(st.value, ctx))))))
            i += 1
            continue

        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            slot = ctx.bind(st.targets[0].id)
            out.append(UIRTerm("ASSIGN", (u_var(slot), _lower_py_expr(st.value, ctx))))
            i += 1
            continue

        if isinstance(st, ast.Return):
            val_t = _lower_py_expr(st.value, ctx) if st.value is not None else u_null()
            out.append(UIRTerm("RETURN", (val_t,)))
            i += 1
            continue

        out.append(UIRTerm("RAW_STMT", (ast.unparse(st),)))
        i += 1

    if not out:
        return UIRTerm("NOP", ())
    if len(out) == 1:
        return out[0]
    return UIRTerm("SEQ", tuple(out))


# --- C / C++ / JS / TS / Rust / Go -> UIR via Tree-Sitter + Structural Lowering ---

_C_FOR_RE = re.compile(
    r"for\s*\(?\s*(?:(?:int|size_t|ssize_t|long|unsigned|let|var)\s+)?([A-Za-z_]\w*)\s*:?=\s*([^;]+);"
    r"\s*([A-Za-z_]\w*)\s*(<=|<)\s*([^;]+);"
    r"\s*(?:\+\+\1|\1\+\+|\1\s*\+=\s*([^{;]+?))\)?\s*\{([\s\S]*)\}$"
)

_C_WHILE_PTR_RE = re.compile(
    r"(?:const\s+\w+\s*\*|\w+\s*\*|let|var)?\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*;\s*"
    r"while\s*\(\s*\1\s*(<=|<)\s*\2\s*\+\s*([^{]+?)\)\s*\{([\s\S]*?)(?:\+\+\1|\1\+\+)\s*;\s*\}$"
)

_C_WHILE_IDX_RE = re.compile(
    r"(?:(?:int|size_t|long|let\s+mut|let|var)\s+)?([A-Za-z_]\w*)\s*:?=\s*([^;]+);\s*"
    r"while\s*\(?\s*\1\s*(<=|<)\s*([^{]+?)\s*\)?\s*\{([\s\S]*?)(?:\+\+\1|\1\+\+|\1\s*\+=\s*([^;]+))\s*;\s*\}$"
)


def _strip_outer_braces(text: str) -> str:
    s = text.strip()
    if s.startswith("{") and s.endswith("}"):
        return s[1:-1].strip()
    return s


def _lower_c_like_expr(expr_str: str, ctx: LoweringContext) -> UIRTerm:
    s = expr_str.strip()
    while s.startswith("(") and s.endswith(")"):
        # Check balanced parens before stripping
        depth = 0
        ok = True
        for idx, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and idx < len(s) - 1:
                    ok = False
                    break
        if ok:
            s = s[1:-1].strip()
        else:
            break

    if s in ("NULL", "nullptr", "null", "undefined", "nil", "None"):
        return u_null()
    if s in ("true", "True"):
        return u_bool(True)
    if s in ("false", "False"):
        return u_bool(False)
    if re.fullmatch(r"-?\d+", s):
        return u_int(int(s))

    # Ternary `c ? t : e` (top-level)
    q_idx = _find_top_level_op(s, "?")
    if q_idx != -1:
        c_idx = _find_top_level_op(s[q_idx + 1:], ":")
        if c_idx != -1:
            cond_s = s[:q_idx]
            then_s = s[q_idx + 1:q_idx + 1 + c_idx]
            else_s = s[q_idx + 1 + c_idx + 1:]
            return UIRTerm(
                "GUARD",
                (_lower_c_like_cond(cond_s, ctx), _lower_c_like_expr(then_s, ctx), _lower_c_like_expr(else_s, ctx)),
            )

    # Logical OR / AND
    for sym, uop in (("||", "OR"), ("&&", "AND")):
        pos = _find_top_level_op(s, sym)
        if pos != -1:
            return UIRTerm(uop, (_lower_c_like_cond(s[:pos], ctx), _lower_c_like_cond(s[pos + len(sym):], ctx)))

    # Comparisons (including JS === / !== and null checks)
    for sym, uop in (("!==", "NE"), ("===", "EQ"), ("!=", "NE"), ("==", "EQ"), ("<=", "LE"), (">=", "GE"), ("<", "LT"), (">", "GT")):
        pos = _find_top_level_op(s, sym)
        if pos != -1:
            lhs_s, rhs_s = s[:pos].strip(), s[pos + len(sym):].strip()
            l_t, r_t = _lower_c_like_expr(lhs_s, ctx), _lower_c_like_expr(rhs_s, ctx)
            if r_t.op == "NULL_VAL" and uop == "EQ":
                return UIRTerm("IS_NULL", (l_t,))
            if r_t.op == "NULL_VAL" and uop == "NE":
                return UIRTerm("NOT_NULL", (l_t,))
            if uop == "GT":
                return UIRTerm("LT", (r_t, l_t))
            if uop == "GE":
                return UIRTerm("LE", (r_t, l_t))
            return UIRTerm(uop, (l_t, r_t))

    # Additive / Multiplicative (right-to-left scan for left-associativity)
    for ops in ((("+", "ADD"), ("-", "SUB")), (("*", "MUL"), ("/", "DIV"), ("%", "MOD"))):
        pos, matched_sym, matched_uop = _rfind_top_level_ops(s, ops)
        if pos > 0:
            return UIRTerm(matched_uop, (_lower_c_like_expr(s[:pos], ctx), _lower_c_like_expr(s[pos + len(matched_sym):], ctx)))

    # Unary `!x`, `*p`, `-x`
    if s.startswith("!"):
        return UIRTerm("NOT", (_lower_c_like_cond(s[1:], ctx),))
    if s.startswith("*"):
        inner = s[1:].strip()
        if inner in ctx.ptr_bases:
            base_ident = ctx.ptr_bases[inner]
            seq_slot = ctx.bind(base_ident, "$seq")
            idx_slot = ctx.bind(inner, "$idx")
            return UIRTerm("INDEX", (u_var(seq_slot), u_var(idx_slot)))
        return UIRTerm("DEREF", (_lower_c_like_expr(inner, ctx),))
    if s.startswith("-"):
        return UIRTerm("NEG", (_lower_c_like_expr(s[1:], ctx),))

    # `.length`, `.size()`, `.len()`, `(int)x.size()`, `static_cast<int>(x.size())`, `len(...)`
    m_cap = re.fullmatch(
        r"(?:(?:\((?:int|size_t|ssize_t|long)\)\s*)|(?:static_cast<[^>]+>\s*\(\s*))?([A-Za-z_]\w*)\.(?:length|size\(\)|len\(\))\)?",
        s,
    )
    if m_cap:
        seq_slot = ctx.bind(m_cap.group(1), "$seq")
        return UIRTerm("CAPACITY", (u_var(seq_slot),))
    m_len = re.fullmatch(r"len\(\s*([A-Za-z_]\w*)\s*\)", s)
    if m_len:
        seq_slot = ctx.bind(m_len.group(1), "$seq")
        return UIRTerm("CAPACITY", (u_var(seq_slot),))

    # Indexing `arr[idx]`
    m_idx = re.fullmatch(r"([A-Za-z_]\w*)\[([^\]]+)\]", s)
    if m_idx:
        seq_slot = ctx.bind(m_idx.group(1), "$seq")
        return UIRTerm("INDEX", (u_var(seq_slot), _lower_c_like_expr(m_idx.group(2), ctx)))

    # Field access `obj->field` or `obj.field`
    m_fld = re.fullmatch(r"([A-Za-z_]\w*)(->|\.)([A-Za-z_]\w*)", s)
    if m_fld:
        if m_fld.group(2) == "->":
            ctx.arrow_bases.add(m_fld.group(1))
        return UIRTerm("FIELD", (_lower_c_like_expr(m_fld.group(1), ctx), u_str(m_fld.group(3))))

    # Function call `fn(a, b)`
    m_call = re.fullmatch(r"([A-Za-z_][\w.]*)\((.*)\)", s)
    if m_call:
        fn_nm = m_call.group(1)
        raw_args = _split_top_level_commas(m_call.group(2))
        return UIRTerm("CALL_FN", (u_str(fn_nm), *(_lower_c_like_expr(a, ctx) for a in raw_args)))

    # Plain identifier (check C capacity parameter mapping!)
    if re.fullmatch(r"[A-Za-z_]\w*", s):
        if s in ctx.cap_to_seq:
            seq_slot = ctx.bind(ctx.cap_to_seq[s], "$seq")
            return UIRTerm("CAPACITY", (u_var(seq_slot),))
        return u_var(ctx.bind(s))

    return UIRTerm("RAW_EXPR", (s,))


def _lower_c_like_cond(cond_str: str, ctx: LoweringContext) -> UIRTerm:
    s = cond_str.strip()
    # Recognize JS `x !== null && x !== undefined` as single `NOT_NULL(x)`
    m_js_nn = re.fullmatch(
        r"\(?\s*([A-Za-z_][\w.>]*)\s*!==?\s*null\s*&&\s*\1\s*!==?\s*undefined\s*\)?",
        s,
    )
    if m_js_nn:
        return UIRTerm("NOT_NULL", (_lower_c_like_expr(m_js_nn.group(1), ctx),))
    m_js_null = re.fullmatch(
        r"\(?\s*([A-Za-z_][\w.>]*)\s*===?\s*null\s*\|\|\s*\1\s*===?\s*undefined\s*\)?",
        s,
    )
    if m_js_null:
        return UIRTerm("IS_NULL", (_lower_c_like_expr(m_js_null.group(1), ctx),))

    if s.startswith("!"):
        inner = _lower_c_like_expr(s[1:].strip(), ctx)
        if inner.op not in ("LT", "LE", "EQ", "NE", "IS_NULL", "NOT_NULL", "AND", "OR", "CONST_BOOL"):
            return UIRTerm("NOT", (UIRTerm("TRUTHY", (inner,)),))
        return UIRTerm("NOT", (inner,))

    t = _lower_c_like_expr(s, ctx)
    if t.op in ("LT", "LE", "EQ", "NE", "IS_NULL", "NOT_NULL", "AND", "OR", "NOT", "CONST_BOOL"):
        return t
    return UIRTerm("TRUTHY", (t,))


def _find_top_level_op(s: str, op: str) -> int:
    depth = 0
    in_str: str | None = None
    i = 0
    L = len(op)
    while i <= len(s) - L:
        ch = s[i]
        if in_str:
            if ch == "\\" and i + 1 < len(s):
                i += 2
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"'):
                in_str = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            elif depth == 0 and s[i:i + L] == op:
                # Avoid matching `<`/`>` inside `<=`/`>=`/`->`/`<<`/`>>` or `=` inside `==`/`!=`/`<=`/`>=`
                prev_ch = s[i - 1] if i > 0 else ""
                next_ch = s[i + L] if i + L < len(s) else ""
                if op == ">" and prev_ch in ("-", ">"):
                    i += 1
                    continue
                if op == "<" and (prev_ch == "<" or next_ch == "<"):
                    i += 1
                    continue
                if op in ("<", ">") and next_ch in ("=", ">"):
                    i += 1
                    continue
                if op == "==" and (prev_ch in "!<>" or next_ch == "="):
                    i += 1
                    continue
                if op == "!=" and next_ch == "=":
                    i += 1
                    continue
                return i
        i += 1
    return -1


def _rfind_top_level_ops(s: str, ops: Sequence[tuple[str, str]]) -> tuple[int, str, str]:
    depth = 0
    best = (-1, "", "")
    for i, ch in enumerate(s):
        if ch in "([{":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in "]}":
            depth = max(0, depth - 1)
        elif depth == 0 and i > 0:
            for sym, uop in ops:
                if s[i:i + len(sym)] == sym:
                    if sym == "-" and i + 1 < len(s) and s[i + 1] == ">":
                        continue
                    prev_non_ws = s[:i].rstrip()
                    if prev_non_ws and prev_non_ws[-1] not in "(,[{+-*/%=<>!&|?:":
                        best = (i, sym, uop)
    return best


def _split_top_level_commas(s: str) -> list[str]:
    if not s.strip():
        return []
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(s):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(s[start:i].strip())
            start = i + 1
    parts.append(s[start:].strip())
    return [p for p in parts if p]


def _lower_c_like_body(text: str, ctx: LoweringContext) -> UIRTerm:
    s = _strip_outer_braces(text)
    if not s:
        return UIRTerm("NOP", ())

    # Pointer while loop: `const int *p = arr; while (p <= arr + n) { sum += *p; p++; }`
    m_ptr = _C_WHILE_PTR_RE.fullmatch(s)
    if m_ptr:
        ptr_nm, base_nm, cmp_op, bound_s, body_s = m_ptr.groups()
        ctx.ptr_bases[ptr_nm] = base_nm
        ctx.bind(base_nm, "$seq")
        idx_slot = ctx.bind(ptr_nm, "$idx")
        bound_t = _lower_c_like_expr(bound_s, ctx)
        excl_t = UIRTerm("ADD", (bound_t, u_int(1))) if cmp_op == "<=" else bound_t
        body_t = _lower_c_like_body(body_s, ctx)
        return UIRTerm("ITER_RANGE", (u_var(idx_slot), u_int(0), excl_t, u_int(1), body_t))

    # Index while loop: `int i = 0; while (i <= n) { ...; i++; }`
    m_wh = _C_WHILE_IDX_RE.fullmatch(s)
    if m_wh:
        idx_nm, start_s, cmp_op, bound_s, body_s, step_s = m_wh.groups()
        idx_slot = ctx.bind(idx_nm, "$idx")
        start_t = _lower_c_like_expr(start_s, ctx)
        bound_t = _lower_c_like_expr(bound_s, ctx)
        excl_t = UIRTerm("ADD", (bound_t, u_int(1))) if cmp_op == "<=" else bound_t
        step_t = _lower_c_like_expr(step_s, ctx) if step_s else u_int(1)
        body_t = _lower_c_like_body(body_s, ctx)
        return UIRTerm("ITER_RANGE", (u_var(idx_slot), start_t, excl_t, step_t, body_t))

    # Standard `for (i = 0; i < n; i++) { ... }`
    m_for = _C_FOR_RE.fullmatch(s)
    if m_for:
        idx_nm, start_s, idx2, cmp_op, bound_s, step_s, body_s = m_for.groups()
        if idx_nm == idx2:
            idx_slot = ctx.bind(idx_nm, "$idx")
            start_t = _lower_c_like_expr(start_s, ctx)
            bound_t = _lower_c_like_expr(bound_s, ctx)
            excl_t = UIRTerm("ADD", (bound_t, u_int(1))) if cmp_op == "<=" else bound_t
            step_t = _lower_c_like_expr(step_s, ctx) if step_s else u_int(1)
            body_t = _lower_c_like_body(body_s, ctx)
            return UIRTerm("ITER_RANGE", (u_var(idx_slot), start_t, excl_t, step_t, body_t))

    # Rust range `for i in 0..=xs.len() { ... }` or `for i in 0..xs.len() { ... }`
    m_rust_for = re.fullmatch(r"for\s+([A-Za-z_]\w*)\s+in\s+([^.]+)\.\.(=?)([^{]+?)\s*\{([\s\S]*)\}$", s)
    if m_rust_for:
        idx_nm, start_s, incl_eq, bound_s, body_s = m_rust_for.groups()
        idx_slot = ctx.bind(idx_nm, "$idx")
        start_t = _lower_c_like_expr(start_s, ctx)
        bound_t = _lower_c_like_expr(bound_s, ctx)
        excl_t = UIRTerm("ADD", (bound_t, u_int(1))) if incl_eq == "=" else bound_t
        body_t = _lower_c_like_body(body_s, ctx)
        return UIRTerm("ITER_RANGE", (u_var(idx_slot), start_t, excl_t, u_int(1), body_t))

    # Early-return guard: `if (cond) { return A; } return B;` or `if (cond) return A; return B;`
    m_early = re.fullmatch(
        r"if\s*\(([^)]+)\)\s*\{?\s*return\s+([^;{}]+);\s*\}?\s*(?:else\s*\{?\s*)?return\s+([^;{}]+);\s*\}?",
        s,
    )
    if m_early:
        cond_s, then_s, else_s = m_early.groups()
        return UIRTerm(
            "RETURN",
            (UIRTerm("GUARD", (_lower_c_like_cond(cond_s, ctx), _lower_c_like_expr(then_s, ctx), _lower_c_like_expr(else_s, ctx))),),
        )

    # Split statements by top-level `;`
    stmts = _split_c_statements(s)
    if len(stmts) > 1:
        # Check if statements [0, 1] form `init; while(...)` followed by trailing `return`!
        joined_head = f"{stmts[0]} {stmts[1]}"
        if ("while" in stmts[1]) and (_C_WHILE_PTR_RE.fullmatch(joined_head) or _C_WHILE_IDX_RE.fullmatch(joined_head)):
            head_t = _lower_c_like_body(joined_head, ctx)
            tail_t = [_lower_c_like_body(x, ctx) for x in stmts[2:]]
            return UIRTerm("SEQ", (head_t, *tail_t))
        return UIRTerm("SEQ", tuple(_lower_c_like_body(x, ctx) for x in stmts))

    single = stmts[0].rstrip(";").strip()
    if single.startswith("return "):
        return UIRTerm("RETURN", (_lower_c_like_expr(single[7:], ctx),))
    m_aug = re.fullmatch(r"([A-Za-z_]\w*)\s*([+\-*/])=\s*(.+)", single)
    if m_aug:
        nm, op_ch, rhs_s = m_aug.groups()
        slot = ctx.bind(nm)
        uop = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}[op_ch]
        return UIRTerm("ASSIGN", (u_var(slot), UIRTerm(uop, (u_var(slot), _lower_c_like_expr(rhs_s, ctx)))))
    m_asg = re.fullmatch(r"(?:(?:int|long|double|float|size_t|auto|let|var|const)\s+)?([A-Za-z_]\w*)\s*:?=\s*(.+)", single)
    if m_asg:
        nm, rhs_s = m_asg.groups()
        slot = ctx.bind(nm)
        return UIRTerm("ASSIGN", (u_var(slot), _lower_c_like_expr(rhs_s, ctx)))
    return _lower_c_like_expr(single, ctx)


def _split_c_statements(s: str) -> list[str]:
    out: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth = max(0, depth - 1)
            if ch == "}" and depth == 0:
                seg = s[start:i + 1].strip()
                if seg:
                    out.append(seg)
                start = i + 1
        elif ch == ";" and depth == 0:
            seg = s[start:i + 1].strip()
            if seg:
                out.append(seg)
            start = i + 1
        i += 1
    rem = s[start:].strip()
    if rem:
        out.append(rem)
    return out


def lower_to_uir(
    code: str,
    language: str,
    *,
    c_params: Sequence[tuple[str, str]] = (),
    as_condition: bool = False,
) -> tuple[UIRTerm, LoweringContext]:
    """Lower a statement, function body, or expression in any supported language into UIR."""
    lang = language.lower()
    cap_pairs = _infer_c_capacity_pairs(c_params) if lang in ("c", "cpp") else {}
    ctx = LoweringContext(
        language=lang,
        seq_cap_pairs=cap_pairs,
        cap_to_seq={v: k for k, v in cap_pairs.items()},
    )
    for _, pname in c_params:
        if pname in cap_pairs:
            ctx.bind(pname, "$seq")
        elif pname not in ctx.cap_to_seq:
            ctx.bind(pname)

    if lang == "python":
        try:
            if as_condition:
                try:
                    expr_tree = ast.parse(code.strip(), mode="eval")
                except SyntaxError:
                    expr_tree = ast.parse(f"({code.strip()})", mode="eval")
                return _lower_py_cond(expr_tree.body, ctx), ctx
            try:
                mod = ast.parse(textwrap.dedent(code))
            except SyntaxError:
                mod = ast.parse(f"({code.strip()})")
            if len(mod.body) == 1 and isinstance(mod.body[0], ast.FunctionDef):
                fn = mod.body[0]
                for arg in fn.args.args:
                    ctx.bind(arg.arg)
                return _lower_py_stmts(fn.body, ctx), ctx
            if len(mod.body) == 1 and isinstance(mod.body[0], ast.Expr):
                return _lower_py_expr(mod.body[0].value, ctx), ctx
            return _lower_py_stmts(mod.body, ctx), ctx
        except SyntaxError:
            pass

    if as_condition:
        return _lower_c_like_cond(code, ctx), ctx
    return _lower_c_like_body(code, ctx), ctx


def emit_uir(term: UIRTerm, language: str, ctx: LoweringContext, *, indent: str = "") -> str:
    """Compile a canonical `UIRTerm` back into idiomatic target-language code."""
    lang = language.lower()

    def _name(slot: str) -> str:
        if slot in ctx.slot_to_ident:
            return ctx.slot_to_ident[slot]
        return slot.lstrip("$")

    def _expr(t: UIRTerm) -> str:
        op = t.op
        if op == "VAR":
            slot = str(t.args[0])
            # If this slot was a C pointer loop index `$idx0` mapped from `p`, emit index var if lowered to range
            return _name(slot)
        if op == "CONST_INT":
            return str(int(t.args[0]))
        if op == "CONST_BOOL":
            b = bool(t.args[0])
            if lang == "python":
                return "True" if b else "False"
            return "true" if b else "false"
        if op == "CONST_STR":
            return json.dumps(str(t.args[0]))
        if op == "NULL_VAL":
            return {"python": "None", "c": "NULL", "cpp": "nullptr", "javascript": "null", "typescript": "null", "go": "nil", "rust": "None"}.get(lang, "NULL")
        if op == "CAPACITY":
            seq_expr = _expr(t.args[0])
            if lang == "python":
                return f"len({seq_expr})"
            if lang in ("javascript", "typescript"):
                return f"{seq_expr}.length"
            if lang == "cpp":
                if seq_expr in ctx.seq_cap_pairs:
                    return ctx.seq_cap_pairs[seq_expr]
                return f"static_cast<int>({seq_expr}.size())"
            if lang == "c":
                if seq_expr in ctx.seq_cap_pairs:
                    return ctx.seq_cap_pairs[seq_expr]
                return f"(int)(sizeof({seq_expr}) / sizeof({seq_expr}[0]))"
            if lang == "rust":
                return f"{seq_expr}.len()"
            if lang == "go":
                return f"len({seq_expr})"
        if op == "IS_NULL":
            x = _expr(t.args[0])
            if lang == "python":
                return f"({x} is None)"
            if lang in ("javascript", "typescript"):
                return f"({x} === null || {x} === undefined)"
            if lang == "cpp":
                return f"({x} == nullptr)"
            if lang == "go":
                return f"({x} == nil)"
            return f"({x} == NULL)"
        if op == "NOT_NULL":
            x = _expr(t.args[0])
            if lang == "python":
                return f"({x} is not None)"
            if lang in ("javascript", "typescript"):
                return f"({x} !== null && {x} !== undefined)"
            if lang == "cpp":
                return f"({x} != nullptr)"
            if lang == "go":
                return f"({x} != nil)"
            return f"({x} != NULL)"
        if op == "TRUTHY":
            x = _expr(t.args[0])
            return f"bool({x})" if lang == "python" else f"(!!({x}))"
        if op in ("ADD", "SUB", "MUL", "DIV", "MOD"):
            l, r = _expr(t.args[0]), _expr(t.args[1])
            sym = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "//" if lang == "python" else "/", "MOD": "%"}[op]
            return f"({l} {sym} {r})"
        if op == "NEG":
            return f"(-{_expr(t.args[0])})"
        if op in ("LT", "LE", "EQ", "NE"):
            l, r = _expr(t.args[0]), _expr(t.args[1])
            if lang in ("javascript", "typescript") and op in ("EQ", "NE"):
                sym = "===" if op == "EQ" else "!=="
            else:
                sym = {"LT": "<", "LE": "<=", "EQ": "==", "NE": "!="}[op]
            return f"({l} {sym} {r})"
        if op in ("AND", "OR"):
            l, r = _expr(t.args[0]), _expr(t.args[1])
            sym = ("and" if op == "AND" else "or") if lang == "python" else ("&&" if op == "AND" else "||")
            return f"({l} {sym} {r})"
        if op == "NOT":
            sub = _expr(t.args[0])
            return f"(not {sub})" if lang == "python" else f"(!{sub})"
        if op == "INDEX":
            return f"{_expr(t.args[0])}[{_expr(t.args[1])}]"
        if op == "DEREF":
            return f"(*{_expr(t.args[0])})"
        if op == "FIELD":
            base = _expr(t.args[0])
            fld_arg = t.args[1]
            fld = str(fld_arg.args[0]) if isinstance(fld_arg, UIRTerm) and fld_arg.op == "CONST_STR" else str(fld_arg)
            sep = "->" if (lang in ("c", "cpp") and (base in ctx.arrow_bases or base in ctx.seq_cap_pairs)) else "."
            return f"{base}{sep}{fld}"
        if op == "CONTAINS":
            seq_e, item_e = _expr(t.args[0]), _expr(t.args[1])
            if lang == "python":
                return f"({item_e} in {seq_e})"
            if lang in ("javascript", "typescript"):
                return f"{seq_e}.includes({item_e})"
        if op == "GUARD":
            c_e, t_e, f_e = _expr(t.args[0]), _expr(t.args[1]), _expr(t.args[2])
            if lang == "python":
                return f"({t_e} if {c_e} else {f_e})"
            return f"({c_e} ? {t_e} : {f_e})"
        if op == "CLAMP":
            v_e, lo_e, hi_e = _expr(t.args[0]), _expr(t.args[1]), _expr(t.args[2])
            if lang == "python":
                return f"max({lo_e}, min({hi_e}, {v_e}))"
            return f"(({v_e} < {lo_e}) ? {lo_e} : (({v_e} > {hi_e}) ? {hi_e} : {v_e}))"
        if op == "CALL_FN":
            fn_arg = t.args[0]
            fn_nm = str(fn_arg.args[0]) if isinstance(fn_arg, UIRTerm) and fn_arg.op == "CONST_STR" else str(fn_arg)
            arg_s = ", ".join(_expr(a) for a in t.args[1:])
            return f"{fn_nm}({arg_s})"
        if op in ("RAW_PY", "RAW_EXPR"):
            return str(t.args[0])
        return str(t.args[0]) if t.args else "0"

    def _stmt(t: UIRTerm, pad: str) -> str:
        if t.op == "SEQ":
            return "\n".join(_stmt(sub, pad) for sub in t.args if sub.op != "NOP")
        if t.op == "NOP":
            return f"{pad}pass" if lang == "python" else f"{pad};"
        if t.op == "RETURN":
            val = t.args[0]
            if val.op == "GUARD":
                c_e = _expr(val.args[0])
                th_e = _expr(val.args[1])
                el_e = _expr(val.args[2])
                if lang == "python":
                    return f"{pad}if {c_e}:\n{pad}    return {th_e}\n{pad}return {el_e}"
                return f"{pad}if ({c_e}) {{\n{pad}    return {th_e};\n{pad}}}\n{pad}return {el_e};"
            return f"{pad}return {_expr(val)}" + ("" if lang == "python" else ";")
        if t.op == "ASSIGN":
            lhs_arg = t.args[0]
            lhs_slot = str(lhs_arg.args[0]) if isinstance(lhs_arg, UIRTerm) and lhs_arg.op == "VAR" else str(lhs_arg)
            lhs = _name(lhs_slot)
            rhs = _expr(t.args[1])
            return f"{pad}{lhs} = {rhs}" + ("" if lang == "python" else ";")
        if t.op == "GUARD":
            c_e = _expr(t.args[0])
            th_s = _stmt(t.args[1], pad + "    ")
            el_t = t.args[2]
            if lang == "python":
                if el_t.op == "NOP":
                    return f"{pad}if {c_e}:\n{th_s}"
                return f"{pad}if {c_e}:\n{th_s}\n{pad}else:\n{_stmt(el_t, pad + '    ')}"
            if el_t.op == "NOP":
                return f"{pad}if ({c_e}) {{\n{th_s}\n{pad}}}"
            return f"{pad}if ({c_e}) {{\n{th_s}\n{pad}}} else {{\n{_stmt(el_t, pad + '    ')}\n{pad}}}"
        if t.op == "ITER_RANGE":
            idx_arg, start_t, excl_t, step_t, body_t = t.args
            idx_slot = str(idx_arg.args[0]) if isinstance(idx_arg, UIRTerm) and idx_arg.op == "VAR" else str(idx_arg)
            idx_nm = _name(idx_slot)
            # If the C source used a pointer variable `p` that mapped to `$idx0`, use clean `_idx` so indexing works cleanly
            if idx_nm in ctx.ptr_bases:
                idx_nm = "_idx"
                ctx.slot_to_ident[idx_slot] = idx_nm
            start_e, excl_e, step_e = _expr(start_t), _expr(excl_t), _expr(step_t)
            body_s = _stmt(body_t, pad + "    ")
            if lang == "python":
                rng = f"range({excl_e})" if (start_e == "0" and step_e == "1") else f"range({start_e}, {excl_e}, {step_e})"
                return f"{pad}for {idx_nm} in {rng}:\n{body_s}"
            if lang in ("javascript", "typescript"):
                inc = f"{idx_nm}++" if step_e == "1" else f"{idx_nm} += {step_e}"
                return f"{pad}for (let {idx_nm} = {start_e}; {idx_nm} < {excl_e}; {inc}) {{\n{body_s}\n{pad}}}"
            if lang == "go":
                inc = f"{idx_nm}++" if step_e == "1" else f"{idx_nm} += {step_e}"
                return f"{pad}for {idx_nm} := {start_e}; {idx_nm} < {excl_e}; {inc} {{\n{body_s}\n{pad}}}"
            if lang == "rust":
                return f"{pad}for {idx_nm} in {start_e}..{excl_e} {{\n{body_s}\n{pad}}}"
            inc = f"{idx_nm}++" if step_e == "1" else f"{idx_nm} += {step_e}"
            return f"{pad}for (int {idx_nm} = {start_e}; {idx_nm} < {excl_e}; {inc}) {{\n{body_s}\n{pad}}}"
        return f"{pad}{_expr(t)}" + ("" if lang == "python" else ";")

    if term.op in ("SEQ", "RETURN", "ASSIGN", "ITER_RANGE") or (
        term.op == "GUARD" and any(isinstance(a, UIRTerm) and a.op in ("SEQ", "RETURN", "ASSIGN", "NOP") for a in term.args[1:])
    ):
        return _stmt(term, indent)
    return indent + _expr(term)


# =========================================================================== #
# 3. UIR Anti-Unification & Quotiented Cross-Language Causal Law Store        #
# =========================================================================== #

def anti_unify_uir_pair(before: UIRTerm, after: UIRTerm) -> tuple[Any, Any]:
    """Compute canonical UIR anti-unification `(lhs_pattern, rhs_pattern)`.

    Abstracts concrete variables (`VAR`) and shared unchanged subtrees into `?hK`
    pattern variables while preserving changed semantic operators (`TRUTHY` -> `NOT_NULL`,
    `ADD(?cap, 1)` -> `?cap`, etc.) so laws transfer across variable names, loop styles,
    and programming languages.
    """
    c_before = canonicalize_uir(before)
    c_after = canonicalize_uir(after)
    var_holes: dict[str, PVar] = {}
    subtree_holes: dict[str, PVar] = {}
    return _pair_generalize(c_before, c_after, var_holes, subtree_holes)


def _pair_generalize(
    b: Any,
    a: Any,
    var_holes: dict[str, PVar],
    subtree_holes: dict[str, PVar],
) -> tuple[Any, Any]:
    def _var_h(slot: str) -> PVar:
        h = var_holes.get(slot)
        if h is None:
            h = PVar(f"?v{len(var_holes)}")
            var_holes[slot] = h
        return h

    def _pat(x: Any) -> Any:
        if not isinstance(x, UIRTerm):
            if isinstance(x, str) and x.startswith("$"):
                return _var_h(x)
            return x
        if x.op == "VAR":
            return _var_h(str(x.args[0]))
        return PTerm(x.op, tuple(_pat(ch) for ch in x.args))

    if isinstance(b, UIRTerm) and isinstance(a, UIRTerm):
        if b.op == "VAR" and a.op == "VAR":
            return _var_h(str(b.args[0])), _var_h(str(a.args[0]))
        if b == a and b.op not in ("CONST_INT", "CONST_BOOL", "NULL_VAL", "CAPACITY", "VAR"):
            dg = b.digest()
            h = subtree_holes.get(dg)
            if h is None:
                h = PVar(f"?sub{len(subtree_holes)}")
                subtree_holes[dg] = h
            return h, h
        if b.op == a.op and len(b.args) == len(a.args):
            lb, la = [], []
            for xb, xa in zip(b.args, a.args):
                pb, pa = _pair_generalize(xb, xa, var_holes, subtree_holes)
                lb.append(pb)
                la.append(pa)
            return PTerm(b.op, tuple(lb)), PTerm(a.op, tuple(la))
    return _pat(b), _pat(a)


def match_uir_pattern(pat: Any, term: Any, subst: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Structural unification of `pat` (`PTerm`/`PVar`) against canonical `UIRTerm`."""
    cur = {} if subst is None else dict(subst)
    if isinstance(pat, PVar):
        if pat.name in cur:
            return cur if cur[pat.name] == term else None
        cur[pat.name] = term
        return cur
    if isinstance(pat, PTerm):
        if not isinstance(term, UIRTerm) or pat.op != term.op or len(pat.args) != len(term.args):
            return None
        for pa, ta in zip(pat.args, term.args):
            cur = match_uir_pattern(pa, ta, cur)
            if cur is None:
                return None
        return cur
    return cur if pat == term else None


def instantiate_uir_pattern(pat: Any, subst: Mapping[str, Any]) -> Any:
    if isinstance(pat, PVar):
        return subst[pat.name]
    if isinstance(pat, PTerm):
        return UIRTerm(pat.op, tuple(instantiate_uir_pattern(a, subst) for a in pat.args))
    return pat


def rewrite_uir_subterms(term: UIRTerm, lhs_pat: Any, rhs_pat: Any) -> list[UIRTerm]:
    """Apply `(lhs_pat -> rhs_pat)` at matching root or child subterms of canonical `term`."""
    candidates: list[UIRTerm] = []
    subst = match_uir_pattern(lhs_pat, term)
    if subst is not None:
        try:
            rep = instantiate_uir_pattern(rhs_pat, subst)
            if isinstance(rep, UIRTerm) and rep != term:
                candidates.append(rep)
        except KeyError:
            pass
    for idx, arg in enumerate(term.args):
        if isinstance(arg, UIRTerm):
            for sub_rep in rewrite_uir_subterms(arg, lhs_pat, rhs_pat):
                new_args = list(term.args)
                new_args[idx] = sub_rep
                cand = UIRTerm(term.op, tuple(new_args))
                if cand not in candidates:
                    candidates.append(cand)
    return candidates


@dataclass
class CausalLaw:
    """Inspectable, falsifiable, language-neutral causal repair law."""
    law_id: str
    diagnostic_class: str
    lhs_pattern: dict[str, Any]
    rhs_pattern: dict[str, Any]
    origin_languages: list[str]
    verified_transfers: int = 0
    refutations: int = 0
    scope_exclusions: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "CausalLaw":
        return CausalLaw(
            law_id=str(d["law_id"]),
            diagnostic_class=str(d.get("diagnostic_class") or "general"),
            lhs_pattern=dict(d["lhs_pattern"]),
            rhs_pattern=dict(d["rhs_pattern"]),
            origin_languages=list(d.get("origin_languages") or []),
            verified_transfers=int(d.get("verified_transfers") or 0),
            refutations=int(d.get("refutations") or 0),
            scope_exclusions=list(d.get("scope_exclusions") or []),
            created_at=float(d.get("created_at") or 0.0),
        )


class CausalLawStore:
    """External, inspectable, editable store of e-graph quotiented UIR causal laws.

    Zero world-knowledge weights: laws are added/removed in <1 ms as plain JSON,
    deduplicated by canonical `(lhs_pattern, rhs_pattern)` digest so equivalent
    discoveries across Python, C, C++, and JS merge into ONE law instead of
    accumulating language-specific rules.
    """

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        default_p = ROOT / "canonical" / "astra_runtime" / "tmp" / "uir_causal_law_store_v1.json"
        self.path = pathlib.Path(path) if path else default_p
        self.laws: dict[str, CausalLaw] = {}
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, Mapping) and raw.get("schema") == LAW_STORE_SCHEMA:
                for item in raw.get("laws") or []:
                    law = CausalLaw.from_dict(item)
                    self.laws[law.law_id] = law
        except Exception:
            self.laws = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": LAW_STORE_SCHEMA,
            "authority": AUTHORITY,
            "law_count": len(self.laws),
            "laws": [law.to_dict() for law in sorted(self.laws.values(), key=lambda x: x.law_id)],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def admit_from_verified_pair(
        self,
        before_code: str,
        after_code: str,
        language: str,
        *,
        diagnostic_class: str = "general",
        c_params: Sequence[tuple[str, str]] = (),
        as_condition: bool = False,
    ) -> CausalLaw | None:
        """Generalize a verified `(before, after)` repair into a canonical UIR law.

        Refuses Concrete-Path / No-Op / Constant-Overfit degeneracies. Merges into
        existing law if canonical UIR patterns match (preventing rule bloat).
        """
        b_uir, _ = lower_to_uir(before_code, language, c_params=c_params, as_condition=as_condition)
        a_uir, _ = lower_to_uir(after_code, language, c_params=c_params, as_condition=as_condition)
        cb, ca = canonicalize_uir(b_uir), canonicalize_uir(a_uir)
        if cb == ca or cb.op.startswith("RAW_") or ca.op.startswith("RAW_") or ca.op == "CONST_BOOL":
            return None

        def _contains_bool_null_tautology(t: UIRTerm) -> bool:
            if t.op in ("IS_NULL", "NOT_NULL") and t.args and isinstance(t.args[0], UIRTerm):
                if _is_bool_valued_uir(t.args[0]):
                    return True
            return any(_contains_bool_null_tautology(a) for a in t.args if isinstance(a, UIRTerm))

        if _contains_bool_null_tautology(ca):
            return None
        lhs_p, rhs_p = anti_unify_uir_pair(cb, ca)
        if not isinstance(lhs_p, PTerm) or not isinstance(rhs_p, (PTerm, PVar)):
            return None
        lhs_d = lhs_p.to_dict()
        rhs_d = rhs_p.to_dict() if isinstance(rhs_p, PTerm) else {"pvar": rhs_p.name}
        # Refuse unbound holes on RHS (prevents `FOREIGN_IDENT_UNBOUND` fabrication!)
        lhs_holes = _collect_pvars(lhs_d)
        rhs_holes = _collect_pvars(rhs_d)
        if not rhs_holes.issubset(lhs_holes):
            return None

        blob = json.dumps({"lhs": lhs_d, "rhs": rhs_d}, sort_keys=True, separators=(",", ":"))
        law_id = "uir_law_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
        existing = self.laws.get(law_id)
        if existing is not None:
            if language.lower() not in existing.origin_languages:
                existing.origin_languages.append(language.lower())
            self.save()
            return existing

        law = CausalLaw(
            law_id=law_id,
            diagnostic_class=diagnostic_class,
            lhs_pattern=lhs_d,
            rhs_pattern=rhs_d,
            origin_languages=[language.lower()],
        )
        self.laws[law_id] = law
        self.save()
        return law

    def propose_transfers(
        self,
        code: str,
        target_language: str,
        *,
        c_params: Sequence[tuple[str, str]] = (),
        as_condition: bool = False,
        indent: str = "",
    ) -> list[tuple[CausalLaw, str]]:
        """Apply stored universal UIR laws to `code` in `target_language` (even if learned in another language!)."""
        if not self.laws:
            return []
        uir, ctx = lower_to_uir(code, target_language, c_params=c_params, as_condition=as_condition)
        canon = canonicalize_uir(uir)
        proposals: list[tuple[CausalLaw, str]] = []
        # Rank laws with high verified_transfers and low refutations first (ordering, never deleting fallback)
        ordered_laws = sorted(
            self.laws.values(),
            key=lambda lw: (lw.verified_transfers - lw.refutations, lw.created_at),
            reverse=True,
        )
        for law in ordered_laws:
            if target_language.lower() in law.scope_exclusions:
                continue
            lhs_p = PTerm.from_dict(law.lhs_pattern)
            rhs_p = PTerm.from_dict(law.rhs_pattern)
            for rewritten in rewrite_uir_subterms(canon, lhs_p, rhs_p):
                emitted = emit_uir(rewritten, target_language, copy.deepcopy(ctx), indent=indent)
                if emitted.strip() != code.strip():
                    proposals.append((law, emitted))
        return proposals


def _collect_pvars(d: Any) -> set[str]:
    if isinstance(d, Mapping):
        if "pvar" in d:
            return {str(d["pvar"])}
        out: set[str] = set()
        for v in d.values():
            out |= _collect_pvars(v)
        return out
    if isinstance(d, (list, tuple)):
        out = set()
        for x in d:
            out |= _collect_pvars(x)
        return out
    return set()


# =========================================================================== #
# 4. Multi-File Polyglot Code Property Graph (CPG) & Causal Data-Flow Lineage #
# =========================================================================== #

@dataclass
class CausalSite:
    """A candidate causal expression, guard, loop, or statement inside a project's CPG."""
    site_id: str
    rel_path: str
    language: str
    func_name: str
    kind: str  # "guard" | "loop" | "return_expr" | "assign_rhs" | "func_body"
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    source_text: str
    c_params: tuple[tuple[str, str], ...] = ()
    upstream_distance: int = 0
    causal_chain: tuple[str, ...] = ()
    suspiciousness: float = 0.0


@dataclass
class FunctionCPG:
    rel_path: str
    language: str
    name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    params: list[tuple[str, str]]
    calls: list[tuple[str, list[str], int]]      # (callee_name, arg_texts, line)
    defs: dict[str, list[tuple[int, str]]]       # var_name -> [(line, rhs_text)]
    uses: dict[str, list[int]]                   # var_name -> [lines]
    sites: list[CausalSite] = field(default_factory=list)


@dataclass
class ProjectCPG:
    root: pathlib.Path
    functions: dict[str, list[FunctionCPG]] = field(default_factory=dict)  # name -> [FunctionCPG]
    by_file: dict[str, list[FunctionCPG]] = field(default_factory=dict)
    callers_of: dict[str, list[tuple[str, str, int]]] = field(default_factory=dict)  # callee -> [(file, caller, line)]
    callees_of: dict[tuple[str, str], list[str]] = field(default_factory=dict)       # (file, caller) -> [callee]
    pure_helpers: dict[str, tuple[str, str, int]] = field(default_factory=dict)      # name -> (rel_path, mod_import, arity)
    class_methods: dict[str, list[tuple[str, tuple[str, ...]]]] = field(default_factory=dict)  # ClassName -> [(method, (p1, ...))]


_SOURCE_EXTS = {
    ".py": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".js": "javascript",
    ".ts": "typescript",
}


def build_project_cpg(root: pathlib.Path) -> ProjectCPG:
    """Construct the multi-file Code Property Graph (AST + CFG guards + Def-Use DFG + Call Graph)."""
    root = pathlib.Path(root).resolve()
    cpg = ProjectCPG(root=root)

    for fp in sorted(root.rglob("*")):
        if not fp.is_file():
            continue
        rel_parts = fp.relative_to(root).parts
        if any(p in tsk.IGNORED_DIRS or p.startswith(".") for p in rel_parts):
            continue
        lang = _SOURCE_EXTS.get(fp.suffix.lower())
        if not lang:
            continue
        rel = fp.relative_to(root).as_posix()
        # Skip test files when harvesting repair target sites, but still record their calls
        is_test_file = (
            fp.name.startswith("test_")
            or fp.name.endswith(("_test.py", "_test.c", "_test.cpp", ".test.js", "tests.c"))
            or "tests" in rel_parts[:-1]
        )
        raw = fp.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        if lang == "python":
            fns = _extract_python_functions_cpg(rel, text, raw, include_sites=not is_test_file)
            if not is_test_file:
                for cls_nm, qmethods in _extract_python_class_query_methods(text).items():
                    existing = cpg.class_methods.setdefault(cls_nm, [])
                    for qm in qmethods:
                        if qm not in existing:
                            existing.append(qm)
        else:
            fns = _extract_polyglot_functions_cpg(rel, lang, text, raw, include_sites=not is_test_file)

        cpg.by_file[rel] = fns
        for fn in fns:
            cpg.functions.setdefault(fn.name, []).append(fn)
            if not is_test_file and lang == "python" and not fn.name.startswith("_"):
                mod_name = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel
                if mod_name.endswith(".__init__"):
                    mod_name = mod_name[:-9]
                cpg.pure_helpers[fn.name] = (rel, mod_name, len(fn.params))

    # Wire inter-procedural call edges across files
    for rel, fns in cpg.by_file.items():
        for fn in fns:
            callees: list[str] = []
            for callee_raw, _args, ln in fn.calls:
                short = callee_raw.split(".")[-1].split("->")[-1]
                if short in cpg.functions:
                    callees.append(short)
                    cpg.callers_of.setdefault(short, []).append((rel, fn.name, ln))
            cpg.callees_of[(rel, fn.name)] = callees

    return cpg


def _line_byte_offsets(raw: bytes) -> list[int]:
    offsets = [0]
    pos = 0
    for line in raw.splitlines(keepends=True):
        pos += len(line)
        offsets.append(pos)
    return offsets


def _py_node_byte_span(node: ast.AST, line_offsets: Sequence[int], raw: bytes) -> tuple[int, int]:
    lineno = getattr(node, "lineno", 1)
    col = getattr(node, "col_offset", 0)
    end_lineno = getattr(node, "end_lineno", lineno)
    end_col = getattr(node, "end_col_offset", col)
    line_s = raw[line_offsets[lineno - 1]:line_offsets[lineno]]
    start_b = line_offsets[lineno - 1] + len(line_s.decode("utf-8", errors="replace")[:col].encode("utf-8"))
    end_line_s = raw[line_offsets[end_lineno - 1]:line_offsets[end_lineno]]
    end_b = line_offsets[end_lineno - 1] + len(end_line_s.decode("utf-8", errors="replace")[:end_col].encode("utf-8"))
    return start_b, end_b


def _extract_python_class_query_methods(text: str) -> dict[str, list[tuple[str, tuple[str, ...]]]]:
    """AST-mine provably side-effect-free query methods `(method_name, non_self_params)` per class."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    out: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    bases_map: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        bases_map[node.name] = bases
        methods: list[tuple[str, tuple[str, ...]]] = []
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
                continue
            if not item.args.args or item.args.args[0].arg != "self":
                continue
            if len(item.args.args) > 3:
                continue
            has_return = False
            mutates_state = False
            for sub in ast.walk(item):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    has_return = True
                elif isinstance(sub, (ast.Delete, ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom)):
                    mutates_state = True
                    break
                elif isinstance(sub, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                    tgts = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                    for t in tgts:
                        if isinstance(t, (ast.Attribute, ast.Subscript)):
                            mutates_state = True
                            break
            if has_return and not mutates_state:
                # Only count required positional params (exclude params that have defaults so arity is minimal)
                n_defaults = len(item.args.defaults)
                non_self = item.args.args[1:]
                req_params = non_self[:len(non_self) - n_defaults] if n_defaults else non_self
                methods.append((item.name, tuple(a.arg for a in req_params)))
        if methods:
            out[node.name] = methods
    # Propagate base-class query methods inside the same file
    for cls_nm, bases in bases_map.items():
        for b in bases:
            if b in out:
                cur = out.setdefault(cls_nm, [])
                for m in out[b]:
                    if m not in cur:
                        cur.append(m)
    return out


def _extract_python_functions_cpg(
    rel: str,
    text: str,
    raw: bytes,
    *,
    include_sites: bool,
) -> list[FunctionCPG]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    offsets = _line_byte_offsets(raw)
    out: list[FunctionCPG] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        sb, eb = _py_node_byte_span(node, offsets, raw)
        params = [(ast.unparse(a.annotation) if a.annotation else "Any", a.arg) for a in node.args.args]
        calls: list[tuple[str, list[str], int]] = []
        defs: dict[str, list[tuple[int, str]]] = {}
        uses: dict[str, list[int]] = {}
        sites: list[CausalSite] = []

        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                cname = ast.unparse(sub.func)
                cargs = [ast.unparse(a) for a in sub.args]
                calls.append((cname, cargs, getattr(sub, "lineno", node.lineno)))
            elif isinstance(sub, ast.Assign):
                rhs_txt = ast.unparse(sub.value)
                for tgt in sub.targets:
                    if isinstance(tgt, ast.Name):
                        defs.setdefault(tgt.id, []).append((sub.lineno, rhs_txt))
            elif isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name):
                defs.setdefault(sub.target.id, []).append((sub.lineno, ast.unparse(sub.value)))
            elif isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                uses.setdefault(sub.id, []).append(sub.lineno)

        if include_sites:
            site_idx = 0
            for sub in ast.walk(node):
                if isinstance(sub, (ast.If, ast.While)):
                    tb, te = _py_node_byte_span(sub.test, offsets, raw)
                    sites.append(CausalSite(
                        site_id=f"{rel}:{node.name}:guard:{site_idx}",
                        rel_path=rel, language="python", func_name=node.name, kind="guard",
                        start_line=sub.test.lineno, end_line=getattr(sub.test, "end_lineno", sub.test.lineno),
                        start_byte=tb, end_byte=te,
                        source_text=raw[tb:te].decode("utf-8", errors="replace"),
                    ))
                    site_idx += 1
                elif (
                    isinstance(sub, ast.For)
                    and isinstance(sub.iter, ast.Call)
                    and isinstance(sub.iter.func, ast.Name)
                    and sub.iter.func.id == "range"
                ):
                    _sb_col, le = _py_node_byte_span(sub, offsets, raw)
                    lb = offsets[sub.lineno - 1]
                    sites.append(CausalSite(
                        site_id=f"{rel}:{node.name}:for:{site_idx}",
                        rel_path=rel, language="python", func_name=node.name, kind="loop",
                        start_line=sub.lineno, end_line=getattr(sub, "end_lineno", sub.lineno),
                        start_byte=lb, end_byte=le,
                        source_text=raw[lb:le].decode("utf-8", errors="replace"),
                    ))
                    site_idx += 1
                elif isinstance(sub, ast.Try):
                    for h in sub.handlers:
                        if h.type is not None:
                            hb, he = _py_node_byte_span(h.type, offsets, raw)
                            sites.append(CausalSite(
                                site_id=f"{rel}:{node.name}:except:{site_idx}",
                                rel_path=rel, language="python", func_name=node.name, kind="except_type",
                                start_line=sub.lineno, end_line=getattr(sub, "end_lineno", sub.lineno),
                                start_byte=hb, end_byte=he,
                                source_text=raw[hb:he].decode("utf-8", errors="replace"),
                            ))
                            site_idx += 1
                elif isinstance(sub, (ast.Return, ast.Yield)) and sub.value is not None:
                    rb, re_b = _py_node_byte_span(sub.value, offsets, raw)
                    sites.append(CausalSite(
                        site_id=f"{rel}:{node.name}:ret:{site_idx}",
                        rel_path=rel, language="python", func_name=node.name, kind="return_expr",
                        start_line=sub.value.lineno, end_line=getattr(sub.value, "end_lineno", sub.value.lineno),
                        start_byte=rb, end_byte=re_b,
                        source_text=raw[rb:re_b].decode("utf-8", errors="replace"),
                    ))
                    site_idx += 1
                elif isinstance(sub, ast.Assign) and len(sub.targets) == 1:
                    ab, ae = _py_node_byte_span(sub.value, offsets, raw)
                    sites.append(CausalSite(
                        site_id=f"{rel}:{node.name}:asg:{site_idx}",
                        rel_path=rel, language="python", func_name=node.name, kind="assign_rhs",
                        start_line=sub.value.lineno, end_line=getattr(sub.value, "end_lineno", sub.value.lineno),
                        start_byte=ab, end_byte=ae,
                        source_text=raw[ab:ae].decode("utf-8", errors="replace"),
                    ))
                    site_idx += 1
                elif isinstance(sub, ast.AnnAssign) and sub.value is not None:
                    ab, ae = _py_node_byte_span(sub.value, offsets, raw)
                    sites.append(CausalSite(
                        site_id=f"{rel}:{node.name}:annasg:{site_idx}",
                        rel_path=rel, language="python", func_name=node.name, kind="assign_rhs",
                        start_line=sub.value.lineno, end_line=getattr(sub.value, "end_lineno", sub.value.lineno),
                        start_byte=ab, end_byte=ae,
                        source_text=raw[ab:ae].decode("utf-8", errors="replace"),
                    ))
                    site_idx += 1

            # Also expose whole-function body site for loop/multi-statement UIR lowering
            if node.body:
                bs, _ = _py_node_byte_span(node.body[0], offsets, raw)
                _, be = _py_node_byte_span(node.body[-1], offsets, raw)
                # Expand start_byte back to line start so indentation stays intact
                line_start = offsets[node.body[0].lineno - 1]
                sites.append(CausalSite(
                    site_id=f"{rel}:{node.name}:body:{site_idx}",
                    rel_path=rel, language="python", func_name=node.name, kind="func_body",
                    start_line=node.body[0].lineno,
                    end_line=getattr(node.body[-1], "end_lineno", node.body[-1].lineno),
                    start_byte=line_start, end_byte=be,
                    source_text=raw[line_start:be].decode("utf-8", errors="replace"),
                ))

        out.append(FunctionCPG(
            rel_path=rel, language="python", name=node.name,
            start_line=node.lineno, end_line=getattr(node, "end_lineno", node.lineno),
            start_byte=sb, end_byte=eb,
            params=params, calls=calls, defs=defs, uses=uses, sites=sites,
        ))
    return out


def _extract_polyglot_functions_cpg(
    rel: str,
    lang: str,
    text: str,
    raw: bytes,
    *,
    include_sites: bool,
) -> list[FunctionCPG]:
    ts_lang = "cpp" if lang == "c" else lang
    try:
        tree = tsk.parse_bytes(ts_lang, raw)
    except Exception:
        return []

    out: list[FunctionCPG] = []

    def _walk(node: Any) -> Iterator[Any]:
        yield node
        for ch in node.children:
            yield from _walk(ch)

    from typing import Iterator

    fn_types = {"function_definition", "function_declaration", "method_definition", "function_item"}
    for node in _walk(tree.root_node):
        if node.type not in fn_types:
            continue
        fn_name = _ts_function_name(node, raw)
        if not fn_name:
            continue
        body_node = next((c for c in node.children if c.type in ("compound_statement", "statement_block", "block")), None)
        if body_node is None:
            continue
        c_params = tuple(_ts_extract_params(node, raw))
        calls: list[tuple[str, list[str], int]] = []
        defs: dict[str, list[tuple[int, str]]] = {}
        uses: dict[str, list[int]] = {}
        sites: list[CausalSite] = []
        site_idx = 0

        for sub in _walk(body_node):
            if sub.type == "call_expression":
                named = [c for c in sub.children if c.is_named]
                if named:
                    cname = raw[named[0].start_byte:named[0].end_byte].decode("utf-8", errors="replace")
                    args_n = named[1] if len(named) > 1 else None
                    cargs = [
                        raw[a.start_byte:a.end_byte].decode("utf-8", errors="replace")
                        for a in (args_n.children if args_n else []) if a.is_named
                    ]
                    calls.append((cname, cargs, sub.start_point[0] + 1))
            elif sub.type in ("assignment_expression", "init_declarator"):
                named = [c for c in sub.children if c.is_named]
                if len(named) >= 2:
                    lhs_txt = raw[named[0].start_byte:named[0].end_byte].decode("utf-8", errors="replace").lstrip("*").strip()
                    rhs_n = named[-1]
                    rhs_txt = raw[rhs_n.start_byte:rhs_n.end_byte].decode("utf-8", errors="replace")
                    defs.setdefault(lhs_txt, []).append((sub.start_point[0] + 1, rhs_txt))
                    if include_sites and sub.type == "assignment_expression" and "=" in raw[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace"):
                        # Only plain `=` rhs, not `+=` where rhs is delta
                        raw_sub = raw[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")
                        if not any(op in raw_sub for op in ("+=", "-=", "*=", "/=")):
                            sites.append(CausalSite(
                                site_id=f"{rel}:{fn_name}:asg:{site_idx}",
                                rel_path=rel, language=lang, func_name=fn_name, kind="assign_rhs",
                                start_line=rhs_n.start_point[0] + 1, end_line=rhs_n.end_point[0] + 1,
                                start_byte=rhs_n.start_byte, end_byte=rhs_n.end_byte,
                                source_text=rhs_txt, c_params=c_params,
                            ))
                            site_idx += 1
            elif sub.type == "identifier":
                id_txt = raw[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")
                uses.setdefault(id_txt, []).append(sub.start_point[0] + 1)

            if include_sites:
                if sub.type == "if_statement":
                    cond_n = next((c for c in sub.children if c.type in ("condition_clause", "parenthesized_expression")), None)
                    if cond_n is not None:
                        # Strip outer parens for clean condition expression
                        cs, ce = cond_n.start_byte, cond_n.end_byte
                        ctxt = raw[cs:ce].decode("utf-8", errors="replace")
                        if ctxt.startswith("(") and ctxt.endswith(")") and _has_balanced_outer_parens(ctxt):
                            cs += 1
                            ce -= 1
                            ctxt = raw[cs:ce].decode("utf-8", errors="replace")
                        sites.append(CausalSite(
                            site_id=f"{rel}:{fn_name}:guard:{site_idx}",
                            rel_path=rel, language=lang, func_name=fn_name, kind="guard",
                            start_line=cond_n.start_point[0] + 1, end_line=cond_n.end_point[0] + 1,
                            start_byte=cs, end_byte=ce, source_text=ctxt, c_params=c_params,
                        ))
                        site_idx += 1
                elif sub.type in ("for_statement", "while_statement"):
                    if sub.type == "while_statement":
                        cond_n = next((c for c in sub.children if c.type in ("condition_clause", "parenthesized_expression")), None)
                        if cond_n is not None:
                            cs, ce = cond_n.start_byte, cond_n.end_byte
                            ctxt = raw[cs:ce].decode("utf-8", errors="replace")
                            if ctxt.startswith("(") and ctxt.endswith(")") and _has_balanced_outer_parens(ctxt):
                                cs += 1
                                ce -= 1
                                ctxt = raw[cs:ce].decode("utf-8", errors="replace")
                            sites.append(CausalSite(
                                site_id=f"{rel}:{fn_name}:wguard:{site_idx}",
                                rel_path=rel, language=lang, func_name=fn_name, kind="guard",
                                start_line=cond_n.start_point[0] + 1, end_line=cond_n.end_point[0] + 1,
                                start_byte=cs, end_byte=ce, source_text=ctxt, c_params=c_params,
                            ))
                            site_idx += 1
                    sites.append(CausalSite(
                        site_id=f"{rel}:{fn_name}:loop:{site_idx}",
                        rel_path=rel, language=lang, func_name=fn_name, kind="loop",
                        start_line=sub.start_point[0] + 1, end_line=sub.end_point[0] + 1,
                        start_byte=sub.start_byte, end_byte=sub.end_byte,
                        source_text=raw[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace"),
                        c_params=c_params,
                    ))
                    site_idx += 1
                elif sub.type == "return_statement":
                    named = [c for c in sub.children if c.is_named]
                    if named:
                        rn = named[0]
                        sites.append(CausalSite(
                            site_id=f"{rel}:{fn_name}:ret:{site_idx}",
                            rel_path=rel, language=lang, func_name=fn_name, kind="return_expr",
                            start_line=rn.start_point[0] + 1, end_line=rn.end_point[0] + 1,
                            start_byte=rn.start_byte, end_byte=rn.end_byte,
                            source_text=raw[rn.start_byte:rn.end_byte].decode("utf-8", errors="replace"),
                            c_params=c_params,
                        ))
                        site_idx += 1
                elif sub.type == "expression_statement" and lang in ("c", "cpp"):
                    st_txt = raw[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")
                    if "->" in st_txt and "\n" not in st_txt.strip():
                        sites.append(CausalSite(
                            site_id=f"{rel}:{fn_name}:deref:{site_idx}",
                            rel_path=rel, language=lang, func_name=fn_name, kind="deref_stmt",
                            start_line=sub.start_point[0] + 1, end_line=sub.end_point[0] + 1,
                            start_byte=sub.start_byte, end_byte=sub.end_byte,
                            source_text=st_txt,
                            c_params=c_params,
                        ))
                        site_idx += 1

        if include_sites:
            # Inner body between `{` and `}`
            inner_s = body_node.start_byte + 1
            inner_e = body_node.end_byte - 1
            if inner_e > inner_s:
                sites.append(CausalSite(
                    site_id=f"{rel}:{fn_name}:body:{site_idx}",
                    rel_path=rel, language=lang, func_name=fn_name, kind="func_body",
                    start_line=body_node.start_point[0] + 1, end_line=body_node.end_point[0] + 1,
                    start_byte=inner_s, end_byte=inner_e,
                    source_text=raw[inner_s:inner_e].decode("utf-8", errors="replace"),
                    c_params=c_params,
                ))

        out.append(FunctionCPG(
            rel_path=rel, language=lang, name=fn_name,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            start_byte=node.start_byte, end_byte=node.end_byte,
            params=list(c_params), calls=calls, defs=defs, uses=uses, sites=sites,
        ))
    return out


def _ts_function_name(node: Any, raw: bytes) -> str:
    for ch in node.children:
        if ch.type == "identifier" or ch.type == "property_identifier":
            return raw[ch.start_byte:ch.end_byte].decode("utf-8", errors="replace")
        if ch.type in ("function_declarator", "pointer_declarator"):
            sub = _ts_function_name(ch, raw)
            if sub:
                return sub
    return ""


def _ts_extract_params(fn_node: Any, raw: bytes) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []

    def _find_plist(n: Any) -> Any | None:
        if n.type in ("parameter_list", "formal_parameters", "parameters"):
            return n
        for ch in n.children:
            if ch.type not in ("compound_statement", "statement_block", "block"):
                res = _find_plist(ch)
                if res is not None:
                    return res
        return None

    plist = _find_plist(fn_node)
    if plist is None:
        return params
    for ch in plist.children:
        if not ch.is_named:
            continue
        txt = raw[ch.start_byte:ch.end_byte].decode("utf-8", errors="replace").strip()
        if not txt or txt == "void":
            continue
        m = re.search(r"([A-Za-z_]\w*)\s*(?:\[\s*\])?$", txt)
        if m:
            pname = m.group(1)
            ptype = txt[:m.start(1)].strip() + ("[]" if txt.endswith("]") else "")
            params.append((ptype or "var", pname))
    return params


def _has_balanced_outer_parens(s: str) -> bool:
    depth = 0
    for idx, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and idx < len(s) - 1:
                return False
    return depth == 0


def trace_causal_lineage(
    cpg: ProjectCPG,
    *,
    symptom_symbols: Sequence[str] = (),
    failure_output: str = "",
    executed_lines: Mapping[str, set[int] | Mapping[int, int]] | None = None,
    max_hops: int = 5,
) -> list[CausalSite]:
    """Trace inter-procedural backward & forward data-flow lineage across ALL project files.

    Intersects static CPG (AST + CFG + Def-Use DFG) with dynamic Temporal Execution Graph
    `executed_lines` when available (CT-Repair, Jul 2026), narrowing multi-thousand-line
    files to the exact executed sites ranked by temporal proximity to failure.
    """
    seeds: list[tuple[FunctionCPG, tuple[str, ...], float]] = []
    mentioned_files: set[str] = set()
    mentioned_lines: dict[str, set[int]] = {}
    traceback_lines: dict[str, set[int]] = {}
    exec_map = executed_lines or {}
    exec_seq: dict[str, dict[int, int]] = {}
    max_seq = 1
    for rel, lns in exec_map.items():
        if isinstance(lns, Mapping):
            seq_d = {int(k): int(v) for k, v in lns.items()}
            exec_seq[rel] = seq_d
            if seq_d:
                max_seq = max(max_seq, max(seq_d.values()))
        else:
            exec_seq[rel] = {int(k): 1 for k in lns}
        if rel in cpg.by_file and lns:
            mentioned_files.add(rel)
            mentioned_lines.setdefault(rel, set()).update(exec_seq[rel].keys())

    # Filter out passing test log lines (`:PASS`) so only failing assertions & stack frames seed causal tracing
    filtered_failure = "\n".join(
        line for line in (failure_output or "").splitlines() if ":PASS" not in line
    )

    # Extract Python, C/C++ (ASan/UBSan/GDB/Unity/assert), and JS stack locations from failure output
    for m in re.finditer(r'([A-Za-z0-9_./\-]+\.(?:py|c|h|cpp|js|ts))["\'(:, ]+(?:line )?(\d+)', filtered_failure):
        cand_rel = os.path.normpath(m.group(1)).lstrip("./")
        while cand_rel.startswith("../"):
            cand_rel = cand_rel[3:]
        ln = int(m.group(2))
        for known_rel in cpg.by_file:
            if known_rel == cand_rel or known_rel.endswith("/" + cand_rel) or cand_rel.endswith("/" + known_rel) or known_rel.endswith(cand_rel):
                mentioned_files.add(known_rel)
                mentioned_lines.setdefault(known_rel, set()).add(ln)
                traceback_lines.setdefault(known_rel, set()).add(ln)

    # Extract top ASan/UBSan/GDB crash frame function names (`#0 0x... in func_name`)
    crash_frame_fns: set[str] = set()
    for m_fr in re.finditer(r"#\d+\s+0x[0-9a-fA-F]+\s+in\s+([A-Za-z_]\w*)", filtered_failure):
        fn_tok = m_fr.group(1)
        if fn_tok in cpg.functions:
            crash_frame_fns.add(fn_tok)

    seed_names = set(symptom_symbols) | crash_frame_fns
    for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", filtered_failure):
        if tok in cpg.functions:
            seed_names.add(tok)

    any_test_line_hits = any(
        bool(mentioned_lines.get(rel)) and any(not f.sites for f in fns)
        for rel, fns in cpg.by_file.items()
    )
    if not exec_map:
        for rel, fns in cpg.by_file.items():
            test_lns = mentioned_lines.get(rel, set())
            if any_test_line_hits and not test_lns:
                continue
            for fn in fns:
                if not fn.sites:  # test file function
                    if test_lns and not any(fn.start_line <= l <= fn.end_line for l in test_lns):
                        continue
                    for callee_raw, _, _ in fn.calls:
                        short = callee_raw.split(".")[-1].split("->")[-1]
                        if short in cpg.functions:
                            seed_names.add(short)
                            if test_lns:
                                crash_frame_fns.add(short)

    seen_fns: set[tuple[str, str]] = set()
    queue: list[tuple[FunctionCPG, int, tuple[str, ...], float]] = []

    for rel in mentioned_files:
        for fn in cpg.by_file.get(rel, ()):
            if not fn.sites:
                continue
            lns = mentioned_lines.get(rel, set())
            hit = any(fn.start_line <= l <= fn.end_line for l in lns)
            if lns and not hit:
                continue
            base_score = 220.0 if hit else 65.0
            key = (fn.rel_path, fn.name)
            if key not in seen_fns:
                seen_fns.add(key)
                queue.append((fn, 0, (f"{fn.rel_path}:{fn.name}",), base_score))

    for nm in sorted(seed_names):
        for fn in cpg.functions.get(nm, ()):
            if not fn.sites:
                continue
            key = (fn.rel_path, fn.name)
            if key not in seen_fns:
                seen_fns.add(key)
                fn_sc = 185.0 if nm in crash_frame_fns else 85.0
                queue.append((fn, 0, (f"{fn.rel_path}:{fn.name}",), fn_sc))

    if not queue:
        for rel, fns in sorted(cpg.by_file.items()):
            for fn in fns:
                if fn.sites:
                    queue.append((fn, 0, (f"{fn.rel_path}:{fn.name}",), 50.0))

    idx = 0
    while idx < len(queue):
        fn, hop, chain, score = queue[idx]
        idx += 1
        seeds.append((fn, chain, score))
        if hop >= max_hops:
            continue
        # Traverse upstream data-flow producers (callees whose return values feed `fn`!)
        for callee_nm in cpg.callees_of.get((fn.rel_path, fn.name), ()):
            for callee_fn in cpg.functions.get(callee_nm, ()):
                if not callee_fn.sites:
                    continue
                ckey = (callee_fn.rel_path, callee_fn.name)
                if ckey not in seen_fns:
                    seen_fns.add(ckey)
                    # Cross-file producer gets high causal priority: downstream crash often stems from upstream producer!
                    cross_bonus = 8.0 if callee_fn.rel_path != fn.rel_path else 0.0
                    queue.append((
                        callee_fn,
                        hop + 1,
                        chain + (f"<-dataflow:{callee_fn.rel_path}:{callee_fn.name}",),
                        score * 0.92 + cross_bonus,
                    ))
        # Traverse callers passing arguments into `fn`
        for caller_rel, caller_nm, _ln in cpg.callers_of.get(fn.name, ()):
            for caller_fn in cpg.functions.get(caller_nm, ()):
                if caller_fn.rel_path != caller_rel or not caller_fn.sites:
                    continue
                ckey = (caller_fn.rel_path, caller_fn.name)
                if ckey not in seen_fns:
                    seen_fns.add(ckey)
                    queue.append((
                        caller_fn,
                        hop + 1,
                        chain + (f"<-caller:{caller_fn.rel_path}:{caller_fn.name}",),
                        score * 0.85,
                    ))

    # Extract identifiers & keyword arguments referenced inside the failing test function(s)
    failing_test_idents: set[str] = set()
    _trivial_toks = {"self", "cls", "assert", "true", "false", "none", "pytest", "raises", "test", "return", "with", "from", "import"}
    fail_fn_names = set(re.findall(r"\b(test_[A-Za-z0-9_]+)\b", filtered_failure))
    for rel, fns in cpg.by_file.items():
        t_lns = mentioned_lines.get(rel, set())
        for fn in fns:
            if not fn.sites:
                matched_t = (fn.name in fail_fn_names) or (bool(t_lns) and any(fn.start_line <= l <= fn.end_line for l in t_lns))
                if matched_t:
                    try:
                        raw_t = (cpg.root / rel).read_bytes()[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
                        for tok in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\b", raw_t):
                            if tok.lower() not in _trivial_toks and not tok.startswith("test_"):
                                failing_test_idents.add(tok)
                    except Exception:
                        pass

    uncaught_leaf_excs = set(re.findall(
        r"\b(TypeError|ValueError|OverflowError|RecursionError|KeyError|IndexError|ZeroDivisionError)\b",
        filtered_failure,
    ))
    ranked_sites: list[CausalSite] = []
    kind_bonus = {"guard": 6.0, "loop": 6.0, "deref_stmt": 6.0, "assign_rhs": 6.0, "return_expr": 6.0, "except_type": 6.0, "func_body": 4.0}
    for fn, chain, base_score in seeds:
        file_lns = mentioned_lines.get(fn.rel_path, set())
        tb_lns = traceback_lines.get(fn.rel_path, set())
        file_seqs = exec_seq.get(fn.rel_path, {})
        for st in fn.sites:
            if file_seqs and st.kind != "func_body":
                if not any(st.start_line <= l <= st.end_line for l in file_seqs):
                    continue
            tb_exact = any(st.start_line <= l <= st.end_line for l in tb_lns)
            tb_near = (not tb_exact) and any(abs(st.start_line - l) <= 5 for l in tb_lns)
            exact_hit = any(st.start_line <= l <= st.end_line for l in file_lns)
            near_hit = (not exact_hit) and any(abs(st.start_line - l) <= 4 for l in file_lns)
            line_bonus = (28.0 if exact_hit else (10.0 if near_hit else 0.0)) + (55.0 if tb_exact else (22.0 if tb_near else 0.0))
            site_max_seq = max((file_seqs[l] for l in range(st.start_line, st.end_line + 1) if l in file_seqs), default=0)
            temporal_bonus = 18.0 * (site_max_seq / max_seq) if site_max_seq > 0 else 0.0
            site_toks = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\b", st.source_text)) if st.kind != "func_body" else set()
            overlap_bonus = 24.0 if (failing_test_idents and (site_toks & failing_test_idents)) else 0.0
            exc_join_bonus = 18.0 if (st.kind == "except_type" and uncaught_leaf_excs and not uncaught_leaf_excs.issubset(site_toks)) else 0.0
            enriched = dataclasses.replace(
                st,
                upstream_distance=len(chain) - 1,
                causal_chain=chain,
                suspiciousness=round(base_score + kind_bonus.get(st.kind, 0.0) + line_bonus + temporal_bonus + overlap_bonus + exc_join_bonus, 3),
            )
            ranked_sites.append(enriched)

    ranked_sites.sort(key=lambda s: (-s.suspiciousness, s.upstream_distance, s.rel_path, s.start_line))
    return ranked_sites


# =========================================================================== #
# 5. Z3 SMT Safety & Boundary Verifier + Angelic CEGIS Invention Engine       #
# =========================================================================== #

def z3_verify_uir_safety(term: UIRTerm) -> dict[str, Any]:
    """Prove loop-bound safety, division-by-zero freedom, and loop termination via Z3 SMT.

    Checks universal algebraic safety invariants on `term`:
      1. Loop index inbounds: inside `ITER_RANGE(idx, start, excl, step, body)`, if `body`
         indexes `INDEX(seq, idx_expr)`, verify `forall n >= 0, start <= idx < excl => 0 <= idx_expr < n`.
         Catches off-by-one `excl = n + 1` (`i <= n`) immediately with an exact Z3 counterexample!
      2. Loop termination: `step > 0` when counting up toward `excl`.
      3. Safe division: any `DIV(a, b)` inside an unguarded expression must not divide by 0
         without an enclosing guard `b != 0` / `b > 0`.
    """
    if not _HAS_Z3:
        return {"checked": False, "safe": True, "counterexamples": []}

    cex_list: list[dict[str, Any]] = []

    def _to_z3(t: UIRTerm, env: dict[str, Any]) -> Any | None:
        if t.op == "CONST_INT":
            return z3.IntVal(int(t.args[0]))
        if t.op == "VAR":
            nm = str(t.args[0])
            if nm not in env:
                env[nm] = z3.Int(nm)
            return env[nm]
        if t.op == "CAPACITY":
            seq_key = f"cap_{t.args[0].digest()[:8]}"
            if seq_key not in env:
                v = z3.Int(seq_key)
                env[seq_key] = v
            return env[seq_key]
        if t.op in ("ADD", "SUB", "MUL"):
            a, b = _to_z3(t.args[0], env), _to_z3(t.args[1], env)
            if a is None or b is None:
                return None
            return a + b if t.op == "ADD" else (a - b if t.op == "SUB" else a * b)
        if t.op in ("LT", "LE", "EQ", "NE"):
            a, b = _to_z3(t.args[0], env), _to_z3(t.args[1], env)
            if a is None or b is None:
                return None
            return a < b if t.op == "LT" else (a <= b if t.op == "LE" else (a == b if t.op == "EQ" else a != b))
        if t.op == "NOT":
            sub = _to_z3(t.args[0], env)
            return z3.Not(sub) if sub is not None else None
        if t.op in ("AND", "OR"):
            a, b = _to_z3(t.args[0], env), _to_z3(t.args[1], env)
            if a is None or b is None:
                return None
            return z3.And(a, b) if t.op == "AND" else z3.Or(a, b)
        return None

    def _collect_index_ops(t: UIRTerm) -> list[tuple[UIRTerm, UIRTerm]]:
        found: list[tuple[UIRTerm, UIRTerm]] = []
        if t.op == "INDEX":
            found.append((t.args[0], t.args[1]))
        for a in t.args:
            if isinstance(a, UIRTerm):
                found.extend(_collect_index_ops(a))
        return found

    def _walk_check(t: UIRTerm, path_conds: list[UIRTerm]) -> None:
        if t.op == "ITER_RANGE":
            idx_arg, start_t, excl_t, step_t, body_t = t.args
            idx_slot = str(idx_arg.args[0]) if isinstance(idx_arg, UIRTerm) and idx_arg.op == "VAR" else str(idx_arg)
            env: dict[str, Any] = {}
            idx_z = z3.Int(idx_slot)
            env[idx_slot] = idx_z
            start_z = _to_z3(start_t, env)
            excl_z = _to_z3(excl_t, env)
            step_z = _to_z3(step_t, env)
            if step_z is not None:
                s_term = z3.Solver()
                s_term.set("timeout", 200)
                s_term.add(step_z <= 0)
                if s_term.check() == z3.sat:
                    cex_list.append({"kind": "NON_POSITIVE_LOOP_STEP", "model": str(s_term.model())})
            if start_z is not None and excl_z is not None:
                for seq_t, idx_expr in _collect_index_ops(body_t):
                    cap_z = _to_z3(UIRTerm("CAPACITY", (seq_t,)), env)
                    ix_z = _to_z3(idx_expr, env)
                    if cap_z is not None and ix_z is not None:
                        solver = z3.Solver()
                        solver.set("timeout", 200)
                        solver.add(cap_z >= 0)
                        for pc in path_conds:
                            pcz = _to_z3(pc, env)
                            if pcz is not None:
                                solver.add(pcz)
                        solver.add(idx_z >= start_z)
                        solver.add(idx_z < excl_z)
                        solver.add(z3.Or(ix_z < 0, ix_z >= cap_z))
                        if solver.check() == z3.sat:
                            m = solver.model()
                            cex_list.append({
                                "kind": "OUT_OF_BOUNDS_INDEX",
                                "idx_expr": idx_expr.canonical_dict(),
                                "model": {str(d): str(m[d]) for d in m.decls()},
                            })
            _walk_check(body_t, path_conds)
            return

        if t.op == "GUARD":
            cond_t, then_t, else_t = t.args
            _walk_check(then_t, path_conds + [cond_t])
            _walk_check(else_t, path_conds + [UIRTerm("NOT", (cond_t,))])
            return

        if t.op == "DIV":
            env = {}
            den_z = _to_z3(t.args[1], env)
            if den_z is not None:
                solver = z3.Solver()
                solver.set("timeout", 200)
                for k, v in env.items():
                    if k.startswith("cap_"):
                        solver.add(v >= 0)
                for pc in path_conds:
                    pcz = _to_z3(pc, env)
                    if pcz is not None:
                        solver.add(pcz)
                solver.add(den_z == 0)
                # Only flag if denominator is a variable/capacity (not non-zero constant)
                if t.args[1].op != "CONST_INT" and solver.check() == z3.sat:
                    m = solver.model()
                    cex_list.append({
                        "kind": "POTENTIAL_DIV_BY_ZERO",
                        "den": t.args[1].canonical_dict(),
                        "model": {str(d): str(m[d]) for d in m.decls()},
                    })

        for a in t.args:
            if isinstance(a, UIRTerm):
                _walk_check(a, path_conds)

    _walk_check(canonicalize_uir(term), [])
    return {"checked": True, "safe": len(cex_list) == 0, "counterexamples": cex_list}


def synthesize_cegis_uir_candidates(
    site: CausalSite,
    cpg: ProjectCPG,
    *,
    angelic_obligations: Sequence[tuple[Mapping[str, Any], Any]] = (),
    failure_diagnostic: str = "",
) -> list[tuple[str, str, str]]:
    """First-principles UIR + Z3 CEGIS candidate generator at `site` (zero per-bug hand rules).

    Derives candidate UIR programs from:
      1. Z3 safety counterexample repair: when `z3_verify_uir_safety(canon_site)` finds an
         `OUT_OF_BOUNDS_INDEX` or `POTENTIAL_DIV_BY_ZERO` or `NON_POSITIVE_LOOP_STEP`,
         constructs the exact algebraic UIR transformation that makes Z3 return `UNSAT`!
      2. Semantic Lattice Refinement on `TRUTHY(x)` vs `NOT_NULL(x)` vs `CAPACITY(x) > 0`
         (resolving type/nullability conflations across Python, C, C++, and JS).
      3. Angelic Value & Guard STUN Synthesis over in-scope variables, parameters, and
         cross-module `ProjectCPG.pure_helpers` (inventing multi-branch guards, clamped
         bounds, state resets, and cross-file helper compositions without test literals!).

    Returns `[(reason_tag, patched_site_code, optional_extra_import)]`.
    """
    as_cond = site.kind == "guard"
    indent = ""
    if site.kind in ("func_body", "loop"):
        m_ind = re.match(r"^([ \t]*)", site.source_text)
        indent = m_ind.group(1) if m_ind else ""

    uir, ctx = lower_to_uir(
        site.source_text,
        site.language,
        c_params=site.c_params,
        as_condition=as_cond,
    )
    canon = canonicalize_uir(uir)
    proposals: list[tuple[str, str, str]] = []
    seen_code: set[str] = {site.source_text.strip()}

    def _emit_and_keep(tag: str, cand_uir: UIRTerm, extra_import: str = "") -> None:
        # Require Z3 safety check to pass on every synthesized UIR candidate!
        safety = z3_verify_uir_safety(cand_uir)
        if safety["checked"] and not safety["safe"]:
            # Allow division candidates only if original already had no guard and we are fixing another part
            if any(c["kind"] == "OUT_OF_BOUNDS_INDEX" for c in safety["counterexamples"]):
                return
        code = emit_uir(cand_uir, site.language, copy.deepcopy(ctx), indent=indent)
        norm = code.strip()
        if norm and norm not in seen_code:
            seen_code.add(norm)
            proposals.append((tag, code, extra_import))

    skip_uir_rewrite = site.kind in ("deref_stmt", "except_type") or (
        site.kind == "func_body" and ("else if" in site.source_text or site.source_text.count(";") > 3)
    )

    if not skip_uir_rewrite:
        # --- Mechanism A: Z3 Counterexample-Guided Safety Repair ---
        orig_safety = z3_verify_uir_safety(canon)
        for cex in orig_safety.get("counterexamples") or ():
            if cex["kind"] == "OUT_OF_BOUNDS_INDEX":
                for repaired in _z3_repair_loop_bounds(canon):
                    _emit_and_keep("Z3_CEGIS_INBOUNDS_PROOF", repaired)
            elif cex["kind"] == "POTENTIAL_DIV_BY_ZERO":
                for repaired in _z3_guard_division_zero(canon):
                    _emit_and_keep("Z3_CEGIS_NONZERO_DIV_PROOF", repaired)

        # --- Mechanism B: Nullability vs Truthiness & Relational Lattice Refinements ---
        for tag, refined in _semantic_lattice_refinements(canon):
            if site.language in ("c", "cpp") and tag in ("UIR_TRUTHY_TO_IS_NULL", "UIR_TRUTHY_TO_NOT_NULL", "UIR_NOT_TRUTHY_TO_IS_NULL"):
                continue
            _emit_and_keep(tag, refined)

    # --- Mechanism C: Angelic Obligation Synthesis (Live Frame + Cross-File CPG Helpers) ---
    if angelic_obligations and site.language == "python":
        for tag, expr_code, imp in _synthesize_from_python_angelic_obligations(site, cpg, angelic_obligations):
            norm = expr_code.strip()
            if norm and norm not in seen_code:
                seen_code.add(norm)
                proposals.append((tag, expr_code, imp))

    # --- Mechanism D: Cross-File CPG Helper Composition & Boundary Guard Invention ---
    for tag, code_str, imp in _propose_cpg_helper_and_guard_inventions(site, cpg, canon, ctx, indent, failure_diagnostic):
        norm = code_str.strip()
        if norm and norm not in seen_code:
            seen_code.add(norm)
            proposals.append((tag, code_str, imp))

    return proposals


def _z3_repair_loop_bounds(term: UIRTerm) -> list[UIRTerm]:
    """Derive exact exclusive loop bounds that satisfy Z3's `0 <= idx_expr < CAPACITY(seq)` invariant."""
    out: list[UIRTerm] = []
    if term.op == "ITER_RANGE":
        idx_arg, start_t, excl_t, step_t, body_t = term.args
        idx_var = idx_arg if isinstance(idx_arg, UIRTerm) else u_var(str(idx_arg))
        # Collect capacities of sequences indexed inside `body_t`, and check index offsets (`idx + 1` needs `cap - 1`!)
        max_offset = 0
        caps: list[UIRTerm] = []

        def _scan(n: UIRTerm) -> None:
            nonlocal max_offset
            if n.op == "INDEX":
                seq_t, ix_t = n.args
                cap_t = UIRTerm("CAPACITY", (seq_t,))
                if cap_t not in caps:
                    caps.append(cap_t)
                if ix_t.op == "ADD" and idx_var in ix_t.args:
                    other = ix_t.args[1] if ix_t.args[0] == idx_var else ix_t.args[0]
                    if isinstance(other, UIRTerm) and other.op == "CONST_INT":
                        max_offset = max(max_offset, int(other.args[0]))
            for a in n.args:
                if isinstance(a, UIRTerm):
                    _scan(a)

        _scan(body_t)
        for cap_t in caps:
            safe_excl = cap_t if max_offset == 0 else UIRTerm("SUB", (cap_t, u_int(max_offset)))
            cand = UIRTerm("ITER_RANGE", (idx_var, start_t, safe_excl, step_t, body_t))
            if z3_verify_uir_safety(cand)["safe"]:
                out.append(cand)
        # Also if `excl_t` is `ADD(X, 1)`, strip `+ 1`
        if excl_t.op == "ADD" and u_int(1) in excl_t.args:
            base_b = excl_t.args[0] if excl_t.args[1] == u_int(1) else excl_t.args[1]
            cand2 = UIRTerm("ITER_RANGE", (idx_var, start_t, base_b, step_t, body_t))
            if cand2 not in out and z3_verify_uir_safety(cand2)["safe"]:
                out.append(cand2)

    for i, a in enumerate(term.args):
        if isinstance(a, UIRTerm):
            for sub in _z3_repair_loop_bounds(a):
                nargs = list(term.args)
                nargs[i] = sub
                out.append(UIRTerm(term.op, tuple(nargs)))
    return out


def _z3_guard_division_zero(term: UIRTerm) -> list[UIRTerm]:
    out: list[UIRTerm] = []
    if term.op == "DIV":
        num, den = term.args
        out.append(UIRTerm("GUARD", (UIRTerm("EQ", (den, u_int(0))), u_int(0), term)))
    if term.op == "RETURN" and isinstance(term.args[0], UIRTerm) and term.args[0].op == "DIV":
        num, den = term.args[0].args
        out.append(UIRTerm("RETURN", (UIRTerm("GUARD", (UIRTerm("EQ", (den, u_int(0))), u_int(0), term.args[0])),)))
    for i, a in enumerate(term.args):
        if isinstance(a, UIRTerm) and term.op != "RETURN":
            for sub in _z3_guard_division_zero(a):
                nargs = list(term.args)
                nargs[i] = sub
                out.append(UIRTerm(term.op, tuple(nargs)))
    return out


_BOOL_VALUED_OPS = frozenset({
    "EQ", "NEQ", "LT", "LE", "GT", "GE", "AND", "OR", "NOT", "IS_NULL", "NOT_NULL", "CONST_BOOL",
})
_BOOL_VALUED_BUILTINS = frozenset({
    "hasattr", "isinstance", "issubclass", "callable", "bool",
    "startswith", "endswith", "isdigit", "isalpha", "isalnum",
})


def _is_bool_valued_uir(t: UIRTerm) -> bool:
    if t.op in _BOOL_VALUED_OPS:
        return True
    if t.op in ("RAW_PY", "RAW_EXPR") and t.args:
        raw_s = str(t.args[0])
        if any(op in raw_s for op in (" is ", " in ", " == ", " != ", " <= ", " >= ", " < ", " > ", " and ", " or ")):
            return True
    if t.op in ("CALL_FN", "CALL") and t.args and isinstance(t.args[0], UIRTerm) and t.args[0].op in ("CONST_STR", "SYMBOL"):
        fn_nm = str(t.args[0].args[0]).rsplit(".", 1)[-1]
        if fn_nm in _BOOL_VALUED_BUILTINS:
            return True
    return False


def _semantic_lattice_refinements(term: UIRTerm) -> list[tuple[str, UIRTerm]]:
    """Systematic semantic meaning refinements (nullability vs truthiness, strict vs non-strict relations, sign/op duals)."""
    out: list[tuple[str, UIRTerm]] = []

    if term.op == "TRUTHY":
        x = term.args[0]
        # Python descriptor protocol: `hasattr(obj, attr)` returns True even when `obj.attr = None` (disabled dunder);
        # refine to `(getattr(obj, attr, None) is not None)` WITHOUT creating a `bool is None` dead-branch tautology!
        if (
            x.op == "CALL_FN"
            and len(x.args) == 3
            and isinstance(x.args[0], UIRTerm)
            and x.args[0].op == "CONST_STR"
            and x.args[0].args[0] == "hasattr"
        ):
            getattr_call = UIRTerm("CALL_FN", (u_str("getattr"), x.args[1], x.args[2], u_null()))
            out.append(("UIR_DESCRIPTOR_NONNULL_GETATTR", UIRTerm("NOT_NULL", (getattr_call,))))
        # NEVER wrap boolean-valued expressions in `is None` / `is not None` (constant False/True dead-branch tautology!)
        if not _is_bool_valued_uir(x):
            out.append(("UIR_TRUTHY_TO_NOT_NULL", UIRTerm("NOT_NULL", (x,))))
            out.append(("UIR_TRUTHY_TO_IS_NULL", UIRTerm("IS_NULL", (x,))))
    elif term.op == "NOT" and isinstance(term.args[0], UIRTerm) and term.args[0].op == "TRUTHY":
        x = term.args[0].args[0]
        if not _is_bool_valued_uir(x):
            out.append(("UIR_NOT_TRUTHY_TO_IS_NULL", UIRTerm("IS_NULL", (x,))))
    elif term.op == "LT":
        a, b = term.args
        out.append(("UIR_BOUND_LT_TO_LE", UIRTerm("LE", (a, b))))
        if b.op == "ADD" and b.args[1] == u_int(1):
            out.append(("UIR_BOUND_EXCL_SHRINK", UIRTerm("LT", (a, b.args[0]))))
        out.append(("UIR_REL_SWAP_DIR", UIRTerm("LT", (b, a))))
        out.append(("UIR_REL_COMPLEMENT", UIRTerm("LE", (b, a))))
    elif term.op == "LE":
        a, b = term.args
        out.append(("UIR_BOUND_LE_TO_LT", UIRTerm("LT", (a, b))))
        out.append(("UIR_REL_SWAP_DIR", UIRTerm("LE", (b, a))))
    elif term.op == "EQ":
        out.append(("UIR_EQ_TO_NE", UIRTerm("NE", term.args)))
    elif term.op == "NE":
        out.append(("UIR_NE_TO_EQ", UIRTerm("EQ", term.args)))
    elif term.op == "IS_NULL":
        out.append(("UIR_IS_NULL_TO_NOT_NULL", UIRTerm("NOT_NULL", term.args)))
    elif term.op == "NOT_NULL":
        out.append(("UIR_NOT_NULL_TO_IS_NULL", UIRTerm("IS_NULL", term.args)))
    elif term.op in ("AND", "OR"):
        dual = "OR" if term.op == "AND" else "AND"
        a, b = term.args
        # 1. Logical Implication Refinement (`P and Q` -> `(not P) or Q`, and 3-way `X and P and Q` -> `X and ((not P) or Q)`)
        if term.op == "AND":
            if isinstance(a, UIRTerm) and a.op == "AND":
                out.append((
                    "UIR_BOOL_CONJUNCT_TO_IMPLIES",
                    UIRTerm("AND", (a.args[0], UIRTerm("OR", (UIRTerm("NOT", (a.args[1],)), b)))),
                ))
            out.append(("UIR_BOOL_AND_TO_IMPLIES", UIRTerm("OR", (UIRTerm("NOT", (a,)), b))))
        # 2. Operator-precedence re-association (`(x and y) or z` <-> `x and (y or z)`) BEFORE blunt op-flip
        if term.op == "OR" and isinstance(a, UIRTerm) and a.op == "AND":
            out.append(("UIR_BOOL_REASSOC_AND_OVER_OR", UIRTerm("AND", (a.args[0], UIRTerm("OR", (a.args[1], b))))))
        elif term.op == "OR" and isinstance(b, UIRTerm) and b.op == "AND":
            out.append(("UIR_BOOL_REASSOC_OR_OVER_AND", UIRTerm("AND", (UIRTerm("OR", (a, b.args[0])), b.args[1]))))
        elif term.op == "AND" and isinstance(a, UIRTerm) and a.op == "OR":
            out.append(("UIR_BOOL_REASSOC_OR_AND_LEFT", UIRTerm("OR", (a.args[0], UIRTerm("AND", (a.args[1], b))))))
        elif term.op == "AND" and isinstance(b, UIRTerm) and b.op == "OR":
            out.append(("UIR_BOOL_REASSOC_OR_AND_RIGHT", UIRTerm("OR", (UIRTerm("AND", (a, b.args[0])), b.args[1]))))
        out.append((f"UIR_BOOL_{term.op}_TO_{dual}", UIRTerm(dual, term.args)))
    elif term.op in ("ADD", "SUB"):
        dual = "SUB" if term.op == "ADD" else "ADD"
        out.append((f"UIR_ARITH_{term.op}_TO_{dual}", UIRTerm(dual, term.args)))
        if term.op == "ADD" and term.args[1] != u_int(1):
            out.append(("UIR_OFFSET_PLUS_ONE", UIRTerm("ADD", (term, u_int(1)))))
    elif term.op == "MUL":
        out.append(("UIR_ARITH_MUL_TO_ADD", UIRTerm("ADD", term.args)))
        out.append(("UIR_ARITH_MUL_TO_DIV", UIRTerm("DIV", term.args)))

    for idx, arg in enumerate(term.args):
        if isinstance(arg, UIRTerm):
            for sub_tag, sub_rep in _semantic_lattice_refinements(arg):
                nargs = list(term.args)
                nargs[idx] = sub_rep
                out.append((sub_tag, UIRTerm(term.op, tuple(nargs))))
    return out


_SAFE_PY_EVAL = {
    "abs": abs, "min": min, "max": max, "len": len, "sum": sum, "all": all, "any": any,
    "bool": bool, "int": int, "float": float, "str": str, "list": list, "tuple": tuple,
    "set": set, "dict": dict, "sorted": sorted, "reversed": reversed, "round": round,
    "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
}


def _synthesize_from_python_angelic_obligations(
    site: CausalSite,
    cpg: ProjectCPG,
    obligations: Sequence[tuple[Mapping[str, Any], Any]],
) -> list[tuple[str, str, str]]:
    """Bottom-up observational equivalence + STUN conditional synthesis over live frame & CPG helpers.

    Strictly forbids test-literal laundering: only variables in `sigma`, universal algebraic
    constants `{0, 1, -1, True, False, None, '', ()}`, and pure project helpers from `cpg`
    may appear in synthesized expressions.
    """
    if not obligations:
        return []
    shared_vars = sorted(
        set.intersection(*(set(sig.keys()) for sig, _ in obligations))
        - {"__builtins__", "__brain_angel__"}
    )
    shared_vars = [v for v in shared_vars if not v.startswith("__")][:8]
    if not shared_vars:
        return []

    # Build atomic candidate expressions (size 1 and size 2)
    atoms: list[tuple[str, str]] = [(v, "") for v in shared_vars]
    atoms.extend([("0", ""), ("1", ""), ("-1", ""), ("None", ""), ("True", ""), ("False", "")])

    depth1: list[tuple[str, str]] = list(atoms)
    for v in shared_vars:
        sample_v = obligations[0][0].get(v)
        depth1.append((f"({v} is None)", ""))
        depth1.append((f"({v} is not None)", ""))
        depth1.append((f"(not {v})", ""))
        if isinstance(sample_v, (int, float)) and not isinstance(sample_v, bool):
            depth1.extend([
                (f"abs({v})", ""), (f"(-{v})", ""),
                (f"({v} + 1)", ""), (f"({v} - 1)", ""),
                (f"max(0, {v})", ""), (f"({v} > 0)", ""), (f"({v} >= 0)", ""), (f"({v} < 0)", ""), (f"({v} == 0)", ""),
            ])
        elif isinstance(sample_v, str):
            depth1.extend([
                (f"{v}.strip()", ""), (f"{v}.lower()", ""), (f"len({v})", ""), (f"(len({v}) > 0)", ""),
            ])
        elif isinstance(sample_v, (list, tuple, set, dict)):
            depth1.extend([
                (f"len({v})", ""), (f"(len({v}) > 0)", ""), (f"(len({v}) - 1)", ""),
                (f"list({v})", ""), (f"tuple({v})", ""),
            ])

    # Pairwise combinations of variables
    for a, b in itertools.combinations(shared_vars, 2):
        depth1.extend([
            (f"({a} + {b})", ""), (f"({a} - {b})", ""), (f"({b} - {a})", ""),
            (f"({a} * {b})", ""), (f"min({a}, {b})", ""), (f"max({a}, {b})", ""),
            (f"({a} == {b})", ""), (f"({a} != {b})", ""),
            (f"({a} < {b})", ""), (f"({a} <= {b})", ""),
            (f"({a} and {b})", ""), (f"({a} or {b})", ""),
        ])

    # Cross-module pure helper composition from `cpg.pure_helpers` (solves `FOREIGN_IDENT_UNBOUND`!)
    loaded_helpers: dict[str, Callable[..., Any]] = {}
    mod_ns_cache: dict[str, dict[str, Any]] = {}
    for h_name, (h_rel, h_mod, h_arity) in list(cpg.pure_helpers.items())[:12]:
        if h_name == site.func_name or h_arity > min(2, len(shared_vars)) or h_arity == 0:
            continue
        hp = cpg.root / h_rel
        try:
            if h_rel not in mod_ns_cache:
                ns: dict[str, Any] = {"__builtins__": __builtins__}
                exec(compile(hp.read_text(encoding="utf-8"), str(hp), "exec"), ns)  # noqa: S102
                mod_ns_cache[h_rel] = ns
            ns = mod_ns_cache[h_rel]
            if callable(ns.get(h_name)):
                loaded_helpers[h_name] = ns[h_name]
                imp_stmt = f"from {h_mod} import {h_name}" if h_rel != site.rel_path else ""
                for perm in itertools.permutations(shared_vars, h_arity):
                    depth1.append((f"{h_name}({', '.join(perm)})", imp_stmt))
        except Exception:
            continue

    # Observational-equivalence evaluation across all obligations
    seen_obs: set[tuple[Any, ...]] = set()
    exact_matches: list[tuple[str, str, str]] = []
    partial_terms: list[tuple[str, str, list[bool]]] = []
    predicates: list[tuple[str, list[bool]]] = []

    eval_globals = {"__builtins__": _SAFE_PY_EVAL, **loaded_helpers}

    def _val_eq(actual: Any, target: Any) -> bool:
        if type(actual) is not type(target):
            return False
        return bool(actual == target)

    for expr_s, imp_s in depth1:
        try:
            code_obj = compile(expr_s, "<cegis_synth>", "eval")
        except SyntaxError:
            continue
        outs: list[Any] = []
        sat_vec: list[bool] = []
        bool_vec: list[bool] = []
        ok_all = True
        is_bool_pred = True
        for sig, expected in obligations:
            try:
                val = eval(code_obj, eval_globals, dict(sig))  # noqa: S307
            except Exception as exc:
                outs.append(("__ERR__", type(exc).__name__))
                sat_vec.append(False)
                is_bool_pred = False
                ok_all = False
                continue
            outs.append((type(val).__name__, repr(val)[:80]))
            matched = _val_eq(val, expected)
            sat_vec.append(matched)
            if not matched:
                ok_all = False
            if isinstance(val, bool):
                bool_vec.append(val)
            else:
                is_bool_pred = False

        obs_key = tuple(outs)
        if obs_key in seen_obs and not ok_all:
            continue
        seen_obs.add(obs_key)

        if ok_all:
            exact_matches.append(("ANGELIC_CEGIS_EXACT_SYNTH", expr_s, imp_s))
        elif any(sat_vec):
            partial_terms.append((expr_s, imp_s, sat_vec))
        if is_bool_pred and len(bool_vec) == len(obligations) and any(bool_vec) and not all(bool_vec):
            predicates.append((expr_s, bool_vec))

    # For guard sites, also synthesize guard strengthening `(orig and P)` and weakening `(orig or P)`!
    if site.kind == "guard" and predicates:
        try:
            orig_code = compile(site.source_text, "<orig_guard>", "eval")
            orig_bools = [bool(eval(orig_code, eval_globals, dict(sig))) for sig, _ in obligations]  # noqa: S307
            for pred_s, p_vec in predicates:
                if all(bool(ob and pv) == bool(exp) for ob, pv, (_, exp) in zip(orig_bools, p_vec, obligations)):
                    exact_matches.append(("ANGELIC_GUARD_STRENGTHEN", f"(({site.source_text}) and {pred_s})", ""))
                if all(bool(ob or pv) == bool(exp) for ob, pv, (_, exp) in zip(orig_bools, p_vec, obligations)):
                    exact_matches.append(("ANGELIC_GUARD_WEAKEN", f"(({site.source_text}) or {pred_s})", ""))
        except Exception:
            pass

    if exact_matches:
        return exact_matches[:8]

    # STUN Unification: combine two partial terms `(t_then, t_else)` under synthesized predicate `cond`!
    stun_matches: list[tuple[str, str, str]] = []
    for pred_s, p_vec in predicates[:24]:
        for t1_s, imp1, sat1 in partial_terms[:30]:
            if not all(s1 for pv, s1 in zip(p_vec, sat1) if pv):
                continue
            for t2_s, imp2, sat2 in partial_terms[:30]:
                if imp1 and imp2 and imp1 != imp2:
                    continue
                if all(s2 for pv, s2 in zip(p_vec, sat2) if not pv):
                    comb = f"({t1_s} if {pred_s} else {t2_s})"
                    stun_matches.append(("ANGELIC_STUN_GUARD_SYNTH", comb, imp1 or imp2))
                    if len(stun_matches) >= 4:
                        return stun_matches
    return stun_matches


def _propose_cpg_helper_and_guard_inventions(
    site: CausalSite,
    cpg: ProjectCPG,
    canon: UIRTerm,
    ctx: LoweringContext,
    indent: str,
    failure_diagnostic: str,
) -> list[tuple[str, str, str]]:
    """Invent missing null/bounds preconditions and cross-file helper normalizations on function bodies/returns."""
    out: list[tuple[str, str, str]] = []
    diag = (failure_diagnostic or "").lower()

    if site.kind == "except_type" and site.language == "python":
        # Exception Lattice Join (`ExistingType ⊔ UncaughtLeafExceptions`): never catches Exception/BaseException/AssertionError!
        leaf_excs = [
            e for e in ("TypeError", "ValueError", "OverflowError", "RecursionError", "KeyError", "IndexError", "ZeroDivisionError")
            if re.search(rf"\b{e}\b", failure_diagnostic or "")
        ]
        if leaf_excs:
            try:
                parsed_exc = ast.parse(f"({site.source_text.strip()})", mode="eval").body
                existing_items = [ast.unparse(el) for el in parsed_exc.elts] if isinstance(parsed_exc, ast.Tuple) else [ast.unparse(parsed_exc)]
            except SyntaxError:
                existing_items = [site.source_text.strip()]
            missing = [e for e in leaf_excs if e not in existing_items]
            if missing:
                joined_all = "(" + ", ".join(existing_items + missing) + ")"
                out.append(("UIR_EXCEPT_LATTICE_JOIN", joined_all, ""))
                for m_single in missing:
                    if len(missing) > 1:
                        out.append(("UIR_EXCEPT_LATTICE_JOIN_SINGLE", "(" + ", ".join(existing_items + [m_single]) + ")", ""))
        return out[:4]

    if site.kind == "func_body":
        # Find function metadata
        fn_meta = next((f for f in cpg.by_file.get(site.rel_path, ()) if f.name == site.func_name), None)
        if fn_meta is None:
            return out

        # 1. Missing Null / Empty Precondition Guard on pointer/nullable parameter (C, C++, JS, Python)
        if site.language in ("c", "cpp"):
            fallbacks = _infer_c_return_fallbacks(cpg.root / site.rel_path, fn_meta)
            null_tok = "NULL" if site.language == "c" else "nullptr"
            ptr_params = [pname for ptype, pname in fn_meta.params if "*" in ptype]
            for ret_prefix in fallbacks:
                ret_stmt = f"return {ret_prefix};" if ret_prefix else "return;"
                for pname in ptr_params:
                    guard_c = f"\n    if ({pname} == {null_tok}) {{ {ret_stmt} }}\n" + site.source_text
                    out.append(("CEGIS_NULL_PTR_PRECONDITION", guard_c, ""))
                if len(ptr_params) >= 2:
                    disj = " || ".join(f"({p} == {null_tok})" for p in ptr_params)
                    out.append(("CEGIS_MULTI_PTR_NULL_PRECONDITION", f"\n    if ({disj}) {{ {ret_stmt} }}\n" + site.source_text, ""))
            for ptype, pname in fn_meta.params:
                if any(t in ptype for t in ("int", "long", "ssize_t")) and pname in ("n", "len", "count", "idx", "index"):
                    ret_stmt = f"return {fallbacks[0]};" if fallbacks[0] else "return;"
                    guard_neg = f"\n    if ({pname} < 0) {{ {ret_stmt} }}\n" + site.source_text
                    out.append(("CEGIS_NEG_BOUND_PRECONDITION", guard_neg, ""))
        elif site.language == "python" and any(k in diag for k in ("none", "typeerror", "attributeerror", "indexerror", "zerodivision")):
            for _ptype, pname in fn_meta.params:
                if pname == "self":
                    continue
                out.append((
                    "CEGIS_PY_NONE_GUARD",
                    f"{indent}if {pname} is None:\n{indent}    return None\n{site.source_text}",
                    "",
                ))
        elif site.language in ("javascript", "typescript"):
            for _ptype, pname in fn_meta.params:
                out.append((
                    "CEGIS_JS_NULLISH_GUARD",
                    f"\n    if ({pname} === null || {pname} === undefined) {{ return null; }}\n" + site.source_text,
                    "",
                ))

    elif site.kind == "deref_stmt" and site.language in ("c", "cpp"):
        null_tok = "NULL" if site.language == "c" else "nullptr"
        # Extract chained or direct pointer receiver `A->B->C = ...` -> guard `A->B != NULL` and `A != NULL`
        lhs_part = site.source_text.split("=", 1)[0].strip()
        for m_ptr in re.finditer(r"([A-Za-z_]\w*(?:->[A-Za-z_]\w*)+)", lhs_part):
            chain_expr = m_ptr.group(1)
            segs = chain_expr.split("->")
            for k in range(len(segs) - 1, 0, -1):
                recv = "->".join(segs[:k])
                out.append(("CEGIS_DEREF_RECEIVER_NULL_GUARD", f"if ({recv} != {null_tok}) {{ {site.source_text} }}", ""))

    elif site.kind == "guard" and site.language in ("c", "cpp"):
        null_tok = "NULL" if site.language == "c" else "nullptr"
        # 1. Short-circuit null pointer argument passed to C comparison/string call (`fn(..., p->field) != 0` -> `((p->field == NULL) || (fn(...) != 0))` or `((p->field != NULL) && ...)`)
        for m_call_arg in re.finditer(r"([A-Za-z_]\w*\([^()]*\b([A-Za-z_]\w*->[A-Za-z_]\w*)\b[^()]*\)\s*(?:!=\s*0|==\s*0)?)", site.source_text):
            full_call_cmp, ptr_arg = m_call_arg.group(1), m_call_arg.group(2)
            if f"{ptr_arg} != {null_tok}" not in site.source_text and f"{ptr_arg} == {null_tok}" not in site.source_text:
                if "!=" in full_call_cmp:
                    guarded_or = site.source_text.replace(full_call_cmp, f"(({ptr_arg} == {null_tok}) || ({full_call_cmp}))", 1)
                    out.append(("CEGIS_CALL_ARG_NULL_SHORTCIRCUIT_OR", guarded_or, ""))
                guarded_and = site.source_text.replace(full_call_cmp, f"(({ptr_arg} != {null_tok}) && ({full_call_cmp}))", 1)
                out.append(("CEGIS_CALL_ARG_NULL_SHORTCIRCUIT_AND", guarded_and, ""))
        # 2. If guard dereferences `p->field` without checking `p != NULL`, synthesize `(p != NULL) && (cond)`
        for m_ptr in re.finditer(r"\b([A-Za-z_]\w*(?:->[A-Za-z_]\w*)*)->[A-Za-z_]\w*", site.source_text):
            recv = m_ptr.group(1)
            if f"{recv} != {null_tok}" not in site.source_text and f"{recv} == {null_tok}" not in site.source_text:
                out.append(("CEGIS_GUARD_DEREF_PREFIX", f"({recv} != {null_tok}) && ({site.source_text})", ""))

    if site.kind == "guard" and site.language == "python" and site.source_text.strip() != "False":
        out.append(("UIR_GUARD_OBSOLETE_BYPASS", "False", ""))

    # 2. Cross-module pure helper wrapping, string delimiter normalization & container materialization at `return_expr` / `assign_rhs`
    if site.kind in ("return_expr", "assign_rhs") and site.language == "python":
        if len(cpg.pure_helpers) <= 12:
            for h_name, (h_rel, h_mod, h_arity) in cpg.pure_helpers.items():
                if h_rel != site.rel_path and h_arity == 1 and h_name != site.func_name and h_name not in site.source_text:
                    imp = f"from {h_mod} import {h_name}"
                    out.append(("CPG_CROSS_FILE_HELPER_WRAP", f"{h_name}({site.source_text})", imp))
        if (
            any(tok in site.source_text for tok in ('f"', "f'", ".format(", '" ', "' ", " + ", " % "))
            and not site.source_text.endswith((".strip()", ".rstrip()"))
        ):
            out.append(("UIR_STR_TRAILING_DELIM_STRIP", f"({site.source_text}).strip()", ""))
        if not site.source_text.startswith(("list(", "tuple(")):
            out.append(("UIR_DEFENSIVE_SEQ_COPY", f"list({site.source_text})", ""))

    return out[:7]


def _infer_c_return_fallbacks(fp: pathlib.Path, fn_meta: FunctionCPG) -> list[str]:
    try:
        raw = fp.read_bytes()
        lo = max(0, fn_meta.start_byte - 64)
        header = raw[lo:min(fn_meta.end_byte, fn_meta.start_byte + 200)].decode("utf-8", errors="replace")
        header = re.sub(r"/\*.*?\*/", " ", header, flags=re.S).rsplit("*/", 1)[-1]
        header = re.sub(r"//[^\n]*", " ", header)
        sig = header.split("{", 1)[0]
        ret_part = sig.rsplit(fn_meta.name, 1)[0]
        if "*" in ret_part:
            return ["NULL" if fn_meta.language == "c" else "nullptr"]
        if "void" in ret_part:
            return [""]
        if "double" in ret_part or "float" in ret_part:
            cands = ['__builtin_nan("")', "0.0"]
            for ptype, pname in fn_meta.params:
                if ("double" in ptype or "float" in ptype) and "*" not in ptype:
                    cands.append(pname)
            return cands[:3]
        if "bool" in ret_part:
            return ["false" if fn_meta.language == "cpp" else "0"]
    except Exception:
        pass
    return ["0"]


# =========================================================================== #
# 6. Fast CoW / `/dev/shm` Polyglot Verifiers & Closed-Loop Repair Driver     #
# =========================================================================== #

def _shm_root() -> pathlib.Path:
    shm = pathlib.Path("/dev/shm")
    return shm if shm.is_dir() and os.access(shm, os.W_OK) else pathlib.Path(tempfile.gettempdir())


def _apply_site_patch(raw_file: bytes, site: CausalSite, replacement: str, extra_import: str = "") -> bytes:
    patched = raw_file[:site.start_byte] + replacement.encode("utf-8") + raw_file[site.end_byte:]
    if extra_import and site.language == "python":
        txt = patched.decode("utf-8", errors="replace")
        if extra_import not in txt:
            # Place after any `from __future__` imports and module docstring so syntax is always valid!
            try:
                mod = ast.parse(txt)
                insert_line = 1
                for stmt in mod.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        insert_line = getattr(stmt, "end_lineno", stmt.lineno) + 1
                    elif isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
                        insert_line = getattr(stmt, "end_lineno", stmt.lineno) + 1
                    else:
                        break
                lines = txt.splitlines(keepends=True)
                lines.insert(max(0, insert_line - 1), extra_import + "\n")
                patched = "".join(lines).encode("utf-8")
            except SyntaxError:
                return raw_file
    return patched


def _count_ts_error_nodes(node: Any) -> int:
    cnt = 1 if (node.type == "ERROR" or bool(getattr(node, "is_missing", False))) else 0
    for ch in node.children:
        if getattr(ch, "has_error", False) or ch.type == "ERROR":
            cnt += _count_ts_error_nodes(ch)
    return cnt


def _syntactically_valid(raw_bytes: bytes, language: str, orig_bytes: bytes | None = None) -> bool:
    lang = language.lower()
    if lang == "python":
        try:
            ast.parse(raw_bytes.decode("utf-8"))
            return True
        except (SyntaxError, UnicodeDecodeError):
            return False
    ts_lang = "cpp" if lang == "c" else lang
    try:
        tree = tsk.parse_bytes(ts_lang, raw_bytes)
        if not bool(getattr(tree.root_node, "has_error", False)):
            return True
        if orig_bytes is not None:
            orig_tree = tsk.parse_bytes(ts_lang, orig_bytes)
            if bool(getattr(orig_tree.root_node, "has_error", False)):
                return _count_ts_error_nodes(tree.root_node) <= _count_ts_error_nodes(orig_tree.root_node)
        return False
    except Exception:
        return True


def _run_suite_in_scratch(
    project_root: pathlib.Path,
    test_cmd: Sequence[str],
    overrides: Mapping[str, bytes] | None = None,
    *,
    timeout_s: float = 15.0,
) -> tuple[bool, int, str]:
    """Zero-copy `os.link` CoW clone in `/dev/shm` + fresh-bytecode isolated test run."""
    with tempfile.TemporaryDirectory(prefix="brain-scm-", dir=str(_shm_root())) as td:
        work = pathlib.Path(td) / "work"
        _fast_hardlink_clone(project_root, work)
        for rel, content in (overrides or {}).items():
            target = work / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            target.write_bytes(content)
            if target.suffix == ".py":
                pyc_dir = target.parent / "__pycache__"
                if pyc_dir.is_dir():
                    shutil.rmtree(pyc_dir, ignore_errors=True)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = str(pathlib.Path(td) / "pycache")
        env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1"
        env["UBSAN_OPTIONS"] = "print_stacktrace=1:halt_on_error=1"
        existing_pp = env.get("PYTHONPATH", "")
        src_dir = work / "src"
        pp_entries = [str(work)] + ([str(src_dir)] if src_dir.is_dir() else [])
        env["PYTHONPATH"] = os.pathsep.join(pp_entries + ([existing_pp] if existing_pp else []))

        try:
            proc = subprocess.run(
                list(test_cmd),
                cwd=str(work),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
            return proc.returncode == 0, proc.returncode, combined
        except subprocess.TimeoutExpired as exc:
            out = ((exc.stdout or b"") if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
            return False, 124, f"TIMEOUT:{out}"


def _fast_hardlink_clone(src: pathlib.Path, dst: pathlib.Path) -> None:
    src = src.resolve()
    dst.mkdir(parents=True, exist_ok=True)
    for cur, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in tsk.IGNORED_DIRS]
        rel = pathlib.Path(cur).relative_to(src)
        tdir = dst / rel
        tdir.mkdir(parents=True, exist_ok=True)
        for fn in files:
            if fn.endswith((".pyc", ".pyo")):
                continue
            sp = pathlib.Path(cur) / fn
            if sp.is_symlink():
                continue
            dp = tdir / fn
            try:
                os.link(sp, dp)
            except OSError:
                shutil.copy2(sp, dp)


class _PytestForkZygote:
    """Linux `os.fork()` CoW memory runner with pre-imported `pytest` (`~10 ms` per candidate).

    Clones `project_root` into `/dev/shm` ONCE, pre-imports `pytest` in the parent process,
    and evaluates each candidate patch inside an isolated `os.fork()` child that calls
    `os._exit(rc)` -- eliminating `~950 ms` cold Python/plugin boot and repeated repo cloning
    while guaranteeing 100% process-memory and `sys.modules` isolation across candidates.
    """

    def __init__(self, project_root: pathlib.Path, pytest_targets: Sequence[str]) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="brain-zygote-", dir=str(_shm_root()))
        self.work = pathlib.Path(self._tmp.name) / "work"
        _fast_hardlink_clone(project_root, self.work)
        self.targets = list(pytest_targets)
        self._orig_cache: dict[str, bytes | None] = {}
        local_pkgs: set[str] = {"_brain_angel_rt"}
        for base_d in (self.work, self.work / "src"):
            if base_d.is_dir():
                for child in base_d.iterdir():
                    if child.is_dir() and not child.name.startswith((".", "test")):
                        local_pkgs.add(child.name)
                    elif child.is_file() and child.suffix == ".py" and not child.name.startswith("test_"):
                        local_pkgs.add(child.stem)
        self._local_pkgs = local_pkgs
        self._direct_specs: list[tuple[Any, str, str | None, str]] = []
        if all("::" in t and "[" not in t for t in self.targets):
            specs: list[tuple[Any, str, str | None, str]] = []
            ok_compile = True
            for t in self.targets:
                parts = t.split("::")
                f_rel = parts[0]
                fp = self.work / f_rel
                if not fp.is_file() or len(parts) not in (2, 3):
                    ok_compile = False
                    break
                try:
                    cobj = compile(fp.read_bytes(), str(fp), "exec")
                    if len(parts) == 2:
                        specs.append((cobj, str(fp), None, parts[1]))
                    else:
                        specs.append((cobj, str(fp), parts[1], parts[2]))
                except Exception:
                    ok_compile = False
                    break
            if ok_compile and specs:
                self._direct_specs = specs
        try:
            import pytest as _pt  # noqa: F401
            self._pytest: Any = _pt
        except Exception:
            self._pytest = None
        # Self-verify that direct execution reproduces the baseline failure (if not, fall back to pytest.main!)
        if self._direct_specs and self.available:
            if self.run_fast({}, timeout_s=1.2):
                self._direct_specs = []

    @property
    def available(self) -> bool:
        return self._pytest is not None and hasattr(os, "fork")

    def run_fast(self, overrides: Mapping[str, bytes], *, timeout_s: float = 1.2) -> bool:
        if not self.available:
            return False
        import signal
        written: list[tuple[pathlib.Path, bytes | None]] = []
        try:
            for rel, data in overrides.items():
                fp = self.work / rel
                prev = fp.read_bytes() if fp.is_file() else None
                written.append((fp, prev))
                fp.parent.mkdir(parents=True, exist_ok=True)
                if fp.exists():
                    fp.unlink()
                fp.write_bytes(data)

            pid = os.fork()
            if pid == 0:
                try:
                    signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
                    signal.setitimer(signal.ITIMER_REAL, max(0.2, float(timeout_s)))
                    sys.dont_write_bytecode = True
                    devnull = os.open(os.devnull, os.O_WRONLY)
                    os.dup2(devnull, 1)
                    os.dup2(devnull, 2)
                    os.chdir(self.work)
                    src_d = self.work / "src"
                    if src_d.is_dir():
                        sys.path.insert(0, str(src_d))
                    sys.path.insert(0, str(self.work))
                    for mname in list(sys.modules.keys()):
                        top = mname.split(".", 1)[0]
                        if top in self._local_pkgs:
                            sys.modules.pop(mname, None)
                    if self._direct_specs:
                        import unittest as _ut
                        for cobj, fpath, cls_nm, fn_nm in self._direct_specs:
                            ns: dict[str, Any] = {"__name__": "__test_direct__", "__file__": fpath, "__builtins__": __builtins__}
                            exec(cobj, ns)  # noqa: S102
                            if cls_nm is None:
                                fn_obj = ns[fn_nm]
                                if getattr(fn_obj, "__code__", None) and fn_obj.__code__.co_argcount > 0:
                                    rc = int(self._pytest.main(["-q", "--tb=no", "-o", "addopts=", "-p", "no:cacheprovider", *self.targets]))
                                    os._exit(0 if rc == 0 else 1)
                                fn_obj()
                            else:
                                cls_obj = ns[cls_nm]
                                if isinstance(cls_obj, type) and issubclass(cls_obj, _ut.TestCase):
                                    cls_obj(fn_nm).debug()
                                else:
                                    inst = cls_obj()
                                    meth = getattr(inst, fn_nm)
                                    if (
                                        (getattr(meth, "__code__", None) and meth.__code__.co_argcount > 1)
                                        or hasattr(cls_obj, "setup_method")
                                        or hasattr(cls_obj, "setup_class")
                                        or hasattr(cls_obj, "teardown_method")
                                    ):
                                        rc = int(self._pytest.main(["-q", "--tb=no", "-o", "addopts=", "-p", "no:cacheprovider", *self.targets]))
                                        os._exit(0 if rc == 0 else 1)
                                    meth()
                        os._exit(0)
                    rc = int(self._pytest.main(["-q", "--tb=no", "-o", "addopts=", "-p", "no:cacheprovider", *self.targets]))
                    os._exit(0 if rc == 0 else 1)
                except BaseException:
                    os._exit(2)
            _, status = os.waitpid(pid, 0)
            return os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
        finally:
            for fp, prev in reversed(written):
                if prev is None:
                    fp.unlink(missing_ok=True)
                else:
                    if fp.exists():
                        fp.unlink()
                    fp.write_bytes(prev)

    def close(self) -> None:
        self._tmp.cleanup()


def _harvest_python_angelic_obligations(
    project_root: pathlib.Path,
    site: CausalSite,
    test_cmd: Sequence[str],
    *,
    zygote: _PytestForkZygote | None = None,
) -> list[tuple[dict[str, Any], Any]]:
    """Instrument `site` once in a scratch workspace to discover frame-local angelic obligations!"""
    if site.language != "python" or site.kind not in ("guard", "return_expr", "assign_rhs"):
        return []

    orig_bytes = (project_root / site.rel_path).read_bytes()
    helper_mod = (
        "import json, os\n"
        "_LOG = os.environ.get('BRAIN_ANGEL_LOG', '')\n"
        "_MODE = os.environ.get('BRAIN_ANGEL_MODE', 'record')\n"
        "_FIDX = int(os.environ.get('BRAIN_ANGEL_FLIP_IDX', '-1'))\n"
        "_CNT = 0\n"
        "def _probe(val, loc):\n"
        "    global _CNT\n"
        "    cur = _CNT\n"
        "    _CNT += 1\n"
        "    if _LOG:\n"
        "        safe = {k: v for k, v in loc.items() if isinstance(v, (int, float, str, bool, list, tuple, dict, type(None)))}\n"
        "        try:\n"
        "            with open(_LOG, 'a', encoding='utf-8') as f:\n"
        "                f.write(json.dumps({'loc': safe, 'val': val}, default=repr) + '\\n')\n"
        "        except Exception:\n"
        "            pass\n"
        "    if _FIDX >= 0 and cur != _FIDX:\n"
        "        return val\n"
        "    if _MODE == 'flip_bool':\n"
        "        return not bool(val)\n"
        "    if _MODE == 'plus_one' and isinstance(val, int) and not isinstance(val, bool):\n"
        "        return val + 1\n"
        "    if _MODE == 'minus_one' and isinstance(val, int) and not isinstance(val, bool):\n"
        "        return val - 1\n"
        "    if _MODE == 'zero':\n"
        "        return 0\n"
        "    return val\n"
    ).encode("utf-8")

    wrapped_expr = f"__import__('_brain_angel_rt')._probe(({site.source_text}), locals())"
    inst_bytes = _apply_site_patch(orig_bytes, site, wrapped_expr)
    if not _syntactically_valid(inst_bytes, "python"):
        return []

    def _exec_probe(ovr: Mapping[str, bytes]) -> bool:
        if zygote is not None and zygote.available:
            return zygote.run_fast(ovr, timeout_s=1.2)
        ok_s, _, _ = _run_suite_in_scratch(project_root, test_cmd, ovr, timeout_s=6.0)
        return ok_s

    with tempfile.TemporaryDirectory(prefix="brain-angel-", dir=str(_shm_root())) as td:
        log_file = pathlib.Path(td) / "trace.jsonl"
        old_log = os.environ.get("BRAIN_ANGEL_LOG")
        old_mode = os.environ.get("BRAIN_ANGEL_MODE")
        old_fidx = os.environ.get("BRAIN_ANGEL_FLIP_IDX")
        try:
            os.environ["BRAIN_ANGEL_LOG"] = str(log_file)
            os.environ["BRAIN_ANGEL_MODE"] = "record"
            os.environ["BRAIN_ANGEL_FLIP_IDX"] = "-1"
            overrides = {site.rel_path: inst_bytes, "_brain_angel_rt.py": helper_mod}
            _exec_probe(overrides)
            if not log_file.is_file():
                return []
            records = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not records:
                return []

            modes = ["flip_bool"] if site.kind == "guard" else ["plus_one", "minus_one", "zero", "flip_bool"]
            os.environ["BRAIN_ANGEL_LOG"] = ""
            for mode in modes:
                os.environ["BRAIN_ANGEL_MODE"] = mode
                os.environ["BRAIN_ANGEL_FLIP_IDX"] = "-1"
                if _exec_probe(overrides):
                    obligations: list[tuple[dict[str, Any], Any]] = []
                    for rec in records[:16]:
                        loc = rec["loc"]
                        v = rec["val"]
                        if mode == "flip_bool":
                            obligations.append((loc, not bool(v)))
                        elif mode == "plus_one" and isinstance(v, int):
                            obligations.append((loc, v + 1))
                        elif mode == "minus_one" and isinstance(v, int):
                            obligations.append((loc, v - 1))
                        elif mode == "zero":
                            obligations.append((loc, 0))
                    return obligations

            if len(records) > 1:
                os.environ["BRAIN_ANGEL_MODE"] = "flip_bool" if site.kind == "guard" else "plus_one"
                step_candidates = list(dict.fromkeys([len(records) - 1, 0, len(records) - 2]))
                for k_idx in step_candidates:
                    if not (0 <= k_idx < len(records)):
                        continue
                    os.environ["BRAIN_ANGEL_FLIP_IDX"] = str(k_idx)
                    if _exec_probe(overrides):
                        obligations = []
                        for idx_r, rec in enumerate(records[:20]):
                            v = rec["val"]
                            if idx_r == k_idx:
                                target_v = (not bool(v)) if site.kind == "guard" else (v + 1 if isinstance(v, int) else v)
                            else:
                                target_v = bool(v) if site.kind == "guard" else v
                            obligations.append((rec["loc"], target_v))
                        return obligations
        finally:
            for env_k, prev in (("BRAIN_ANGEL_LOG", old_log), ("BRAIN_ANGEL_MODE", old_mode), ("BRAIN_ANGEL_FLIP_IDX", old_fidx)):
                if prev is None:
                    os.environ.pop(env_k, None)
                else:
                    os.environ[env_k] = prev
    return []


def _collect_python_executed_lines(
    project_root: pathlib.Path,
    test_cmd: Sequence[str],
) -> dict[str, dict[int, int]]:
    """Collect dynamic Temporal Execution Graph `(rel_path -> {lineno: last_step_seq})`.

    Tracks `_IN_TEST` call depth so module-import noise (e.g., 950+ lines executed at `import`
    time before any `test_*` function begins) is excluded, and records the monotonic temporal
    step index `last_step_seq` so lines executed closest in time to the failure rank highest.
    """
    cmd0 = os.path.basename(test_cmd[0]) if test_cmd else ""
    if "python" not in cmd0 and "pytest" not in cmd0:
        return {}
    with tempfile.TemporaryDirectory(prefix="brain-teg-", dir=str(_shm_root())) as td:
        work = pathlib.Path(td) / "work"
        _fast_hardlink_clone(project_root, work)
        cov_json = pathlib.Path(td) / "cov.json"
        sitecust = work / "sitecustomize.py"
        sitecust.write_text(
            "import atexit, json, os, sys\n"
            f"_ROOT = os.path.realpath({str(work)!r}) + os.sep\n"
            f"_OUT = {str(cov_json)!r}\n"
            "_TEST_HITS = {}\n"
            "_ALL_HITS = {}\n"
            "_STATE = [0, 0]\n"  # [in_test_depth, monotonic_seq]
            "def _tr(frame, event, arg):\n"
            "    fn = frame.f_code.co_filename\n"
            "    if not fn.startswith(_ROOT) or 'sitecustomize' in fn:\n"
            "        return None\n"
            "    cname = frame.f_code.co_name\n"
            "    is_t = cname.startswith('test_') or '/tests/' in fn or os.path.basename(fn).startswith('test_')\n"
            "    if event == 'call' and cname.startswith('test_'):\n"
            "        _STATE[0] += 1\n"
            "        def _tr_test(f2, ev2, a2):\n"
            "            if ev2 == 'return' and f2 is frame:\n"
            "                _STATE[0] = max(0, _STATE[0] - 1)\n"
            "            return _tr(f2, ev2, a2)\n"
            "        return _tr_test\n"
            "    if not is_t and event in ('call', 'line'):\n"
            "        _STATE[1] += 1\n"
            "        rel = fn[len(_ROOT):]\n"
            "        _ALL_HITS.setdefault(rel, {})[frame.f_lineno] = _STATE[1]\n"
            "        if _STATE[0] > 0:\n"
            "            _TEST_HITS.setdefault(rel, {})[frame.f_lineno] = _STATE[1]\n"
            "    return _tr\n"
            "sys.settrace(_tr)\n"
            "@atexit.register\n"
            "def _dump():\n"
            "    sys.settrace(None)\n"
            "    chosen = _TEST_HITS if _TEST_HITS else _ALL_HITS\n"
            "    with open(_OUT, 'w', encoding='utf-8') as f:\n"
            "        json.dump(chosen, f)\n",
            encoding="utf-8",
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        src_dir = work / "src"
        pp = [str(work)] + ([str(src_dir)] if src_dir.is_dir() else [])
        if env.get("PYTHONPATH"):
            pp.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pp)
        try:
            subprocess.run(list(test_cmd), cwd=str(work), env=env, capture_output=True, text=True, timeout=10.0)
            if cov_json.is_file():
                raw = json.loads(cov_json.read_text(encoding="utf-8"))
                return {
                    k: {int(ln_s): int(seq) for ln_s, seq in v.items()}
                    for k, v in raw.items()
                    if not k.startswith("tests/") and not os.path.basename(k).startswith("test_")
                }
        except Exception:
            pass
    return {}


@dataclass
class CausalRepairResult:
    repaired: bool
    status: str
    rel_path: str | None = None
    func_name: str | None = None
    mechanism: str | None = None
    patched_files: dict[str, str] = field(default_factory=dict)
    causal_chain: list[str] = field(default_factory=list)
    admitted_law_id: str | None = None
    candidates_evaluated: int = 0
    elapsed_ms: float = 0.0
    baseline_failure_excerpt: str = ""


def _capture_python_multi_site_frames(
    project_root: pathlib.Path,
    sites: Sequence[CausalSite],
    pytest_targets: Sequence[str],
    *,
    max_frames_per_site: int = 4,
    timeout_s: float = 5.0,
) -> dict[tuple[str, int], list[dict[str, dict[str, Any]]]]:
    """Capture runtime local-variable type/emptiness snapshots across ALL `sites` in ONE trace run."""
    py_sites = [s for s in sites if s.language == "python"]
    if not py_sites or not pytest_targets:
        return {}
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain_mfrm_", dir=str(_shm_root())))
    try:
        _fast_hardlink_clone(project_root, work)
        out_json = work / "_brain_mframes.json"
        targets_map: dict[str, dict[int, str]] = {}
        for s in py_sites:
            abs_p = os.path.realpath(str(work / s.rel_path))
            targets_map.setdefault(abs_p, {})[int(s.start_line)] = f"{s.rel_path}:{s.start_line}"
        driver = (
            "import json, os, sys, pytest\n"
            f"TARGETS = {targets_map!r}\n"
            f"MAX_F = {int(max_frames_per_site)}\n"
            "OUT = {}\n"
            "IN_TEST = [0]\n"
            "def _snap(loc):\n"
            "    d = {}\n"
            "    for k, v in list(loc.items()):\n"
            "        if k.startswith('__') or callable(v):\n"
            "            continue\n"
            "        tp = type(v)\n"
            "        mro = [c.__name__ for c in getattr(tp, '__mro__', (tp,))[:4]]\n"
            "        is_seq = isinstance(v, (list, tuple))\n"
            "        elem_mro = []\n"
            "        if is_seq and len(v) > 0:\n"
            "            etp = type(v[0])\n"
            "            elem_mro = [c.__name__ for c in getattr(etp, '__mro__', (etp,))[:4]]\n"
            "        try:\n"
            "            emp = (not bool(v))\n"
            "        except Exception:\n"
            "            emp = False\n"
            "        ln = len(v) if isinstance(v, (str, list, tuple, dict, set)) else -1\n"
            "        d[k] = {'type': tp.__name__, 'mro': mro, 'is_seq': is_seq, 'is_str': isinstance(v, str), 'is_none': (v is None), 'empty': emp, 'len': ln, 'elem_mro': elem_mro}\n"
            "    return d\n"
            "def _tr(frame, event, arg):\n"
            "    co = frame.f_code\n"
            "    base = os.path.basename(co.co_filename)\n"
            "    is_tf = base.startswith('test_') or base.endswith('_test.py')\n"
            "    if is_tf and co.co_name.startswith('test_'):\n"
            "        if event == 'call':\n"
            "            IN_TEST[0] += 1\n"
            "        elif event == 'return' and IN_TEST[0] > 0:\n"
            "            IN_TEST[0] -= 1\n"
            "        return _tr\n"
            "    if IN_TEST[0] <= 0:\n"
            "        return None\n"
            "    rp = os.path.realpath(co.co_filename)\n"
            "    lmap = TARGETS.get(rp)\n"
            "    if lmap is not None:\n"
            "        if event == 'line':\n"
            "            key = lmap.get(frame.f_lineno)\n"
            "            if key is not None:\n"
            "                lst = OUT.setdefault(key, [])\n"
            "                if len(lst) < MAX_F:\n"
            "                    lst.append(_snap(frame.f_locals))\n"
            "        return _tr\n"
            "    return None\n"
            "sys.settrace(_tr)\n"
            "try:\n"
            f"    pytest.main(['-q', '--tb=no', '-o', 'addopts=', '-p', 'no:cacheprovider', *{list(pytest_targets)!r}])\n"
            "finally:\n"
            "    sys.settrace(None)\n"
            f"    open({str(out_json)!r}, 'w').write(json.dumps(OUT))\n"
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        src_d = work / "src"
        py_paths = [str(src_d), str(work)] if src_d.is_dir() else [str(work)]
        if env.get("PYTHONPATH"):
            py_paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(py_paths)
        subprocess.run(
            [sys.executable, "-c", driver],
            cwd=str(work),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_s,
            check=False,
        )
        if out_json.is_file():
            raw_d = json.loads(out_json.read_text(encoding="utf-8"))
            res: dict[tuple[str, int], list[dict[str, dict[str, Any]]]] = {}
            for k_str, flist in raw_d.items():
                r_path, ln_s = k_str.rsplit(":", 1)
                res[(r_path, int(ln_s))] = flist
            return res
    except Exception:
        return {}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {}


def _capture_python_site_frames(
    project_root: pathlib.Path,
    site: CausalSite,
    pytest_targets: Sequence[str],
    *,
    max_frames: int = 4,
    timeout_s: float = 4.0,
) -> list[dict[str, dict[str, Any]]]:
    """Capture structured runtime type/emptiness signatures of local variables at `site` for `pytest_targets`."""
    if site.language != "python" or not pytest_targets:
        return []
    work = pathlib.Path(tempfile.mkdtemp(prefix="brain_frm_", dir=str(_shm_root())))
    try:
        _fast_hardlink_clone(project_root, work)
        out_json = work / "_brain_frames.json"
        target_abs = os.path.realpath(str(work / site.rel_path))
        driver = (
            "import json, os, sys, pytest\n"
            f"TARGET_FILE = {target_abs!r}\n"
            f"TARGET_LINE = {int(site.start_line)}\n"
            f"MAX_FRAMES = {int(max_frames)}\n"
            "FRAMES = []\n"
            "def _snap(loc):\n"
            "    d = {}\n"
            "    for k, v in list(loc.items()):\n"
            "        if k.startswith('__') or callable(v):\n"
            "            continue\n"
            "        tp = type(v)\n"
            "        mro = [c.__name__ for c in getattr(tp, '__mro__', (tp,))[:4]]\n"
            "        is_seq = isinstance(v, (list, tuple))\n"
            "        elem_mro = []\n"
            "        if is_seq and len(v) > 0:\n"
            "            etp = type(v[0])\n"
            "            elem_mro = [c.__name__ for c in getattr(etp, '__mro__', (etp,))[:4]]\n"
            "        try:\n"
            "            emp = (not bool(v))\n"
            "        except Exception:\n"
            "            emp = False\n"
            "        ln = len(v) if isinstance(v, (str, list, tuple, dict, set)) else -1\n"
            "        d[k] = {'type': tp.__name__, 'mro': mro, 'is_seq': is_seq, 'is_str': isinstance(v, str), 'is_none': (v is None), 'empty': emp, 'len': ln, 'elem_mro': elem_mro}\n"
            "    return d\n"
            "def _tr(frame, event, arg):\n"
            "    if len(FRAMES) >= MAX_FRAMES:\n"
            "        return None\n"
            "    fn = frame.f_code.co_filename\n"
            "    if os.path.realpath(fn) == TARGET_FILE:\n"
            "        if event == 'line' and frame.f_lineno == TARGET_LINE:\n"
            "            FRAMES.append(_snap(frame.f_locals))\n"
            "        return _tr\n"
            "    return _tr\n"
            "sys.settrace(_tr)\n"
            "try:\n"
            f"    pytest.main(['-q', '--tb=no', '-o', 'addopts=', '-p', 'no:cacheprovider', *{list(pytest_targets)!r}])\n"
            "finally:\n"
            "    sys.settrace(None)\n"
            f"    open({str(out_json)!r}, 'w').write(json.dumps(FRAMES))\n"
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        src_d = work / "src"
        py_paths = [str(src_d), str(work)] if src_d.is_dir() else [str(work)]
        if env.get("PYTHONPATH"):
            py_paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(py_paths)
        subprocess.run(
            [sys.executable, "-c", driver],
            cwd=str(work),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_s,
            check=False,
        )
        if out_json.is_file():
            return json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return []
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return []


def _propose_petri_net_morphisms(
    site: CausalSite,
    cpg: ProjectCPG,
    frames: Sequence[Mapping[str, Mapping[str, Any]]],
) -> list[tuple[str, str, str]]:
    """Type-directed Petri-net component reachability over live frame types & AST-mined repo methods."""
    if site.language != "python" or site.kind not in ("assign_rhs", "return_expr") or not frames:
        return []
    f0 = frames[0]
    out: list[tuple[str, str, str]] = []
    site_idents = set(re.findall(r"\b([A-Za-z_]\w*)\b", site.source_text))

    def _bind_method_args(req_params: Sequence[str], exclude_var: str) -> list[str] | None:
        bound: list[str] = []
        for p in req_params:
            if p in f0 and p != exclude_var:
                bound.append(p)
            else:
                return None
        return bound

    # 1. Petri-Net Functor / Comprehension Lift: `seq_v: Iterable[ClassC]` + `ClassC.m(req_params)` -> `[item.m(...) for item in seq_v]`
    for v_name, meta in f0.items():
        if v_name.startswith("_") or not meta.get("is_seq"):
            continue
        for cls_nm in meta.get("elem_mro") or ():
            for m_name, req_params in cpg.class_methods.get(cls_nm, ()):
                bound = _bind_method_args(req_params, v_name)
                if bound is not None:
                    call_s = f"_item.{m_name}({', '.join(bound)})"
                    out.append(("REPO_PETRI_COMPREHENSION_MAP", f"[{call_s} for _item in {v_name}]", ""))
                    out.append(("REPO_PETRI_COMPREHENSION_FILTER_NONNULL", f"[_r for _r in ({call_s} for _item in {v_name}) if _r is not None]", ""))

    # 2. Sequence-to-String Join Morphism when variable in `site.source_text` is a sequence of strings at runtime
    for v_name in sorted(site_idents):
        meta = f0.get(v_name)
        if not meta:
            continue
        if meta.get("is_seq"):
            out.append(("REPO_PETRI_SEQ_JOIN_COMMA", f"', '.join(str(_x) for _x in {v_name})", ""))
            if v_name != site.source_text.strip():
                rep_join = re.sub(rf"\b{re.escape(v_name)}\b", f"', '.join(str(_x) for _x in {v_name})", site.source_text)
                if rep_join != site.source_text:
                    out.append(("REPO_PETRI_EMBEDDED_SEQ_JOIN", rep_join, ""))
        # 3. Direct repo query method on receiver variable in `site.source_text`
        for cls_nm in meta.get("mro") or ():
            for m_name, req_params in cpg.class_methods.get(cls_nm, ()):
                if m_name in site.source_text:
                    continue
                bound = _bind_method_args(req_params, v_name)
                if bound is not None:
                    out.append(("REPO_PETRI_DIRECT_QUERY_METHOD", f"{v_name}.{m_name}({', '.join(bound)})", ""))

    return out[:4]


def _eval_frame_guard_kind(guard_kind: str, var_name: str, frame: Mapping[str, Mapping[str, Any]]) -> bool | None:
    m = frame.get(var_name)
    if m is None:
        return None
    if guard_kind == "is_none":
        return bool(m["is_none"])
    if guard_kind == "is_not_none":
        return not bool(m["is_none"])
    if guard_kind == "empty":
        return bool(m["empty"])
    if guard_kind == "nonempty":
        return not bool(m["empty"])
    if guard_kind == "is_seq":
        return bool(m["is_seq"])
    if guard_kind == "not_seq":
        return not bool(m["is_seq"])
    if guard_kind == "is_str":
        return bool(m["is_str"])
    if guard_kind == "not_str":
        return not bool(m["is_str"])
    return None


def _attempt_dual_program_splice(
    root: pathlib.Path,
    site: CausalSite,
    cand_tag: str,
    cand_code: str,
    extra_imp: str,
    orig_b: bytes,
    pos_frames: Sequence[Mapping[str, Mapping[str, Any]]],
    reg_nodes: Sequence[str],
    norm_test_cmd: Sequence[str],
) -> tuple[bytes, str] | None:
    """Counterexample-Partitioned Dual-Program Splicing (`(cand_code if G else orig)`).

    Invoked ONLY when `cand_code` ALREADY passed `fast_targets` (`pos_frames`) and broke `reg_nodes`,
    while `site.source_text` passes `reg_nodes` and fails `fast_targets`.
    """
    if site.language != "python" or site.kind not in ("assign_rhs", "return_expr", "guard") or not pos_frames or not reg_nodes:
        return None
    neg_map = _capture_python_multi_site_frames(root, [site], reg_nodes[:3], max_frames_per_site=4, timeout_s=4.0)
    neg_frames = neg_map.get((site.rel_path, int(site.start_line)), [])
    if not neg_frames:
        return None

    shared_vars = sorted(
        set.intersection(*(set(f.keys()) for f in (*pos_frames, *neg_frames)))
    )
    site_idents = set(re.findall(r"\b([A-Za-z_]\w*)\b", site.source_text))
    # Prioritize variables mentioned in `site.source_text` or `cand_code`
    cand_idents = site_idents | set(re.findall(r"\b([A-Za-z_]\w*)\b", cand_code))
    ordered_vars = sorted(shared_vars, key=lambda v: (0 if v in cand_idents else 1, v))

    guard_templates = [
        ("is_seq", "isinstance({v}, (list, tuple))"),
        ("not_seq", "(not isinstance({v}, (list, tuple)))"),
        ("is_none", "({v} is None)"),
        ("is_not_none", "({v} is not None)"),
        ("empty", "(not {v})"),
        ("nonempty", "bool({v})"),
        ("is_str", "isinstance({v}, str)"),
        ("not_str", "(not isinstance({v}, str))"),
    ]

    separating_guards: list[str] = []
    for v in ordered_vars:
        if v.startswith("_") or v == "self":
            continue
        for g_kind, g_tmpl in guard_templates:
            pos_vals = [_eval_frame_guard_kind(g_kind, v, f) for f in pos_frames]
            neg_vals = [_eval_frame_guard_kind(g_kind, v, f) for f in neg_frames]
            if all(pv is True for pv in pos_vals) and all(nv is False for nv in neg_vals):
                separating_guards.append(g_tmpl.format(v=v))
                if len(separating_guards) >= 3:
                    break
        if len(separating_guards) >= 3:
            break

    for g_expr in separating_guards[:2]:
        spliced_code = f"(({cand_code}) if {g_expr} else ({site.source_text}))"
        spliced_b = _apply_site_patch(orig_b, site, spliced_code, extra_import=extra_imp)
        if not _syntactically_valid(spliced_b, site.language, orig_b):
            continue
        ok_full, _, _ = _run_suite_in_scratch(root, norm_test_cmd, {site.rel_path: spliced_b})
        if ok_full:
            return spliced_b, f"DUAL_PROGRAM_SPLICE:{cand_tag}+IF({g_expr})"
    return None


def _extract_pytest_failed_nodes(output: str) -> list[str]:
    """Extract pytest node IDs from `FAILED <node_id> [- <reason>]` lines, preserving spaces inside `[...]`."""
    nodes: list[str] = []
    for m in re.finditer(r"^FAILED\s+(.+?)(?:\s+-\s+.*)?$", output, re.M):
        nid = m.group(1).strip()
        if nid and nid not in nodes:
            nodes.append(nid)
    return nodes


def repair_project_causally(
    project_root: pathlib.Path | str,
    test_cmd: Sequence[str],
    *,
    law_store: CausalLawStore | None = None,
    symptom_symbols: Sequence[str] = (),
    max_sites: int = 28,
    max_candidates: int = 64,
    admit_learned_law: bool = True,
    apply_in_place: bool = False,
    skill_store: Any = None,
    invariant_store: Any = None,
    origin: str = "",
    nexus_enabled: bool = True,
) -> CausalRepairResult:
    """End-to-end zero-model causal localization, UIR transfer, Angelic CEGIS, and verification."""
    t0 = time.perf_counter_ns()
    root = pathlib.Path(project_root).resolve()
    store = law_store if law_store is not None else CausalLawStore()

    is_pytest = any("pytest" in part for part in test_cmd)
    norm_test_cmd = list(test_cmd)
    if is_pytest and "-rf" not in norm_test_cmd:
        # Insert `-o addopts= -rf` right after `pytest` so repo `addopts` (--cov) never break runs
        # and `FAILED <node_id>` is always emitted in short test summary info!
        pt_idx = next(i for i, p in enumerate(norm_test_cmd) if "pytest" in p)
        norm_test_cmd = norm_test_cmd[:pt_idx + 1] + ["-o", "addopts=", "-rf"] + norm_test_cmd[pt_idx + 1:]

    # 1. Baseline check: never fabricate a repair if baseline already passes!
    base_ok, _base_rc, base_out = _run_suite_in_scratch(root, norm_test_cmd)
    if base_ok:
        return CausalRepairResult(
            repaired=False,
            status="REFUSED__BASELINE_ALREADY_PASSING",
            elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
        )

    # Extract specific failing pytest node IDs from `base_out`
    focused_cmd: Sequence[str] = norm_test_cmd
    fast_targets: list[str] = []
    initial_failed_nodes: list[str] = []
    if is_pytest:
        initial_failed_nodes = _extract_pytest_failed_nodes(base_out)
        if initial_failed_nodes and len(initial_failed_nodes) <= 24:
            fast_targets = initial_failed_nodes[:12]
            focused_cmd = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *fast_targets]
        else:
            # Fall back to positional test path args from `test_cmd`
            pt_idx = next(i for i, p in enumerate(test_cmd) if "pytest" in p)
            fast_targets = [a for a in test_cmd[pt_idx + 1:] if not a.startswith("-")]

    zygote = _PytestForkZygote(root, fast_targets) if (is_pytest and fast_targets) else None
    try:
        def _verify_candidate(overrides: Mapping[str, bytes]) -> bool:
            if zygote is not None and zygote.available:
                if not zygote.run_fast(overrides, timeout_s=1.2):
                    return False
            elif focused_cmd != norm_test_cmd:
                ok_fast, _, _ = _run_suite_in_scratch(root, focused_cmd, overrides, timeout_s=6.0)
                if not ok_fast:
                    return False
            ok_full, _, _ = _run_suite_in_scratch(root, norm_test_cmd, overrides)
            return ok_full

        # 2. Build Multi-File Polyglot CPG + Dynamic TEG & Trace Backward/Forward Causal Lineage
        cpg = build_project_cpg(root)
        exec_lines = _collect_python_executed_lines(root, focused_cmd)
        sites = trace_causal_lineage(
            cpg,
            symptom_symbols=symptom_symbols,
            failure_output=base_out,
            executed_lines=exec_lines,
        )[:max_sites]
        if not sites:
            return CausalRepairResult(
                repaired=False,
                status="OPEN__NO_CAUSAL_SITES_IN_CPG",
                elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                baseline_failure_excerpt=base_out[-500:],
            )

        evaluated = 0
        file_cache: dict[str, bytes] = {}
        nexus = None
        if nexus_enabled:
            try:
                from canonical.swe_kernel import causal_nexus_v1 as nexus  # noqa: PLC0415
            except Exception:
                nexus = None

        def _raw_of(rel: str) -> bytes:
            if rel not in file_cache:
                file_cache[rel] = (root / rel).read_bytes()
            return file_cache[rel]

        # 3. Pass 1 — O(1) Quotiented Cross-Language UIR Law Store Transfer (Ordered first, never blocks fallback!)
        for site in sites:
            if evaluated >= max_candidates:
                break
            as_cond = site.kind == "guard"
            m_ind = re.match(r"^([ \t]*)", site.source_text) if site.kind in ("func_body", "loop") else None
            indent = m_ind.group(1) if m_ind else ""
            for law, candidate_code in store.propose_transfers(
                site.source_text,
                site.language,
                c_params=site.c_params,
                as_condition=as_cond,
                indent=indent,
            ):
                if evaluated >= max_candidates:
                    break
                orig_b = _raw_of(site.rel_path)
                patched_bytes = _apply_site_patch(orig_b, site, candidate_code)
                if not _syntactically_valid(patched_bytes, site.language, orig_b):
                    continue
                evaluated += 1
                if _verify_candidate({site.rel_path: patched_bytes}):
                    law.verified_transfers += 1
                    if site.language not in law.origin_languages:
                        law.origin_languages.append(site.language)
                    store.save()
                    patched_str = patched_bytes.decode("utf-8")
                    if apply_in_place:
                        (root / site.rel_path).write_bytes(patched_bytes)
                    return CausalRepairResult(
                        repaired=True,
                        status="VERIFIED__ZERO_SHOT_UIR_LAW_TRANSFER",
                        rel_path=site.rel_path,
                        func_name=site.func_name,
                        mechanism=f"UIR_LAW_TRANSFER:{law.law_id}",
                        patched_files={site.rel_path: patched_str},
                        causal_chain=list(site.causal_chain),
                        admitted_law_id=law.law_id,
                        candidates_evaluated=evaluated,
                        elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                        baseline_failure_excerpt=base_out[-400:],
                    )

        # 3.4 Specification-contract pass — the test's own `pytest.raises` is the missing contract.
        #
        # A `DID NOT RAISE` failure has no wrong expression to blame: the program is missing a
        # statement. The test states which exception it expects, for which call, and with which
        # argument; the guard that enforces it is one line. Guards accumulate: a guard that strictly
        # shrinks the failing set is kept and the next one is stacked on top, because a real commit
        # often states two contracts in the same method.
        spec_module = None
        if is_pytest:
            try:
                from canonical.swe_kernel import spec_contract_synthesis_v1 as spec_module  # noqa: PLC0415
            except Exception:
                spec_module = None
        if spec_module is not None:
            test_sources: list[str] = []
            seen_paths: set[str] = set()
            for node_id in initial_failed_nodes:
                rel = node_id.split("::", 1)[0]
                if rel and rel not in seen_paths and (root / rel).is_file():
                    seen_paths.add(rel)
                    test_sources.append((root / rel).read_text(encoding="utf-8", errors="replace"))
            active_guards: dict[tuple[str, str], list[str]] = {}
            active_tags: list[str] = []
            cur_failed = set(initial_failed_nodes)

            def _compose_guard_overrides() -> dict[str, bytes] | None:
                files: dict[str, dict[str, bytes]] = {}
                for (rel, _fname) in active_guards:
                    files.setdefault(rel, {})
                for (rel, _fname), _gtexts in active_guards.items():
                    files.setdefault(rel, {})
                per_rel: dict[str, bytes] = {}
                for rel in files:
                    per_rel[rel] = _raw_of(rel)
                for (rel, fname), gtexts in active_guards.items():
                    site = None
                    for fn_cpg in cpg.functions.get(fname, []):
                        if fn_cpg.rel_path != rel:
                            continue
                        site = next((st for st in fn_cpg.sites if st.kind == "func_body"), None)
                        if site is not None:
                            break
                    if site is None:
                        return None
                    per_rel[rel] = _apply_site_patch(per_rel[rel], site, "".join(gtexts) + site.source_text)
                for rel, raw in per_rel.items():
                    if not _syntactically_valid(raw, "python", _raw_of(rel)):
                        return None
                return per_rel

            # A quarter of the budget, never more than 8: test-stated contracts are a *cheap*
            # first hypothesis, not the whole search. Spending the budget here starves the
            # later UIR/nexus passes and turns a repair into an exhaustion (`pyjwt@5fde08a`).
            spec_budget = min(8, max(2, max_candidates // 4))
            spec_spent = 0
            for guard_sel in spec_module.synthesize_spec_guards(
                root, cpg, test_sources, max_candidates=24, prioritize=tuple(initial_failed_nodes),
            ):
                if evaluated >= max_candidates or spec_spent >= spec_budget:
                    break
                spec_spent += 1
                g_tag, g_fn, g_fn_cpg, g_patched = guard_sel
                body_site = next((st for st in g_fn_cpg.sites if st.kind == "func_body"), None)
                if body_site is None:
                    continue
                guard_text = g_patched[body_site.start_byte:
                                       body_site.start_byte + (len(g_patched) - len(_raw_of(g_fn_cpg.rel_path)))]
                key = (g_fn_cpg.rel_path, g_fn)
                trial = {k: list(v) for k, v in active_guards.items()}
                trial.setdefault(key, []).append(guard_text.decode("utf-8", errors="replace"))
                saved = active_guards
                active_guards = trial
                overrides = _compose_guard_overrides()
                if overrides is None:
                    active_guards = saved
                    continue
                evaluated += 1
                ok_full, _, out_full = _run_suite_in_scratch(root, norm_test_cmd, overrides)
                if ok_full:
                    final_tag = "+".join([*active_tags, g_tag])
                    if skill_store is not None:
                        try:
                            skill_store.learn(
                                body_site.source_text,
                                "".join(active_guards[key]) + body_site.source_text,
                                origin=origin, diagnostic_class="SPEC_CONTRACT_GUARD",
                            )
                        except Exception:
                            pass
                    if apply_in_place:
                        for rel, raw in overrides.items():
                            (root / rel).write_bytes(raw)
                    return CausalRepairResult(
                        repaired=True,
                        status="VERIFIED__SPEC_CONTRACT_GUARD",
                        rel_path=g_fn_cpg.rel_path,
                        func_name=g_fn,
                        mechanism=final_tag,
                        patched_files={rel: raw.decode("utf-8") for rel, raw in overrides.items()},
                        causal_chain=[f"{g_fn_cpg.rel_path}:{g_fn}"],
                        candidates_evaluated=evaluated,
                        elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                        baseline_failure_excerpt=base_out[-400:],
                    )
                reg_nodes = _extract_pytest_failed_nodes(out_full)
                shrinks = 0 < len(reg_nodes) < len(cur_failed) and set(reg_nodes).issubset(cur_failed)
                if shrinks:
                    active_tags.append(g_tag)
                    cur_failed = set(reg_nodes)
                else:
                    active_guards = saved

        # 3.5 Causal Nexus pass — expected-value abduction + single-site counterfactual proof.
        #
        # The failing assertion publishes the value it wanted. Forcing that literal at one suspect
        # site in an isolated CoW clone is one executed counterfactual per (site, obligation) and
        # proves exactly which site owes the value, instead of ranking sites by suspicion.
        if nexus is not None and is_pytest and initial_failed_nodes:
            obls = nexus.extract_value_obligations(base_out)
            if obls:
                witnesses = nexus.angelic_nexus_blame(
                    root, sites, base_out, focused_cmd, obligations=obls, max_sites=8,
                )
                for w_idx, w in enumerate(witnesses):
                    support = sum(
                        1 for o in obls if repr(o.expected_value)[:200] == w.forced_value_repr[:200]
                    )
                    # Frame provenance is the expensive part, so it is computed for the proven
                    # nexus only. It is what lets a data-shaped value become a repair: the site
                    # must be shown to produce that value itself.
                    frame_exprs = (
                        nexus.derive_frame_expressions(root, w.site, focused_cmd) if w_idx == 0 else {}
                    )
                    for tag, cand_code, extra_imp in nexus.synthesize_nexus_repairs(
                        w.site, w, cpg=cpg, supporting_obligations=max(1, support),
                        frame_exprs=frame_exprs, prefer_names=tuple(cpg.functions)[:400],
                    ):
                        if evaluated >= max_candidates:
                            break
                        orig_b = _raw_of(w.site.rel_path)
                        patched_bytes = _apply_site_patch(orig_b, w.site, cand_code, extra_import=extra_imp)
                        if not _syntactically_valid(patched_bytes, w.site.language, orig_b):
                            continue
                        evaluated += 1
                        if _verify_candidate({w.site.rel_path: patched_bytes}):
                            if origin and skill_store is not None:
                                try:
                                    skill_store.learn(
                                        w.site.source_text, cand_code, origin=origin, diagnostic_class=tag,
                                    )
                                except Exception:
                                    pass
                            patched_str = patched_bytes.decode("utf-8")
                            if apply_in_place:
                                (root / w.site.rel_path).write_bytes(patched_bytes)
                            return CausalRepairResult(
                                repaired=True,
                                status="VERIFIED__ANGELIC_NEXUS_FALLBACK",
                                rel_path=w.site.rel_path,
                                func_name=w.site.func_name,
                                mechanism=f"{tag}|forced={w.forced_value_repr[:60]}",
                                patched_files={w.site.rel_path: patched_str},
                                causal_chain=list(w.site.causal_chain),
                                candidates_evaluated=evaluated,
                                elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                                baseline_failure_excerpt=base_out[-400:],
                            )
                if witnesses:
                    # A proven nexus is the only site worth expanding first: it alone closes every
                    # failing test, so the CEGIS budget below is spent there before anywhere else.
                    nexus_ids = {id(w.site) for w in witnesses}
                    sites = [w.site for w in witnesses] + [st for st in sites if id(st) not in nexus_ids]

        # 4. Pass 2 — First-Principles Z3 + Angelic Abduction + Repo-Native Petri Net + Compositional Multi-Site + Dual-Program Splicing
        batch_frames = (
            _capture_python_multi_site_frames(root, sites[:8], fast_targets[:6], max_frames_per_site=4, timeout_s=5.0)
            if (is_pytest and fast_targets)
            else {}
        )
        accum_hunks: dict[str, list[tuple[CausalSite, str, str]]] = {}
        accum_tags: list[str] = []
        cur_failed_set: set[str] = set(initial_failed_nodes)

        def _overlaps_accum(st: CausalSite) -> bool:
            for prev_s, _, _ in accum_hunks.get(st.rel_path, ()):
                if not (st.end_byte <= prev_s.start_byte or st.start_byte >= prev_s.end_byte):
                    return True
            return False

        def _build_merged_overrides(st: CausalSite, code_s: str, imp_s: str) -> dict[str, bytes] | None:
            merged: dict[str, bytes] = {}
            all_rels = set(accum_hunks.keys()) | {st.rel_path}
            for r_p in all_rels:
                hlist = list(accum_hunks.get(r_p, ()))
                if r_p == st.rel_path:
                    hlist.append((st, code_s, imp_s))
                hlist.sort(key=lambda item: -item[0].start_byte)
                cur_b = _raw_of(r_p)
                orig_r = cur_b
                for h_site, h_code, h_imp in hlist:
                    cur_b = _apply_site_patch(cur_b, h_site, h_code, extra_import=h_imp)
                if not _syntactically_valid(cur_b, st.language, orig_r):
                    return None
                merged[r_p] = cur_b
            return merged

        for idx, site in enumerate(sites):
            if evaluated >= max_candidates:
                break
            if _overlaps_accum(site):
                continue
            obligations = _harvest_python_angelic_obligations(root, site, focused_cmd, zygote=zygote) if (idx < 4 and not accum_hunks) else []
            site_frames = batch_frames.get((site.rel_path, int(site.start_line)), [])
            candidates = list(synthesize_cegis_uir_candidates(
                site,
                cpg,
                angelic_obligations=obligations,
                failure_diagnostic=base_out,
            )[:6])
            if site_frames:
                seen_cand_s = {c[1].strip() for c in candidates}
                for p_tag, p_code, p_imp in _propose_petri_net_morphisms(site, cpg, site_frames):
                    if p_code.strip() not in seen_cand_s:
                        seen_cand_s.add(p_code.strip())
                        candidates.append((p_tag, p_code, p_imp))
            if skill_store is not None:
                for morph, morph_src in skill_store.propose(site.source_text):
                    candidates.append((f"TREE_REWRITE_{morph.morphism_id[4:14]}", morph_src, ""))
            candidates = candidates[:12]

            for tag, cand_code, extra_imp in candidates:
                if evaluated >= max_candidates:
                    break
                if invariant_store is not None and nexus is not None:
                    # L3 negative space: a shape that already caused a regression is filtered in
                    # microseconds, before a clone, a compile, or a test run is paid for.
                    if invariant_store.refuted(site.kind, tag, nexus.candidate_features(site, cand_code)) is not None:
                        continue
                overrides = _build_merged_overrides(site, cand_code, extra_imp)
                if overrides is None:
                    continue
                evaluated += 1

                # Stage A: Fast failing-test screen (or multi-site strict-subset check when >=2 failing tests)
                can_check_subset = (
                    is_pytest
                    and len(cur_failed_set) >= 2
                    and idx < 10
                    and tag.startswith(("UIR_EXCEPT_", "UIR_STR_", "UIR_BOOL_", "REPO_PETRI_"))
                )
                if not accum_hunks and not can_check_subset:
                    if zygote is not None and zygote.available:
                        ok_fast = zygote.run_fast(overrides, timeout_s=1.2)
                    elif focused_cmd != norm_test_cmd:
                        ok_fast, _, _ = _run_suite_in_scratch(root, focused_cmd, overrides, timeout_s=6.0)
                    else:
                        ok_fast = True
                    if not ok_fast:
                        continue

                # Stage B: Full module/suite check
                ok_full, _, reg_out = _run_suite_in_scratch(root, norm_test_cmd, overrides)
                final_overrides = overrides
                final_tag = "+".join([*accum_tags, tag]) if accum_tags else tag
                final_status = (
                    "VERIFIED__MULTI_SITE_COMPOSITIONAL_CEGIS" if accum_tags else "VERIFIED__FIRST_PRINCIPLES_CEGIS"
                )
                if not ok_full and is_pytest:
                    reg_nodes = _extract_pytest_failed_nodes(reg_out)
                    new_failed_set = set(reg_nodes)
                    # Check monotonic strict Pareto subset progress (`0 < |F_new| < |F_cur|` and `F_new ⊂ F_cur`, zero regressions!)
                    if (
                        len(cur_failed_set) >= 2
                        and 0 < len(new_failed_set) < len(cur_failed_set)
                        and new_failed_set.issubset(cur_failed_set)
                        and "ERROR " not in reg_out
                    ):
                        accum_hunks.setdefault(site.rel_path, []).append((site, cand_code, extra_imp))
                        accum_tags.append(tag)
                        cur_failed_set = new_failed_set
                        break
                    if not accum_hunks and site_frames and reg_nodes:
                        orig_b = _raw_of(site.rel_path)
                        spliced = _attempt_dual_program_splice(
                            root, site, tag, cand_code, extra_imp, orig_b, site_frames, reg_nodes, norm_test_cmd,
                        )
                        if spliced is not None:
                            spliced_b, final_tag = spliced
                            final_overrides = {site.rel_path: spliced_b}
                            final_status = "VERIFIED__DUAL_PROGRAM_SPLICE"
                            ok_full = True
                    if not ok_full and not accum_hunks and invariant_store is not None and nexus is not None:
                        invariant_store.record(
                            site.kind,
                            tag,
                            nexus.candidate_features(site, cand_code),
                            ",".join(sorted(reg_nodes))[:240],
                            origin=origin,
                        )

                if ok_full:
                    admitted_id: str | None = None
                    if admit_learned_law and not extra_imp and final_status == "VERIFIED__FIRST_PRINCIPLES_CEGIS":
                        law = store.admit_from_verified_pair(
                            site.source_text,
                            cand_code,
                            site.language,
                            diagnostic_class=tag,
                            c_params=site.c_params,
                            as_condition=(site.kind == "guard"),
                        )
                        if law is not None:
                            admitted_id = law.law_id
                    if skill_store is not None and site.kind == "func_body" and not extra_imp:
                        # Statement-level crystallization: the 2026-11-24 ablation's own gap
                        # (`learned_skill_id=None` on multi-statement fixes) closes here.
                        try:
                            skill_store.learn(
                                site.source_text, cand_code, origin=origin, diagnostic_class=final_tag,
                            )
                        except Exception:
                            pass
                    patched_str_map = {rp: b.decode("utf-8") for rp, b in final_overrides.items()}
                    if apply_in_place:
                        for rp, b in final_overrides.items():
                            (root / rp).write_bytes(b)
                    return CausalRepairResult(
                        repaired=True,
                        status=final_status,
                        rel_path=site.rel_path,
                        func_name=site.func_name,
                        mechanism=final_tag,
                        patched_files=patched_str_map,
                        causal_chain=list(site.causal_chain),
                        admitted_law_id=admitted_id,
                        candidates_evaluated=evaluated,
                        elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                        baseline_failure_excerpt=base_out[-400:],
                    )

        # 3.9 Last-resort: frame-bound exception containment.
        #
        # Every earlier pass is done, so this cannot displace a repair that already worked: it only
        # touches commits that were about to be reported OPEN. The failure text names the exact
        # `file:line` frames, and containing an escaping exception at those statements is a contract
        # the project's own tests publish (`"KeyboardInterrupt escaped Command.main()"`). Greedy and
        # Pareto: a containment is kept only if the failing set strictly shrinks, and the run stops
        # the moment the suite is green.
        if spec_module is not None:
            # An elicitation attempt (re-run each failing node with --tb=long) was measured here and
            # changed nothing on click@fc518e4: even a long traceback does not show the raise site,
            # because the interrupt is raised inside the test's own `sys.exit` replacement. Removed
            # rather than kept as dead runtime (round V7 of the report).
            try:
                frames = spec_module.mine_escape_frames(base_out, root)
            except Exception:
                frames = []
            contain_accepted: list[Any] = []
            contain_spent = 0
            while frames and contain_spent < 8:
                best: tuple[int, Any, dict[str, bytes]] | None = None
                for frame in frames:
                    if frame in contain_accepted:
                        continue
                    if contain_spent >= 8 or evaluated >= max_candidates + 8:
                        break
                    trial = [*contain_accepted, frame]
                    try:
                        overrides = spec_module.compose_frame_containments(root, trial)
                    except Exception:
                        continue
                    if overrides is None:
                        continue
                    contain_spent += 1
                    evaluated += 1
                    ok_full, _, out_full = _run_suite_in_scratch(root, norm_test_cmd, overrides)
                    if ok_full:
                        if apply_in_place:
                            for rel, raw in overrides.items():
                                (root / rel).write_bytes(raw)
                        tag = "FRAME_CONTAINMENT[" + "+".join(
                            f"{f.rel_path}:{f.lineno}" for f in trial) + "]"
                        return CausalRepairResult(
                            repaired=True,
                            status="VERIFIED__EXCEPTION_CONTAINMENT",
                            rel_path=trial[-1].rel_path,
                            func_name="",
                            mechanism=tag,
                            patched_files={rel: raw.decode("utf-8") for rel, raw in overrides.items()},
                            causal_chain=[f"{f.rel_path}:{f.lineno}" for f in trial],
                            candidates_evaluated=evaluated,
                            elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
                            baseline_failure_excerpt=base_out[-400:],
                        )
                    nodes = _extract_pytest_failed_nodes(out_full)
                    if nodes and set(nodes).issubset(cur_failed) and len(nodes) < len(cur_failed):
                        if best is None or len(nodes) < best[0]:
                            best = (len(nodes), frame, overrides)
                if best is None:
                    break
                contain_accepted.append(best[1])
                cur_failed = set(_extract_pytest_failed_nodes(
                    _run_suite_in_scratch(root, norm_test_cmd, best[2])[2]))
                frames = [f for f in frames if f not in contain_accepted]

        return CausalRepairResult(
            repaired=False,
            status="OPEN__CEGIS_EXHAUSTED_WITHOUT_VERIFIED_FIX",
            candidates_evaluated=evaluated,
            elapsed_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
            baseline_failure_excerpt=base_out[-500:],
        )
    finally:
        if zygote is not None:
            zygote.close()
